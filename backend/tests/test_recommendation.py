import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from backend.services.recommendation import (
    ChargeSlot,
    DeadlineUnreachableError,
    InsufficientDataError,
    NoChargingNeeded,
    RecommendationResult,
    VehicleSpec,
    find_best_window,
    future_slots,
    join_price_and_carbon,
    parse_carbon_slots,
    parse_price_slots,
)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

TEST_VEHICLE = VehicleSpec(
    name="Test EV", battery_capacity_kwh=57.5, ac_charge_rate_kw=11.0
)


def _load_fixture(name: str) -> dict:
    with open(os.path.join(FIXTURES_DIR, name)) as f:
        return json.load(f)


def _load_slots() -> list:
    prices = parse_price_slots(_load_fixture("octopus_agile.json"))
    carbons = parse_carbon_slots(_load_fixture("carbon_intensity_forecast.json"))
    return join_price_and_carbon(prices, carbons)


def test_parse_price_slots_sorts_ascending_and_converts_pence_to_gbp():
    raw = _load_fixture("octopus_agile.json")
    slots = parse_price_slots(raw)

    assert len(slots) == raw["count"]
    assert all(a.start < b.start for a, b in zip(slots, slots[1:]))
    first_result = raw["results"][0]
    matching = next(s for s in slots if s.start.isoformat() == first_result["valid_from"].replace("Z", "+00:00"))
    assert matching.price_gbp_per_kwh == first_result["value_inc_vat"] / 100


def test_parse_carbon_slots_prefers_actual_over_forecast():
    raw = _load_fixture("carbon_intensity_forecast.json")
    slots = parse_carbon_slots(raw)

    assert all(a.start < b.start for a, b in zip(slots, slots[1:]))

    past_entry = next(e for e in raw["data"] if e["intensity"]["actual"] is not None)
    future_entry = next(e for e in raw["data"] if e["intensity"]["actual"] is None)

    past_slot = next(s for s in slots if s.start == datetime.fromisoformat(past_entry["from"].replace("Z", "+00:00")))
    future_slot = next(s for s in slots if s.start == datetime.fromisoformat(future_entry["from"].replace("Z", "+00:00")))

    assert past_slot.intensity_gco2_per_kwh == past_entry["intensity"]["actual"]
    assert future_slot.intensity_gco2_per_kwh == future_entry["intensity"]["forecast"]


def test_join_keeps_every_price_slot_even_without_carbon_match():
    price_slots = parse_price_slots(_load_fixture("octopus_agile.json"))
    carbon_slots = parse_carbon_slots(_load_fixture("carbon_intensity_forecast.json"))

    joined = join_price_and_carbon(price_slots, carbon_slots)

    assert len(joined) == len(price_slots)
    assert any(slot.carbon_gco2_per_kwh is not None for slot in joined)


def test_future_slots_drops_ended_slots():
    price_slots = parse_price_slots(_load_fixture("octopus_agile.json"))
    carbon_slots = parse_carbon_slots(_load_fixture("carbon_intensity_forecast.json"))
    joined = join_price_and_carbon(price_slots, carbon_slots)

    cutoff = joined[len(joined) // 2].end
    remaining = future_slots(joined, now=cutoff)

    assert all(slot.end > cutoff for slot in remaining)
    assert len(remaining) < len(joined)


def test_find_best_window_no_charging_needed():
    slots = _load_slots()
    result = find_best_window(
        slots, TEST_VEHICLE, current_pct=80, target_pct=50, optimize_for="cost"
    )
    assert isinstance(result, NoChargingNeeded)


def test_find_best_window_raises_when_not_enough_slots():
    slots = _load_slots()
    tiny_charge_rate_vehicle = VehicleSpec(
        name="Slow charger", battery_capacity_kwh=57.5, ac_charge_rate_kw=0.5
    )
    with pytest.raises(InsufficientDataError):
        find_best_window(
            slots,
            tiny_charge_rate_vehicle,
            current_pct=0,
            target_pct=100,
            optimize_for="cost",
        )


def test_find_best_window_cost_mode_matches_brute_force_minimum():
    slots = _load_slots()
    result = find_best_window(
        slots, TEST_VEHICLE, current_pct=20, target_pct=80, optimize_for="cost"
    )
    assert isinstance(result, RecommendationResult)

    kwh_per_slot = TEST_VEHICLE.ac_charge_rate_kw * 0.5
    slots_needed = -(-result.kwh_needed // kwh_per_slot)  # ceil division
    slots_needed = int(slots_needed)

    # Independently brute-force every contiguous window's cost and confirm
    # find_best_window actually returned the cheapest one, not just *a* one.
    all_window_costs = [
        sum(s.price_gbp_per_kwh * kwh_per_slot for s in slots[i : i + slots_needed])
        for i in range(len(slots) - slots_needed + 1)
    ]
    assert result.total_cost_gbp == min(all_window_costs)


def test_find_best_window_carbon_mode_matches_brute_force_minimum():
    slots = _load_slots()
    result = find_best_window(
        slots, TEST_VEHICLE, current_pct=20, target_pct=80, optimize_for="carbon"
    )
    assert isinstance(result, RecommendationResult)

    kwh_per_slot = TEST_VEHICLE.ac_charge_rate_kw * 0.5
    slots_needed = int(-(-result.kwh_needed // kwh_per_slot))

    all_window_averages = []
    for i in range(len(slots) - slots_needed + 1):
        window = slots[i : i + slots_needed]
        if all(s.carbon_gco2_per_kwh is not None for s in window):
            all_window_averages.append(
                sum(s.carbon_gco2_per_kwh for s in window) / len(window)
            )
    assert result.average_carbon_gco2_per_kwh == min(all_window_averages)


def _slot(start_iso: str, hours: float, price: float) -> ChargeSlot:
    start = datetime.fromisoformat(start_iso)
    return ChargeSlot(
        start=start,
        end=start + timedelta(hours=hours),
        price_gbp_per_kwh=price,
        carbon_gco2_per_kwh=100.0,
    )


def test_find_best_window_respects_charge_by_deadline():
    slots = _load_slots()
    # Pick a deadline that only the first few slots can meet, forcing the
    # winner to be earlier (and likely pricier) than the true global optimum.
    deadline = slots[3].end

    result = find_best_window(
        slots,
        TEST_VEHICLE,
        current_pct=20,
        target_pct=30,  # small charge so a short window fits before the deadline
        optimize_for="cost",
        charge_by=deadline,
    )

    assert isinstance(result, RecommendationResult)
    assert result.end <= deadline


def test_find_best_window_raises_when_deadline_unreachable():
    slots = _load_slots()
    impossible_deadline = slots[0].start  # before any window can even start

    with pytest.raises(DeadlineUnreachableError):
        find_best_window(
            slots,
            TEST_VEHICLE,
            current_pct=20,
            target_pct=80,
            optimize_for="cost",
            charge_by=impossible_deadline,
        )


def test_find_best_window_never_spans_a_gap_between_runs():
    # Two genuinely contiguous slots, a missing half-hour, then two more.
    # A naive index-based slide would treat slots[1] and slots[2] as
    # adjacent (they aren't - there's a 30 min gap between 01:00 and
    # 01:30) and could wrongly pick a window spanning the gap.
    slots = [
        _slot("2026-01-01T00:00:00+00:00", 0.5, price=10.0),
        _slot("2026-01-01T00:30:00+00:00", 0.5, price=10.0),
        _slot("2026-01-01T01:30:00+00:00", 0.5, price=1.0),
        _slot("2026-01-01T02:00:00+00:00", 0.5, price=1.0),
    ]
    result = find_best_window(
        slots, TEST_VEHICLE, current_pct=20, target_pct=30, optimize_for="cost"
    )

    assert isinstance(result, RecommendationResult)
    # The cheapest genuinely-contiguous 2-slot window is slots[2:4]
    # (price 1.0 + 1.0), not a gap-spanning slots[1:3] (price 10.0 + 1.0)
    # which a broken implementation could have picked.
    assert result.start == slots[2].start
    assert result.end == slots[3].end

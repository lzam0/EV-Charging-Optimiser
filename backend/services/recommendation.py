"""Core recommendation logic: given price data, carbon data, and a vehicle
spec, find the best charging window. Pure functions, no I/O - see
.claude/roadmap/3.md for the full plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import ceil
from typing import Literal

SLOT_HOURS = 0.5


@dataclass(frozen=True)
class PriceSlot:
    start: datetime
    end: datetime
    price_gbp_per_kwh: float


@dataclass(frozen=True)
class CarbonSlot:
    start: datetime
    end: datetime
    intensity_gco2_per_kwh: float


@dataclass(frozen=True)
class ChargeSlot:
    """A half-hour slot with price and (if available) carbon data joined,
    ready for windowing."""

    start: datetime
    end: datetime
    price_gbp_per_kwh: float
    carbon_gco2_per_kwh: float | None


def serialize_slots(slots: list[ChargeSlot]) -> list[dict[str, object]]:
    """Shape ChargeSlots for JSON. ISO-8601 timestamps; carbon may be None."""
    return [
        {
            "start": s.start.isoformat(),
            "end": s.end.isoformat(),
            "price_gbp_per_kwh": s.price_gbp_per_kwh,
            "carbon_gco2_per_kwh": s.carbon_gco2_per_kwh,
        }
        for s in slots
    ]


@dataclass(frozen=True)
class VehicleSpec:
    name: str
    battery_capacity_kwh: float
    ac_charge_rate_kw: float
    make: str
    range_km: float
    charge_port: str
    dc_charge_rate_kw: float | None


def _parse_timestamp(value: str) -> datetime:
    # Both APIs return "Z"-suffixed ISO 8601, which fromisoformat only
    # accepts as "+00:00" (pre-3.11 behaviour; kept explicit either way).
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_price_slots(raw_octopus_response: dict) -> list[PriceSlot]:
    """Parse Octopus Agile standard-unit-rates JSON into ascending
    PriceSlots. Prices arrive in pence inc. VAT; converted to GBP here so
    downstream cost math doesn't need to remember the unit. The API
    returns results newest-first, so this always re-sorts rather than
    trusting response order.
    """
    slots = [
        PriceSlot(
            start=_parse_timestamp(r["valid_from"]),
            end=_parse_timestamp(r["valid_to"]),
            price_gbp_per_kwh=r["value_inc_vat"] / 100,
        )
        for r in raw_octopus_response["results"]
    ]
    return sorted(slots, key=lambda s: s.start)


def parse_carbon_slots(raw_carbon_forecast_response: dict) -> list[CarbonSlot]:
    """Parse Carbon Intensity forecast JSON (the `fw48h` series, not the
    single-slot `/intensity` response) into ascending CarbonSlots. Uses the
    actual measured value when available (past slots), falling back to
    forecast for future slots where `actual` is null.
    """
    slots = []
    for entry in raw_carbon_forecast_response["data"]:
        intensity = entry["intensity"]
        value = (
            intensity["actual"]
            if intensity["actual"] is not None
            else intensity["forecast"]
        )
        slots.append(
            CarbonSlot(
                start=_parse_timestamp(entry["from"]),
                end=_parse_timestamp(entry["to"]),
                intensity_gco2_per_kwh=value,
            )
        )
    return sorted(slots, key=lambda s: s.start)


def join_price_and_carbon(
    price_slots: list[PriceSlot], carbon_slots: list[CarbonSlot]
) -> list[ChargeSlot]:
    """Join price and carbon series on their time window (matched by slot
    start, not list position - the two series are fetched independently and
    aren't guaranteed to align by index).

    Price slots are the backbone: Octopus Agile is the tariff the user
    actually pays, so every price slot is kept even if no carbon data
    matches it (carbon_gco2_per_kwh is None in that case). A carbon slot
    with no matching price slot is simply dropped.
    """
    carbon_by_start = {c.start: c for c in carbon_slots}
    return [
        ChargeSlot(
            start=p.start,
            end=p.end,
            price_gbp_per_kwh=p.price_gbp_per_kwh,
            carbon_gco2_per_kwh=(
                carbon_by_start[p.start].intensity_gco2_per_kwh
                if p.start in carbon_by_start
                else None
            ),
        )
        for p in price_slots
    ]


def future_slots(
    slots: list[ChargeSlot], now: datetime | None = None
) -> list[ChargeSlot]:
    """Drop any slot that has already ended, relative to `now` (UTC)."""
    now = now or datetime.now(timezone.utc)
    return [s for s in slots if s.end > now]


class InsufficientDataError(Exception):
    """Raised when there isn't enough contiguous future slot data to find a
    valid window at all - either no unbroken stretch is long enough, or
    (when optimizing for carbon) no contiguous stretch has complete carbon
    coverage. Distinct from DeadlineUnreachableError below: this means we
    don't have enough usable data, not that we have it but not before the
    user's deadline."""


class DeadlineUnreachableError(Exception):
    """Raised when enough contiguous data exists to complete the charge,
    but not before the given charge_by deadline."""


@dataclass(frozen=True)
class NoChargingNeeded:
    """Returned instead of a window when current_pct already meets or
    exceeds target_pct - a distinct type rather than None, so callers can't
    mistake "nothing to charge" for a bug that silently returned nothing."""


@dataclass(frozen=True)
class RecommendationResult:
    start: datetime
    end: datetime
    total_cost_gbp: float
    average_carbon_gco2_per_kwh: float | None
    kwh_needed: float


def _split_into_contiguous_runs(
    slots: list[ChargeSlot],
) -> list[list[ChargeSlot]]:
    """Split `slots` (assumed sorted ascending) into runs where each slot's
    `end` exactly matches the next slot's `start`. A gap - e.g. one missing
    half-hour from a failed pipeline fetch - starts a new run, so a window
    search never treats two non-adjacent times as back-to-back."""
    if not slots:
        return []
    runs = [[slots[0]]]
    for prev, curr in zip(slots, slots[1:]):
        if curr.start == prev.end:
            runs[-1].append(curr)
        else:
            runs.append([curr])
    return runs


def _score_window(
    window: list[ChargeSlot],
    kwh_per_slot: float,
    optimize_for: Literal["cost", "carbon"],
) -> float | None:
    """Return None when the window can't be scored at all (only possible
    for carbon mode, when a slot in the window has no carbon data)."""
    if optimize_for == "cost":
        return sum(s.price_gbp_per_kwh * kwh_per_slot for s in window)

    carbon_values = [
        s.carbon_gco2_per_kwh for s in window if s.carbon_gco2_per_kwh is not None
    ]
    if len(carbon_values) < len(window):
        return None
    return sum(carbon_values) / len(carbon_values)


def find_best_window(
    slots: list[ChargeSlot],
    vehicle: VehicleSpec,
    current_pct: float,
    target_pct: float,
    optimize_for: Literal["cost", "carbon"],
    charge_by: datetime | None = None,
) -> RecommendationResult | NoChargingNeeded:
    """Find the cheapest (or greenest) contiguous block of slots that
    delivers enough energy to go from current_pct to target_pct, optionally
    finishing by `charge_by`.

    `slots` should be sorted ascending (i.e. the output of
    future_slots(join_price_and_carbon(...))) but does not need to be
    gap-free - candidate windows are only built from genuinely contiguous
    runs of slots (see _split_into_contiguous_runs), so a missing slot
    simply excludes windows that would have spanned it rather than
    corrupting the result.
    """
    if current_pct >= target_pct:
        return NoChargingNeeded()

    kwh_needed = vehicle.battery_capacity_kwh * (target_pct - current_pct) / 100
    kwh_per_slot = vehicle.ac_charge_rate_kw * SLOT_HOURS
    slots_needed = ceil(kwh_needed / kwh_per_slot)

    runs = _split_into_contiguous_runs(slots)
    candidate_windows = [
        run[start_index : start_index + slots_needed]
        for run in runs
        if len(run) >= slots_needed
        for start_index in range(len(run) - slots_needed + 1)
    ]

    if not candidate_windows:
        raise InsufficientDataError(
            f"charging needs {slots_needed} contiguous half-hour slots but "
            f"no unbroken stretch of that length is available in the "
            f"fetched data"
        )

    deadline_windows = candidate_windows
    if charge_by is not None:
        deadline_windows = [w for w in candidate_windows if w[-1].end <= charge_by]
        if not deadline_windows:
            earliest_possible_end = min(w[-1].end for w in candidate_windows)
            raise DeadlineUnreachableError(
                f"can't fully charge by {charge_by.isoformat()} - the "
                f"earliest this charge can finish is "
                f"{earliest_possible_end.isoformat()}"
            )

    best_window: list[ChargeSlot] | None = None
    best_score: float | None = None

    for window in deadline_windows:
        score = _score_window(window, kwh_per_slot, optimize_for)
        if score is None:
            continue
        if best_score is None or score < best_score:
            best_score = score
            best_window = window

    if best_window is None:
        raise InsufficientDataError(
            "no contiguous window had complete carbon data to optimize against"
        )

    total_cost = sum(s.price_gbp_per_kwh * kwh_per_slot for s in best_window)
    carbon_values = [
        s.carbon_gco2_per_kwh for s in best_window if s.carbon_gco2_per_kwh is not None
    ]
    average_carbon = sum(carbon_values) / len(carbon_values) if carbon_values else None

    return RecommendationResult(
        start=best_window[0].start,
        end=best_window[-1].end,
        total_cost_gbp=total_cost,
        average_carbon_gco2_per_kwh=average_carbon,
        kwh_needed=kwh_needed,
    )

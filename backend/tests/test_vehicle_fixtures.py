import json

from backend.services.recommendation import VehicleSpec
from backend.services.vehicle_fixtures import FIXTURES_PATH, VEHICLE_FIXTURES


def test_vehicle_fixtures_is_non_empty():
    assert len(VEHICLE_FIXTURES) > 0


def test_vehicle_fixtures_has_a_realistic_floor():
    # Catches a future regeneration that silently produces a near-empty
    # file (e.g. a filter bug or an upstream schema change) before it ships.
    assert len(VEHICLE_FIXTURES) > 100


def test_every_fixture_is_a_valid_vehicle_spec():
    for vehicle_id, spec in VEHICLE_FIXTURES.items():
        assert vehicle_id, "vehicle id must not be empty"
        assert isinstance(spec, VehicleSpec)
        assert spec.name.strip() != ""
        assert spec.make.strip() != ""
        assert spec.battery_capacity_kwh > 0
        assert spec.ac_charge_rate_kw > 0
        assert spec.range_km > 0
        assert spec.charge_port.strip() != ""
        assert spec.dc_charge_rate_kw is None or spec.dc_charge_rate_kw > 0


def test_committed_fixtures_file_matches_expected_shape():
    raw_entries = json.loads(FIXTURES_PATH.read_text())
    assert isinstance(raw_entries, list)
    assert len(raw_entries) == len(VEHICLE_FIXTURES)

    ids = [entry["id"] for entry in raw_entries]
    assert len(ids) == len(set(ids)), "vehicle ids must be unique"

    for entry in raw_entries:
        assert isinstance(entry["id"], str) and entry["id"]
        assert isinstance(entry["name"], str) and entry["name"]
        assert isinstance(entry["make"], str) and entry["make"]
        assert isinstance(entry["battery_capacity_kwh"], (int, float))
        assert entry["battery_capacity_kwh"] > 0
        assert isinstance(entry["ac_charge_rate_kw"], (int, float))
        assert entry["ac_charge_rate_kw"] > 0
        assert isinstance(entry["range_km"], (int, float))
        assert entry["range_km"] > 0
        assert isinstance(entry["charge_port"], str) and entry["charge_port"]
        assert entry["dc_charge_rate_kw"] is None or (
            isinstance(entry["dc_charge_rate_kw"], (int, float))
            and entry["dc_charge_rate_kw"] > 0
        )

"""Stand-in for the real `vehicles` table (Phase 2). Loads real EV specs
from the open-ev-data dataset (see backend/scripts/generate_ev_fixtures.py)
from a committed static JSON file - no network call here, no database.
Replace with the seeded database table once Phase 2 exists.
"""

import json
from pathlib import Path

from backend.services.recommendation import VehicleSpec

FIXTURES_PATH = Path(__file__).resolve().parent.parent / "data" / "ev_fixtures.json"

_raw_fixtures = json.loads(FIXTURES_PATH.read_text())

VEHICLE_FIXTURES: dict[str, VehicleSpec] = {
    entry["id"]: VehicleSpec(
        name=entry["name"],
        battery_capacity_kwh=entry["battery_capacity_kwh"],
        ac_charge_rate_kw=entry["ac_charge_rate_kw"],
        make=entry["make"],
        range_km=entry["range_km"],
        charge_port=entry["charge_port"],
        dc_charge_rate_kw=entry["dc_charge_rate_kw"],
    )
    for entry in _raw_fixtures
}

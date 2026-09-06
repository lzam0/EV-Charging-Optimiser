"""One-off, manually-run script that downloads a pinned release of the
open-ev-data dataset (github.com/open-ev-data/open-ev-data-dataset,
CDLA-Permissive-2.0 licensed) and writes a filtered, flattened subset to
`backend/data/ev_fixtures.json`, which `backend/services/vehicle_fixtures.py`
loads at import time.

This is NOT part of the running app - it is never imported by the FastAPI
app, and the app never makes a network call for vehicle specs (see root
CLAUDE.md: "EV specs are hardcoded fixtures... NEVER fetch them at runtime
from an external source"). This is a single download of a versioned release
asset, not a crawl - a prior attempt to scrape ev-database.org page-by-page
was blocked by that site's anti-bot protection, which is why this dataset is
used instead.

Re-run it, review the diff to backend/data/ev_fixtures.json, and commit it:

    backend/venv/bin/python3 -m backend.scripts.generate_ev_fixtures

To pick up a newer dataset release later, bump RELEASE_TAG below (check
https://github.com/open-ev-data/open-ev-data-dataset/releases for available
tags) and re-run. The tag is pinned rather than always fetching "latest" so
regeneration is reproducible until that's a deliberate choice.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

RELEASE_TAG = "v1.24.0"
DATASET_URL = (
    "https://github.com/open-ev-data/open-ev-data-dataset/releases/download/"
    f"{RELEASE_TAG}/open-ev-data-{RELEASE_TAG}.json"
)
REQUEST_TIMEOUT_SECONDS = 30
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "ev_fixtures.json"


CONNECTOR_DISPLAY_NAMES = {
    "type1": "Type 1",
    "type2": "Type 2",
    "ccs1": "CCS1",
    "ccs2": "CCS2",
    "nacs": "NACS",
    "chademo": "CHAdeMO",
    "gb_t_dc": "GB/T",
}


@dataclass
class FixtureVehicle:
    id: str
    name: str
    make: str
    battery_capacity_kwh: float
    ac_charge_rate_kw: float
    range_km: float
    charge_port: str
    dc_charge_rate_kw: float | None


def fetch_dataset() -> dict[str, Any]:
    response = requests.get(DATASET_URL, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    return data


def _slugify_unique_code(unique_code: str) -> str:
    return unique_code.replace(":", "_").replace("-", "_")


def _vehicle_name(vehicle: dict[str, Any]) -> str:
    make = vehicle["make"]["name"]
    model = vehicle["model"]["name"]
    trim = vehicle.get("trim", {}).get("name")
    variant = vehicle.get("variant", {}).get("name")
    year = vehicle.get("year")

    name = f"{make} {model}"
    if trim and trim.lower() != "base":
        name = f"{name} {trim}"
    # A variant (e.g. a battery-upgrade or body-style option, like "62 kWh"
    # or "Sportback") often carries the distinguishing detail trim doesn't -
    # two otherwise-identical trims can differ only by variant, so without
    # this two different battery capacities can render as the same name.
    if variant and variant != trim:
        name = f"{name} {variant}"
    if year:
        name = f"{name} ({year})"
    return name


def _battery_capacity_kwh(vehicle: dict[str, Any]) -> float | None:
    battery = vehicle.get("battery", {})
    net = battery.get("pack_capacity_kwh_net")
    if net is not None:
        return float(net)
    gross = battery.get("pack_capacity_kwh_gross")
    return float(gross) if gross is not None else None


def _ac_charge_rate_kw(vehicle: dict[str, Any]) -> float | None:
    ac = vehicle.get("charging", {}).get("ac", {})
    max_power = ac.get("max_power_kw")
    return float(max_power) if max_power is not None else None


def _dc_charge_rate_kw(vehicle: dict[str, Any]) -> float | None:
    dc = vehicle.get("charging", {}).get("dc", {})
    max_power = dc.get("max_power_kw")
    return float(max_power) if max_power is not None else None


def _range_km(vehicle: dict[str, Any]) -> float | None:
    rated = vehicle.get("range", {}).get("rated") or []
    if not rated:
        return None
    # WLTP is the standard UK/EU rating; prefer it, but fall back to
    # whatever cycle is available (e.g. EPA/CLTC) rather than dropping an
    # otherwise-valid GB-market vehicle over a rating-cycle gap.
    wltp = next((r for r in rated if r.get("cycle") == "wltp"), None)
    entry = wltp or rated[0]
    range_km = entry.get("range_km")
    return float(range_km) if range_km is not None else None


def _charge_port(vehicle: dict[str, Any]) -> str | None:
    ports = vehicle.get("charge_ports") or []
    if not ports:
        return None
    names = []
    for port in ports:
        connector = port.get("connector")
        display = CONNECTOR_DISPLAY_NAMES.get(connector, connector)
        if display and display not in names:
            names.append(display)
    return " / ".join(names) if names else None


def is_gb_production(vehicle: dict[str, Any]) -> bool:
    markets = vehicle.get("markets") or []
    status = vehicle.get("availability", {}).get("status")
    return "GB" in markets and status == "production"


def build_fixtures(dataset: dict[str, Any]) -> list[FixtureVehicle]:
    vehicles = dataset["vehicles"]
    print(f"Dataset {RELEASE_TAG}: {len(vehicles)} vehicles total.")

    candidates = [v for v in vehicles if is_gb_production(v)]
    print(f"{len(candidates)} are GB-market and currently in production.")

    fixtures_by_id: dict[str, FixtureVehicle] = {}
    skipped_missing_data = 0

    for vehicle in candidates:
        battery_capacity_kwh = _battery_capacity_kwh(vehicle)
        ac_charge_rate_kw = _ac_charge_rate_kw(vehicle)
        range_km = _range_km(vehicle)
        charge_port = _charge_port(vehicle)
        if (
            battery_capacity_kwh is None
            or ac_charge_rate_kw is None
            or range_km is None
            or charge_port is None
        ):
            skipped_missing_data += 1
            continue

        vehicle_id = _slugify_unique_code(vehicle["unique_code"])
        fixtures_by_id[vehicle_id] = FixtureVehicle(
            id=vehicle_id,
            name=_vehicle_name(vehicle),
            make=vehicle["make"]["name"],
            battery_capacity_kwh=battery_capacity_kwh,
            ac_charge_rate_kw=ac_charge_rate_kw,
            range_km=range_km,
            charge_port=charge_port,
            dc_charge_rate_kw=_dc_charge_rate_kw(vehicle),
        )

    print(
        f"Built {len(fixtures_by_id)} fixtures "
        f"(skipped {skipped_missing_data} missing battery/charging/range data)."
    )
    return sorted(fixtures_by_id.values(), key=lambda v: v.id)


def main() -> None:
    dataset = fetch_dataset()
    fixtures = build_fixtures(dataset)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(
            [
                {
                    "id": v.id,
                    "name": v.name,
                    "make": v.make,
                    "battery_capacity_kwh": v.battery_capacity_kwh,
                    "ac_charge_rate_kw": v.ac_charge_rate_kw,
                    "range_km": v.range_km,
                    "charge_port": v.charge_port,
                    "dc_charge_rate_kw": v.dc_charge_rate_kw,
                }
                for v in fixtures
            ],
            indent=2,
        )
        + "\n"
    )
    print(f"Wrote {len(fixtures)} vehicles to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

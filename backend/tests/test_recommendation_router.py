"""Router-level shape tests for the `slots` key on POST /recommendation.

`backend.routers.recommendation` transitively imports `pipeline.ingest.handler`,
which needs `boto3`. That package is absent from `backend/venv`, so this module
skips cleanly there rather than failing collection. The real gate for the
serialisation logic is `test_serialize_slots_*` in `test_recommendation.py`,
which has no such dependency.
"""

import pytest

pytest.importorskip("boto3")

from datetime import datetime, timedelta, timezone  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.routers import recommendation as router_module  # noqa: E402
from backend.services.vehicle_fixtures import VEHICLE_FIXTURES  # noqa: E402

SLOT_COUNT = 48
# Any real fixture id works here - the test only checks response shape, not
# specific vehicle values - so this picks whichever id happens to be first
# rather than hardcoding one that a future fixture regeneration could remove.
VEHICLE_ID = next(iter(VEHICLE_FIXTURES))


def _slot_windows() -> list[tuple[datetime, datetime]]:
    # Anchor on the next whole half-hour so every generated slot is in the
    # future and survives future_slots().
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    anchor = now.replace(minute=0) + timedelta(minutes=60 if now.minute >= 30 else 30)
    return [
        (anchor + timedelta(minutes=30 * i), anchor + timedelta(minutes=30 * (i + 1)))
        for i in range(SLOT_COUNT)
    ]


def _octopus_response() -> dict:
    return {
        "count": SLOT_COUNT,
        "results": [
            {
                "valid_from": start.isoformat().replace("+00:00", "Z"),
                "valid_to": end.isoformat().replace("+00:00", "Z"),
                "value_inc_vat": 10.0 + i,
            }
            for i, (start, end) in enumerate(_slot_windows())
        ],
    }


def _carbon_response() -> dict:
    return {
        "data": [
            {
                "from": start.isoformat().replace("+00:00", "Z"),
                "to": end.isoformat().replace("+00:00", "Z"),
                "intensity": {"actual": None, "forecast": 100 + i},
            }
            for i, (start, end) in enumerate(_slot_windows())
        ]
    }


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        router_module, "fetch_octopus_prices", lambda: _octopus_response()
    )
    monkeypatch.setattr(
        router_module, "fetch_carbon_forecast", lambda: _carbon_response()
    )
    app = FastAPI()
    app.include_router(router_module.router)
    return TestClient(app)


def _body(client: TestClient, current_pct: float, target_pct: float) -> dict:
    response = client.post(
        "/recommendation",
        json={
            "vehicle_id": VEHICLE_ID,
            "current_pct": current_pct,
            "target_pct": target_pct,
            "optimize_for": "cost",
            "charge_by": None,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_recommendation_response_includes_slots(client: TestClient):
    body = _body(client, current_pct=20, target_pct=80)

    assert body["status"] == "recommendation"
    assert isinstance(body["slots"], list)
    assert body["slots"]
    for entry in body["slots"]:
        assert set(entry) == {
            "start",
            "end",
            "price_gbp_per_kwh",
            "carbon_gco2_per_kwh",
        }
        datetime.fromisoformat(entry["start"])
        datetime.fromisoformat(entry["end"])


def test_no_charging_needed_response_has_no_slots(client: TestClient):
    body = _body(client, current_pct=80, target_pct=80)

    assert body["status"] == "no_charging_needed"
    assert "slots" not in body

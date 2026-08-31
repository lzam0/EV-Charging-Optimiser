"""GET /vehicles - exposes the vehicle fixtures (stand-in for Phase 2's
vehicles table) for the frontend's vehicle selector."""

from fastapi import APIRouter

from backend.services.vehicle_fixtures import VEHICLE_FIXTURES

router = APIRouter()


@router.get("/vehicles")
async def list_vehicles() -> dict[str, dict[str, object]]:
    return {
        vehicle_id: {
            "name": spec.name,
            "battery_capacity_kwh": spec.battery_capacity_kwh,
            "ac_charge_rate_kw": spec.ac_charge_rate_kw,
        }
        for vehicle_id, spec in VEHICLE_FIXTURES.items()
    }

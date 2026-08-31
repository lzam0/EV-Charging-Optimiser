"""POST /recommendation - fetches live carbon + price data and finds the
best charging window for a given vehicle. No Phase 2 database yet, so every
request re-fetches from the Carbon Intensity and Octopus Agile APIs rather
than reading from a store (see .claude/roadmap/4.md)."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.services.recommendation import (
    DeadlineUnreachableError,
    InsufficientDataError,
    NoChargingNeeded,
    future_slots,
    join_price_and_carbon,
    parse_carbon_slots,
    parse_price_slots,
    find_best_window,
)
from backend.services.vehicle_fixtures import VEHICLE_FIXTURES
from pipeline.ingest.handler import fetch_carbon_forecast, fetch_octopus_prices

router = APIRouter()


class RecommendationRequest(BaseModel):
    vehicle_id: str
    current_pct: float
    target_pct: float
    optimize_for: Literal["cost", "carbon"]
    charge_by: datetime | None = None


@router.post("/recommendation")
async def recommend(request: RecommendationRequest) -> JSONResponse:
    vehicle = VEHICLE_FIXTURES.get(request.vehicle_id)
    if vehicle is None:
        return JSONResponse(
            status_code=404,
            content={
                "status": "error",
                "reason": "unknown_vehicle",
                "detail": f"unknown vehicle_id: {request.vehicle_id}",
            },
        )

    price_slots = parse_price_slots(fetch_octopus_prices())
    carbon_slots = parse_carbon_slots(fetch_carbon_forecast())
    slots = future_slots(join_price_and_carbon(price_slots, carbon_slots))

    try:
        result = find_best_window(
            slots,
            vehicle,
            request.current_pct,
            request.target_pct,
            request.optimize_for,
            charge_by=request.charge_by,
        )
    except InsufficientDataError as exc:
        return JSONResponse(
            status_code=422,
            content={
                "status": "error",
                "reason": "insufficient_data",
                "detail": str(exc),
            },
        )
    except DeadlineUnreachableError as exc:
        return JSONResponse(
            status_code=422,
            content={
                "status": "error",
                "reason": "deadline_unreachable",
                "detail": str(exc),
            },
        )

    if isinstance(result, NoChargingNeeded):
        return JSONResponse(content={"status": "no_charging_needed"})

    return JSONResponse(
        content={
            "status": "recommendation",
            "start": result.start.isoformat(),
            "end": result.end.isoformat(),
            "total_cost_gbp": result.total_cost_gbp,
            "average_carbon_gco2_per_kwh": result.average_carbon_gco2_per_kwh,
            "kwh_needed": result.kwh_needed,
        }
    )

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import recommendation, vehicles

app = FastAPI(title="EV Charging Optimiser API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(vehicles.router)
app.include_router(recommendation.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

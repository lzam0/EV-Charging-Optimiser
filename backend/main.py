from fastapi import FastAPI

app = FastAPI(title="EV Charging Optimiser API")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

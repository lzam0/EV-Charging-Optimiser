"""Lambda handler: fetch Carbon Intensity + Octopus Agile data and write raw responses to S3.

Locally (no AWS credentials configured) raw responses are written under
`pipeline/ingest/.local_raw/` instead, so this can be developed and tested
without an AWS account. Swap `write_raw` for a real S3 `put_object` call
once infrastructure exists (see .claude/roadmap/1.md).
"""

import json
import logging
import os
from datetime import datetime, timezone

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CARBON_INTENSITY_URL = "https://api.carbonintensity.org.uk/intensity"
# fw48h = forecast 48h forward from the given date, which comfortably covers
# "tonight" regardless of what time this runs. The recommendation engine
# needs a series, not the single current slot /intensity returns.
CARBON_INTENSITY_FORECAST_URL_TEMPLATE = (
    "https://api.carbonintensity.org.uk/intensity/{date}/fw48h"
)

# AGILE-24-10-01 is the current Agile Octopus product as of 2026-08.
# Product codes change roughly yearly - if this URL starts 404ing, look up
# the new one at https://api.octopus.energy/v1/products/ and find the entry
# with "AGILE" in the code (not AGILE-OUTGOING, which is the export tariff).
# Region C = London; see https://developer.octopus.energy/docs/api/#list-tariff-charges
# for the full region-letter table if this needs to be configurable later.
OCTOPUS_AGILE_URL = (
    "https://api.octopus.energy/v1/products/AGILE-24-10-01/"
    "electricity-tariffs/E-1R-AGILE-24-10-01-C/standard-unit-rates/"
)

LOCAL_RAW_DIR = os.path.join(os.path.dirname(__file__), ".local_raw")


def fetch_carbon_intensity() -> dict:
    response = requests.get(CARBON_INTENSITY_URL, timeout=10)
    response.raise_for_status()
    return response.json()


def fetch_carbon_forecast() -> dict:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = CARBON_INTENSITY_FORECAST_URL_TEMPLATE.format(date=today)
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def fetch_octopus_prices() -> dict:
    # period_from restricts results to only currently-known future slots -
    # without it the endpoint returns years of price history, newest first,
    # paginated ~100 results at a time.
    period_from = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    response = requests.get(
        OCTOPUS_AGILE_URL, params={"period_from": period_from}, timeout=10
    )
    response.raise_for_status()
    return response.json()


def write_raw(source: str, payload: dict) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    os.makedirs(os.path.join(LOCAL_RAW_DIR, source), exist_ok=True)
    path = os.path.join(LOCAL_RAW_DIR, source, f"{timestamp}.json")
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    logger.info("wrote %s", path)


def handler(event: dict, context: object) -> dict:
    results = {}

    try:
        carbon_data = fetch_carbon_intensity()
        write_raw("carbon-intensity", carbon_data)
        results["carbon-intensity"] = "ok"
    except requests.RequestException:
        logger.exception("failed to fetch carbon intensity data")
        results["carbon-intensity"] = "failed"

    try:
        carbon_forecast_data = fetch_carbon_forecast()
        write_raw("carbon-intensity-forecast", carbon_forecast_data)
        results["carbon-intensity-forecast"] = "ok"
    except requests.RequestException:
        logger.exception("failed to fetch carbon intensity forecast")
        results["carbon-intensity-forecast"] = "failed"

    try:
        price_data = fetch_octopus_prices()
        write_raw("octopus-agile", price_data)
        results["octopus-agile"] = "ok"
    except requests.RequestException:
        logger.exception("failed to fetch octopus agile prices")
        results["octopus-agile"] = "failed"

    return results


if __name__ == "__main__":
    print(handler({}, None))

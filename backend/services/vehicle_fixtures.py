"""Stand-in for the real `vehicles` table (Phase 2). Approximate reference
specs for a handful of common EVs - close enough for development, not
guaranteed accurate to the kWh. Replace with the seeded database table once
Phase 2 exists.
"""

from backend.services.recommendation import VehicleSpec

VEHICLE_FIXTURES: dict[str, VehicleSpec] = {
    "tesla_model_3_rwd": VehicleSpec(
        name="Tesla Model 3 RWD",
        battery_capacity_kwh=57.5,
        ac_charge_rate_kw=11.0,
    ),
    "nissan_leaf_62kwh": VehicleSpec(
        name="Nissan Leaf (62kWh)",
        battery_capacity_kwh=59.0,
        ac_charge_rate_kw=6.6,
    ),
    "vw_id3_pro": VehicleSpec(
        name="Volkswagen ID.3 Pro",
        battery_capacity_kwh=58.0,
        ac_charge_rate_kw=11.0,
    ),
    "hyundai_kona_electric": VehicleSpec(
        name="Hyundai Kona Electric",
        battery_capacity_kwh=64.0,
        ac_charge_rate_kw=10.5,
    ),
}

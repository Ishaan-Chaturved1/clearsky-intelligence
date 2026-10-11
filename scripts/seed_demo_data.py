import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.models.domain import (
    Zone,
    EnvironmentalReading,
    DecisionRecord,
    PollutantValue,
    WeatherConditions,
    FireSummary,
    DecisionType,
    ConfidenceLevel,
    DataMode,
    NearbyInfrastructure
)
from app.repositories.local_repository import SQLiteRepository
from app.services.decision_engine import DecisionEngine

def seed_database(db_path: str = None):
    target_db = db_path or settings.SQLITE_DB_PATH
    repo = SQLiteRepository(target_db)
    engine = DecisionEngine()

    zones_json_path = Path(__file__).resolve().parent.parent / "data" / "zones.json"
    with open(zones_json_path, "r", encoding="utf-8") as f:
        zones_data = json.load(f)

    zones = []
    for zd in zones_data:
        z = Zone(
            zone_id=zd["zone_id"],
            name=zd["name"],
            latitude=zd["latitude"],
            longitude=zd["longitude"],
            description=zd["description"],
            zone_type=zd.get("zone_type", "Urban"),
            nearby_infrastructure=NearbyInfrastructure(**zd.get("nearby_infrastructure", {}))
        )
        repo.save_zone(z)
        zones.append(z)

    print(f"Loaded and saved {len(zones)} zones into {target_db}.")

    # Load scenario templates for Delhi zones from data/scenarios.json
    scenarios_json_path = Path(__file__).resolve().parent.parent / "data" / "scenarios.json"
    with open(scenarios_json_path, "r", encoding="utf-8") as f:
        scenarios = json.load(f)

    now = datetime.utcnow()

    # Seed 7 days of historical readings and decisions for backtesting
    print("Generating 7 days of historical timeline for backtesting and analytics...")
    for day_offset in range(6, -1, -1):
        day_time = now - timedelta(days=day_offset)
        # Create 2 evaluation intervals per day (morning & afternoon)
        for hour in [9, 15]:
            eval_time = day_time.replace(hour=hour, minute=0, second=0, microsecond=0)
            eval_iso = eval_time.isoformat() + "Z"

            for zone in zones:
                sc = scenarios.get(zone.zone_id, {
                    "pm25": 60.0, "pm10": 150.0, "ratio": 2.5,
                    "weather": {"temp": 28.0, "rh": 50.0, "ws": 8.0, "wd": 280.0, "blh": 450.0},
                    "fire": {"count": 0, "smoke": False, "dist": None},
                    "stale": False, "mode": DataMode.DEMO
                })

                # Add minor day variation for realistic chart visuals
                var_factor = 1.0 + ((day_offset * 3 + hour) % 7 - 3) * 0.04
                pm25_v = round(sc["pm25"] * var_factor, 1) if sc["pm25"] is not None else None
                pm10_v = round(sc["pm10"] * var_factor, 1) if sc["pm10"] is not None else None
                ratio_v = round(pm10_v / pm25_v, 2) if (pm10_v and pm25_v and pm25_v > 0) else None

                reading = EnvironmentalReading(
                    reading_id=f"RD-{zone.zone_id}-{eval_iso}",
                    zone_id=zone.zone_id,
                    timestamp=eval_iso,
                    pm25=PollutantValue(
                        value=pm25_v,
                        unit="ug/m3",
                        data_type="observed" if zone.zone_id in ["DEL-AV-01", "DEL-WZ-05"] else "modeled",
                        station_id=f"STN-{zone.zone_id[:6]}" if zone.zone_id in ["DEL-AV-01", "DEL-WZ-05"] else None,
                        station_distance_km=2.4 if zone.zone_id in ["DEL-AV-01", "DEL-WZ-05"] else None
                    ),
                    pm10=PollutantValue(
                        value=pm10_v,
                        unit="ug/m3",
                        data_type="observed" if zone.zone_id in ["DEL-AV-01", "DEL-WZ-05"] else "modeled",
                        station_id=f"STN-{zone.zone_id[:6]}" if zone.zone_id in ["DEL-AV-01", "DEL-WZ-05"] else None,
                        station_distance_km=2.4 if zone.zone_id in ["DEL-AV-01", "DEL-WZ-05"] else None
                    ),
                    pm_ratio=ratio_v,
                    weather=WeatherConditions(
                        temperature_c=round(sc["weather"]["temp"] * var_factor, 1),
                        relative_humidity=round(sc["weather"]["rh"] * (1.0 + (1.0 - var_factor)), 1),
                        wind_speed_kmh=sc["weather"]["ws"],
                        wind_direction_deg=sc["weather"]["wd"],
                        boundary_layer_height_m=sc["weather"]["blh"]
                    ),
                    fire_summary=FireSummary(
                        nearby_fires_count=sc["fire"]["count"],
                        closest_fire_distance_km=sc["fire"]["dist"],
                        possible_smoke_transport=sc["fire"]["smoke"]
                    ),
                    data_mode=sc["mode"],
                    is_stale=sc["stale"] if day_offset == 0 and hour == 15 else False
                )
                repo.save_reading(reading)

                # Score decision using deterministic engine
                source_status = {
                    "openaq": "available" if zone.zone_id in ["DEL-AV-01", "DEL-WZ-05"] else "unavailable (demo mode)",
                    "open_meteo_weather": "available",
                    "open_meteo_aq": "available",
                    "nasa_firms": "available" if sc["fire"]["count"] > 0 else "clean (no fire anomalies)",
                    "osm_overpass": "available"
                }

                decision = engine.evaluate(
                    zone=zone,
                    reading=reading,
                    scored_at=eval_iso,
                    source_status=source_status
                )
                repo.save_decision(decision)

    print("Historical seeding complete!")

if __name__ == "__main__":
    seed_database()

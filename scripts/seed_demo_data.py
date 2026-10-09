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

    # Pre-configured scenario templates for Delhi zones
    scenarios = {
        # 1. High Priority Dust Candidate with construction
        "DEL-AV-01": {
            "pm25": 82.0, "pm10": 265.0, "ratio": 3.23,
            "weather": {"temp": 28.0, "rh": 48.0, "ws": 7.5, "wd": 290.0, "blh": 450.0},
            "fire": {"count": 0, "smoke": False, "dist": None},
            "stale": False, "mode": DataMode.DEMO
        },
        # 2. Severe Dust Candidate (Wazirpur)
        "DEL-WZ-05": {
            "pm25": 94.0, "pm10": 295.0, "ratio": 3.14,
            "weather": {"temp": 29.5, "rh": 42.0, "ws": 9.0, "wd": 300.0, "blh": 410.0},
            "fire": {"count": 0, "smoke": False, "dist": None},
            "stale": False, "mode": DataMode.DEMO
        },
        # 3. Active Smoke / Fire influence -> INTERVENTION NOT RECOMMENDED
        "DEL-BAW-10": {
            "pm25": 178.0, "pm10": 210.0, "ratio": 1.18,
            "weather": {"temp": 27.0, "rh": 55.0, "ws": 12.0, "wd": 315.0, "blh": 380.0},
            "fire": {"count": 4, "smoke": True, "dist": 14.5},
            "stale": False, "mode": DataMode.DEMO
        },
        # 4. High Humidity (>80%) -> INTERVENTION NOT RECOMMENDED
        "DEL-OKH-06": {
            "pm25": 70.0, "pm10": 190.0, "ratio": 2.71,
            "weather": {"temp": 22.0, "rh": 86.0, "ws": 6.0, "wd": 110.0, "blh": 280.0},
            "fire": {"count": 0, "smoke": False, "dist": None},
            "stale": False, "mode": DataMode.DEMO
        },
        # 5. High Wind (>20 km/h) -> INTERVENTION NOT RECOMMENDED
        "DEL-IGI-09": {
            "pm25": 65.0, "pm10": 210.0, "ratio": 3.23,
            "weather": {"temp": 31.0, "rh": 38.0, "ws": 23.5, "wd": 270.0, "blh": 650.0},
            "fire": {"count": 0, "smoke": False, "dist": None},
            "stale": False, "mode": DataMode.DEMO
        },
        # 6. Missing Data -> ADVISORY ONLY
        "DEL-ROH-07": {
            "pm25": 58.0, "pm10": None, "ratio": None,
            "weather": {"temp": 28.0, "rh": 50.0, "ws": 8.0, "wd": 280.0, "blh": 500.0},
            "fire": {"count": 0, "smoke": False, "dist": None},
            "stale": False, "mode": DataMode.DEMO
        },
        # 7. Stale Readings (>3h old) -> ADVISORY ONLY
        "DEL-DWK-08": {
            "pm25": 85.0, "pm10": 220.0, "ratio": 2.59,
            "weather": {"temp": 27.5, "rh": 52.0, "ws": 9.5, "wd": 285.0, "blh": 460.0},
            "fire": {"count": 0, "smoke": False, "dist": None},
            "stale": True, "mode": DataMode.DEMO
        },
        # 8. High PM2.5 Vehicular / Combustion without coarse dust (ratio 1.3)
        "DEL-ITO-11": {
            "pm25": 142.0, "pm10": 185.0, "ratio": 1.30,
            "weather": {"temp": 29.0, "rh": 54.0, "ws": 6.5, "wd": 275.0, "blh": 340.0},
            "fire": {"count": 0, "smoke": False, "dist": None},
            "stale": False, "mode": DataMode.DEMO
        },
        # 9. Inversion layer warning (Low BLH 220m, Low wind 3.5 km/h)
        "DEL-JH-04": {
            "pm25": 92.0, "pm10": 240.0, "ratio": 2.61,
            "weather": {"temp": 24.0, "rh": 62.0, "ws": 3.5, "wd": 260.0, "blh": 220.0},
            "fire": {"count": 0, "smoke": False, "dist": None},
            "stale": False, "mode": DataMode.DEMO
        },
        # 10. Clean green institutional zone (Lodhi Road)
        "DEL-LOD-12": {
            "pm25": 38.0, "pm10": 74.0, "ratio": 1.95,
            "weather": {"temp": 27.0, "rh": 51.0, "ws": 7.0, "wd": 250.0, "blh": 580.0},
            "fire": {"count": 0, "smoke": False, "dist": None},
            "stale": False, "mode": DataMode.DEMO
        },
        # 11. Punjabi Bagh (Moderate dust candidate)
        "DEL-PB-02": {
            "pm25": 72.0, "pm10": 195.0, "ratio": 2.71,
            "weather": {"temp": 28.5, "rh": 49.0, "ws": 8.0, "wd": 280.0, "blh": 480.0},
            "fire": {"count": 0, "smoke": False, "dist": None},
            "stale": False, "mode": DataMode.DEMO
        },
        # 12. R.K. Puram (Moderate ambient)
        "DEL-RKP-03": {
            "pm25": 54.0, "pm10": 125.0, "ratio": 2.31,
            "weather": {"temp": 28.0, "rh": 50.0, "ws": 8.5, "wd": 280.0, "blh": 520.0},
            "fire": {"count": 0, "smoke": False, "dist": None},
            "stale": False, "mode": DataMode.DEMO
        }
    }

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

import time
import httpx
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.logging import logger
from app.data_sources.base import SourceFetchResult, global_cache

class OpenMeteoClient:
    def __init__(self):
        self.forecast_url = settings.OPEN_METEO_FORECAST_URL
        self.air_quality_url = settings.OPEN_METEO_AIR_QUALITY_URL
        self.timeout = settings.API_TIMEOUT_SECONDS

    async def get_weather(self, lat: float, lon: float) -> SourceFetchResult:
        cache_key = f"weather_{round(lat, 3)}_{round(lon, 3)}"
        cached = global_cache.get(cache_key)
        if cached:
            return SourceFetchResult(
                source_name="Open-Meteo Weather Forecast",
                is_success=True,
                data=cached,
                is_cached=True,
                fetched_at=time.time()
            )

        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m",
            "hourly": "boundary_layer_height",
            "forecast_days": 1,
            "timezone": "auto"
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.forecast_url, params=params)
                if resp.status_code == 200:
                    raw = resp.json()
                    curr = raw.get("current", {})
                    hourly = raw.get("hourly", {})
                    blh_values = hourly.get("boundary_layer_height", [])
                    blh = blh_values[0] if blh_values else None
                    
                    data = {
                        "temperature_c": curr.get("temperature_2m"),
                        "relative_humidity": curr.get("relative_humidity_2m"),
                        "wind_speed_kmh": curr.get("wind_speed_10m"),
                        "wind_direction_deg": curr.get("wind_direction_10m"),
                        "boundary_layer_height_m": blh,
                        "data_type": "modeled",
                        "raw_timestamp": curr.get("time")
                    }
                    global_cache.set(cache_key, data, ttl_seconds=1800)
                    return SourceFetchResult(
                        source_name="Open-Meteo Weather Forecast",
                        is_success=True,
                        data=data,
                        fetched_at=time.time()
                    )
                else:
                    return SourceFetchResult(
                        source_name="Open-Meteo Weather Forecast",
                        is_success=False,
                        error_message=f"HTTP {resp.status_code}: {resp.text[:100]}",
                        fetched_at=time.time()
                    )
        except Exception as e:
            logger.warning(f"Failed to fetch weather from Open-Meteo for ({lat}, {lon}): {e}")
            return SourceFetchResult(
                source_name="Open-Meteo Weather Forecast",
                is_success=False,
                error_message=str(e),
                fetched_at=time.time()
            )

    async def get_air_quality(self, lat: float, lon: float) -> SourceFetchResult:
        cache_key = f"air_quality_{round(lat, 3)}_{round(lon, 3)}"
        cached = global_cache.get(cache_key)
        if cached:
            return SourceFetchResult(
                source_name="Open-Meteo Air Quality",
                is_success=True,
                data=cached,
                is_cached=True,
                fetched_at=time.time()
            )

        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "pm10,pm2_5,dust",
            "forecast_days": 1,
            "timezone": "auto"
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.air_quality_url, params=params)
                if resp.status_code == 200:
                    raw = resp.json()
                    curr = raw.get("current", {})
                    data = {
                        "pm25": curr.get("pm2_5"),
                        "pm10": curr.get("pm10"),
                        "dust": curr.get("dust"),
                        "data_type": "modeled",
                        "raw_timestamp": curr.get("time")
                    }
                    global_cache.set(cache_key, data, ttl_seconds=1800)
                    return SourceFetchResult(
                        source_name="Open-Meteo Air Quality",
                        is_success=True,
                        data=data,
                        fetched_at=time.time()
                    )
                else:
                    return SourceFetchResult(
                        source_name="Open-Meteo Air Quality",
                        is_success=False,
                        error_message=f"HTTP {resp.status_code}: {resp.text[:100]}",
                        fetched_at=time.time()
                    )
        except Exception as e:
            logger.warning(f"Failed to fetch air quality from Open-Meteo for ({lat}, {lon}): {e}")
            return SourceFetchResult(
                source_name="Open-Meteo Air Quality",
                is_success=False,
                error_message=str(e),
                fetched_at=time.time()
            )

import time
import math
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.core.logging import logger
from app.data_sources.base import SourceFetchResult, global_cache

class OpenMeteoClient:
    def __init__(self):
        self.forecast_url = settings.OPEN_METEO_FORECAST_URL
        self.air_quality_url = settings.OPEN_METEO_AIR_QUALITY_URL
        self.timeout = settings.API_TIMEOUT_SECONDS

    def _calculate_evaporation_and_drying(
        self,
        temperature_c: Optional[float],
        relative_humidity: Optional[float],
        wind_speed_kmh: Optional[float]
    ) -> tuple[Optional[float], Optional[int]]:
        """
        Calculates potential surface evaporation rate (mm/h) and estimated surface drying time (minutes)
        using an empirical aerodynamic vapor-pressure deficit model.
        Assumes standard municipal anti-smog water film thickness ~0.35 mm.
        """
        if temperature_c is None or relative_humidity is None:
            return None, None

        ws = max(0.0, wind_speed_kmh or 5.0)
        # Saturated vapor pressure (Magnus-Tetens formula in hPa)
        t = temperature_c
        es = 6.112 * math.exp((17.67 * t) / (t + 243.5))
        # Actual vapor pressure
        ea = es * (max(0.0, min(100.0, relative_humidity)) / 100.0)
        vpd = max(0.0, es - ea)

        # Potential evaporation rate (mm/h)
        # Penman-derived aerodynamic Dalton transfer: E = (0.015 + 0.0012 * WS) * VPD
        evap_rate = round((0.015 + 0.0012 * ws) * vpd, 3)

        # Drying time for 0.35mm water film
        if evap_rate > 0.005:
            drying_minutes = int(round((0.35 / evap_rate) * 60))
            drying_minutes = max(8, min(240, drying_minutes))
        else:
            drying_minutes = 240  # Stagnant/humid condensation limit

        return evap_rate, drying_minutes

    def _extract_pressure_trends(
        self,
        curr_pressure: Optional[float],
        hourly_times: List[str],
        hourly_pressures: List[Optional[float]],
        curr_time_str: Optional[str]
    ) -> tuple[Optional[float], Optional[float], Optional[float], str]:
        """
        Calculates 3h, 6h, and 12h pressure changes in hPa and determines barometric tendency.
        """
        if curr_pressure is None or not hourly_pressures:
            return None, None, None, "STEADY"

        # Find current index in hourly series
        curr_idx = len(hourly_pressures) - 1
        if curr_time_str and curr_time_str in hourly_times:
            curr_idx = hourly_times.index(curr_time_str)

        def get_delta(hours_back: int) -> Optional[float]:
            target_idx = curr_idx - hours_back
            if 0 <= target_idx < len(hourly_pressures):
                past_val = hourly_pressures[target_idx]
                if past_val is not None:
                    return round(curr_pressure - past_val, 2)
            return None

        p_3h = get_delta(3)
        p_6h = get_delta(6)
        p_12h = get_delta(12)

        # Meteorological barometric tendency classification (World Meteorological Organization standard: > +1.5 hPa/3h)
        tendency = "STEADY"
        if p_3h is not None:
            if p_3h >= 1.5:
                tendency = "RISING"
            elif p_3h <= -1.5:
                tendency = "FALLING"

        return p_3h, p_6h, p_12h, tendency

    async def get_weather(self, lat: float, lon: float) -> SourceFetchResult:
        cache_key = f"weather_adv_{round(lat, 3)}_{round(lon, 3)}"
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
            "current": "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,wind_direction_10m,precipitation",
            "hourly": "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,wind_direction_10m,precipitation,boundary_layer_height",
            "past_hours": 12,
            "forecast_days": 2,
            "timezone": "auto"
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.forecast_url, params=params)
                if resp.status_code == 200:
                    raw = resp.json()
                    curr = raw.get("current", {})
                    hourly = raw.get("hourly", {})

                    hourly_times = hourly.get("time", [])
                    hourly_pressures = hourly.get("surface_pressure", [])
                    hourly_blh = hourly.get("boundary_layer_height", [])

                    curr_time_str = curr.get("time")
                    curr_pressure = curr.get("surface_pressure")
                    curr_temp = curr.get("temperature_2m")
                    curr_rh = curr.get("relative_humidity_2m")
                    curr_ws = curr.get("wind_speed_10m")
                    curr_wd = curr.get("wind_direction_10m")
                    curr_precip = curr.get("precipitation", 0.0)

                    # Extract BLH at current hour
                    blh = None
                    if curr_time_str and curr_time_str in hourly_times:
                        c_idx = hourly_times.index(curr_time_str)
                        if c_idx < len(hourly_blh):
                            blh = hourly_blh[c_idx]
                    elif hourly_blh:
                        blh = hourly_blh[0]

                    p_3h, p_6h, p_12h, tendency = self._extract_pressure_trends(
                        curr_pressure, hourly_times, hourly_pressures, curr_time_str
                    )

                    evap_rate, drying_time = self._calculate_evaporation_and_drying(
                        curr_temp, curr_rh, curr_ws
                    )

                    data = {
                        "temperature_c": curr_temp,
                        "relative_humidity": curr_rh,
                        "surface_pressure_hpa": curr_pressure,
                        "pressure_trend_3h_hpa": p_3h,
                        "pressure_trend_6h_hpa": p_6h,
                        "pressure_trend_12h_hpa": p_12h,
                        "pressure_tendency": tendency,
                        "wind_speed_kmh": curr_ws,
                        "wind_direction_deg": curr_wd,
                        "precipitation_mmh": curr_precip,
                        "evaporation_rate_mmh": evap_rate,
                        "estimated_surface_drying_time_min": drying_time,
                        "boundary_layer_height_m": blh,
                        "data_type": "modeled",
                        "raw_timestamp": curr_time_str,
                        "raw_hourly": hourly
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

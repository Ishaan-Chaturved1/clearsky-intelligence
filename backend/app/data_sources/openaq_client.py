import time
import math
import httpx
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.core.logging import logger
from app.data_sources.base import SourceFetchResult, global_cache

class OpenAQClient:
    """
    OpenAQ API v3 client for ground station pollutant observations.
    Endpoints:
      - /v3/locations
      - /v3/locations/{id}/latest
    """
    def __init__(self):
        self.base_url = settings.OPENAQ_BASE_URL.rstrip('/')
        self.api_key = settings.OPENAQ_API_KEY
        self.timeout = settings.API_TIMEOUT_SECONDS

    def _haversine_distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c

    async def get_nearby_station_measurements(self, lat: float, lon: float, radius_km: float = 25.0) -> SourceFetchResult:
        cache_key = f"openaq_stations_{round(lat, 2)}_{round(lon, 2)}"
        cached = global_cache.get(cache_key)
        if cached is not None:
            return SourceFetchResult(
                source_name="OpenAQ Ground Stations",
                is_success=True,
                data=cached,
                is_cached=True,
                fetched_at=time.time()
            )

        if not self.api_key:
            return SourceFetchResult(
                source_name="OpenAQ Ground Stations",
                is_success=False,
                error_message="OPENAQ_API_KEY environment variable is not configured",
                data=[],
                fetched_at=time.time()
            )

        headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json"
        }
        params = {
            "coordinates": f"{lat},{lon}",
            "radius": int(radius_km * 1000),
            "limit": 10
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.base_url}/locations", headers=headers, params=params)
                if resp.status_code == 200:
                    raw = resp.json()
                    results = raw.get("results", [])
                    stations = []
                    for loc in results:
                        coords = loc.get("coordinates", {})
                        st_lat = coords.get("latitude")
                        st_lon = coords.get("longitude")
                        if st_lat is None or st_lon is None:
                            continue
                        dist_km = self._haversine_distance_km(lat, lon, float(st_lat), float(st_lon))
                        if dist_km > radius_km:
                            continue

                        sensors = loc.get("sensors", [])
                        pm25_val = None
                        pm10_val = None
                        obs_time = loc.get("datetimeLast", {}).get("utc")

                        for sensor in sensors:
                            param = sensor.get("parameter", {}).get("name", "").lower()
                            val = sensor.get("value")
                            unit = sensor.get("parameter", {}).get("units", "ug/m3")
                            if val is not None and unit in ("µg/m³", "ug/m3"):
                                if param == "pm25":
                                    pm25_val = float(val)
                                elif param == "pm10":
                                    pm10_val = float(val)

                        stations.append({
                            "station_id": str(loc.get("id")),
                            "station_name": loc.get("name", "Unknown Station"),
                            "latitude": float(st_lat),
                            "longitude": float(st_lon),
                            "distance_km": round(dist_km, 2),
                            "pm25": pm25_val,
                            "pm10": pm10_val,
                            "observed_at": obs_time
                        })

                    global_cache.set(cache_key, stations, ttl_seconds=900)
                    return SourceFetchResult(
                        source_name="OpenAQ Ground Stations",
                        is_success=True,
                        data=stations,
                        fetched_at=time.time()
                    )
                elif resp.status_code == 429:
                    return SourceFetchResult(
                        source_name="OpenAQ Ground Stations",
                        is_success=False,
                        error_message="OpenAQ rate limit reached (HTTP 429)",
                        fetched_at=time.time()
                    )
                else:
                    return SourceFetchResult(
                        source_name="OpenAQ Ground Stations",
                        is_success=False,
                        error_message=f"HTTP {resp.status_code}: {resp.text[:120]}",
                        fetched_at=time.time()
                    )
        except Exception as e:
            logger.warning(f"Error querying OpenAQ: {e}")
            return SourceFetchResult(
                source_name="OpenAQ Ground Stations",
                is_success=False,
                error_message=str(e),
                fetched_at=time.time()
            )

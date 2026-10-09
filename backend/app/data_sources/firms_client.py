import time
import math
import httpx
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.core.logging import logger
from app.data_sources.base import SourceFetchResult, global_cache

class FirmsClient:
    """
    NASA FIRMS active fire detection client.
    Queries active thermal anomalies (MODIS/VIIRS) and checks for possible
    smoke transport heading toward monitored zones based on meteorological wind direction.
    """
    def __init__(self):
        self.map_key = settings.NASA_FIRMS_MAP_KEY
        self.base_url = settings.NASA_FIRMS_BASE_URL
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

    def _calculate_bearing_deg(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates bearing from point 1 to point 2 in degrees (0 = North, 90 = East)."""
        lat1_r = math.radians(lat1)
        lat2_r = math.radians(lat2)
        diff_lon = math.radians(lon2 - lon1)
        x = math.sin(diff_lon) * math.cos(lat2_r)
        y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(diff_lon)
        initial_bearing = math.atan2(x, y)
        compass_bearing = (math.degrees(initial_bearing) + 360) % 360
        return compass_bearing

    async def check_nearby_fires(
        self,
        zone_lat: float,
        zone_lon: float,
        wind_direction_deg: Optional[float] = None,
        radius_km: float = 50.0
    ) -> SourceFetchResult:
        cache_key = f"firms_fires_{round(zone_lat, 2)}_{round(zone_lon, 2)}"
        cached = global_cache.get(cache_key)
        if cached is not None:
            return SourceFetchResult(
                source_name="NASA FIRMS Fire Detections",
                is_success=True,
                data=cached,
                is_cached=True,
                fetched_at=time.time()
            )

        if not self.map_key:
            return SourceFetchResult(
                source_name="NASA FIRMS Fire Detections",
                is_success=False,
                error_message="NASA_FIRMS_MAP_KEY environment variable is not configured",
                data={
                    "nearby_fires_count": 0,
                    "closest_fire_distance_km": None,
                    "possible_smoke_transport": False,
                    "details": []
                },
                fetched_at=time.time()
            )

        # NASA FIRMS Area/Country CSV API endpoint
        url = f"{self.base_url}/{self.map_key}/VIIRS_SNPP_NRT/IND/1"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    lines = resp.text.strip().splitlines()
                    if len(lines) <= 1:
                        data = {
                            "nearby_fires_count": 0,
                            "closest_fire_distance_km": None,
                            "possible_smoke_transport": False,
                            "details": []
                        }
                        global_cache.set(cache_key, data, ttl_seconds=1800)
                        return SourceFetchResult(
                            source_name="NASA FIRMS Fire Detections",
                            is_success=True,
                            data=data,
                            fetched_at=time.time()
                        )

                    headers = lines[0].split(",")
                    lat_idx = headers.index("latitude") if "latitude" in headers else 0
                    lon_idx = headers.index("longitude") if "longitude" in headers else 1
                    bright_idx = headers.index("bright_ti4") if "bright_ti4" in headers else -1

                    nearby_detections = []
                    closest_dist = None
                    possible_smoke = False

                    for line in lines[1:]:
                        parts = line.split(",")
                        if len(parts) <= max(lat_idx, lon_idx):
                            continue
                        try:
                            f_lat = float(parts[lat_idx])
                            f_lon = float(parts[lon_idx])
                        except ValueError:
                            continue

                        dist = self._haversine_distance_km(zone_lat, zone_lon, f_lat, f_lon)
                        if dist <= radius_km:
                            if closest_dist is None or dist < closest_dist:
                                closest_dist = dist

                            # Bearing from fire to zone
                            bearing_to_zone = self._calculate_bearing_deg(f_lat, f_lon, zone_lat, zone_lon)
                            
                            # Check if wind is blowing smoke from fire toward zone:
                            # Meteorological wind direction is where the wind COMES FROM.
                            # Smoke travels along wind direction + 180 (downwind).
                            # So smoke heads in direction (wind_direction + 180) % 360.
                            is_upwind = False
                            if wind_direction_deg is not None:
                                smoke_heading = (wind_direction_deg + 180) % 360
                                angular_diff = abs(smoke_heading - bearing_to_zone)
                                angular_diff = min(angular_diff, 360 - angular_diff)
                                if angular_diff <= 45.0:
                                    is_upwind = True
                                    possible_smoke = True

                            bright_val = parts[bright_idx] if bright_idx != -1 and bright_idx < len(parts) else "N/A"
                            nearby_detections.append({
                                "latitude": f_lat,
                                "longitude": f_lon,
                                "distance_km": round(dist, 1),
                                "bearing_deg": round(bearing_to_zone, 1),
                                "is_upwind_smoke_path": is_upwind,
                                "brightness": bright_val
                            })

                    data = {
                        "nearby_fires_count": len(nearby_detections),
                        "closest_fire_distance_km": round(closest_dist, 1) if closest_dist is not None else None,
                        "possible_smoke_transport": possible_smoke,
                        "details": nearby_detections[:10]
                    }
                    global_cache.set(cache_key, data, ttl_seconds=1800)
                    return SourceFetchResult(
                        source_name="NASA FIRMS Fire Detections",
                        is_success=True,
                        data=data,
                        fetched_at=time.time()
                    )
                else:
                    return SourceFetchResult(
                        source_name="NASA FIRMS Fire Detections",
                        is_success=False,
                        error_message=f"HTTP {resp.status_code}: {resp.text[:120]}",
                        fetched_at=time.time()
                    )
        except Exception as e:
            logger.warning(f"Error checking NASA FIRMS: {e}")
            return SourceFetchResult(
                source_name="NASA FIRMS Fire Detections",
                is_success=False,
                error_message=str(e),
                fetched_at=time.time()
            )

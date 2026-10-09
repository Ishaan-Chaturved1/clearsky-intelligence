import time
import httpx
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.core.logging import logger
from app.data_sources.base import SourceFetchResult, global_cache

class OverpassClient:
    """
    OpenStreetMap Overpass API client for identifying nearby construction sites
    and arterial roads within ~300-500m of monitored zones.
    Heavy caching (24h TTL) to prevent repeated Overpass queries.
    """
    def __init__(self):
        self.endpoint = settings.OVERPASS_API_URL
        self.timeout = settings.API_TIMEOUT_SECONDS

    async def get_nearby_infrastructure(
        self,
        lat: float,
        lon: float,
        radius_meters: int = 350
    ) -> SourceFetchResult:
        cache_key = f"overpass_infra_{round(lat, 3)}_{round(lon, 3)}"
        cached = global_cache.get(cache_key)
        if cached is not None:
            return SourceFetchResult(
                source_name="OpenStreetMap Overpass",
                is_success=True,
                data=cached,
                is_cached=True,
                fetched_at=time.time()
            )

        # Overpass QL query around coordinates
        query = f"""
        [out:json][timeout:8];
        (
          node["landuse"="construction"](around:{radius_meters},{lat},{lon});
          way["landuse"="construction"](around:{radius_meters},{lat},{lon});
          way["highway"="construction"](around:{radius_meters},{lat},{lon});
          way["building"="construction"](around:{radius_meters},{lat},{lon});
          way["highway"~"motorway|trunk|primary|secondary"](around:{radius_meters},{lat},{lon});
        );
        out tags;
        """

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(self.endpoint, data={"data": query})
                if resp.status_code == 200:
                    elements = resp.json().get("elements", [])
                    construction_sites = []
                    major_roads = []

                    for el in elements:
                        tags = el.get("tags", {})
                        name = tags.get("name", "Unnamed feature")
                        if tags.get("landuse") == "construction" or tags.get("highway") == "construction" or tags.get("building") == "construction":
                            site_desc = f"{name} ({tags.get('highway') or tags.get('landuse') or 'active site'})"
                            if site_desc not in construction_sites:
                                construction_sites.append(site_desc)
                        elif "highway" in tags:
                            road_name = tags.get("name") or tags.get("ref") or f"{tags.get('highway')} road"
                            if road_name not in major_roads:
                                major_roads.append(road_name)

                    data = {
                        "has_construction_nearby": len(construction_sites) > 0,
                        "construction_sites": construction_sites[:5],
                        "major_roads": major_roads[:5],
                        "construction_distance_meters": radius_meters if len(construction_sites) > 0 else None
                    }
                    # Cache for 24 hours
                    global_cache.set(cache_key, data, ttl_seconds=86400)
                    return SourceFetchResult(
                        source_name="OpenStreetMap Overpass",
                        is_success=True,
                        data=data,
                        fetched_at=time.time()
                    )
                else:
                    return SourceFetchResult(
                        source_name="OpenStreetMap Overpass",
                        is_success=False,
                        error_message=f"HTTP {resp.status_code}",
                        data={"has_construction_nearby": False, "construction_sites": [], "major_roads": []},
                        fetched_at=time.time()
                    )
        except Exception as e:
            logger.warning(f"Overpass query error for ({lat}, {lon}): {e}")
            return SourceFetchResult(
                source_name="OpenStreetMap Overpass",
                is_success=False,
                error_message=str(e),
                data={"has_construction_nearby": False, "construction_sites": [], "major_roads": []},
                fetched_at=time.time()
            )

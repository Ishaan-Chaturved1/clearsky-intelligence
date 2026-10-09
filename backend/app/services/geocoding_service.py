import time
import math
import asyncio
from typing import List, Dict, Optional, Any
import httpx
from app.core.config import settings
from app.core.logging import logger
from app.data_sources.base import global_cache

# Known prominent Delhi NCR geographical reference anchors for high-speed local discovery and fallback
DELHI_NCR_ANCHORS = [
    {
        "place_name": "Connaught Place, Central Delhi",
        "display_name": "Connaught Place, New Delhi, Delhi, 110001, India",
        "latitude": 28.6315,
        "longitude": 77.2167,
        "type": "commercial",
        "zone_type": "Commercial Center"
    },
    {
        "place_name": "Anand Vihar, East Delhi",
        "display_name": "Anand Vihar, Shahdara, East Delhi, Delhi, 110092, India",
        "latitude": 28.6469,
        "longitude": 77.3160,
        "type": "transportation",
        "zone_type": "Transit & Construction Corridor"
    },
    {
        "place_name": "Punjabi Bagh, West Delhi",
        "display_name": "Punjabi Bagh, West Delhi, Delhi, 110026, India",
        "latitude": 28.6742,
        "longitude": 77.1311,
        "type": "residential",
        "zone_type": "Traffic Corridor"
    },
    {
        "place_name": "R.K. Puram, South Delhi",
        "display_name": "Ramakrishna Puram, South West Delhi, Delhi, 110022, India",
        "latitude": 28.5638,
        "longitude": 77.1864,
        "type": "residential",
        "zone_type": "Residential & Institutional"
    },
    {
        "place_name": "Jahangirpuri, North West Delhi",
        "display_name": "Jahangirpuri, North West Delhi, Delhi, 110033, India",
        "latitude": 28.7328,
        "longitude": 77.1706,
        "type": "logistics",
        "zone_type": "Dense Commercial / Logistics"
    },
    {
        "place_name": "Wazirpur Industrial Area",
        "display_name": "Wazirpur Industrial Area, North West Delhi, Delhi, 110052, India",
        "latitude": 28.6999,
        "longitude": 77.1654,
        "type": "industrial",
        "zone_type": "Heavy Industrial & Scrap Metal"
    },
    {
        "place_name": "Noida Sector 62, Uttar Pradesh",
        "display_name": "Sector 62, Noida, Gautam Buddha Nagar, Uttar Pradesh, 201309, India",
        "latitude": 28.6280,
        "longitude": 77.3649,
        "type": "tech_hub",
        "zone_type": "IT Corridor & Expressway"
    },
    {
        "place_name": "Gurugram Cyber Hub, Haryana",
        "display_name": "DLF Cyber City, DLF Phase 2, Sector 24, Gurugram, Haryana, 122002, India",
        "latitude": 28.4950,
        "longitude": 77.0895,
        "type": "commercial",
        "zone_type": "Commercial & High-Density Highway"
    },
    {
        "place_name": "Indirapuram, Ghaziabad",
        "display_name": "Indirapuram, Ghaziabad, Uttar Pradesh, 201014, India",
        "latitude": 28.6415,
        "longitude": 77.3714,
        "type": "residential",
        "zone_type": "Dense Residential & Highway"
    },
    {
        "place_name": "Dwarka Sector 8, South West Delhi",
        "display_name": "Dwarka Sector 8, South West Delhi, Delhi, 110077, India",
        "latitude": 28.5714,
        "longitude": 77.0691,
        "type": "residential",
        "zone_type": "Suburban Residential"
    },
    {
        "place_name": "Rohini Sector 16, North West Delhi",
        "display_name": "Sector 16, Rohini, North West Delhi, Delhi, 110089, India",
        "latitude": 28.7325,
        "longitude": 77.1199,
        "type": "residential",
        "zone_type": "Residential & Construction Fringe"
    },
    {
        "place_name": "Okhla Phase II, South East Delhi",
        "display_name": "Okhla Industrial Area Phase II, South East Delhi, Delhi, 110020, India",
        "latitude": 28.5308,
        "longitude": 77.2713,
        "type": "industrial",
        "zone_type": "Industrial Cluster"
    },
    {
        "place_name": "Chandni Chowk, Old Delhi",
        "display_name": "Chandni Chowk, Central Delhi, Delhi, 110006, India",
        "latitude": 28.6562,
        "longitude": 77.2307,
        "type": "heritage_commercial",
        "zone_type": "Dense Commercial"
    },
    {
        "place_name": "Mundka Industrial Area",
        "display_name": "Mundka, West Delhi, Delhi, 110041, India",
        "latitude": 28.6836,
        "longitude": 77.0329,
        "type": "industrial",
        "zone_type": "Heavy Logistics & Unpaved Corridor"
    },
    {
        "place_name": "Bawana Industrial Perimeter",
        "display_name": "Bawana, North Delhi, Delhi, 110039, India",
        "latitude": 28.7762,
        "longitude": 77.0510,
        "type": "industrial",
        "zone_type": "Industrial & Unpaved Perimeter"
    },
    {
        "place_name": "Faridabad Sector 16, Haryana",
        "display_name": "Sector 16, Faridabad, Haryana, 121002, India",
        "latitude": 28.4089,
        "longitude": 77.3178,
        "type": "industrial_residential",
        "zone_type": "Mixed Industrial & Residential"
    }
]

class GeocodingService:
    """
    Geocoding and place discovery service using OpenStreetMap Nominatim with
    compliant User-Agent, in-memory caching, rate limiting, and local fallback anchors.
    """
    def __init__(self):
        self.nominatim_url = "https://nominatim.openstreetmap.org"
        self.headers = {
            "User-Agent": "ClearSky-Intelligence/1.0 (environmental-systems@clearsky.local)",
            "Accept": "application/json"
        }
        self.timeout = settings.API_TIMEOUT_SECONDS
        self._last_request_time = 0.0

    async def _throttle(self):
        """Respect Nominatim policy of max 1 request per second."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)
        self._last_request_time = time.time()

    async def search_places(self, query: str, limit: int = 6) -> List[Dict[str, Any]]:
        """
        Searches real geographic localities, neighborhoods, cities, and addresses.
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        cache_key = f"nominatim_search_{clean_query.lower()[:32]}"
        cached = global_cache.get(cache_key)
        if cached is not None:
            return cached

        results: List[Dict[str, Any]] = []

        try:
            await self._throttle()
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {
                    "q": clean_query,
                    "format": "json",
                    "addressdetails": 1,
                    "limit": limit
                }
                resp = await client.get(f"{self.nominatim_url}/search", params=params, headers=self.headers)
                if resp.status_code == 200:
                    raw_items = resp.json()
                    for item in raw_items:
                        name = item.get("name") or item.get("display_name", "").split(",")[0]
                        results.append({
                            "place_name": name,
                            "display_name": item.get("display_name", ""),
                            "latitude": float(item.get("lat")),
                            "longitude": float(item.get("lon")),
                            "type": item.get("type", "location"),
                            "osm_type": item.get("osm_type"),
                            "boundingbox": item.get("boundingbox")
                        })
        except Exception as e:
            logger.warning(f"Nominatim search request failed for '{clean_query}': {e}")

        # If external geocoding returned few or no results, match against local anchors
        if len(results) < limit:
            q_lower = clean_query.lower()
            for anchor in DELHI_NCR_ANCHORS:
                if (q_lower in anchor["place_name"].lower() or q_lower in anchor["display_name"].lower()) and not any(
                    abs(r["latitude"] - anchor["latitude"]) < 0.01 and abs(r["longitude"] - anchor["longitude"]) < 0.01
                    for r in results
                ):
                    results.append(anchor)
                    if len(results) >= limit:
                        break

        global_cache.set(cache_key, results, ttl_seconds=3600)
        return results

    async def reverse_geocode(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Resolves real geographic place name and address from coordinates.
        """
        cache_key = f"nominatim_reverse_{round(lat, 3)}_{round(lon, 3)}"
        cached = global_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            await self._throttle()
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {
                    "lat": lat,
                    "lon": lon,
                    "format": "json",
                    "addressdetails": 1
                }
                resp = await client.get(f"{self.nominatim_url}/reverse", params=params, headers=self.headers)
                if resp.status_code == 200:
                    data = resp.json()
                    addr = data.get("address", {})
                    name = (
                        addr.get("suburb")
                        or addr.get("neighbourhood")
                        or addr.get("residential")
                        or addr.get("city_district")
                        or addr.get("road")
                        or addr.get("city")
                        or data.get("name")
                        or f"Location ({lat:.3f}, {lon:.3f})"
                    )
                    res = {
                        "place_name": name,
                        "display_name": data.get("display_name", f"{lat:.4f}, {lon:.4f}"),
                        "latitude": lat,
                        "longitude": lon,
                        "address": addr,
                        "type": data.get("type", "geographic_point")
                    }
                    global_cache.set(cache_key, res, ttl_seconds=3600)
                    return res
        except Exception as e:
            logger.warning(f"Reverse geocode failed for ({lat}, {lon}): {e}")

        # Find closest anchor if available
        closest = None
        min_dist = 999.0
        for anchor in DELHI_NCR_ANCHORS:
            d = math.hypot(anchor["latitude"] - lat, anchor["longitude"] - lon) * 111.0
            if d < min_dist:
                min_dist = d
                closest = anchor

        if closest and min_dist <= 5.0:
            res = {
                "place_name": f"{closest['place_name']} Area",
                "display_name": f"Near {closest['display_name']} (~{min_dist:.1f}km)",
                "latitude": lat,
                "longitude": lon,
                "address": {"city": "Delhi NCR"},
                "type": "local_vicinity"
            }
        else:
            res = {
                "place_name": f"Geographic Coordinate ({lat:.4f}, {lon:.4f})",
                "display_name": f"Sector Latitude {lat:.4f}, Longitude {lon:.4f}, Delhi NCR Region",
                "latitude": lat,
                "longitude": lon,
                "address": {},
                "type": "coordinate"
            }

        global_cache.set(cache_key, res, ttl_seconds=1800)
        return res

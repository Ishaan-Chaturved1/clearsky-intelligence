import math
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.data_sources.base import global_cache
from app.models.investigation import CandidateSource, SourceCategory
from app.investigation.normalization import validate_coordinates


class LocalSourceFilterConfig(BaseModel):
    """
    Search radii and query parameters for local geographic features.
    """
    radius_km: float = Field(default=3.0, ge=0.5, le=15.0, description="Search radius in kilometers around the event location")
    max_candidates: int = Field(default=25, ge=1, le=100, description="Maximum candidate sources to return after deduplication")
    include_highways: bool = True
    include_industrial: bool = True
    include_construction: bool = True
    include_waste_facilities: bool = True


class LocalSourceInvestigationResult(BaseModel):
    """
    Container for mapped candidate local emission sources.
    """
    status: str = Field(default="SUCCESS", description="SUCCESS, EMPTY, PARTIAL, PROVIDER_ERROR")
    center_latitude: float
    center_longitude: float
    search_radius_km: float
    candidates: List[CandidateSource] = Field(default_factory=list)
    total_candidates_found: int = 0
    query_timestamp: datetime
    data_source_mode: str = Field(default="LIVE", description="LIVE, CACHED, UNAVAILABLE")
    provider_name: str = "OpenStreetMap Overpass API"
    data_limitations: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two geographic coordinates in kilometers."""
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def calculate_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes initial compass bearing from point 1 to point 2 in degrees (0-360)."""
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    diff_lon = math.radians(lon2 - lon1)
    x = math.sin(diff_lon) * math.cos(lat2_r)
    y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(diff_lon)
    initial_bearing = math.atan2(x, y)
    return (math.degrees(initial_bearing) + 360.0) % 360.0


class LocalSourceInvestigator:
    """
    Identifies proximate geographic features (industrial areas, arterial roads,
    construction parcels, landfills) mapped in OpenStreetMap.
    
    IMPORTANT SCIENTIFIC GUARDRAIL:
    Presence of a mapped feature in OpenStreetMap does NOT prove that it is actively emitting,
    nor does it confirm causation of any pollution elevation. All mapped features are labeled
    strictly as UNVERIFIED candidate hypotheses.
    """

    def __init__(self):
        self.endpoint = settings.OVERPASS_API_URL
        self.timeout = settings.API_TIMEOUT_SECONDS

    async def find_candidate_sources(
        self,
        latitude: float,
        longitude: float,
        config: Optional[LocalSourceFilterConfig] = None
    ) -> LocalSourceInvestigationResult:
        """
        Queries OpenStreetMap Overpass for relevant emission infrastructure within the search radius.
        """
        conf = config or LocalSourceFilterConfig()
        valid_lat, valid_lon = validate_coordinates(latitude, longitude, allow_none=False)

        now_utc = datetime.now(timezone.utc)
        radius_meters = int(conf.radius_km * 1000.0)
        cache_key = f"osm_local_src_{round(valid_lat, 3)}_{round(valid_lon, 3)}_{radius_meters}"
        
        cached = global_cache.get(cache_key)
        if cached is not None:
            return LocalSourceInvestigationResult(
                status="SUCCESS" if cached.get("candidates") else "EMPTY",
                center_latitude=valid_lat,
                center_longitude=valid_lon,
                search_radius_km=conf.radius_km,
                candidates=[CandidateSource(**c) for c in cached.get("candidates", [])],
                total_candidates_found=len(cached.get("candidates", [])),
                query_timestamp=now_utc,
                data_source_mode="CACHED",
                data_limitations=cached.get("limitations", [
                    "Retrieved from cached OpenStreetMap Overpass query.",
                    "Presence of mapped infrastructure does not indicate active emission or confirm causation."
                ])
            )

        # Build Overpass QL query targeting distinct infrastructure classes
        query_clauses = []
        if conf.include_construction:
            query_clauses.append(f'node["landuse"="construction"](around:{radius_meters},{valid_lat},{valid_lon});')
            query_clauses.append(f'way["landuse"="construction"](around:{radius_meters},{valid_lat},{valid_lon});')
            query_clauses.append(f'way["highway"="construction"](around:{radius_meters},{valid_lat},{valid_lon});')
            query_clauses.append(f'way["building"="construction"](around:{radius_meters},{valid_lat},{valid_lon});')
        if conf.include_industrial:
            query_clauses.append(f'way["landuse"="industrial"](around:{radius_meters},{valid_lat},{valid_lon});')
            query_clauses.append(f'relation["landuse"="industrial"](around:{radius_meters},{valid_lat},{valid_lon});')
            query_clauses.append(f'node["industrial"](around:{radius_meters},{valid_lat},{valid_lon});')
            query_clauses.append(f'node["power"="plant"](around:{radius_meters},{valid_lat},{valid_lon});')
            query_clauses.append(f'way["power"="plant"](around:{radius_meters},{valid_lat},{valid_lon});')
        if conf.include_highways:
            query_clauses.append(f'way["highway"~"motorway|trunk|primary"](around:{radius_meters},{valid_lat},{valid_lon});')
        if conf.include_waste_facilities:
            query_clauses.append(f'way["landuse"="landfill"](around:{radius_meters},{valid_lat},{valid_lon});')
            query_clauses.append(f'node["amenity"="waste_disposal"](around:{radius_meters},{valid_lat},{valid_lon});')

        if not query_clauses:
            return LocalSourceInvestigationResult(
                status="EMPTY",
                center_latitude=valid_lat,
                center_longitude=valid_lon,
                search_radius_km=conf.radius_km,
                candidates=[],
                total_candidates_found=0,
                query_timestamp=now_utc,
                data_source_mode="LIVE",
                data_limitations=["No feature categories were enabled for investigation."]
            )

        overpass_ql = f"""
        [out:json][timeout:10];
        (
          {' '.join(query_clauses)}
        );
        out center tags;
        """

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(self.endpoint, data={"data": overpass_ql})
                if resp.status_code != 200:
                    logger.warning(f"Overpass query returned HTTP {resp.status_code}")
                    return LocalSourceInvestigationResult(
                        status="PROVIDER_ERROR",
                        center_latitude=valid_lat,
                        center_longitude=valid_lon,
                        search_radius_km=conf.radius_km,
                        candidates=[],
                        total_candidates_found=0,
                        query_timestamp=now_utc,
                        data_source_mode="UNAVAILABLE",
                        error_message=f"Overpass API HTTP {resp.status_code}",
                        data_limitations=["Overpass provider temporarily unavailable; upstream rate limiting or maintenance."]
                    )

                elements = resp.json().get("elements", [])
                candidates = self._parse_elements(elements, valid_lat, valid_lon, conf.max_candidates, conf.radius_km)

                limitations = [
                    "OpenStreetMap vector data is crowd-sourced and may omit unmapped industrial or construction activities.",
                    "Presence of mapped infrastructure does not indicate active emission or prove causation of pollution elevations.",
                    "All candidate sources are unverified hypotheses subject to meteorological transport and chemical validation."
                ]

                # Cache response for 6 hours
                cache_payload = {
                    "candidates": [c.model_dump() for c in candidates],
                    "limitations": limitations
                }
                global_cache.set(cache_key, cache_payload, ttl_seconds=21600)

                return LocalSourceInvestigationResult(
                    status="SUCCESS" if candidates else "EMPTY",
                    center_latitude=valid_lat,
                    center_longitude=valid_lon,
                    search_radius_km=conf.radius_km,
                    candidates=candidates,
                    total_candidates_found=len(candidates),
                    query_timestamp=now_utc,
                    data_source_mode="LIVE",
                    data_limitations=limitations
                )

        except Exception as exc:
            logger.warning(f"Error querying local sources via Overpass: {exc}")
            return LocalSourceInvestigationResult(
                status="PROVIDER_ERROR",
                center_latitude=valid_lat,
                center_longitude=valid_lon,
                search_radius_km=conf.radius_km,
                candidates=[],
                total_candidates_found=0,
                query_timestamp=now_utc,
                data_source_mode="UNAVAILABLE",
                error_message=str(exc),
                data_limitations=["Local source query failed due to upstream network or timeout exception."]
            )

    @staticmethod
    def _bearing_to_compass(bearing: float) -> str:
        """Converts bearing in degrees to 8-point compass direction."""
        dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        idx = int((bearing + 22.5) // 45.0) % 8
        return dirs[idx]

    def _parse_elements(
        self,
        elements: List[Dict[str, Any]],
        valid_lat: float,
        valid_lon: float,
        max_candidates: int = 25,
        radius_km: float = 15.0
    ) -> List[CandidateSource]:
        candidates: List[CandidateSource] = []
        seen_keys = set()

        for el in elements:
            tags = el.get("tags", {})
            f_lat = el.get("lat") or el.get("center", {}).get("lat")
            f_lon = el.get("lon") or el.get("center", {}).get("lon")
            if f_lat is None or f_lon is None:
                continue

            dist_km = haversine_distance_km(valid_lat, valid_lon, f_lat, f_lon)
            if dist_km > radius_km:
                continue

            cat = SourceCategory.OTHER
            raw_name = tags.get("name")
            desc = ""

            if tags.get("landuse") == "construction" or tags.get("highway") == "construction" or tags.get("building") == "construction":
                cat = SourceCategory.CONSTRUCTION_DUST
                desc = f"Construction site: {tags.get('description') or tags.get('construction') or 'active work'}"
            elif tags.get("landuse") == "industrial" or "industrial" in tags:
                cat = SourceCategory.INDUSTRIAL_EMISSIONS
                desc = f"Industrial facility/estate: {tags.get('industrial') or tags.get('operator') or 'commercial manufacturing'}"
            elif tags.get("power") == "plant":
                cat = SourceCategory.POWER_GENERATION
                desc = f"Power plant: {tags.get('plant:source') or 'generation facility'}"
            elif tags.get("landuse") == "landfill" or tags.get("amenity") == "waste_disposal":
                cat = SourceCategory.LANDFILL_FIRE
                desc = f"Waste/landfill infrastructure: {tags.get('landfill') or 'solid waste disposal'}"
            elif "highway" in tags:
                cat = SourceCategory.ROAD_DUST
                highway_type = tags.get("highway")
                desc = f"Major transport corridor ({highway_type}): {tags.get('ref') or 'high-density roadway'}"

            name = raw_name or desc.split(":")[0]
            dedup_key = f"{cat.value}_{name}_{round(f_lat, 3)}_{round(f_lon, 3)}"
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            bearing = calculate_bearing_deg(valid_lat, valid_lon, f_lat, f_lon)
            bearing_label = self._bearing_to_compass(bearing)

            source_item = CandidateSource(
                source_id=f"osm_{el.get('type', 'feature')}_{el.get('id', uuid.uuid4().hex[:8])}",
                category=cat,
                name=name,
                description=f"{desc} (~{dist_km:.2f} km {bearing_label} of event). DOES NOT confirm active emissions.",
                latitude=round(f_lat, 5),
                longitude=round(f_lon, 5),
                geographic_region="Local Vicinity",
                provider="OpenStreetMap Overpass API",
                verification_status="UNVERIFIED_CANDIDATE",
                data_quality_info="Crowd-sourced OpenStreetMap vector feature. Activity and emission rates not instrumented."
            )
            candidates.append(source_item)
            if len(candidates) >= max_candidates:
                break

        candidates.sort(key=lambda c: haversine_distance_km(valid_lat, valid_lon, c.latitude, c.longitude) if c.latitude and c.longitude else 999.0)
        return candidates

    # Alias for method naming flexibility
    find_nearby_sources = find_candidate_sources



# Export alias matching both naming conventions
LocalSourcesService = LocalSourceInvestigator


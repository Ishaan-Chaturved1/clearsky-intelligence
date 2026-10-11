import math
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import logger
from app.data_sources.firms_client import FirmsClient
from app.models.investigation import CandidateSource, SourceCategory
from app.investigation.normalization import validate_coordinates
from app.investigation.transport_model import TrajectoryPoint


class FireDetectionRecord(BaseModel):
    """
    Individual satellite active fire thermal anomaly record.
    """
    fire_id: str
    latitude: float
    longitude: float
    detection_time_utc: Optional[str] = None
    distance_from_event_km: float
    bearing_from_event_deg: float
    bearing_compass: str
    brightness: Any
    confidence: Optional[str] = None
    satellite_instrument: str = "VIIRS_SNPP_NRT"
    is_upwind: bool = False
    distance_to_trajectory_km: Optional[float] = None
    plausible_smoke_corridor: bool = False


class SatelliteFireCorrelationResult(BaseModel):
    """
    Result of satellite thermal anomaly correlation with event and transport path.
    """
    status: str = Field(default="SUCCESS", description="FIRES_DETECTED, NO_FIRES_DETECTED, CREDENTIALS_MISSING, PROVIDER_ERROR")
    event_latitude: float
    event_longitude: float
    search_radius_km: float
    total_fires_in_region: int = 0
    upwind_fires_count: int = 0
    trajectory_correlated_fires_count: int = 0
    closest_fire_distance_km: Optional[float] = None
    closest_fire_bearing_compass: Optional[str] = None
    fire_records: List[FireDetectionRecord] = Field(default_factory=list)
    candidate_sources: List[CandidateSource] = Field(default_factory=list)
    data_source_mode: str = "LIVE"
    provider_name: str = "NASA FIRMS (VIIRS NRT)"
    query_timestamp: datetime
    error_message: Optional[str] = None
    limitations: List[str] = Field(default_factory=list)


class SatelliteFireCorrelator:
    """
    Correlates NASA FIRMS satellite thermal fire detections with an observed pollution event
    and its calculated atmospheric backward transport trajectory.
    
    IMPORTANT SCIENTIFIC GUARDRAILS:
    1. A satellite thermal anomaly indicates a heat signature; it does NOT confirm the fuel type
       (stubble, municipal waste, forest understory, or industrial flaring).
    2. Proximity to a backward transport trajectory indicates plausibility, NOT causal proof.
    3. Quantitative source attribution percentages cannot be inferred from fire counts alone.
    """

    def __init__(self):
        self.firms_client = FirmsClient()

    async def correlate_fires(
        self,
        event_latitude: Optional[float] = None,
        event_longitude: Optional[float] = None,
        search_radius_km: float = 75.0,
        wind_direction_deg: Optional[float] = None,
        trajectory_points: Optional[List[TrajectoryPoint]] = None,
        event_lat: Optional[float] = None,
        event_lon: Optional[float] = None,
        trajectory: Optional[List[TrajectoryPoint]] = None,
        days_lookback: int = 1
    ) -> SatelliteFireCorrelationResult:
        """
        Retrieves real NASA FIRMS fire detections and determines spatial alignment
        with the event location and the atmospheric transport trajectory.
        """
        lat_val = event_latitude if event_latitude is not None else event_lat
        lon_val = event_longitude if event_longitude is not None else event_lon
        traj_val = trajectory_points if trajectory_points is not None else trajectory

        if lat_val is None or lon_val is None:
            raise ValueError("Event coordinates must be provided")

        valid_lat, valid_lon = validate_coordinates(lat_val, lon_val, allow_none=False)
        now_utc = datetime.now(timezone.utc)
        radius = max(10.0, min(150.0, search_radius_km))

        # Check API key presence or client availability
        if not settings.NASA_FIRMS_MAP_KEY or not self.firms_client.is_available():
            return SatelliteFireCorrelationResult(
                status="CREDENTIALS_MISSING",
                event_latitude=valid_lat,
                event_longitude=valid_lon,
                search_radius_km=radius,
                total_fires_in_region=0,
                data_source_mode="UNAVAILABLE",
                query_timestamp=now_utc,
                error_message="NASA_FIRMS_MAP_KEY environment variable is not configured",
                limitations=[
                    "NASA FIRMS integration requires a valid NASA Earthdata Map Key.",
                    "No satellite fire telemetry could be retrieved without credentials.",
                    "Absence of fire detections reflects unconfigured provider, not absence of active fires."
                ]
            )

        # Delegate query to existing FirmsClient
        res = await self.firms_client.check_nearby_fires(
            zone_lat=valid_lat,
            zone_lon=valid_lon,
            wind_direction_deg=wind_direction_deg,
            radius_km=radius
        )

        if not res.is_success:
            return SatelliteFireCorrelationResult(
                status="PROVIDER_ERROR",
                event_latitude=valid_lat,
                event_longitude=valid_lon,
                search_radius_km=radius,
                total_fires_in_region=0,
                data_source_mode="UNAVAILABLE",
                query_timestamp=now_utc,
                error_message=res.error_message or "NASA FIRMS query failed",
                limitations=["NASA FIRMS upstream request encountered a network or server error."]
            )

        fire_data = res.data or {}
        details = fire_data.get("details", [])
        total_count = fire_data.get("nearby_fires_count", 0)
        closest_dist = fire_data.get("closest_fire_distance_km")

        fire_records: List[FireDetectionRecord] = []
        candidate_sources: List[CandidateSource] = []
        upwind_count = 0
        traj_correlated_count = 0

        for idx, item in enumerate(details):
            f_lat = item.get("latitude")
            f_lon = item.get("longitude")
            f_dist = item.get("distance_km", 0.0)
            f_bearing = item.get("bearing_deg", 0.0)
            is_upwind = item.get("is_upwind_smoke_path", False) or item.get("is_upwind", False)
            brightness = item.get("brightness", "N/A")

            if is_upwind:
                upwind_count += 1

            # Check minimum distance to any point along the backward trajectory path
            min_dist_to_traj = None
            plausible_corridor = False
            if traj_val and len(traj_val) > 0:
                dist_candidates = [
                    self._haversine_km(f_lat, f_lon, pt.latitude, pt.longitude)
                    for pt in traj_val
                ]
                min_dist_to_traj = min(dist_candidates)
                # Within 25 km of the trajectory corridor
                if min_dist_to_traj <= 25.0:
                    plausible_corridor = True
                    traj_correlated_count += 1

            bearing_compass = self._bearing_to_compass(f_bearing)

            rec = FireDetectionRecord(
                fire_id=f"firms_viirs_{idx+1}",
                latitude=f_lat,
                longitude=f_lon,
                distance_from_event_km=f_dist,
                bearing_from_event_deg=f_bearing,
                bearing_compass=bearing_compass,
                brightness=brightness,
                is_upwind=is_upwind,
                distance_to_trajectory_km=round(min_dist_to_traj, 1) if min_dist_to_traj is not None else None,
                plausible_smoke_corridor=plausible_corridor
            )
            fire_records.append(rec)

            # Generate CandidateSource entity for each cluster/detection
            if plausible_corridor or is_upwind or f_dist <= 25.0:
                candidate_sources.append(CandidateSource(
                    source_id=f"fire_cand_{idx+1}",
                    category=SourceCategory.BIOMASS_BURNING,
                    name=f"Thermal Anomaly #{idx+1} ({bearing_compass})",
                    description=(
                        f"Active thermal detection ~{f_dist:.1f} km {bearing_compass} of event. "
                        f"{'Aligned with upwind transport corridor.' if plausible_corridor else 'Outside primary transport corridor.'} "
                        "Satellite detection DOES NOT establish specific material burning or causation."
                    ),
                    latitude=f_lat,
                    longitude=f_lon,
                    geographic_region=f"{bearing_compass} Regional Sector",
                    provider="NASA FIRMS VIIRS",
                    verification_status="CANDIDATE" if plausible_corridor else "UNVERIFIED",
                    data_quality_info="Satellite radiometric brightness detection; surface fuel and combustion efficiency unverified."
                ))

        closest_compass = None
        if fire_records:
            closest_compass = fire_records[0].bearing_compass

        status = "FIRES_DETECTED" if total_count > 0 else "NO_FIRES_DETECTED"
        mode = "CACHED" if res.is_cached else "LIVE"

        limitations = [
            "Satellite thermal sensors detect active fires at time of overpass only (~1-2 times daily per satellite).",
            "Cloud cover, heavy haze, and small or low-temperature fires may prevent thermal detection.",
            "Presence of thermal anomalies along a transport corridor indicates potential biomass smoke influence, not quantitative attribution."
        ]

        return SatelliteFireCorrelationResult(
            status=status,
            event_latitude=valid_lat,
            event_longitude=valid_lon,
            search_radius_km=radius,
            total_fires_in_region=total_count,
            upwind_fires_count=upwind_count,
            trajectory_correlated_fires_count=traj_correlated_count,
            closest_fire_distance_km=closest_dist,
            closest_fire_bearing_compass=closest_compass,
            fire_records=fire_records,
            candidate_sources=candidate_sources,
            data_source_mode=mode,
            provider_name="NASA FIRMS (VIIRS NRT)",
            query_timestamp=now_utc,
            limitations=limitations
        )

    @staticmethod
    def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c

    @staticmethod
    def _bearing_to_compass(bearing: float) -> str:
        dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        idx = int((bearing + 22.5) // 45.0) % 8
        return dirs[idx]

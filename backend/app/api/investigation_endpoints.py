import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.repositories import get_repository
from app.models.investigation import (
    CandidateSource,
    EnvironmentalObservation,
    Investigation,
    InvestigationReport,
    PollutionEvent,
    ProvenanceType,
)
from app.investigation.local_sources import (
    LocalSourceInvestigator,
    LocalSourceFilterConfig,
    LocalSourceInvestigationResult,
)
from app.investigation.transport_model import (
    AtmosphericTransportService,
    TransportAssessment,
)
from app.investigation.satellite_service import (
    SatelliteFireCorrelator,
    SatelliteFireCorrelationResult,
)
from app.investigation.evidence_correlator import (
    EvidenceCorrelator,
    InvestigationDossier,
)
from app.investigation.event_detector import (
    PollutionEventDetector,
    EventDetectionConfig,
)
from app.investigation.normalization import normalize_timestamp

router = APIRouter(prefix="/investigation", tags=["Pollution Investigation"])

# In-memory transient store for recent investigation dossiers (FIFO capped at 50)
_DOSSIER_STORE: OrderedDict[str, InvestigationDossier] = OrderedDict()
_MAX_STORED_DOSSIERS = 50


class InvestigationAnalyzeRequest(BaseModel):
    """
    Request payload to launch an evidence-driven source investigation.
    """
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Target location latitude (-90 to +90)")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Target location longitude (-180 to +180)")
    zone_id: Optional[str] = Field(None, description="Known monitoring zone ID (e.g. DEL-AV-01). Resolves coordinates automatically.")
    pollutant: str = Field(default="PM2.5", description="Primary pollutant under investigation (e.g. PM2.5, PM10)")
    lookback_hours: int = Field(default=12, ge=1, le=48, description="Atmospheric transport look-back window in hours (1-48)")
    radius_km: float = Field(default=5.0, ge=0.5, le=25.0, description="Search radius for local infrastructure features in km")
    pm10: Optional[float] = Field(None, ge=0.0, description="Optional observed PM10 concentration (ug/m3) for ratio analysis")
    pm25: Optional[float] = Field(None, ge=0.0, description="Optional observed PM2.5 concentration (ug/m3) for ratio analysis")
    reference_time: Optional[datetime] = Field(None, description="Event reference time (defaults to current UTC)")


class DossierSummary(BaseModel):
    investigation_id: str
    target_scope: str
    target_latitude: float
    target_longitude: float
    pollutants: List[str]
    supporting_evidence_count: int
    contradicting_evidence_count: int
    confidence_assessment: str
    generated_at: datetime


def _save_dossier(dossier: InvestigationDossier) -> None:
    if len(_DOSSIER_STORE) >= _MAX_STORED_DOSSIERS:
        _DOSSIER_STORE.popitem(last=False)
    _DOSSIER_STORE[dossier.investigation_id] = dossier


@router.get("/local-sources", response_model=LocalSourceInvestigationResult)
async def get_local_candidate_sources(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude"),
    radius_km: float = Query(default=3.0, ge=0.5, le=15.0, description="Search radius in km (0.5 to 15.0)"),
    max_candidates: int = Query(default=25, ge=1, le=100, description="Max candidate features to return")
):
    """
    Query OpenStreetMap Overpass for candidate local emission features (roads, industrial zones,
    construction, waste facilities) within a geographic radius.
    """
    service = LocalSourceInvestigator()
    config = LocalSourceFilterConfig(radius_km=radius_km, max_candidates=max_candidates)
    return await service.find_candidate_sources(latitude, longitude, config)


@router.get("/transport", response_model=TransportAssessment)
async def get_atmospheric_transport(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude"),
    lookback_hours: int = Query(default=12, ge=1, le=48, description="Look-back hours (1 to 48)"),
    reference_time: Optional[datetime] = Query(default=None, description="Event reference time (ISO 8601)")
):
    """
    Estimate backward atmospheric transport trajectory using hourly meteorological observations
    from Open-Meteo. Reconstructs air parcel origins using kinematic wind advection.
    """
    service = AtmosphericTransportService()
    return await service.calculate_backward_trajectory(
        latitude=latitude,
        longitude=longitude,
        lookback_hours=lookback_hours,
        event_time=reference_time
    )


@router.get("/satellite-fires", response_model=SatelliteFireCorrelationResult)
async def get_satellite_fire_correlation(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude"),
    radius_km: float = Query(default=50.0, ge=5.0, le=200.0, description="Search radius in km (5 to 200)"),
    days: int = Query(default=1, ge=1, le=5, description="Lookback window in days (1 to 5)")
):
    """
    Query NASA FIRMS VIIRS satellite active fire thermal anomalies in the region and correlate
    with the target coordinates.
    """
    correlator = SatelliteFireCorrelator()
    return await correlator.correlate_fires(
        event_lat=latitude,
        event_lon=longitude,
        search_radius_km=radius_km,
        days_lookback=days
    )


async def _execute_investigation(
    lat: float,
    lon: float,
    scope_name: str,
    pollutant: str,
    lookback_hours: int,
    radius_km: float,
    pm10: Optional[float],
    pm25: Optional[float],
    reference_time: Optional[datetime],
    zone_id: Optional[str] = None
) -> InvestigationDossier:
    ref_time = normalize_timestamp(reference_time) if reference_time is not None else datetime.now(timezone.utc)
    repo = get_repository()

    # Step 1: Detect or construct PollutionEvent from validated telemetry
    detected_event: Optional[PollutionEvent] = None
    if zone_id:
        try:
            readings = repo.get_reading_history(zone_id, limit=24)
            if readings and len(readings) >= 2:
                obs_list: List[EnvironmentalObservation] = []
                for r in readings:
                    r_time = normalize_timestamp(r.timestamp) if r.timestamp is not None else None
                    if not r_time:
                        continue
                    p_val = r.pm25.value if pollutant.upper() == "PM2.5" else r.pm10.value
                    if p_val is not None and p_val >= 0:
                        obs_list.append(EnvironmentalObservation(
                            observation_id=f"obs_{zone_id}_{int(r_time.timestamp())}",
                            category="air_quality",
                            provider_id="cpcb_station",
                            observation_timestamp=r_time,
                            retrieval_timestamp=datetime.now(timezone.utc),
                            latitude=lat,
                            longitude=lon,
                            station_id=zone_id,
                            pollutant=pollutant,
                            value=p_val,
                            unit="ug/m3",
                            provenance=ProvenanceType.GROUND_MEASUREMENT,
                            data_quality_status="VALID",
                            freshness_status="FRESH"
                        ))
                detector = PollutionEventDetector(EventDetectionConfig(max_observation_age_hours=48.0))
                events = detector.detect_events_from_series(obs_list, pollutant=pollutant, reference_time=ref_time)
                if events:
                    detected_event = events[0]
        except Exception as e:
            logger.warning(f"Error checking reading history for zone {zone_id}: {e}")

    # Extract observed pm concentrations if not explicitly passed
    if pm25 is None and zone_id:
        latest = repo.get_latest_reading(zone_id)
        if latest and latest.pm25.value is not None:
            pm25 = latest.pm25.value
    if pm10 is None and zone_id:
        latest = repo.get_latest_reading(zone_id)
        if latest and latest.pm10.value is not None:
            pm10 = latest.pm10.value

    # Step 2: Query candidate local features (OpenStreetMap)
    local_service = LocalSourceInvestigator()
    local_res = await local_service.find_candidate_sources(
        lat, lon, LocalSourceFilterConfig(radius_km=radius_km, max_candidates=30)
    )

    # Step 3: Estimate backward atmospheric transport (Open-Meteo)
    transport_service = AtmosphericTransportService()
    transport_res = await transport_service.calculate_backward_trajectory(
        latitude=lat, longitude=lon, lookback_hours=lookback_hours, event_time=ref_time
    )

    # Step 4: Correlate satellite thermal fire anomalies (NASA FIRMS)
    fire_correlator = SatelliteFireCorrelator()
    fire_res = await fire_correlator.correlate_fires(
        event_lat=lat,
        event_lon=lon,
        trajectory=transport_res.trajectory_points,
        search_radius_km=min(radius_km * 4.0, 150.0),
        days_lookback=max(1, int(lookback_hours / 24) + 1)
    )

    # Step 5: Synthesize evidence ledger and investigation dossier
    correlator = EvidenceCorrelator()
    dossier = correlator.synthesize_investigation(
        event=detected_event,
        latitude=lat,
        longitude=lon,
        local_sources_res=local_res,
        transport_res=transport_res,
        satellite_res=fire_res,
        pm10=pm10,
        pm25=pm25,
        geographic_scope=scope_name,
        reference_time=ref_time
    )

    _save_dossier(dossier)
    return dossier


@router.post("/analyze", response_model=InvestigationDossier)
async def analyze_pollution_event_post(req: InvestigationAnalyzeRequest):
    """
    Launch an evidence-driven air pollution investigation (POST).
    Evaluates real local geographic features, backward atmospheric transport,
    and satellite active fire thermal anomalies to produce a traceable investigation dossier.
    """
    repo = get_repository()
    lat: Optional[float] = req.latitude
    lon: Optional[float] = req.longitude
    scope_name = "Target Coordinates"

    if req.zone_id:
        zone = repo.get_zone(req.zone_id)
        if not zone:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone '{req.zone_id}' not found in registered monitoring stations."
            )
        lat = zone.latitude
        lon = zone.longitude
        scope_name = f"{zone.name} ({zone.zone_id})"
    elif lat is None or lon is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Must specify either 'zone_id' or valid ('latitude', 'longitude') coordinates."
        )

    return await _execute_investigation(
        lat=lat,
        lon=lon,
        scope_name=scope_name,
        pollutant=req.pollutant,
        lookback_hours=req.lookback_hours,
        radius_km=req.radius_km,
        pm10=req.pm10,
        pm25=req.pm25,
        reference_time=req.reference_time,
        zone_id=req.zone_id
    )


@router.get("/analyze", response_model=InvestigationDossier)
async def analyze_pollution_event_get(
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Latitude"),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0, description="Longitude"),
    zone_id: Optional[str] = Query(None, description="Known monitoring zone ID (e.g. DEL-AV-01)"),
    pollutant: str = Query(default="PM2.5", description="Primary pollutant (PM2.5, PM10)"),
    lookback_hours: int = Query(default=12, ge=1, le=48, description="Look-back hours (1-48)"),
    radius_km: float = Query(default=5.0, ge=0.5, le=25.0, description="Search radius in km"),
    pm10: Optional[float] = Query(None, ge=0.0, description="Observed PM10 in ug/m3"),
    pm25: Optional[float] = Query(None, ge=0.0, description="Observed PM2.5 in ug/m3")
):
    """
    Launch an evidence-driven air pollution investigation (GET).
    Convenience endpoint for frontend queries and browser exploration.
    """
    req = InvestigationAnalyzeRequest(
        latitude=latitude,
        longitude=longitude,
        zone_id=zone_id,
        pollutant=pollutant,
        lookback_hours=lookback_hours,
        radius_km=radius_km,
        pm10=pm10,
        pm25=pm25
    )
    return await analyze_pollution_event_post(req)


@router.get("/dossiers/{investigation_id}", response_model=InvestigationDossier)
def get_investigation_dossier_by_id(investigation_id: str):
    """
    Retrieve an investigation dossier by ID from the active session cache.
    """
    dossier = _DOSSIER_STORE.get(investigation_id)
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation dossier '{investigation_id}' not found in active session cache."
        )
    return dossier


@router.get("/dossiers", response_model=List[DossierSummary])
def list_recent_investigation_dossiers():
    """
    List summaries of recent investigations stored in the active session cache.
    """
    summaries: List[DossierSummary] = []
    for d in reversed(list(_DOSSIER_STORE.values())):
        summaries.append(DossierSummary(
            investigation_id=d.investigation_id,
            target_scope=d.target_scope,
            target_latitude=d.target_latitude,
            target_longitude=d.target_longitude,
            pollutants=d.investigation.pollutants_under_investigation,
            supporting_evidence_count=d.report.evidence_supporting_count,
            contradicting_evidence_count=d.report.evidence_contradicting_count,
            confidence_assessment=d.report.confidence_assessment,
            generated_at=d.generated_at
        ))
    return summaries

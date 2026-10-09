from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Header, Response
from app.core.config import settings
from app.core.logging import logger
from app.models.domain import Zone, DecisionRecord, EnvironmentalReading, DecisionType, DataMode, AlertRecord
from app.schemas.api_models import (
    SystemOverviewResponse,
    ZoneWithLatest,
    WaterSavingsAnalyticsResponse,
    SourcesStatusResponse,
    SourceDetail,
    MethodologyResponse,
    MethodologyRule,
    AdminRefreshRequest,
    AdminRefreshResponse,
    AiDailyBriefResponse
)
from app.repositories.local_repository import SQLiteRepository
from app.repositories.dynamodb_repository import DynamoDBRepository
from app.services.ingestion_service import IngestionService
from app.analytics.water_efficiency import WaterEfficiencyAnalytics
from app.services.ai_brief_service import AiBriefService

router = APIRouter()

# Select repository based on environment
if settings.STORAGE_BACKEND == "dynamodb":
    repository = DynamoDBRepository(region_name=settings.AWS_REGION)
else:
    repository = SQLiteRepository(settings.SQLITE_DB_PATH)

ingestion_service = IngestionService(repository)
analytics_service = WaterEfficiencyAnalytics(
    default_baseline_per_zone_per_day=settings.DEFAULT_BASELINE_INTERVENTIONS_PER_ZONE_PER_DAY,
    default_liters_per_intervention=settings.DEFAULT_ASSUMED_LITERS_PER_INTERVENTION
)
ai_brief_service = AiBriefService()

@router.get("/health")
def get_health():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "storage": settings.STORAGE_BACKEND,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }

@router.get("/overview", response_model=SystemOverviewResponse)
def get_system_overview():
    zones = repository.list_zones()
    decisions = repository.list_latest_decisions()

    candidates = sum(1 for d in decisions if d.decision == DecisionType.INTERVENTION_RECOMMENDED)
    discouraged = sum(1 for d in decisions if d.decision == DecisionType.INTERVENTION_NOT_RECOMMENDED)
    advisory = sum(1 for d in decisions if d.decision == DecisionType.ADVISORY_ONLY)

    # 7-day water analytics for overview metric
    history = repository.get_decision_history(limit=500)
    savings = analytics_service.calculate_savings(
        number_of_zones=len(zones) if zones else 12,
        number_of_days=7,
        decision_records=history,
        is_simulation=True,
        data_mode=DataMode.DEMO
    )

    last_refresh = decisions[0].scored_at if decisions else datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    has_live = any(d.data_mode == DataMode.LIVE for d in decisions)
    mode = DataMode.LIVE if has_live else DataMode.DEMO

    return SystemOverviewResponse(
        total_monitored_zones=len(zones),
        intervention_candidates=candidates,
        intervention_discouraged=discouraged,
        advisory_only_zones=advisory,
        estimated_water_saved_liters=savings.estimated_water_saved_liters,
        intervention_reduction_percent=savings.intervention_reduction_percent,
        last_data_refresh=last_refresh,
        data_mode=mode,
        sources_coverage={
            "openaq": "Available (Ground Stations)",
            "open_meteo": "Active (Forecast & Models)",
            "nasa_firms": "Active (Thermal Anomaly Grid)",
            "osm_overpass": "Cached (Infrastructure GIS)"
        }
    )

@router.get("/zones", response_model=List[ZoneWithLatest])
def list_zones_with_status():
    zones = repository.list_zones()
    results = []
    for z in zones:
        reading = repository.get_latest_reading(z.zone_id)
        decision = repository.get_latest_decision(z.zone_id)
        results.append(ZoneWithLatest(
            zone=z,
            latest_reading=reading,
            latest_decision=decision
        ))
    return results

@router.get("/zones/{zone_id}", response_model=ZoneWithLatest)
def get_zone_detail(zone_id: str):
    zone = repository.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")
    reading = repository.get_latest_reading(zone_id)
    decision = repository.get_latest_decision(zone_id)
    return ZoneWithLatest(
        zone=zone,
        latest_reading=reading,
        latest_decision=decision
    )

@router.get("/zones/{zone_id}/history")
def get_zone_history(zone_id: str, limit: int = Query(50, ge=1, le=200)):
    zone = repository.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")
    readings = repository.get_reading_history(zone_id, limit=limit)
    decisions = repository.get_decision_history(zone_id=zone_id, limit=limit)
    return {
        "zone_id": zone_id,
        "readings": readings,
        "decisions": decisions
    }

@router.get("/decisions/latest", response_model=List[DecisionRecord])
def get_latest_decisions():
    return repository.list_latest_decisions()

@router.get("/decisions/history", response_model=List[DecisionRecord])
def get_decision_history(zone_id: Optional[str] = None, limit: int = Query(100, ge=1, le=500)):
    return repository.get_decision_history(zone_id=zone_id, limit=limit)

@router.get("/analytics/water-savings", response_model=WaterSavingsAnalyticsResponse)
def get_water_savings(
    days: int = Query(7, ge=1, le=30),
    baseline_rate: Optional[float] = Query(None, ge=0.0, le=10.0),
    liters_per_op: Optional[float] = Query(None, ge=100.0, le=50000.0)
):
    zones = repository.list_zones()
    zone_count = len(zones) if zones else 12
    history = repository.get_decision_history(limit=days * zone_count * 2)

    return analytics_service.calculate_savings(
        number_of_zones=zone_count,
        number_of_days=days,
        decision_records=history,
        baseline_per_zone_per_day=baseline_rate,
        assumed_liters_per_intervention=liters_per_op,
        is_simulation=True,
        data_mode=DataMode.DEMO
    )

@router.get("/analytics/water-savings/export")
def export_water_savings_csv(
    days: int = Query(7, ge=1, le=30),
    baseline_rate: Optional[float] = Query(None, ge=0.0, le=10.0),
    liters_per_op: Optional[float] = Query(None, ge=100.0, le=50000.0)
):
    zones = repository.list_zones()
    zone_count = len(zones) if zones else 12
    history = repository.get_decision_history(limit=days * zone_count * 2)

    analytics = analytics_service.calculate_savings(
        number_of_zones=zone_count,
        number_of_days=days,
        decision_records=history,
        baseline_per_zone_per_day=baseline_rate,
        assumed_liters_per_intervention=liters_per_op,
        is_simulation=True,
        data_mode=DataMode.DEMO
    )
    csv_text = analytics_service.generate_csv_export(analytics)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=clearsky_water_savings_{days}days.csv"}
    )

@router.get("/analytics/overview")
def get_analytics_overview():
    zones = repository.list_zones()
    zone_count = len(zones) if zones else 12
    history = repository.get_decision_history(limit=500)
    res_7d = analytics_service.calculate_savings(zone_count, 7, history)
    res_30d = analytics_service.calculate_savings(zone_count, 30, history)
    return {
        "seven_day": res_7d,
        "thirty_day": res_30d
    }

@router.get("/sources/status", response_model=SourcesStatusResponse)
def get_sources_status():
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    sources = [
        SourceDetail(
            source_name="OpenAQ API v3",
            status="HEALTHY" if settings.OPENAQ_API_KEY else "DEMO",
            last_successful_retrieval=now_iso,
            available_variables=["PM2.5 (observed)", "PM10 (observed)"],
            data_classification="OBSERVED",
            coverage_limitations="Requires station within 25km radius; rate-limited endpoints."
        ),
        SourceDetail(
            source_name="Open-Meteo Weather Forecast",
            status="HEALTHY",
            last_successful_retrieval=now_iso,
            available_variables=["Temperature (2m)", "Relative Humidity", "Wind Speed (10m)", "Wind Direction", "Boundary Layer Height"],
            data_classification="MODELED",
            coverage_limitations="Global NWP models; boundary-layer height modeled at regional grid cell."
        ),
        SourceDetail(
            source_name="Open-Meteo Atmospheric Chemistry",
            status="HEALTHY",
            last_successful_retrieval=now_iso,
            available_variables=["PM2.5 (modeled)", "PM10 (modeled)", "Dust"],
            data_classification="MODELED",
            coverage_limitations="CAMS European/Global atmospheric reanalysis forecast estimates."
        ),
        SourceDetail(
            source_name="NASA FIRMS (VIIRS/MODIS)",
            status="HEALTHY" if settings.NASA_FIRMS_MAP_KEY else "DEMO",
            last_successful_retrieval=now_iso,
            available_variables=["Thermal Anomalies", "Brightness Temperature", "Smoke Transport Vector"],
            data_classification="OBSERVED",
            coverage_limitations="Satellite orbital pass latency ~2-4 hours; cloud cover may obscure anomalies."
        ),
        SourceDetail(
            source_name="OpenStreetMap Overpass API",
            status="HEALTHY",
            last_successful_retrieval=now_iso,
            available_variables=["Construction Features (300m)", "Primary Arterial Roads"],
            data_classification="OBSERVED",
            coverage_limitations="Crowdsourced spatial features; cached with 24-hour TTL to prevent Overpass exhaustion."
        )
    ]
    return SourcesStatusResponse(
        system_health="OPTIMAL",
        data_mode=DataMode.DEMO if not settings.OPENAQ_API_KEY else DataMode.LIVE,
        last_checked_at=now_iso,
        sources=sources
    )

@router.get("/methodology", response_model=MethodologyResponse)
def get_methodology():
    return MethodologyResponse(
        title="ClearSky Intelligence Decision Engine Methodology",
        version="v1.2-Deterministic",
        core_premise=(
            "Targeted dust suppression (anti-smog water misting) should only occur when evidence supports "
            "coarse mechanical/fugitive dust dominance, atmospheric conditions are suitable for droplet deposition, "
            "and sufficient fresh observations exist. Generic high AQI alone does NOT warrant water deployment."
        ),
        rules=[
            MethodologyRule(
                rule_id="RULE-01",
                name="Potential Coarse Dust Dominance",
                rationale="Coarse earth/road dust elevates PM10 disproportionately relative to PM2.5.",
                threshold="PM10/PM2.5 Ratio >= 2.0 and PM10 >= 120 µg/m³",
                decision_impact="INTERVENTION_RECOMMENDED candidate (priority 2-5)",
                scientific_limitation="A high ratio is an empirical indicator, not definitive chemical speciation proof."
            ),
            MethodologyRule(
                rule_id="RULE-02",
                name="Smoke / Fire Influence Exclusion",
                rationale="Water mist spraying cannot wash fine combustion smoke aerosols from the regional airshed.",
                threshold="Active fire anomaly within 50km with upwind smoke transport vector",
                decision_impact="INTERVENTION_NOT_RECOMMENDED (Strict Precedence)",
                scientific_limitation="Transport trajectory assumes straight-line advection along surface wind."
            ),
            MethodologyRule(
                rule_id="RULE-03",
                name="High Relative Humidity Suppression",
                rationale="At high ambient humidity, water mist evaporates poorly, risks ground puddling and creates artificial fogging.",
                threshold="Relative Humidity >= 80%",
                decision_impact="INTERVENTION_NOT_RECOMMENDED",
                scientific_limitation="Operational municipal guideline rather than fundamental thermodynamic barrier."
            ),
            MethodologyRule(
                rule_id="RULE-04",
                name="High Wind Dispersion Exclusion",
                rationale="High wind speeds drift mist droplets away from the target corridor before settling.",
                threshold="Wind Speed >= 20 km/h",
                decision_impact="INTERVENTION_NOT_RECOMMENDED",
                scientific_limitation="Actual drift depends on droplet micron size and equipment elevation."
            ),
            MethodologyRule(
                rule_id="RULE-05",
                name="Pollution Inversion Advisory",
                rationale="Low boundary layer height and stagnant winds trap ground-level pollutants.",
                threshold="Boundary Layer Height <= 300m and Wind Speed <= 5 km/h",
                decision_impact="Adds operational warning and elevates candidate priority",
                scientific_limitation="Inversion trapping affects all pollutants, not just dust."
            ),
            MethodologyRule(
                rule_id="RULE-06",
                name="Nearby Construction Dust Warning",
                rationale="Active excavation, foundation, or civil work within ~300m is a primary localized fugitive dust source.",
                threshold="Mapped construction site <= 300m + elevated PM10",
                decision_impact="Increases intervention priority (+1) and flags contractor review",
                scientific_limitation="OSM construction tags indicate ongoing work, not real-time dust emission rates."
            )
        ],
        confidence_calculation=(
            "Confidence is assigned as HIGH when both PM2.5 and PM10 are valid direct station observations within 25km, "
            "MEDIUM when derived from atmospheric numerical models or partial data, and LOW when readings are stale or incomplete."
        ),
        system_limitations=[
            "ClearSky Intelligence does not claim anti-smog guns eliminate PM2.5.",
            "Water spraying recommendations carry no guaranteed health improvement claims.",
            "Calculated water savings are relative to a fixed-schedule operational assumption, not metered flow meters.",
            "Model estimates must never be treated as exact hyper-local street-level sensors."
        ]
    )

@router.get("/brief/daily", response_model=AiDailyBriefResponse)
def get_daily_brief():
    zones = repository.list_zones()
    decisions = repository.list_latest_decisions()
    return ai_brief_service.generate_brief(zones, decisions)

@router.get("/alerts", response_model=List[AlertRecord])
def get_recent_alerts(limit: int = Query(20, ge=1, le=100)):
    return repository.list_recent_alerts(limit=limit)

@router.post("/admin/refresh", response_model=AdminRefreshResponse)
async def admin_refresh_data(
    req: AdminRefreshRequest,
    authorization: Optional[str] = Header(None)
):
    # Protect refresh endpoint
    key = req.admin_key or (authorization.replace("Bearer ", "") if authorization else "")
    if settings.ENVIRONMENT != "development" and key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized: Invalid admin credentials")

    decisions = await ingestion_service.run_full_cycle(force_demo=req.force_mock)
    has_live = any(d.data_mode == DataMode.LIVE for d in decisions)

    return AdminRefreshResponse(
        success=True,
        message=f"Successfully ingested and scored {len(decisions)} zones.",
        refreshed_zones_count=len(decisions),
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        data_mode=DataMode.LIVE if has_live else DataMode.DEMO
    )

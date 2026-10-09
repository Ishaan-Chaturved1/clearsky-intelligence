from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Header, Response
from app.core.config import settings
from app.core.logging import logger
from app.models.domain import (
    Zone,
    DecisionRecord,
    EnvironmentalReading,
    DecisionType,
    DataMode,
    AlertRecord,
    CitizenReport,
    RewardItem,
    ViolationCategory,
    ReportStatus
)
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
    AiDailyBriefResponse,
    CitizenReportCreateRequest,
    CitizenReportVerifyRequest,
    CitizenWalletResponse,
    RewardRedeemRequest,
    RewardRedeemResponse,
    AtmosphericAnalysisResponse,
    CandidateRoadSegmentsResponse,
    ForecastWindowsResponse,
    StrategyComparisonResponse,
    InterventionLogCreateRequest
)
from app.models.domain import InterventionOutcomeRecord
from app.repositories.local_repository import SQLiteRepository
from app.repositories.dynamodb_repository import DynamoDBRepository
from app.services.ingestion_service import IngestionService
from app.analytics.water_efficiency import WaterEfficiencyAnalytics
from app.services.ai_brief_service import AiBriefService
from app.services.spatial_service import SpatialService
from app.services.forecast_service import ForecastService
from app.services.predictive_model_service import PredictiveModelService

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
spatial_service = SpatialService()
forecast_service = ForecastService()
predictive_service = PredictiveModelService()

def calculate_indian_aqi(pm10: Optional[float], pm25: Optional[float]) -> int:
    """
    Computes Indian National Air Quality Index (CPCB breakpoint formula)
    for PM10 (24h) and PM2.5 (24h).
    """
    def calc_sub_index(conc: Optional[float], breakpoints: list) -> int:
        if conc is None or conc < 0:
            return 0
        for (c_low, c_high, i_low, i_high) in breakpoints:
            if c_low <= conc <= c_high:
                return int(round(((i_high - i_low) / (c_high - c_low)) * (conc - c_low) + i_low))
        if conc > breakpoints[-1][1]:
            # Extrapolate beyond severe threshold
            c_low, c_high, i_low, i_high = breakpoints[-1]
            return min(500, int(round(i_high + (conc - c_high) * 0.5)))
        return 0

    pm10_bp = [
        (0, 50, 0, 50),
        (51, 100, 51, 100),
        (101, 250, 101, 200),
        (251, 350, 201, 300),
        (351, 430, 301, 400),
        (431, 500, 401, 500),
    ]
    pm25_bp = [
        (0, 30, 0, 50),
        (31, 60, 51, 100),
        (61, 90, 101, 200),
        (91, 120, 201, 300),
        (121, 250, 301, 400),
        (251, 380, 401, 500),
    ]

    sub_pm10 = calc_sub_index(pm10, pm10_bp)
    sub_pm25 = calc_sub_index(pm25, pm25_bp)
    return max(sub_pm10, sub_pm25, 25)

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

@router.get("/zones/{zone_id}/atmospheric-analysis", response_model=AtmosphericAnalysisResponse)
def get_zone_atmospheric_analysis(zone_id: str):
    zone = repository.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")

    reading = repository.get_latest_reading(zone_id)
    decision = repository.get_latest_decision(zone_id)

    pm10_val = reading.pm10.value if reading and reading.pm10 else None
    pm25_val = reading.pm25.value if reading and reading.pm25 else None
    ratio = reading.pm_ratio if reading else None
    w = reading.weather if reading else None

    # Compute Indian AQI
    aqi = calculate_indian_aqi(pm10_val, pm25_val)

    # Ratio interpretation
    if ratio is not None:
        if ratio >= 2.0:
            ratio_interp = f"PM10/PM2.5 ratio is {ratio:.2f} >= 2.0. Disproportionate coarse particulate elevation consistent with fugitive mechanical road dust or construction resuspension."
        else:
            ratio_interp = f"PM10/PM2.5 ratio is {ratio:.2f} < 2.0. Particulate mass dominated by fine sub-micron aerosols (vehicular combustion soot / industrial secondary aerosols)."
    else:
        ratio_interp = "PM ratio unavailable due to incomplete or near-zero PM2.5 measurements."

    # Pressure interpretation
    press_val = w.surface_pressure_hpa if w else None
    p_tend = w.pressure_tendency if w else "STEADY"
    p_3h = w.pressure_trend_3h_hpa if w else None
    p_6h = w.pressure_trend_6h_hpa if w else None
    p_12h = w.pressure_trend_12h_hpa if w else None

    if p_tend == "FALLING":
        press_interp = f"Barometric pressure is falling ({p_3h:+.1f} hPa/3h). May indicate approaching weather trough or localized gustiness. Evaluated as supporting meteorological context."
    elif p_tend == "RISING":
        press_interp = f"Barometric pressure is rising ({p_3h:+.1f} hPa/3h). Consistent with building regional anticyclone / subsidence. Evaluated as supporting meteorological context."
    else:
        press_interp = "Surface pressure is steady with minor diurnal fluctuations. Supporting meteorological evidence confirms stable barometric conditions."

    # Wind drift assessment
    ws = w.wind_speed_kmh if w else None
    if ws is not None:
        if ws >= 20.0:
            drift_risk = "PROHIBITIVE: Severe spray drift will carry water droplets away from road target before deposition."
        elif ws >= 14.0:
            drift_risk = "MODERATE: Spray cone will experience drift; lower cannon elevation required."
        else:
            drift_risk = "LOW: Gentle breeze facilitates direct localized road surface settling."
    else:
        drift_risk = "UNKNOWN: Wind speed telemetry unavailable."

    # Freshness
    now_dt = datetime.now(timezone.utc)
    freshness_sec = 0
    if reading and reading.timestamp:
        try:
            obs_dt = datetime.fromisoformat(reading.timestamp.replace("Z", "+00:00"))
            freshness_sec = max(0, int((now_dt - obs_dt).total_seconds()))
        except Exception:
            freshness_sec = 1800

    station_dist = (reading.pm10.station_distance_km if reading and reading.pm10 else None) or 4.5

    return AtmosphericAnalysisResponse(
        zone_id=zone.zone_id,
        zone_name=zone.name,
        latitude=zone.latitude,
        longitude=zone.longitude,
        timestamp=reading.timestamp if reading else now_dt.isoformat().replace("+00:00", "Z"),
        aqi_estimate=aqi,
        aqi_standard="Indian National AQI (CPCB Standard)",
        pm10_value=pm10_val,
        pm25_value=pm25_val,
        pm_ratio=ratio,
        pm_ratio_interpretation=ratio_interp,
        temperature_c=w.temperature_c if w else None,
        relative_humidity=w.relative_humidity if w else None,
        surface_pressure_hpa=press_val,
        pressure_trend_3h_hpa=p_3h,
        pressure_trend_6h_hpa=p_6h,
        pressure_trend_12h_hpa=p_12h,
        pressure_tendency=p_tend or "STEADY",
        pressure_interpretation=press_interp,
        wind_speed_kmh=ws,
        wind_direction_deg=w.wind_direction_deg if w else None,
        wind_drift_risk=drift_risk,
        precipitation_mmh=w.precipitation_mmh if w else 0.0,
        rain_suppression_active=(w.precipitation_mmh or 0.0) >= 0.1 if w else False,
        evaporation_rate_mmh=w.evaporation_rate_mmh if w else None,
        estimated_surface_drying_time_min=w.estimated_surface_drying_time_min if w else None,
        boundary_layer_height_m=w.boundary_layer_height_m if w else None,
        inversion_detected=(w.boundary_layer_height_m or 999) <= 300 if w else False,
        contributing_stations_count=2 if reading and reading.pm10.data_type == "observed" else 1,
        nearest_station_distance_km=station_dist,
        spatial_coverage_rating="GOOD" if station_dist <= 10.0 else "FAIR",
        data_freshness_seconds=freshness_sec,
        decision=decision.decision.value if decision else "ADVISORY_ONLY",
        decision_rationale=decision.reasons if decision else ["Awaiting telemetry."],
        triggered_rules=decision.triggered_rules if decision else [],
        conditions_to_change_decision=decision.conditions_to_change if decision else []
    )

@router.get("/zones/{zone_id}/candidate-segments", response_model=CandidateRoadSegmentsResponse)
def get_zone_candidate_segments(zone_id: str):
    zone = repository.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")

    reading = repository.get_latest_reading(zone_id)
    pm10 = reading.pm10.value if reading and reading.pm10 else None
    segments = spatial_service.get_candidate_road_segments(zone, pm10)

    total_water = sum(s.water_required_liters for s in segments)
    total_trips = sum(s.tanker_trips_required for s in segments)

    return CandidateRoadSegmentsResponse(
        zone_id=zone.zone_id,
        zone_name=zone.name,
        total_segments=len(segments),
        total_water_required_liters=round(total_water, 0),
        total_tanker_trips=total_trips,
        segments=segments
    )

@router.get("/zones/{zone_id}/forecast-windows", response_model=ForecastWindowsResponse)
def get_zone_forecast_windows(zone_id: str):
    zone = repository.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")

    # Evaluate future operating windows
    windows = forecast_service.evaluate_hourly_windows(None, zone_id, limit_hours=12)
    optimal_count = sum(1 for w in windows if w.suitability_label == "OPTIMAL")
    best_window = windows[0] if windows else None

    return ForecastWindowsResponse(
        zone_id=zone.zone_id,
        zone_name=zone.name,
        forecast_source="Open-Meteo Hourly Numerical Weather Prediction",
        optimal_windows_count=optimal_count,
        best_window=best_window,
        windows=windows,
        forecasting_disclaimer="Forecast rankings represent weather-suitability for dust-suppression deposition. Future particulate concentrations are not synthetically predicted."
    )

@router.get("/analytics/strategy-comparison", response_model=StrategyComparisonResponse)
def get_strategy_comparison(
    days: int = Query(7, ge=1, le=30),
    tanker_liters: float = Query(5000.0, ge=1000.0, le=25000.0)
):
    zones = repository.list_zones()
    zone_count = len(zones) if zones else 12
    scenarios = analytics_service.calculate_strategy_comparison(
        number_of_zones=zone_count,
        number_of_days=days,
        liters_per_tanker=tanker_liters
    )
    return StrategyComparisonResponse(
        number_of_zones=zone_count,
        reporting_period_days=days,
        tanker_capacity_liters=tanker_liters,
        scenarios=scenarios,
        methodology_summary="Audited comparison between fixed-schedule spraying, generic AQI threshold spraying, ClearSky atmospheric intelligence, and alternative dust-control methods.",
        audit_notes="Water savings calculations assume treated secondary non-potable effluent. Monetary estimates reflect municipal tanker vehicle trip overheads."
    )

@router.get("/interventions", response_model=List[InterventionOutcomeRecord])
def list_logged_interventions(zone_id: Optional[str] = None, limit: int = Query(50, ge=1, le=100)):
    return predictive_service.list_interventions(zone_id=zone_id, limit=limit)

@router.post("/interventions", response_model=InterventionOutcomeRecord)
def log_intervention_event(req: InterventionLogCreateRequest):
    import uuid
    zone = repository.get_zone(req.zone_id)
    zone_name = zone.name if zone else "Monitored Sector"
    reading = repository.get_latest_reading(req.zone_id)
    weather = reading.weather if reading else WeatherConditions()

    delta = None
    if req.post_intervention_pm10_1h is not None:
        delta = round(req.pre_intervention_pm10 - req.post_intervention_pm10_1h, 1)

    record = InterventionOutcomeRecord(
        intervention_id=f"INT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}",
        zone_id=req.zone_id,
        zone_name=zone_name,
        road_segment_id=req.road_segment_id,
        timestamp_start=req.timestamp_start,
        timestamp_end=req.timestamp_end,
        water_volume_liters=req.water_volume_liters,
        tanker_capacity_liters=req.tanker_capacity_liters,
        method=req.method,
        pre_intervention_pm10=req.pre_intervention_pm10,
        post_intervention_pm10_1h=req.post_intervention_pm10_1h,
        post_intervention_pm10_3h=req.post_intervention_pm10_3h,
        control_zone_pm10=req.control_zone_pm10,
        observed_delta_pm10=delta,
        weather_at_intervention=weather,
        status="CALIBRATING",
        notes=req.notes or "Empirical operational record ingested for model calibration."
    )
    return predictive_service.log_intervention(record)

@router.get("/interventions/effectiveness-summary")
def get_intervention_effectiveness_summary():
    return predictive_service.get_effectiveness_summary()

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
    scenarios = analytics_service.calculate_strategy_comparison(zone_count, days, liters_per_op or 5000.0)
    csv_text = analytics_service.generate_csv_export(analytics, scenarios=scenarios)
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
            ),
            MethodologyRule(
                rule_id="RULE-07",
                name="Precipitation & Wet Road Disqualification",
                rationale="Active rainfall or damp road surfaces naturally suppress mechanical dust resuspension, making water spraying redundant and hazardous.",
                threshold="Current precipitation >= 0.1 mm/h",
                decision_impact="INTERVENTION_DISCOURAGED (Safety Gate)",
                scientific_limitation="Small rain showers may evaporate quickly depending on pavement temperature."
            ),
            MethodologyRule(
                rule_id="RULE-08",
                name="Surface Evaporation & Rapid Drying Feasibility",
                rationale="Under extreme heat and low humidity, applied water evaporates in <12 minutes, failing to justify tanker deployment.",
                threshold="Estimated surface drying time < 12 minutes",
                decision_impact="ALTERNATIVE_DUST_CONTROL_SUGGESTED (Bio-binders or sweepers)",
                scientific_limitation="Evaporation rate is estimated via aerodynamic vapor pressure deficit equations."
            ),
            MethodologyRule(
                rule_id="RULE-09",
                name="Barometric Pressure Trend Context",
                rationale="Surface barometric pressure and 3h/6h/12h trends indicate synoptic weather evolution (cyclonic troughs vs anticyclonic subsidence).",
                threshold="Barometric tendency classification (RISING >= +1.5 hPa/3h, FALLING <= -1.5 hPa/3h)",
                decision_impact="Supporting meteorological evidence; not a standalone trigger for spraying",
                scientific_limitation="Pressure change correlates with regional airmass movement but is not a direct measure of particulate mass."
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

# ==========================================
# Citizen Reporting Loop & Eco-Rewards Store
# ==========================================

CATEGORY_LABELS = {
    "UNCOVERED_CONSTRUCTION": "Uncovered Construction Site",
    "ILLEGAL_DEMOLITION": "Illegal Unmitigated Demolition",
    "INDUSTRIAL_EMISSION": "Industrial Stack Emissions",
    "OPEN_WASTE_BURNING": "Open Waste & Biomass Burning",
    "UNPAVED_ROAD_DUST": "Unpaved Road Dust Resuspension",
}

@router.get("/reports", response_model=List[CitizenReport])
def list_citizen_reports(limit: int = Query(50, ge=1, le=100)):
    """Retrieve public incident reporting queue."""
    return repository.list_citizen_reports(limit=limit)

@router.post("/reports", response_model=CitizenReport)
def submit_citizen_report(req: CitizenReportCreateRequest):
    """
    Submit a citizen air quality or construction violation report.
    Automatically correlates with proximate monitored zones and Overpass spatial data.
    """
    import math
    import uuid

    zones = repository.list_zones()
    nearest_zone = None
    min_dist_km = 999.0

    if req.zone_id:
        nearest_zone = repository.get_zone(req.zone_id)
    else:
        for z in zones:
            dlat = math.radians(z.latitude - req.latitude)
            dlon = math.radians(z.longitude - req.longitude)
            a = math.sin(dlat / 2)**2 + math.cos(math.radians(req.latitude)) * math.cos(math.radians(z.latitude)) * math.sin(dlon / 2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            dist = 6371.0 * c
            if dist < min_dist_km:
                min_dist_km = dist
                nearest_zone = z

    zone_id = nearest_zone.zone_id if nearest_zone else None
    zone_name = nearest_zone.name if nearest_zone else "Delhi NCR Region"

    # Correlate evidence with regional telemetry
    category_str = req.category.upper()
    cat_label = CATEGORY_LABELS.get(category_str, "Uncategorized Air Emission")
    correlation = f"Geolocated within {min_dist_km:.1f}km of {zone_name}."

    if category_str == "UNCOVERED_CONSTRUCTION" and nearest_zone and nearest_zone.nearby_infrastructure.has_construction_nearby:
        correlation += f" Correlated with active proximate construction site ({nearest_zone.nearby_infrastructure.construction_distance_meters or 300}m tag) and elevated PM10."
    elif category_str == "OPEN_WASTE_BURNING":
        correlation += " Cross-referenced against regional satellite thermal anomaly grid; flagged for rapid municipal dispatch."
    elif category_str == "INDUSTRIAL_EMISSION":
        correlation += " Correlated with proximate industrial cluster and stack air quality boundaries."

    report_id = f"REP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    report = CitizenReport(
        report_id=report_id,
        created_at=now_iso,
        category=category_str,
        category_label=cat_label,
        zone_id=zone_id,
        zone_name=zone_name,
        latitude=req.latitude,
        longitude=req.longitude,
        location_address=req.location_address,
        description=req.description,
        photo_url=req.photo_url or "https://images.unsplash.com/photo-1541888946425-d0fbb186156f?auto=format&fit=crop&w=600&q=80",
        has_voice_note=req.has_voice_note,
        voice_note_transcript=req.voice_note_transcript,
        reporter_name=req.reporter_name or "Concerned Citizen",
        reporter_contact=req.reporter_contact or "Anonymous Web Submission",
        channel=req.channel or "WEB",
        status=ReportStatus.PENDING_AUDIT,
        points_awarded=0,
        evidence_correlation=correlation,
        verification_notes="Incident ingested into public verification queue."
    )

    repository.save_citizen_report(report)
    return report

@router.post("/reports/{report_id}/verify", response_model=CitizenReport)
def verify_citizen_report(report_id: str, req: CitizenReportVerifyRequest):
    """
    Review and verify an incident report. Awards ClearSky Points upon verification.
    """
    existing = repository.get_citizen_report(report_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Report not found")

    status_str = req.status.upper()
    points = req.points_to_award if status_str in ("VERIFIED_VIOLATION", "ACTION_DISPATCHED", "RESOLVED") else 0

    existing.status = status_str
    existing.points_awarded = points
    existing.verification_notes = req.verification_notes or f"Verified by municipal audit team. {points} ClearSky Points awarded to citizen."

    repository.update_citizen_report(existing)
    return existing

@router.get("/rewards/catalog", response_model=List[RewardItem])
def get_rewards_catalog():
    """List eco-friendly items redeemable with ClearSky Points."""
    return repository.list_rewards_catalog()

@router.get("/rewards/wallet", response_model=CitizenWalletResponse)
def get_citizen_wallet(contact: str = Query("+91 98112 43210")):
    """Get citizen point balance, history, and active redeemed vouchers."""
    data = repository.get_citizen_points(contact)
    return CitizenWalletResponse(**data)

@router.post("/rewards/redeem", response_model=RewardRedeemResponse)
def redeem_reward_item(req: RewardRedeemRequest):
    """Redeem an Eco-Store item using accumulated ClearSky Points."""
    result = repository.redeem_reward(req.reporter_contact, req.item_id)
    if not result:
        raise HTTPException(status_code=400, detail="Insufficient ClearSky Points or invalid item ID.")
    return RewardRedeemResponse(**result)


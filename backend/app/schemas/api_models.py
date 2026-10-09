from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from app.models.domain import Zone, DecisionRecord, EnvironmentalReading, DataMode, StrategyComparisonScenario

class SystemOverviewResponse(BaseModel):
    total_monitored_zones: int
    intervention_candidates: int
    intervention_discouraged: int
    advisory_only_zones: int
    estimated_water_saved_liters: float
    intervention_reduction_percent: float
    last_data_refresh: str
    data_mode: DataMode
    sources_coverage: Dict[str, str]

class ZoneWithLatest(BaseModel):
    zone: Zone
    latest_reading: Optional[EnvironmentalReading] = None
    latest_decision: Optional[DecisionRecord] = None

class WaterSavingsAnalyticsResponse(BaseModel):
    reporting_period_days: int
    number_of_zones: int
    baseline_interventions_per_zone_per_day: float
    assumed_liters_per_intervention: float
    
    baseline_interventions: int
    recommended_interventions: int
    avoided_interventions: int
    
    baseline_water_liters: float
    recommended_water_liters: float
    estimated_water_saved_liters: float
    intervention_reduction_percent: float
    
    daily_trend: List[Dict[str, Any]]
    is_simulation: bool
    data_source_mode: DataMode
    assumptions_note: str

class SourceDetail(BaseModel):
    source_name: str
    status: str  # 'HEALTHY', 'DEGRADED', 'OFFLINE', 'DEMO'
    last_successful_retrieval: Optional[str] = None
    last_error: Optional[str] = None
    available_variables: List[str]
    data_classification: str  # 'OBSERVED', 'MODELED', 'SIMULATED'
    coverage_limitations: str

class SourcesStatusResponse(BaseModel):
    system_health: str
    data_mode: DataMode
    last_checked_at: str
    sources: List[SourceDetail]

class MethodologyRule(BaseModel):
    rule_id: str
    name: str
    rationale: str
    threshold: str
    decision_impact: str
    scientific_limitation: str

class MethodologyResponse(BaseModel):
    title: str
    version: str
    core_premise: str
    rules: List[MethodologyRule]
    confidence_calculation: str
    system_limitations: List[str]

class AdminRefreshRequest(BaseModel):
    admin_key: Optional[str] = None
    force_mock: bool = False

class AdminRefreshResponse(BaseModel):
    success: bool
    message: str
    refreshed_zones_count: int
    timestamp: str
    data_mode: DataMode

class AiDailyBriefResponse(BaseModel):
    generated_at: str
    headline: str
    summary_text: str
    high_priority_zones: List[str]
    cautions_and_disclaimers: List[str]
    provider: str  # 'Amazon Bedrock' or 'Deterministic Fallback'

class CitizenReportCreateRequest(BaseModel):
    category: str
    zone_id: Optional[str] = None
    latitude: float
    longitude: float
    location_address: str
    description: str
    photo_url: Optional[str] = None
    has_voice_note: bool = False
    voice_note_transcript: Optional[str] = None
    reporter_name: str = "Citizen Reporter"
    reporter_contact: str = ""
    channel: str = "WEB"

class CitizenReportVerifyRequest(BaseModel):
    status: str
    points_to_award: int = 100
    verification_notes: Optional[str] = None
    admin_key: Optional[str] = None

class CitizenWalletResponse(BaseModel):
    reporter_contact: str
    reporter_name: str
    total_points: int
    verified_reports_count: int
    reports: List[Dict[str, Any]]
    redeemed_vouchers: List[Dict[str, Any]] = Field(default_factory=list)

class RewardRedeemRequest(BaseModel):
    reporter_contact: str
    item_id: str

class RewardRedeemResponse(BaseModel):
    success: bool
    voucher_code: str
    item_title: str
    points_spent: int
    remaining_points: int
    instructions: str

class AtmosphericAnalysisResponse(BaseModel):
    zone_id: str
    zone_name: str
    latitude: float
    longitude: float
    timestamp: str
    aqi_estimate: int
    aqi_standard: str = "Indian National AQI (CPCB Standard)"
    pm10_value: Optional[float] = None
    pm25_value: Optional[float] = None
    pm_ratio: Optional[float] = None
    pm_ratio_interpretation: str
    temperature_c: Optional[float] = None
    relative_humidity: Optional[float] = None
    surface_pressure_hpa: Optional[float] = None
    pressure_trend_3h_hpa: Optional[float] = None
    pressure_trend_6h_hpa: Optional[float] = None
    pressure_trend_12h_hpa: Optional[float] = None
    pressure_tendency: str = "STEADY"
    pressure_interpretation: str
    wind_speed_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    wind_drift_risk: str
    precipitation_mmh: Optional[float] = 0.0
    rain_suppression_active: bool = False
    evaporation_rate_mmh: Optional[float] = None
    estimated_surface_drying_time_min: Optional[int] = None
    boundary_layer_height_m: Optional[float] = None
    inversion_detected: bool = False
    contributing_stations_count: int = 0
    nearest_station_distance_km: Optional[float] = None
    spatial_coverage_rating: str = "GOOD"
    data_freshness_seconds: int = 0
    decision: str
    decision_rationale: List[str] = Field(default_factory=list)
    triggered_rules: List[str] = Field(default_factory=list)
    conditions_to_change_decision: List[str] = Field(default_factory=list)

class CandidateRoadSegmentsResponse(BaseModel):
    zone_id: str
    zone_name: str
    total_segments: int
    total_water_required_liters: float
    total_tanker_trips: int
    segments: List[Any]  # CandidateRoadSegment objects

class ForecastWindowsResponse(BaseModel):
    zone_id: str
    zone_name: str
    forecast_source: str = "Open-Meteo Hourly Numerical Weather Prediction"
    optimal_windows_count: int
    best_window: Optional[Any] = None  # ForecastWindow
    windows: List[Any]  # List[ForecastWindow]
    forecasting_disclaimer: str

class StrategyComparisonResponse(BaseModel):
    number_of_zones: int
    reporting_period_days: int
    tanker_capacity_liters: float
    scenarios: List[StrategyComparisonScenario]
    methodology_summary: str
    audit_notes: str

class InterventionLogCreateRequest(BaseModel):
    zone_id: str
    road_segment_id: Optional[str] = None
    timestamp_start: str
    timestamp_end: str
    water_volume_liters: float
    tanker_capacity_liters: float = 5000.0
    method: str = "MIST_CANNON"  # 'MIST_CANNON', 'ROAD_WETTING', 'MECHANICAL_SWEEPER'
    pre_intervention_pm10: float
    post_intervention_pm10_1h: Optional[float] = None
    post_intervention_pm10_3h: Optional[float] = None
    control_zone_pm10: Optional[float] = None
    notes: Optional[str] = None

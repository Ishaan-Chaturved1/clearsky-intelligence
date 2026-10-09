from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class DecisionType(str, Enum):
    INTERVENTION_RECOMMENDED = "INTERVENTION_RECOMMENDED"
    TARGETED_INTERVENTION_RECOMMENDED = "TARGETED_INTERVENTION_RECOMMENDED"
    INTERVENTION_NOT_RECOMMENDED = "INTERVENTION_NOT_RECOMMENDED"
    INTERVENTION_DISCOURAGED = "INTERVENTION_DISCOURAGED"
    ADVISORY_ONLY = "ADVISORY_ONLY"
    ALTERNATIVE_DUST_CONTROL_SUGGESTED = "ALTERNATIVE_DUST_CONTROL_SUGGESTED"

class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class DataMode(str, Enum):
    LIVE = "LIVE"
    CACHED = "CACHED"
    DEMO = "DEMO"

class PollutantValue(BaseModel):
    value: Optional[float] = None
    unit: str = "ug/m3"
    data_type: str = "modeled"  # 'observed', 'modeled', 'interpolated', 'unavailable'
    station_id: Optional[str] = None
    station_distance_km: Optional[float] = None
    aqi_sub_index: Optional[int] = None
    aqi_category: Optional[str] = None

class WeatherConditions(BaseModel):
    temperature_c: Optional[float] = None
    relative_humidity: Optional[float] = None
    surface_pressure_hpa: Optional[float] = None
    pressure_trend_3h_hpa: Optional[float] = None
    pressure_trend_6h_hpa: Optional[float] = None
    pressure_trend_12h_hpa: Optional[float] = None
    pressure_tendency: Optional[str] = "STEADY"  # 'FALLING', 'STEADY', 'RISING'
    wind_speed_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    boundary_layer_height_m: Optional[float] = None
    precipitation_mmh: Optional[float] = 0.0
    evaporation_rate_mmh: Optional[float] = None
    estimated_surface_drying_time_min: Optional[int] = None
    data_type: str = "modeled"

class FireSummary(BaseModel):
    nearby_fires_count: int = 0
    closest_fire_distance_km: Optional[float] = None
    possible_smoke_transport: bool = False
    details: List[Dict[str, Any]] = Field(default_factory=list)

class NearbyInfrastructure(BaseModel):
    major_roads: List[str] = Field(default_factory=list)
    construction_sites: List[str] = Field(default_factory=list)
    has_construction_nearby: bool = False
    construction_distance_meters: Optional[int] = None

class Zone(BaseModel):
    zone_id: str
    name: str
    latitude: float
    longitude: float
    description: str
    zone_type: str = "General Urban"
    nearby_infrastructure: NearbyInfrastructure = Field(default_factory=NearbyInfrastructure)

class EnvironmentalReading(BaseModel):
    reading_id: str
    zone_id: str
    timestamp: str  # ISO-8601
    pm25: PollutantValue
    pm10: PollutantValue
    pm_ratio: Optional[float] = None
    weather: WeatherConditions
    fire_summary: FireSummary = Field(default_factory=FireSummary)
    data_mode: DataMode = DataMode.DEMO
    is_stale: bool = False

class DecisionRecord(BaseModel):
    decision_id: str
    zone_id: str
    decision: DecisionType
    priority: Optional[int] = None  # 1 to 5 when INTERVENTION_RECOMMENDED
    confidence: ConfidenceLevel
    pollutants: Dict[str, PollutantValue]
    weather: WeatherConditions
    reasons: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    triggered_rules: List[str] = Field(default_factory=list)
    conditions_to_change: List[str] = Field(default_factory=list)
    source_status: Dict[str, str] = Field(default_factory=dict)
    data_mode: DataMode = DataMode.DEMO
    observed_at: str
    scored_at: str
    station_distance_km: Optional[float] = None
    data_freshness_seconds: Optional[int] = None

class AlertRecord(BaseModel):
    alert_id: str
    zone_id: str
    zone_name: str
    severity: str  # "HIGH", "MEDIUM", "LOW"
    alert_type: str  # "HIGH_PRIORITY_INTERVENTION", "DECISION_CHANGE", "SOURCE_OUTAGE", "STALE_DATA"
    message: str
    decision: DecisionType
    priority: Optional[int] = None
    created_at: str

class ViolationCategory(str, Enum):
    UNCOVERED_CONSTRUCTION = "UNCOVERED_CONSTRUCTION"
    ILLEGAL_DEMOLITION = "ILLEGAL_DEMOLITION"
    INDUSTRIAL_EMISSION = "INDUSTRIAL_EMISSION"
    OPEN_WASTE_BURNING = "OPEN_WASTE_BURNING"
    UNPAVED_ROAD_DUST = "UNPAVED_ROAD_DUST"

class ReportStatus(str, Enum):
    PENDING_AUDIT = "PENDING_AUDIT"
    VERIFIED_VIOLATION = "VERIFIED_VIOLATION"
    ACTION_DISPATCHED = "ACTION_DISPATCHED"
    REJECTED = "REJECTED"
    RESOLVED = "RESOLVED"

class CitizenReport(BaseModel):
    report_id: str
    created_at: str
    category: ViolationCategory
    category_label: str
    zone_id: Optional[str] = None
    zone_name: Optional[str] = None
    latitude: float
    longitude: float
    location_address: str
    description: str
    photo_url: Optional[str] = None
    has_voice_note: bool = False
    voice_note_transcript: Optional[str] = None
    reporter_name: str
    reporter_contact: str
    channel: str = "WEB"  # "WEB", "WHATSAPP", "TELEGRAM", "EMAIL"
    status: ReportStatus = ReportStatus.PENDING_AUDIT
    points_awarded: int = 0
    evidence_correlation: Optional[str] = None
    verification_notes: Optional[str] = None

class RewardItem(BaseModel):
    item_id: str
    title: str
    category: str
    points_cost: int
    description: str
    sponsor: str
    in_stock: bool = True
    badge_label: Optional[str] = None

class CandidateRoadSegment(BaseModel):
    segment_id: str
    zone_id: str
    road_name: str
    road_classification: str = "primary"  # 'trunk', 'primary', 'secondary'
    length_km: float
    estimated_width_m: float = 14.0
    surface_area_m2: float
    traffic_index: str = "HIGH"  # 'HIGH', 'MEDIUM', 'LOW'
    construction_adjacent: bool = False
    construction_distance_m: Optional[int] = None
    water_required_liters: float
    tanker_trips_required: int = 1
    priority_score: int = 3  # 1 to 5
    recommended_action: str = "TARGETED_SPRAYING"
    estimated_cost_inr: float = 0.0

class ForecastWindow(BaseModel):
    window_id: str
    start_time: str
    end_time: str
    hour_label: str
    suitability_score: int  # 0 to 100
    suitability_label: str  # 'OPTIMAL', 'MODERATE', 'POOR', 'PROHIBITED'
    forecast_temp_c: float
    forecast_rh_percent: float
    forecast_wind_kmh: float
    forecast_precipitation_mmh: float = 0.0
    forecast_pressure_hpa: Optional[float] = None
    rationale: str
    safety_concerns: List[str] = Field(default_factory=list)

class AlternativeDustControlMeasure(BaseModel):
    strategy_type: str
    name: str
    suitability_reason: str
    estimated_efficiency_percent: int
    relative_water_saved_liters: float
    recommended_duration_days: int = 7

class InterventionOutcomeRecord(BaseModel):
    intervention_id: str
    zone_id: str
    zone_name: Optional[str] = None
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
    observed_delta_pm10: Optional[float] = None
    weather_at_intervention: WeatherConditions
    status: str = "CALIBRATING"  # 'LOGGED', 'CALIBRATING', 'VERIFIED'
    notes: Optional[str] = None

class StrategyComparisonScenario(BaseModel):
    strategy_id: str
    strategy_name: str
    water_used_liters: float
    water_saved_vs_baseline_liters: float
    water_saved_percent: float
    total_trips: int
    estimated_cost_inr: float
    cost_savings_inr: float
    intervention_frequency: str
    suitability_notes: str


from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class DecisionType(str, Enum):
    INTERVENTION_RECOMMENDED = "INTERVENTION_RECOMMENDED"
    INTERVENTION_NOT_RECOMMENDED = "INTERVENTION_NOT_RECOMMENDED"
    ADVISORY_ONLY = "ADVISORY_ONLY"

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

class WeatherConditions(BaseModel):
    temperature_c: Optional[float] = None
    relative_humidity: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    boundary_layer_height_m: Optional[float] = None
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
    source_status: Dict[str, str] = Field(default_factory=dict)
    data_mode: DataMode = DataMode.DEMO
    observed_at: str
    scored_at: str

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

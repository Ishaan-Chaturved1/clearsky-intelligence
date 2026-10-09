from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from app.models.domain import Zone, DecisionRecord, EnvironmentalReading, DataMode

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

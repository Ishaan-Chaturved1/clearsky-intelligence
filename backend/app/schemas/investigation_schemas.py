from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.models.investigation import (
    ProvenanceType,
    SourceCategory,
    EvidenceDirection,
    PollutionEvent,
    CandidateSource,
    EvidenceItem,
    SourceContributionAssessment,
    Investigation,
    InvestigationReport,
    EnvironmentalObservation
)


class EnvironmentalObservationCreate(BaseModel):
    category: str = Field(default="air_quality")
    provider_id: str
    observation_timestamp: datetime
    retrieval_timestamp: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    station_id: Optional[str] = None
    pollutant: Optional[str] = None
    value: float
    unit: str = "ug/m3"
    method_or_product: Optional[str] = None
    provenance: ProvenanceType = ProvenanceType.GROUND_MEASUREMENT
    data_quality_status: str = "VALID"
    freshness_status: str = "FRESH"
    uncertainty_metadata: Optional[Dict[str, Any]] = None
    source_metadata: Optional[Dict[str, Any]] = None


class EnvironmentalObservationResponse(BaseModel):
    observation_id: str
    category: str
    provider_id: str
    observation_timestamp: datetime
    retrieval_timestamp: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    station_id: Optional[str] = None
    pollutant: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    method_or_product: Optional[str] = None
    provenance: ProvenanceType
    data_quality_status: str
    freshness_status: str


class PollutionEventResponse(BaseModel):
    event_id: str
    event_category: str
    geographic_scope: str
    start_timestamp: datetime
    detection_timestamp: datetime
    end_timestamp: Optional[datetime] = None
    affected_pollutants: List[str]
    severity: str
    detection_method: str
    input_observation_ids: List[str]
    baseline_metadata: Dict[str, Any]
    event_status: str
    summary: str


class EventDetectionRequest(BaseModel):
    observations: List[EnvironmentalObservationCreate]
    pollutant: str
    geographic_scope: Optional[str] = None
    rate_threshold_ug_m3_h: Optional[float] = None
    relative_change_threshold: Optional[float] = None
    reference_time: Optional[datetime] = None


class EventDetectionResponse(BaseModel):
    detected_events: List[PollutionEventResponse]
    evaluated_count: int
    pollutant: str
    has_anomaly: bool


class CandidateSourceResponse(BaseModel):
    source_id: str
    category: SourceCategory
    name: Optional[str] = None
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geographic_region: Optional[str] = None
    provider: str
    verification_status: str
    supporting_evidence_count: int
    contradicting_evidence_count: int


class EvidenceItemResponse(BaseModel):
    evidence_id: str
    evidence_type: str
    provider: str
    timestamp_start: datetime
    source_reference: str
    description: str
    direction: EvidenceDirection
    provenance: ProvenanceType


class SourceContributionResponse(BaseModel):
    pollutant: str
    source_category: SourceCategory
    is_quantitative: bool
    estimated_contribution_value: Optional[float] = None
    estimated_contribution_range: Optional[Tuple[float, float]] = None
    unit_or_basis: str
    geographic_scope: str
    time_period: str
    methodology_reference: str
    uncertainty_info: Optional[str] = None
    limitations: List[str]


class InvestigationResponse(BaseModel):
    investigation_id: str
    geographic_scope: str
    time_window_start: datetime
    time_window_end: Optional[datetime] = None
    associated_event_id: Optional[str] = None
    pollutants_under_investigation: List[str]
    candidate_sources: List[CandidateSourceResponse]
    status: str
    created_at: datetime
    updated_at: datetime


class InvestigationReportResponse(BaseModel):
    report_id: str
    investigation_id: str
    summary_of_observed_event: str
    main_measured_facts: List[str]
    potential_contributing_sources: List[CandidateSourceResponse]
    evidence_supporting_count: int
    evidence_contradicting_count: int
    confidence_assessment: str
    data_gaps: List[str]
    recommended_next_steps: List[str]
    generated_at: datetime

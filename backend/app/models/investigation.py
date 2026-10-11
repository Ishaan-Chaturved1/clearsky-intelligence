from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field, field_validator, model_validator


class ProvenanceType(str, Enum):
    """
    Classifies the physical or mathematical origin of an environmental data point.
    Prevents synthetic or modeled estimates from being conflated with ground sensor telemetry.
    """
    GROUND_MEASUREMENT = "GROUND_MEASUREMENT"
    SATELLITE_DERIVED = "SATELLITE_DERIVED"
    MODELED = "MODELED"
    INTERPOLATED = "INTERPOLATED"
    CITIZEN_REPORTED = "CITIZEN_REPORTED"
    SYNTHETIC = "SYNTHETIC"


class SourceCategory(str, Enum):
    """
    Recognized candidate sources and mechanisms for air pollution episodes.
    """
    AGRICULTURAL_BURNING = "AGRICULTURAL_BURNING"
    BIOMASS_BURNING = "BIOMASS_BURNING"
    OPEN_WASTE_BURNING = "OPEN_WASTE_BURNING"
    LANDFILL_FIRE = "LANDFILL_FIRE"
    CONSTRUCTION_DUST = "CONSTRUCTION_DUST"
    ROAD_DUST = "ROAD_DUST"
    VEHICLE_EMISSIONS = "VEHICLE_EMISSIONS"
    INDUSTRIAL_EMISSIONS = "INDUSTRIAL_EMISSIONS"
    POWER_GENERATION = "POWER_GENERATION"
    RESIDENTIAL_COMBUSTION = "RESIDENTIAL_COMBUSTION"
    DUST_STORM = "DUST_STORM"
    EXPOSED_SOIL = "EXPOSED_SOIL"
    SECONDARY_PARTICULATE_FORMATION = "SECONDARY_PARTICULATE_FORMATION"
    METEOROLOGICAL_ACCUMULATION = "METEOROLOGICAL_ACCUMULATION"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class EvidenceDirection(str, Enum):
    """
    Direction of evidence relative to a specific hypothesis or candidate source.
    """
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    CONTEXT_ONLY = "CONTEXT_ONLY"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"


class PollutantReading(BaseModel):
    """
    Validated pollutant concentration reading.
    Concentration is stored independently of any AQI or index transformation.
    """
    pollutant: str = Field(..., description="Standard pollutant identifier (e.g. PM2.5, PM10, NO2, SO2, CO, O3)")
    concentration: float = Field(..., description="Numeric pollutant concentration")
    unit: str = Field(default="ug/m3", description="Physical measurement unit")
    aqi_sub_index: Optional[int] = Field(default=None, description="Calculated CPCB sub-index if applicable")
    aqi_category: Optional[str] = Field(default=None, description="Air quality band label")
    provenance: ProvenanceType = Field(default=ProvenanceType.GROUND_MEASUREMENT)
    data_quality_status: str = Field(default="VALID", description="VALID, SUSPECT, INVALID, FLAG_NEGATIVE")
    uncertainty: Optional[float] = Field(default=None, ge=0.0, description="1-sigma uncertainty bound if instrumentally measured")

    @field_validator("concentration")
    @classmethod
    def validate_concentration_not_nan(cls, v: float) -> float:
        import math
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Pollutant concentration must be a finite real number")
        if v < 0:
            raise ValueError("Pollutant concentration cannot be negative for physical particulate/gas measurements")
        return v


class EnvironmentalObservation(BaseModel):
    """
    Normalized and provenance-tracked observation entity.
    Coordinates are optional for gridded or regional datasets.
    """
    observation_id: str
    category: str = Field(..., description="Observation category (e.g. air_quality, weather, thermal_anomaly)")
    provider_id: str = Field(..., description="Originating provider (e.g. openaq, open_meteo, firms, cpcb)")
    observation_timestamp: datetime = Field(..., description="Time of observation in UTC")
    retrieval_timestamp: datetime = Field(..., description="Time the record was fetched by ClearSky in UTC")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    station_id: Optional[str] = None
    pollutant: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    method_or_product: Optional[str] = None
    provenance: ProvenanceType
    data_quality_status: str = Field(default="VALID")
    freshness_status: str = Field(default="FRESH")
    uncertainty_metadata: Optional[Dict[str, Any]] = None
    source_metadata: Optional[Dict[str, Any]] = None

    @field_validator("latitude")
    @classmethod
    def validate_lat(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            import math
            if math.isnan(v) or math.isinf(v):
                raise ValueError("Latitude must be a finite number")
            if not (-90.0 <= v <= 90.0):
                raise ValueError(f"Latitude {v} out of bounds [-90.0, 90.0]")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_lon(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            import math
            if math.isnan(v) or math.isinf(v):
                raise ValueError("Longitude must be a finite number")
            if not (-180.0 <= v <= 180.0):
                raise ValueError(f"Longitude {v} out of bounds [-180.0, 180.0]")
        return v


class WeatherObservation(BaseModel):
    """
    Validated atmospheric observation. Clearly demarcates observed vs forecast data.
    """
    observation_id: str
    observation_timestamp: datetime
    retrieval_timestamp: datetime
    provider_id: str
    is_forecast: bool = Field(default=False, description="True if value represents future meteorological projection")
    temperature_c: Optional[float] = None
    relative_humidity: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    wind_speed_kmh: Optional[float] = Field(default=None, ge=0.0)
    wind_direction_deg: Optional[float] = Field(default=None, ge=0.0, le=360.0)
    surface_pressure_hpa: Optional[float] = None
    precipitation_mmh: Optional[float] = Field(default=0.0, ge=0.0)
    boundary_layer_height_m: Optional[float] = Field(default=None, ge=0.0)
    inversion_detected: Optional[bool] = Field(default=None, description="Set only when a verified calculation or profile indicates inversion")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    coverage_area: Optional[str] = None
    provenance: ProvenanceType = Field(default=ProvenanceType.MODELED)
    data_quality_status: str = Field(default="VALID")


class PollutionEvent(BaseModel):
    """
    A detected significant change or elevation in pollutant concentration.
    Represents an observed phenomenon, completely independent of suspected or confirmed causes.
    """
    event_id: str
    event_category: str = Field(default="CONCENTRATION_SPIKE", description="CONCENTRATION_SPIKE, SUSTAINED_ELEVATION, DIURNAL_ANOMALY")
    geographic_scope: str = Field(..., description="Zone, station, or locality identifier")
    start_timestamp: datetime
    detection_timestamp: datetime
    end_timestamp: Optional[datetime] = None
    affected_pollutants: List[str] = Field(..., min_length=1)
    severity: str = Field(default="MODERATE", description="MODERATE, SIGNIFICANT, SEVERE, CRITICAL")
    detection_method: str = Field(..., description="RATE_OF_RISE, RELATIVE_CHANGE, BASELINE_THRESHOLD")
    input_observation_ids: List[str] = Field(default_factory=list)
    baseline_metadata: Dict[str, Any] = Field(default_factory=dict)
    data_quality_indicators: Dict[str, Any] = Field(default_factory=dict)
    event_status: str = Field(default="ACTIVE", description="ACTIVE, RESOLVED, DISMISSED, UNDER_INVESTIGATION")
    summary: str


class CandidateSource(BaseModel):
    """
    Potential pollution emission source or infrastructure element identified near an event.
    Must never be conflated with a confirmed cause.
    """
    source_id: str
    category: SourceCategory
    name: Optional[str] = None
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geographic_region: Optional[str] = None
    activity_start: Optional[datetime] = None
    activity_end: Optional[datetime] = None
    provider: str
    verification_status: str = Field(default="UNVERIFIED", description="UNVERIFIED, CANDIDATE, RULED_OUT, CONFIRMED")
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    contradicting_evidence_ids: List[str] = Field(default_factory=list)
    data_quality_info: Optional[str] = None


class EvidenceItem(BaseModel):
    """
    Discrete piece of empirical or modeled evidence supporting, contradicting,
    or contextualizing a pollution investigation hypothesis.
    """
    evidence_id: str
    evidence_type: str = Field(..., description="GROUND_TELEMETRY, WIND_TRAJECTORY, SATELLITE_THERMAL, INFRASTRUCTURE_PROXIMITY, CITIZEN_REPORT")
    provider: str
    timestamp_start: datetime
    timestamp_end: Optional[datetime] = None
    geographic_coverage: Optional[str] = None
    source_reference: str = Field(..., description="Reference ID or URI to raw data or model payload")
    description: str
    hypothesis_id: Optional[str] = Field(default=None, description="Hypothesis or candidate source under evaluation")
    direction: EvidenceDirection = Field(default=EvidenceDirection.CONTEXT_ONLY)
    data_quality_indicators: Dict[str, Any] = Field(default_factory=dict)
    known_limitations: List[str] = Field(default_factory=list)
    provenance: ProvenanceType
    retrieval_timestamp: Optional[datetime] = None
    observation_timestamp: Optional[datetime] = None
    data_freshness_seconds: Optional[float] = None
    relationship_to_hypothesis: Optional[str] = None
    evidence_quality_score: Optional[float] = None
    missing_information: List[str] = Field(default_factory=list)


class InvestigationReadinessReport(BaseModel):
    """
    Deterministic investigation readiness and missing-data assessment.
    Establishes whether adequate empirical evidence exists to support an investigation.
    """
    investigation_id: str
    investigation_type: str = Field(default="GENERAL_SURGE", description="LOCAL_DUST, REGIONAL_BIOMASS_BURNING, INDUSTRIAL_EMISSIONS, GENERAL_SURGE")
    required_evidence_categories: List[str] = Field(default_factory=list)
    available_evidence_categories: List[str] = Field(default_factory=list)
    missing_evidence_categories: List[str] = Field(default_factory=list)
    stale_evidence_categories: List[str] = Field(default_factory=list)
    failed_data_sources: List[str] = Field(default_factory=list)
    geographic_coverage_limitations: List[str] = Field(default_factory=list)
    temporal_coverage_limitations: List[str] = Field(default_factory=list)
    transport_analysis_possible: bool = True
    quantitative_attribution_defensible: bool = False
    readiness_score: float = Field(default=100.0, ge=0.0, le=100.0)
    readiness_verdict: str = Field(default="READY", description="READY, PARTIAL, INSUFFICIENT")
    additional_data_needed: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SourceContributionAssessment(BaseModel):
    """
    Quantitative or qualitative source apportionment assessment.
    Enforces scientific rigor: quantitative claims require documented methodology
    and uncertainty bounds; qualitative hypotheses do not claim fabricated percentages.
    """
    pollutant: str
    source_category: SourceCategory
    is_quantitative: bool = Field(default=False)
    estimated_contribution_value: Optional[float] = Field(default=None, description="Single-point contribution value if strictly verified")
    estimated_contribution_range: Optional[Tuple[float, float]] = Field(default=None, description="Uncertainty range (low, high)")
    unit_or_basis: str = Field(default="qualitative_rank", description="ug/m3, percent_range, qualitative_rank")
    geographic_scope: str
    time_period: str
    methodology_reference: str
    study_or_model_id: Optional[str] = None
    model_version: Optional[str] = None
    uncertainty_info: Optional[str] = None
    limitations: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_methodology_on_quantitative(self) -> "SourceContributionAssessment":
        if self.is_quantitative:
            if not self.methodology_reference or len(self.methodology_reference.strip()) == 0:
                raise ValueError("Quantitative source contribution requires explicit methodology_reference")
            has_val = self.estimated_contribution_value is not None
            has_range = self.estimated_contribution_range is not None
            if not (has_val or has_range):
                raise ValueError("Quantitative assessment requires estimated_contribution_value or estimated_contribution_range")
        return self


class Investigation(BaseModel):
    """
    Formal source investigation workspace linking detected events, evidence,
    candidate hypotheses, and uncertainty analysis.
    """
    investigation_id: str
    geographic_scope: str
    time_window_start: datetime
    time_window_end: Optional[datetime] = None
    associated_event_id: Optional[str] = None
    pollutants_under_investigation: List[str] = Field(default_factory=list)
    candidate_source_hypotheses: List[CandidateSource] = Field(default_factory=list)
    supporting_evidence: List[EvidenceItem] = Field(default_factory=list)
    contradicting_evidence: List[EvidenceItem] = Field(default_factory=list)
    context_evidence: List[EvidenceItem] = Field(default_factory=list)
    insufficient_evidence: List[EvidenceItem] = Field(default_factory=list)
    analysis_methods: List[str] = Field(default_factory=list)
    data_quality_limitations: List[str] = Field(default_factory=list)
    alternative_explanations: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    readiness: Optional[InvestigationReadinessReport] = None
    attribution_type: str = Field(default="QUALITATIVE_HYPOTHESIS", description="QUALITATIVE_HYPOTHESIS, NONE, SCREENING_LEVEL")
    status: str = Field(default="OPEN", description="OPEN, UNRESOLVED, INCONCLUSIVE, COMPLETED")
    created_at: datetime
    updated_at: datetime

    @property
    def evidence_ledger(self) -> List[EvidenceItem]:
        return self.supporting_evidence + self.contradicting_evidence + self.context_evidence + self.insufficient_evidence


class InvestigationReport(BaseModel):
    """
    Structured report dossier for an investigation.
    May be generated even when an event remains unresolved.
    """
    report_id: str
    investigation_id: str
    summary_of_observed_event: str
    main_measured_facts: List[str] = Field(..., min_length=1)
    potential_contributing_sources: List[CandidateSource] = Field(default_factory=list)
    evidence_supporting: List[EvidenceItem] = Field(default_factory=list)
    evidence_contradicting: List[EvidenceItem] = Field(default_factory=list)
    origin_and_transport_findings: Optional[str] = None
    source_contributions: List[SourceContributionAssessment] = Field(default_factory=list)
    confidence_assessment: str
    alternative_explanations: List[str] = Field(default_factory=list)
    data_gaps: List[str] = Field(default_factory=list)
    recommended_next_steps: List[str] = Field(default_factory=list)
    data_source_references: List[str] = Field(default_factory=list)
    generated_at: datetime

    @property
    def evidence_supporting_count(self) -> int:
        return len(self.evidence_supporting)

    @property
    def evidence_contradicting_count(self) -> int:
        return len(self.evidence_contradicting)

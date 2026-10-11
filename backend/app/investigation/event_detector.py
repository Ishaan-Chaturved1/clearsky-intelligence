import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.investigation import EnvironmentalObservation, PollutionEvent
from app.investigation.normalization import normalize_timestamp


class EventDetectionConfig(BaseModel):
    """
    Configurable operational thresholds for detecting significant changes in pollutant concentrations.
    Thresholds are provisional operational parameters and can be tuned per region.
    """
    rate_threshold_ug_m3_h: float = Field(
        default=25.0,
        description="Threshold rate of rise in ug/m3 per hour to flag a concentration spike"
    )
    relative_change_threshold: float = Field(
        default=0.50,
        description="Minimum fractional increase (e.g. 0.50 = 50%) relative to baseline to flag a surge"
    )
    min_baseline_for_relative: float = Field(
        default=10.0,
        description="Minimum baseline concentration in ug/m3 required to evaluate relative change (avoids division by zero/near-zero)"
    )
    min_elapsed_hours: float = Field(
        default=0.25,
        description="Minimum time interval between observations in hours (15 mins) to prevent sensor jitter from inflating hourly rates"
    )
    max_elapsed_hours: float = Field(
        default=24.0,
        description="Maximum time window between observations in hours"
    )
    max_observation_age_hours: float = Field(
        default=6.0,
        description="Maximum allowed age of the latest observation relative to evaluation reference time"
    )


class EventDetectionResult(BaseModel):
    """
    Result container for a detection run.
    """
    detected_events: List[PollutionEvent] = Field(default_factory=list)
    eval_timestamp: datetime
    observations_evaluated: int
    pollutants_evaluated: List[str]
    audit_notes: List[str] = Field(default_factory=list)


class PollutionEventDetector:
    """
    Deterministic engine for detecting significant changes in atmospheric pollutant concentrations.
    
    IMPORTANT SCIENTIFIC CONSTRAINT:
    This detector identifies empirical physical changes and statistical anomalies in telemetry.
    It does NOT determine the cause of pollution, does NOT attribute emissions to any source,
    and does NOT recommend physical interventions.
    """

    def __init__(self, config: Optional[EventDetectionConfig] = None):
        self.config = config or EventDetectionConfig()

    def detect_events_from_series(
        self,
        observations: List[EnvironmentalObservation],
        pollutant: str,
        geographic_scope: Optional[str] = None,
        reference_time: Optional[datetime] = None
    ) -> List[PollutionEvent]:
        """
        Evaluates a time series of environmental observations for a specific pollutant.
        
        Detection algorithms:
        1. Rate of Rise: (latest - baseline) / elapsed_hours >= rate_threshold_ug_m3_h
        2. Relative Surge: (latest - baseline) / baseline >= relative_change_threshold (when baseline >= min_baseline)
        """
        ref_time = normalize_timestamp(reference_time) if reference_time else datetime.now(timezone.utc)
        events: List[PollutionEvent] = []

        # 1. Filter and validate observations for the requested pollutant
        valid_obs: List[EnvironmentalObservation] = []
        for obs in observations:
            if obs.pollutant and obs.pollutant.upper() != pollutant.upper():
                continue
            if obs.value is None or math.isnan(obs.value) or math.isinf(obs.value):
                continue
            if obs.value < 0:
                continue
            if obs.data_quality_status == "INVALID":
                continue
            valid_obs.append(obs)

        if len(valid_obs) < 2:
            return []

        # 2. Sort observations chronologically
        sorted_obs = sorted(valid_obs, key=lambda x: normalize_timestamp(x.observation_timestamp))

        # Check for duplicate timestamps
        timestamps = [normalize_timestamp(x.observation_timestamp) for x in sorted_obs]
        for i in range(1, len(timestamps)):
            if timestamps[i] <= timestamps[i - 1]:
                raise ValueError(
                    f"Observation timestamps must be strictly monotonic. Found duplicate or non-increasing timestamp: {timestamps[i]}"
                )

        latest_obs = sorted_obs[-1]
        earlier_obs = sorted_obs[0]  # Window baseline

        latest_time = normalize_timestamp(latest_obs.observation_timestamp)
        earlier_time = normalize_timestamp(earlier_obs.observation_timestamp)

        # 3. Check for stale latest observation
        age_hours = (ref_time - latest_time).total_seconds() / 3600.0
        if age_hours > self.config.max_observation_age_hours:
            # Data is too stale to trigger active pollution events
            return []

        elapsed_hours = (latest_time - earlier_time).total_seconds() / 3600.0
        if elapsed_hours < self.config.min_elapsed_hours:
            return []
        if elapsed_hours > self.config.max_elapsed_hours:
            # Re-anchor baseline to the earliest observation within the max window
            in_window = [o for o in sorted_obs if (latest_time - normalize_timestamp(o.observation_timestamp)).total_seconds() / 3600.0 <= self.config.max_elapsed_hours]
            if len(in_window) < 2:
                return []
            earlier_obs = in_window[0]
            earlier_time = normalize_timestamp(earlier_obs.observation_timestamp)
            elapsed_hours = (latest_time - earlier_time).total_seconds() / 3600.0

        latest_val = latest_obs.value
        baseline_val = earlier_obs.value

        abs_change = latest_val - baseline_val
        rate_of_rise = abs_change / elapsed_hours

        # Compute relative change if baseline is above threshold
        rel_change: Optional[float] = None
        if baseline_val >= self.config.min_baseline_for_relative:
            rel_change = abs_change / baseline_val

        detected_methods: List[str] = []
        severity = "MODERATE"

        # Check Rate of Rise
        if rate_of_rise >= self.config.rate_threshold_ug_m3_h and abs_change > 0:
            detected_methods.append("RATE_OF_RISE")
            if rate_of_rise >= self.config.rate_threshold_ug_m3_h * 2.5:
                severity = "SEVERE"
            elif rate_of_rise >= self.config.rate_threshold_ug_m3_h * 1.5:
                severity = "SIGNIFICANT"

        # Check Relative Surge
        if rel_change is not None and rel_change >= self.config.relative_change_threshold and abs_change > 0:
            detected_methods.append("RELATIVE_CHANGE")
            if rel_change >= self.config.relative_change_threshold * 2.0 and severity != "SEVERE":
                severity = "SIGNIFICANT"

        if not detected_methods:
            return []

        # Determine scope
        scope = geographic_scope or latest_obs.station_id or "LOCAL_SERIES"

        rel_pct_str = f" (+{rel_change * 100:.1f}%)" if rel_change is not None else ""
        summary_text = (
            f"Observed rapid elevation in {pollutant} from {baseline_val:.1f} {latest_obs.unit or 'ug/m3'} to "
            f"{latest_val:.1f} {latest_obs.unit or 'ug/m3'}{rel_pct_str} over {elapsed_hours:.2f} hours "
            f"(rate: {rate_of_rise:+.1f} {latest_obs.unit or 'ug/m3'}/h). Methods: {', '.join(detected_methods)}."
        )

        event = PollutionEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            event_category="CONCENTRATION_SPIKE" if "RATE_OF_RISE" in detected_methods else "SUSTAINED_ELEVATION",
            geographic_scope=scope,
            start_timestamp=earlier_time,
            detection_timestamp=latest_time,
            affected_pollutants=[pollutant],
            severity=severity,
            detection_method="+".join(detected_methods),
            input_observation_ids=[earlier_obs.observation_id, latest_obs.observation_id],
            baseline_metadata={
                "baseline_concentration": baseline_val,
                "latest_concentration": latest_val,
                "absolute_change": abs_change,
                "relative_change": rel_change,
                "rate_of_rise_per_hour": rate_of_rise,
                "elapsed_hours": elapsed_hours,
                "unit": latest_obs.unit or "ug/m3",
                "observations_in_window": len(sorted_obs),
            },
            data_quality_indicators={
                "earlier_provenance": earlier_obs.provenance.value,
                "latest_provenance": latest_obs.provenance.value,
                "earlier_status": earlier_obs.data_quality_status,
                "latest_status": latest_obs.data_quality_status,
            },
            event_status="ACTIVE",
            summary=summary_text
        )
        events.append(event)
        return events

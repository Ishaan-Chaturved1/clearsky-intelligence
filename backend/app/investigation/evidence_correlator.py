import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.investigation import (
    CandidateSource,
    EvidenceDirection,
    EvidenceItem,
    Investigation,
    InvestigationReport,
    PollutionEvent,
    ProvenanceType,
    SourceCategory,
)
from app.investigation.local_sources import LocalSourceInvestigationResult, calculate_bearing_deg
from app.investigation.transport_model import TransportAssessment
from app.investigation.satellite_service import SatelliteFireCorrelationResult


class InvestigationDossier(BaseModel):
    """
    Complete synthesized investigation dossier packaging the event,
    local sources, transport trajectory, satellite detections, and evidence ledger.
    """
    investigation_id: str
    target_latitude: float
    target_longitude: float
    target_scope: str
    event: Optional[PollutionEvent] = None
    investigation: Investigation
    report: InvestigationReport
    local_sources: LocalSourceInvestigationResult
    transport: TransportAssessment
    satellite: SatelliteFireCorrelationResult
    generated_at: datetime
    data_completeness_rating: str = "HIGH"  # HIGH, MODERATE, LIMITED


class EvidenceCorrelator:
    """
    Deterministic evidence synthesis engine for air pollution source investigations.
    
    EVIDENCE DIRECTION CRITERIA:
    - SUPPORTS: Consistent spatial proximity, aligned meteorological transport, or matching pollutant size ratios.
    - CONTRADICTS: Transport wind vector blowing away from candidate, active precipitation, or mismatching particle ratio.
    - CONTEXT_ONLY: Mapped feature in vicinity without active transport or confirmed emission status.
    - INSUFFICIENT_INFORMATION: Stale, missing, or inconclusive telemetry.
    """

    def synthesize_investigation(
        self,
        event: Optional[PollutionEvent],
        latitude: float,
        longitude: float,
        local_sources_res: LocalSourceInvestigationResult,
        transport_res: TransportAssessment,
        satellite_res: SatelliteFireCorrelationResult,
        pm10: Optional[float] = None,
        pm25: Optional[float] = None,
        scope_name: Optional[str] = None,
        geographic_scope: Optional[str] = None,
        reference_time: Optional[datetime] = None
    ) -> InvestigationDossier:
        """
        Synthesizes an end-to-end evidence ledger and formal investigation dossier.
        """
        now_utc = reference_time or datetime.now(timezone.utc)
        inv_id = f"inv_{uuid.uuid4().hex[:12]}"
        rep_id = f"rep_{uuid.uuid4().hex[:12]}"
        resolved_scope = scope_name or geographic_scope or (event.geographic_scope if event else f"Coord ({latitude:.3f}, {longitude:.3f})")
        scope = resolved_scope

        supporting_evidence: List[EvidenceItem] = []
        contradicting_evidence: List[EvidenceItem] = []
        context_evidence: List[EvidenceItem] = []
        all_candidate_sources: List[CandidateSource] = []
        facts: List[str] = []
        data_gaps: List[str] = []
        limitations: List[str] = []
        next_steps: List[str] = []

        # 1. Establish measured physical facts
        if event is not None:
            facts.append(f"Detected event '{event.event_category}': {event.summary}")
            facts.append(f"Severity: {event.severity} | Detection method: {event.detection_method}")
        else:
            facts.append(f"No anomalous spike event triggered under current operational rate-of-rise thresholds.")

        if pm10 is not None and pm25 is not None:
            ratio = pm25 / pm10 if pm10 > 0 else None
            ratio_str = f", PM2.5/PM10 ratio = {ratio:.2f}" if ratio is not None else ""
            facts.append(f"Latest particulate measurements: PM10 = {pm10:.1f} ug/m3, PM2.5 = {pm25:.1f} ug/m3{ratio_str}")
        elif pm25 is not None:
            facts.append(f"Latest fine particulate PM2.5 = {pm25:.1f} ug/m3")
        elif pm10 is not None:
            facts.append(f"Latest coarse particulate PM10 = {pm10:.1f} ug/m3")

        # 2. Correlate Local Sources
        wind_dir = transport_res.dominant_upwind_bearing_deg
        wind_speed = transport_res.average_transport_speed_kmh or 0.0

        for cand in local_sources_res.candidates:
            all_candidate_sources.append(cand)
            if cand.latitude and cand.longitude:
                bearing_from_event = calculate_bearing_deg(latitude, longitude, cand.latitude, cand.longitude)
                # Wind direction is where wind comes FROM.
                # If wind direction matches bearing from event to candidate, candidate is UPWIND of the event!
                is_upwind = False
                is_downwind = False
                if wind_dir is not None and wind_speed >= 3.0:
                    diff = abs(wind_dir - bearing_from_event)
                    diff = min(diff, 360.0 - diff)
                    if diff <= 45.0:
                        is_upwind = True
                    elif diff >= 135.0:
                        is_downwind = True

                ev_id = f"ev_local_{cand.source_id}"
                
                # Check particle ratio compatibility
                pm_ratio = (pm25 / pm10) if (pm10 and pm25 and pm10 > 0) else None

                if is_upwind:
                    direction = EvidenceDirection.SUPPORTS
                    desc = f"{cand.name} is situated directly upwind (bearing {bearing_from_event:.0f}° vs wind from {wind_dir:.0f}°) at {wind_speed:.1f} km/h."
                    if cand.category == SourceCategory.CONSTRUCTION_DUST and pm_ratio is not None and pm_ratio < 0.50:
                        desc += " Low PM2.5/PM10 ratio aligns with coarse mechanical dust generation."
                    ev_item = EvidenceItem(
                        evidence_id=ev_id,
                        evidence_type="LOCAL_SOURCE_UPWIND_ALIGNMENT",
                        provider=cand.provider,
                        timestamp_start=now_utc,
                        source_reference=cand.source_id,
                        description=desc,
                        hypothesis_id=cand.source_id,
                        direction=direction,
                        provenance=ProvenanceType.GROUND_MEASUREMENT
                    )
                    supporting_evidence.append(ev_item)
                    cand.verification_status = "CANDIDATE"
                    cand.supporting_evidence_ids.append(ev_id)

                elif is_downwind:
                    direction = EvidenceDirection.CONTRADICTS
                    desc = f"{cand.name} is located downwind of event location (bearing {bearing_from_event:.0f}° vs wind from {wind_dir:.0f}°). Plume dispersion carries emissions away from this sensor."
                    ev_item = EvidenceItem(
                        evidence_id=ev_id,
                        evidence_type="LOCAL_SOURCE_DOWNWIND_MISALIGNMENT",
                        provider=cand.provider,
                        timestamp_start=now_utc,
                        source_reference=cand.source_id,
                        description=desc,
                        hypothesis_id=cand.source_id,
                        direction=direction,
                        provenance=ProvenanceType.GROUND_MEASUREMENT
                    )
                    contradicting_evidence.append(ev_item)
                    cand.contradicting_evidence_ids.append(ev_id)

                else:
                    direction = EvidenceDirection.CONTEXT_ONLY
                    ev_item = EvidenceItem(
                        evidence_id=ev_id,
                        evidence_type="LOCAL_INFRASTRUCTURE_PROXIMITY",
                        provider=cand.provider,
                        timestamp_start=now_utc,
                        source_reference=cand.source_id,
                        description=f"{cand.name} is mapped within {local_sources_res.search_radius_km:.1f} km radius. Cross-wind orientation or light wind conditions.",
                        hypothesis_id=cand.source_id,
                        direction=direction,
                        provenance=ProvenanceType.GROUND_MEASUREMENT
                    )
                    context_evidence.append(ev_item)

        # 3. Correlate Atmospheric Transport
        if transport_res.status == "COMPLETED":
            facts.append(
                f"Backward trajectory: {transport_res.lookback_hours}h path length {transport_res.total_path_length_km} km, "
                f"net displacement {transport_res.net_displacement_km} km from {transport_res.dominant_upwind_compass or 'N/A'} "
                f"({transport_res.dominant_upwind_bearing_deg or 0:.0f}°)."
            )
            if transport_res.min_boundary_layer_height_m is not None and transport_res.min_boundary_layer_height_m < 350.0:
                ev_blh = EvidenceItem(
                    evidence_id="ev_blh_compression",
                    evidence_type="ATMOSPHERIC_BOUNDARY_LAYER",
                    provider="Open-Meteo Weather Model",
                    timestamp_start=now_utc,
                    source_reference="open_meteo_blh",
                    description=f"Boundary layer compressed to {transport_res.min_boundary_layer_height_m:.0f} m, significantly restricting vertical ventilation and trapping ground-level emissions.",
                    direction=EvidenceDirection.SUPPORTS,
                    provenance=ProvenanceType.MODELED
                )
                supporting_evidence.append(ev_blh)
        elif transport_res.status == "PROVIDER_ERROR":
            data_gaps.append("Weather reanalysis unavailable; backward transport could not be modeled.")
        else:
            data_gaps.append(f"Transport trajectory status: {transport_res.status} ({transport_res.data_completeness_pct:.0f}% complete).")

        # 4. Correlate Satellite Fire Telemetry
        if satellite_res.status in ("FIRES_DETECTED", "SUCCESS") and (satellite_res.total_fires_in_region > 0 or len(satellite_res.candidate_sources) > 0):
            facts.append(
                f"Satellite detections: {satellite_res.total_fires_in_region} thermal anomalies within {satellite_res.search_radius_km} km "
                f"({satellite_res.trajectory_correlated_fires_count} aligned with backward transport corridor)."
            )
            for f_cand in satellite_res.candidate_sources:
                all_candidate_sources.append(f_cand)
                f_dir = EvidenceDirection.SUPPORTS if satellite_res.trajectory_correlated_fires_count > 0 else EvidenceDirection.CONTEXT_ONLY
                ev_f = EvidenceItem(
                    evidence_id=f"ev_fire_{f_cand.source_id}",
                    evidence_type="SATELLITE_FIRE_DETECTION",
                    provider=f_cand.provider,
                    timestamp_start=now_utc,
                    source_reference=f_cand.source_id,
                    description=f"{f_cand.name}: {f_cand.description}",
                    hypothesis_id=f_cand.source_id,
                    direction=f_dir,
                    provenance=ProvenanceType.SATELLITE_DERIVED
                )
                if f_dir == EvidenceDirection.SUPPORTS:
                    supporting_evidence.append(ev_f)
                    f_cand.supporting_evidence_ids.append(ev_f.evidence_id)
                else:
                    context_evidence.append(ev_f)

            if satellite_res.trajectory_correlated_fires_count > 0:
                ev_fire_traj = EvidenceItem(
                    evidence_id="ev_fire_trajectory_overlap",
                    evidence_type="SATELLITE_THERMAL_CORRIDOR_OVERLAP",
                    provider="NASA FIRMS VIIRS",
                    timestamp_start=now_utc,
                    source_reference="nasa_firms_viirs",
                    description=(
                        f"{satellite_res.trajectory_correlated_fires_count} active thermal anomalies intersect the "
                        f"estimated upwind backward transport corridor within 25 km."
                    ),
                    direction=EvidenceDirection.SUPPORTS,
                    provenance=ProvenanceType.SATELLITE_DERIVED
                )
                supporting_evidence.append(ev_fire_traj)
            else:
                ev_fire_distant = EvidenceItem(
                    evidence_id="ev_fire_outside_corridor",
                    evidence_type="SATELLITE_THERMAL_OFF_CORRIDOR",
                    provider="NASA FIRMS VIIRS",
                    timestamp_start=now_utc,
                    source_reference="nasa_firms_viirs",
                    description=(
                        f"{satellite_res.total_fires_in_region} thermal anomalies detected in regional sector, "
                        f"but none intersect the primary backward transport corridor."
                    ),
                    direction=EvidenceDirection.CONTEXT_ONLY,
                    provenance=ProvenanceType.SATELLITE_DERIVED
                )
                context_evidence.append(ev_fire_distant)

        elif satellite_res.status == "NO_FIRES_DETECTED":
            facts.append(f"NASA FIRMS: Zero active thermal fire anomalies detected within {satellite_res.search_radius_km} km radius.")
            ev_no_fire = EvidenceItem(
                evidence_id="ev_no_satellite_fires",
                evidence_type="SATELLITE_THERMAL_ABSENCE",
                provider="NASA FIRMS VIIRS",
                timestamp_start=now_utc,
                source_reference="nasa_firms_viirs",
                description="Zero satellite thermal anomalies detected in the regional search domain. Contradicts large-scale open burning within range.",
                direction=EvidenceDirection.CONTRADICTS,
                provenance=ProvenanceType.SATELLITE_DERIVED
            )
            contradicting_evidence.append(ev_no_fire)

        elif satellite_res.status == "CREDENTIALS_MISSING":
            data_gaps.append("NASA FIRMS Map Key not configured; satellite active fire detection offline.")
        else:
            data_gaps.append(f"Satellite fire provider status: {satellite_res.status} ({satellite_res.error_message or 'error'}).")

        # 5. Compile Limitations and Next Steps
        limitations.extend(local_sources_res.data_limitations)
        limitations.extend(transport_res.limitations)
        limitations.extend(satellite_res.limitations)
        limitations.append("Source attribution percentages cannot be scientifically calculated without chemical speciation (ions, carbon fractions).")
        limitations.append("All hypotheses are preliminary and require regulatory ground inspection.")

        next_steps.append("Perform ground physical inspection of high-priority upwind candidate facilities.")
        if satellite_res.status == "CREDENTIALS_MISSING":
            next_steps.append("Configure NASA_FIRMS_MAP_KEY to enable satellite thermal fire correlation.")
        next_steps.append("Acquire high-resolution chemical speciation telemetry to calibrate source apportionment models.")

        # Determine rating
        if len(data_gaps) == 0 and transport_res.status == "COMPLETED" and satellite_res.status in ("FIRES_DETECTED", "NO_FIRES_DETECTED"):
            comp_rating = "HIGH"
        elif len(data_gaps) <= 1:
            comp_rating = "MODERATE"
        else:
            comp_rating = "LIMITED"

        # Construct Investigation model
        investigation_entity = Investigation(
            investigation_id=inv_id,
            geographic_scope=scope,
            time_window_start=transport_res.trajectory_points[-1].timestamp if transport_res.trajectory_points else now_utc,
            time_window_end=now_utc,
            associated_event_id=event.event_id if event else None,
            pollutants_under_investigation=event.affected_pollutants if event else ["PM10", "PM2.5"],
            candidate_source_hypotheses=all_candidate_sources,
            supporting_evidence=supporting_evidence,
            contradicting_evidence=contradicting_evidence,
            context_evidence=context_evidence,
            analysis_methods=[
                "Kinematic Backward Wind Advection",
                "OpenStreetMap Infrastructure Proximity Screening",
                "Satellite Thermal Anomaly Trajectory Overlap"
            ],
            data_quality_limitations=limitations,
            alternative_explanations=[
                "Secondary inorganic aerosol formation from regional precursor gases (SO2, NOx, NH3)",
                "Nocturnal temperature inversion causing accumulation of baseline urban emissions",
                "Local unmapped construction or unpaved road dust resuspension"
            ],
            missing_evidence=data_gaps,
            status="OPEN",
            created_at=now_utc,
            updated_at=now_utc
        )

        # Construct Report dossier
        report_entity = InvestigationReport(
            report_id=rep_id,
            investigation_id=inv_id,
            summary_of_observed_event=event.summary if event else f"Source investigation conducted for {scope}.",
            main_measured_facts=facts,
            potential_contributing_sources=all_candidate_sources,
            evidence_supporting=supporting_evidence,
            evidence_contradicting=contradicting_evidence,
            origin_and_transport_findings=(
                f"Air parcels arrived from {transport_res.dominant_upwind_compass or 'N/A'} "
                f"({transport_res.dominant_upwind_bearing_deg or 0:.0f}°) traveling ~{transport_res.total_path_length_km:.1f} km over "
                f"{transport_res.lookback_hours} hours at average speed {transport_res.average_transport_speed_kmh or 0:.1f} km/h."
                if transport_res.status == "COMPLETED" else "Transport model incomplete due to meteorological data gaps."
            ),
            source_contributions=[],  # Enforce rule: No fabricated quantitative percentages!
            confidence_assessment=f"Evidence coverage rated {comp_rating}. {len(supporting_evidence)} supporting lines of evidence, {len(contradicting_evidence)} contradicting.",
            alternative_explanations=investigation_entity.alternative_explanations,
            data_gaps=data_gaps,
            recommended_next_steps=next_steps,
            data_source_references=[
                "Open-Meteo Atmospheric Weather API",
                "OpenStreetMap Overpass API",
                "NASA FIRMS Active Fire Data"
            ],
            generated_at=now_utc
        )

        return InvestigationDossier(
            investigation_id=inv_id,
            target_latitude=latitude,
            target_longitude=longitude,
            target_scope=scope,
            event=event,
            investigation=investigation_entity,
            report=report_entity,
            local_sources=local_sources_res,
            transport=transport_res,
            satellite=satellite_res,
            generated_at=now_utc,
            data_completeness_rating=comp_rating
        )

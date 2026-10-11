import pytest
from datetime import datetime, timezone, timedelta

from app.models.investigation import (
    CandidateSource,
    EvidenceDirection,
    EvidenceItem,
    InvestigationReadinessReport,
    ProvenanceType,
    SourceCategory,
)
from app.investigation.evidence_correlator import EvidenceCorrelator, InvestigationDossier
from app.investigation.local_sources import LocalSourceInvestigationResult
from app.investigation.transport_model import TransportAssessment, TrajectoryPoint
from app.investigation.satellite_service import SatelliteFireCorrelationResult, FireDetectionRecord


@pytest.fixture
def correlator():
    return EvidenceCorrelator()


def _make_transport(event_lat=28.6315, event_lon=77.2167, bearing_deg=90.0, speed_kmh=10.0):
    return TransportAssessment(
        start_latitude=event_lat,
        start_longitude=event_lon,
        event_timestamp=datetime.now(timezone.utc),
        lookback_hours=12,
        dominant_upwind_bearing_deg=bearing_deg,
        dominant_upwind_compass="E",
        uncertainty_description="Test uncertainty",
        trajectory_points=[
            TrajectoryPoint(
                step_hours_back=0,
                timestamp=datetime.now(timezone.utc),
                latitude=event_lat,
                longitude=event_lon,
                wind_speed_kmh=speed_kmh,
                wind_direction_deg=bearing_deg
            )
        ]
    )


def test_41_supporting_evidence(correlator):
    """41. Supporting evidence when satellite fire aligns with upwind transport."""
    event_lat, event_lon = 28.6315, 77.2167

    local_res = LocalSourceInvestigationResult(
        center_latitude=event_lat,
        center_longitude=event_lon,
        search_radius_km=5.0,
        candidates=[],
        total_candidates_found=0,
        query_timestamp=datetime.now(timezone.utc)
    )

    transport_res = _make_transport(event_lat, event_lon, bearing_deg=90.0)

    fire_cand = CandidateSource(
        source_id="fire_sup_01",
        category=SourceCategory.BIOMASS_BURNING,
        name="Satellite Active Fire",
        latitude=28.6315,
        longitude=77.3500,
        provider="NASA FIRMS",
        verification_status="CORRELATED_THERMAL_ANOMALY"
    )
    fire_record = FireDetectionRecord(
        fire_id="fire_sup_01",
        latitude=28.6315,
        longitude=77.3500,
        distance_from_event_km=15.0,
        bearing_from_event_deg=90.0,
        bearing_compass="E",
        brightness=340.0,
        is_upwind=True,
        plausible_smoke_corridor=True
    )
    fire_res = SatelliteFireCorrelationResult(
        event_latitude=event_lat,
        event_longitude=event_lon,
        search_radius_km=50.0,
        total_fires_in_region=1,
        upwind_fires_count=1,
        trajectory_correlated_fires_count=1,
        fire_records=[fire_record],
        candidate_sources=[fire_cand],
        query_timestamp=datetime.now(timezone.utc)
    )

    dossier = correlator.synthesize_investigation(
        event=None,
        latitude=event_lat,
        longitude=event_lon,
        local_sources_res=local_res,
        transport_res=transport_res,
        satellite_res=fire_res,
        boundary_layer_height_m=200.0,
        pm10=180.0,
        pm25=120.0
    )

    supports_items = [e for e in dossier.investigation.evidence_ledger if e.direction == EvidenceDirection.SUPPORTS]
    assert len(supports_items) >= 1

    # Check enriched Stage 5 fields
    first_support = supports_items[0]
    assert first_support.observation_timestamp is not None
    assert first_support.retrieval_timestamp is not None
    assert first_support.evidence_quality_score is not None
    assert first_support.evidence_quality_score > 0.0
    assert first_support.relationship_to_hypothesis is not None


def test_42_contradicting_evidence(correlator):
    """42. Contradicting evidence when boundary layer is high or candidate is downwind."""
    event_lat, event_lon = 28.6315, 77.2167

    # Candidate is at bearing 270 (West), but wind is blowing from East (90), so candidate is downwind
    ind_cand = CandidateSource(
        source_id="ind_downwind",
        category=SourceCategory.INDUSTRIAL_EMISSIONS,
        name="Downwind Plant",
        latitude=28.6315,
        longitude=77.1000,
        provider="OpenStreetMap",
        verification_status="UNVERIFIED"
    )
    local_res = LocalSourceInvestigationResult(
        center_latitude=event_lat,
        center_longitude=event_lon,
        search_radius_km=5.0,
        candidates=[ind_cand],
        total_candidates_found=1,
        query_timestamp=datetime.now(timezone.utc)
    )

    transport_res = _make_transport(event_lat, event_lon, bearing_deg=90.0)
    fire_res = SatelliteFireCorrelationResult(
        event_latitude=event_lat,
        event_longitude=event_lon,
        search_radius_km=50.0,
        total_fires_in_region=0,
        upwind_fires_count=0,
        trajectory_correlated_fires_count=0,
        fire_records=[],
        candidate_sources=[],
        query_timestamp=datetime.now(timezone.utc)
    )

    dossier = correlator.synthesize_investigation(
        event=None,
        latitude=event_lat,
        longitude=event_lon,
        local_sources_res=local_res,
        transport_res=transport_res,
        satellite_res=fire_res,
        boundary_layer_height_m=1800.0,  # High boundary layer height (> 1500m) contradicts accumulation
        pm10=100.0,
        pm25=50.0
    )

    contradicts = [e for e in dossier.investigation.evidence_ledger if e.direction == EvidenceDirection.CONTRADICTS]
    assert len(contradicts) >= 1
    assert any("boundary layer" in c.description.lower() or "downwind" in c.description.lower() for c in contradicts)


def test_43_context_only_evidence(correlator):
    """43. Context-only evidence (e.g. candidate nearby with no strong wind or unverified status)."""
    event_lat, event_lon = 28.6315, 77.2167

    ind_cand = CandidateSource(
        source_id="ind_neutral",
        category=SourceCategory.ROAD_DUST,
        name="Ring Road Construction",
        latitude=28.6320,
        longitude=77.2170,
        provider="OpenStreetMap",
        verification_status="UNVERIFIED"
    )
    local_res = LocalSourceInvestigationResult(
        center_latitude=event_lat,
        center_longitude=event_lon,
        search_radius_km=5.0,
        candidates=[ind_cand],
        total_candidates_found=1,
        query_timestamp=datetime.now(timezone.utc)
    )

    transport_res = _make_transport(event_lat, event_lon, bearing_deg=180.0, speed_kmh=1.0)
    fire_res = SatelliteFireCorrelationResult(
        event_latitude=event_lat,
        event_longitude=event_lon,
        search_radius_km=50.0,
        total_fires_in_region=0,
        upwind_fires_count=0,
        trajectory_correlated_fires_count=0,
        fire_records=[],
        candidate_sources=[],
        query_timestamp=datetime.now(timezone.utc)
    )

    dossier = correlator.synthesize_investigation(
        event=None,
        latitude=event_lat,
        longitude=event_lon,
        local_sources_res=local_res,
        transport_res=transport_res,
        satellite_res=fire_res,
        boundary_layer_height_m=800.0,
        pm10=120.0,
        pm25=60.0
    )

    context_items = [e for e in dossier.investigation.evidence_ledger if e.direction == EvidenceDirection.CONTEXT_ONLY]
    assert len(context_items) >= 1


def test_44_insufficient_evidence(correlator):
    """44. Insufficient evidence when no local sources or fire records are found."""
    event_lat, event_lon = 28.6315, 77.2167

    local_res = LocalSourceInvestigationResult(
        center_latitude=event_lat,
        center_longitude=event_lon,
        search_radius_km=5.0,
        candidates=[],
        total_candidates_found=0,
        query_timestamp=datetime.now(timezone.utc)
    )
    transport_res = _make_transport(event_lat, event_lon)
    fire_res = SatelliteFireCorrelationResult(
        event_latitude=event_lat,
        event_longitude=event_lon,
        search_radius_km=50.0,
        total_fires_in_region=0,
        upwind_fires_count=0,
        trajectory_correlated_fires_count=0,
        fire_records=[],
        candidate_sources=[],
        query_timestamp=datetime.now(timezone.utc)
    )

    dossier = correlator.synthesize_investigation(
        event=None,
        latitude=event_lat,
        longitude=event_lon,
        local_sources_res=local_res,
        transport_res=transport_res,
        satellite_res=fire_res,
        boundary_layer_height_m=None,
        pm10=None,
        pm25=None
    )

    insufficient = [e for e in dossier.investigation.evidence_ledger if e.direction == EvidenceDirection.INSUFFICIENT_INFORMATION]
    assert len(insufficient) >= 1
    assert any("insufficient" in item.description.lower() or "no active thermal" in item.description.lower() for item in insufficient)


def test_45_stale_evidence_handling(correlator):
    """45. Stale evidence: check that timestamps and freshness calculations are properly recorded."""
    event_lat, event_lon = 28.6315, 77.2167

    local_res = LocalSourceInvestigationResult(
        center_latitude=event_lat,
        center_longitude=event_lon,
        search_radius_km=5.0,
        candidates=[],
        total_candidates_found=0,
        query_timestamp=datetime.now(timezone.utc) - timedelta(hours=6)
    )
    transport_res = _make_transport(event_lat, event_lon)
    fire_res = SatelliteFireCorrelationResult(
        event_latitude=event_lat,
        event_longitude=event_lon,
        search_radius_km=50.0,
        total_fires_in_region=0,
        upwind_fires_count=0,
        trajectory_correlated_fires_count=0,
        fire_records=[],
        candidate_sources=[],
        query_timestamp=datetime.now(timezone.utc)
    )

    dossier = correlator.synthesize_investigation(
        event=None,
        latitude=event_lat,
        longitude=event_lon,
        local_sources_res=local_res,
        transport_res=transport_res,
        satellite_res=fire_res,
        boundary_layer_height_m=250.0,
        pm10=150.0,
        pm25=90.0
    )

    for item in dossier.investigation.evidence_ledger:
        assert item.retrieval_timestamp is not None
        assert item.data_freshness_seconds is not None
        assert item.data_freshness_seconds >= 0.0


def test_46_and_47_missing_weather_and_fire_observations(correlator):
    """46. Missing weather observations & 47. Missing fire observations check readiness assessment."""
    event_lat, event_lon = 28.6315, 77.2167

    local_res = LocalSourceInvestigationResult(
        center_latitude=event_lat,
        center_longitude=event_lon,
        search_radius_km=5.0,
        candidates=[],
        total_candidates_found=0,
        query_timestamp=datetime.now(timezone.utc)
    )
    transport_res = _make_transport(event_lat, event_lon)
    fire_res = SatelliteFireCorrelationResult(
        event_latitude=event_lat,
        event_longitude=event_lon,
        search_radius_km=50.0,
        total_fires_in_region=0,
        upwind_fires_count=0,
        trajectory_correlated_fires_count=0,
        fire_records=[],
        candidate_sources=[],
        query_timestamp=datetime.now(timezone.utc)
    )

    dossier = correlator.synthesize_investigation(
        event=None,
        latitude=event_lat,
        longitude=event_lon,
        local_sources_res=local_res,
        transport_res=transport_res,
        satellite_res=fire_res,
        boundary_layer_height_m=None,  # Missing boundary layer
        pm10=None,
        pm25=None
    )

    readiness = dossier.readiness
    assert readiness is not None
    assert "fire_observations" in readiness.missing_evidence_categories or "meteorology" in readiness.missing_evidence_categories
    assert readiness.quantitative_attribution_defensible is False
    assert len(readiness.additional_data_needed) > 0


def test_48_conflicting_observations(correlator):
    """48. Conflicting observations: fire detected downwind while boundary layer is low."""
    event_lat, event_lon = 28.6315, 77.2167

    transport_res = _make_transport(event_lat, event_lon, bearing_deg=90.0)  # Wind from East

    # Fire is at bearing 270 (West), so it's downwind
    fire_cand = CandidateSource(
        source_id="fire_downwind",
        category=SourceCategory.BIOMASS_BURNING,
        name="Downwind Fire",
        latitude=28.6315,
        longitude=77.0000,
        provider="NASA FIRMS",
        verification_status="DOWNWIND_UNALIGNED"
    )
    fire_record = FireDetectionRecord(
        fire_id="fire_downwind",
        latitude=28.6315,
        longitude=77.0000,
        distance_from_event_km=20.0,
        bearing_from_event_deg=270.0,
        bearing_compass="W",
        brightness=320.0,
        is_upwind=False,
        plausible_smoke_corridor=False
    )
    fire_res = SatelliteFireCorrelationResult(
        event_latitude=event_lat,
        event_longitude=event_lon,
        search_radius_km=50.0,
        total_fires_in_region=1,
        upwind_fires_count=0,
        trajectory_correlated_fires_count=0,
        fire_records=[fire_record],
        candidate_sources=[fire_cand],
        query_timestamp=datetime.now(timezone.utc)
    )

    local_res = LocalSourceInvestigationResult(
        center_latitude=event_lat,
        center_longitude=event_lon,
        search_radius_km=5.0,
        candidates=[],
        total_candidates_found=0,
        query_timestamp=datetime.now(timezone.utc)
    )

    dossier = correlator.synthesize_investigation(
        event=None,
        latitude=event_lat,
        longitude=event_lon,
        local_sources_res=local_res,
        transport_res=transport_res,
        satellite_res=fire_res,
        boundary_layer_height_m=200.0,
        pm10=180.0,
        pm25=120.0
    )

    # Downwind fire should be CONTRADICTS
    downwind_items = [e for e in dossier.investigation.evidence_ledger if e.source_reference == "fire_downwind"]
    assert len(downwind_items) >= 1
    assert downwind_items[0].direction == EvidenceDirection.CONTRADICTS


def test_49_no_unsupported_causal_attribution(correlator):
    """49. No unsupported causal attribution: ensure synthesis and readiness enforce uncertainty."""
    event_lat, event_lon = 28.6315, 77.2167

    local_res = LocalSourceInvestigationResult(
        center_latitude=event_lat,
        center_longitude=event_lon,
        search_radius_km=5.0,
        candidates=[],
        total_candidates_found=0,
        query_timestamp=datetime.now(timezone.utc)
    )
    transport_res = _make_transport(event_lat, event_lon)
    fire_res = SatelliteFireCorrelationResult(
        event_latitude=event_lat,
        event_longitude=event_lon,
        search_radius_km=50.0,
        total_fires_in_region=0,
        upwind_fires_count=0,
        trajectory_correlated_fires_count=0,
        fire_records=[],
        candidate_sources=[],
        query_timestamp=datetime.now(timezone.utc)
    )

    dossier = correlator.synthesize_investigation(
        event=None,
        latitude=event_lat,
        longitude=event_lon,
        local_sources_res=local_res,
        transport_res=transport_res,
        satellite_res=fire_res,
        boundary_layer_height_m=220.0,
        pm10=150.0,
        pm25=100.0
    )

    # Synthesis should not claim 100% certainty or prove direct causation
    assert dossier.readiness.quantitative_attribution_defensible is False
    assert dossier.investigation.attribution_type in ["QUALITATIVE_HYPOTHESIS", "NONE", "SCREENING_LEVEL"]


def test_50_no_fabricated_source_percentages(correlator):
    """50. No fabricated source percentages: check that dossier does not contain made-up % splits."""
    event_lat, event_lon = 28.6315, 77.2167

    local_res = LocalSourceInvestigationResult(
        center_latitude=event_lat,
        center_longitude=event_lon,
        search_radius_km=5.0,
        candidates=[],
        total_candidates_found=0,
        query_timestamp=datetime.now(timezone.utc)
    )
    transport_res = _make_transport(event_lat, event_lon)
    fire_res = SatelliteFireCorrelationResult(
        event_latitude=event_lat,
        event_longitude=event_lon,
        search_radius_km=50.0,
        total_fires_in_region=0,
        upwind_fires_count=0,
        trajectory_correlated_fires_count=0,
        fire_records=[],
        candidate_sources=[],
        query_timestamp=datetime.now(timezone.utc)
    )

    dossier = correlator.synthesize_investigation(
        event=None,
        latitude=event_lat,
        longitude=event_lon,
        local_sources_res=local_res,
        transport_res=transport_res,
        satellite_res=fire_res,
        boundary_layer_height_m=220.0,
        pm10=150.0,
        pm25=100.0
    )

    for item in dossier.investigation.evidence_ledger:
        # Should not make quantitative fraction claims like "43% dust"
        assert "43%" not in item.description
        assert "57%" not in item.description

    assert dossier.readiness.readiness_verdict in ["READY", "PARTIAL", "INSUFFICIENT"]

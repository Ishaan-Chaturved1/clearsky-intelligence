import math
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.data_sources.base import SourceFetchResult
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
from app.investigation.local_sources import (
    LocalSourceInvestigator,
    LocalSourceFilterConfig,
    LocalSourceInvestigationResult,
    haversine_distance_km,
    calculate_bearing_deg,
)
from app.investigation.transport_model import (
    AtmosphericTransportService,
    TransportAssessment,
    TrajectoryPoint,
    destination_point,
)
from app.investigation.satellite_service import (
    SatelliteFireCorrelator,
    SatelliteFireCorrelationResult,
    FireDetectionRecord,
)
from app.investigation.evidence_correlator import (
    EvidenceCorrelator,
    InvestigationDossier,
)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clear_cache_between_tests():
    from app.data_sources.base import global_cache
    global_cache.clear()
    yield
    global_cache.clear()


# ==============================================================================
# 1. LOCAL SOURCES TESTS
# ==============================================================================

def test_haversine_distance_known_points():
    lat1, lon1 = 28.6315, 77.2167
    lat2, lon2 = 28.6129, 77.2295
    dist = haversine_distance_km(lat1, lon1, lat2, lon2)
    assert 2.0 <= dist <= 3.0
    assert haversine_distance_km(lat1, lon1, lat1, lon1) == 0.0


def test_calculate_bearing_known():
    assert round(calculate_bearing_deg(0.0, 0.0, 1.0, 0.0)) == 0
    assert round(calculate_bearing_deg(0.0, 0.0, 0.0, 1.0)) == 90
    assert round(calculate_bearing_deg(1.0, 0.0, 0.0, 0.0)) == 180
    assert round(calculate_bearing_deg(0.0, 1.0, 0.0, 0.0)) == 270


def test_local_source_deduplication_and_provenance():
    investigator = LocalSourceInvestigator()
    mock_elements = [
        {
            "id": 1001,
            "lat": 28.6350,
            "lon": 77.2200,
            "tags": {"highway": "primary", "name": "Barakhamba Road"}
        },
        # Duplicate element with same ID
        {
            "id": 1001,
            "lat": 28.6350,
            "lon": 77.2200,
            "tags": {"highway": "primary", "name": "Barakhamba Road"}
        },
        # Missing coordinates
        {
            "id": 1002,
            "tags": {"landuse": "industrial", "name": "Unmapped Facility"}
        },
        # Valid industrial area
        {
            "id": 1003,
            "lat": 28.6400,
            "lon": 77.2250,
            "tags": {"landuse": "industrial", "name": "Okhla Phase II"}
        }
    ]

    candidates = investigator._parse_elements(mock_elements, 28.6315, 77.2167, max_candidates=25, radius_km=10.0)
    assert len(candidates) == 2
    ids = [c.source_id for c in candidates]
    assert any("1001" in cid for cid in ids)
    assert any("Okhla" in (c.name or "") for c in candidates)
    for c in candidates:
        assert c.verification_status == "UNVERIFIED_CANDIDATE"
        assert c.provider == "OpenStreetMap Overpass API"
        assert "DOES NOT confirm active emissions" in c.description


@pytest.mark.asyncio
async def test_local_source_empty_result_does_not_fake_facilities():
    investigator = LocalSourceInvestigator()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"elements": []}

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__.return_value = mock_client

    with patch("httpx.AsyncClient", return_value=mock_client):
        res = await investigator.find_candidate_sources(28.6315, 77.2167, LocalSourceFilterConfig(radius_km=2.0))
        assert res.status == "EMPTY"
        assert len(res.candidates) == 0
        assert res.total_candidates_found == 0


@pytest.mark.asyncio
async def test_local_source_timeout_handling():
    investigator = LocalSourceInvestigator()
    mock_client = AsyncMock()
    mock_client.post.side_effect = Exception("ReadTimeout")
    mock_client.__aenter__.return_value = mock_client

    with patch("httpx.AsyncClient", return_value=mock_client):
        res = await investigator.find_candidate_sources(28.6315, 77.2167)
        assert res.status == "PROVIDER_ERROR"
        assert res.data_source_mode == "UNAVAILABLE"
        assert len(res.candidates) == 0


# ==============================================================================
# 2. ATMOSPHERIC TRANSPORT TESTS
# ==============================================================================

def test_destination_point_exact_physics():
    lat, lon = destination_point(0.0, 0.0, 0.0, 111.19)
    assert round(lat, 1) == 1.0
    assert round(lon, 1) == 0.0

    lat, lon = destination_point(0.0, 0.0, 90.0, 111.19)
    assert round(lat, 1) == 0.0
    assert round(lon, 1) == 1.0


@pytest.mark.asyncio
async def test_backward_wind_direction_interpretation():
    service = AtmosphericTransportService()
    now = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
    mock_weather_data = {
        "hourly": {
            "time": [(now - timedelta(hours=i)).strftime("%Y-%m-%dT%H:00") for i in range(12, -1, -1)],
            "wind_speed_10m": [10.0] * 13,
            "wind_direction_10m": [0.0] * 13,  # Wind FROM North
            "boundary_layer_height": [800.0] * 13,
            "temperature_2m": [25.0] * 13,
            "precipitation": [0.0] * 13
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_weather_data

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp
    mock_client.__aenter__.return_value = mock_client

    with patch("httpx.AsyncClient", return_value=mock_client):
        assessment = await service.calculate_backward_trajectory(28.0, 77.0, lookback_hours=6, event_time=now)
        assert assessment.status == "COMPLETED"
        assert len(assessment.trajectory_points) >= 1
        earliest_point = assessment.trajectory_points[-1]
        assert earliest_point.latitude > 28.0
        assert assessment.dominant_upwind_compass == "N"


@pytest.mark.asyncio
async def test_transport_large_gap_reported_honestly():
    service = AtmosphericTransportService()
    now = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
    mock_weather_data = {
        "hourly": {
            "time": [(now - timedelta(hours=i)).strftime("%Y-%m-%dT%H:00") for i in range(12, -1, -1)],
            "wind_speed_10m": [None] * 13,
            "wind_direction_10m": [None] * 13,
            "boundary_layer_height": [None] * 13,
            "temperature_2m": [None] * 13,
            "precipitation": [None] * 13
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_weather_data

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp
    mock_client.__aenter__.return_value = mock_client

    with patch("httpx.AsyncClient", return_value=mock_client):
        assessment = await service.calculate_backward_trajectory(28.0, 77.0, lookback_hours=6, event_time=now)
        assert assessment.status in ("INSUFFICIENT_DATA", "PARTIAL")


@pytest.mark.asyncio
async def test_transport_scientific_limitations_included():
    service = AtmosphericTransportService()
    now = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
    mock_weather_data = {
        "hourly": {
            "time": [(now - timedelta(hours=i)).strftime("%Y-%m-%dT%H:00") for i in range(12, -1, -1)],
            "wind_speed_10m": [8.0] * 13,
            "wind_direction_10m": [45.0] * 13,
            "boundary_layer_height": [750.0] * 13,
            "temperature_2m": [22.0] * 13,
            "precipitation": [0.0] * 13
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_weather_data

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp
    mock_client.__aenter__.return_value = mock_client

    with patch("httpx.AsyncClient", return_value=mock_client):
        res = await service.calculate_backward_trajectory(28.0, 77.0, lookback_hours=6, event_time=now)
        assert len(res.limitations) >= 3
        assert any("NOT a full atmospheric dispersion" in lim for lim in res.limitations)
        assert any("does not prove causation" in lim.lower() for lim in res.limitations)


# ==============================================================================
# 3. SATELLITE FIRE TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_satellite_fire_correlation_with_trajectory():
    correlator = SatelliteFireCorrelator()
    mock_result = SourceFetchResult(
        source_name="firms",
        is_success=True,
        fetched_at=datetime.now(timezone.utc).timestamp(),
        data={
            "nearby_fires_count": 2,
            "closest_fire_distance_km": 15.0,
            "details": [
                {
                    "latitude": 28.80,
                    "longitude": 77.00,
                    "distance_km": 15.0,
                    "bearing_deg": 0.0,
                    "brightness": 340.5,
                    "confidence": "high",
                    "satellite_instrument": "VIIRS_SNPP_NRT",
                    "is_upwind": True
                },
                {
                    "latitude": 27.00,
                    "longitude": 77.00,
                    "distance_km": 110.0,
                    "bearing_deg": 180.0,
                    "brightness": 310.2,
                    "confidence": "nominal",
                    "satellite_instrument": "VIIRS_SNPP_NRT",
                    "is_upwind": False
                }
            ]
        }
    )

    traj = [
        TrajectoryPoint(
            step_hours_back=0,
            timestamp=datetime.now(timezone.utc),
            latitude=28.0,
            longitude=77.0,
            wind_speed_kmh=15.0,
            wind_direction_deg=0.0
        ),
        TrajectoryPoint(
            step_hours_back=3,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=3),
            latitude=28.78,
            longitude=77.01,
            wind_speed_kmh=15.0,
            wind_direction_deg=0.0
        )
    ]

    with patch.object(correlator.firms_client, "is_available", return_value=True), \
         patch.object(correlator.firms_client, "check_nearby_fires", new_callable=AsyncMock, return_value=mock_result), \
         patch("app.investigation.satellite_service.settings.NASA_FIRMS_MAP_KEY", "mock_key_123"):

        result = await correlator.correlate_fires(28.0, 77.0, trajectory=traj, search_radius_km=100.0)
        assert result.status == "FIRES_DETECTED"
        assert result.total_fires_in_region == 2
        assert result.trajectory_correlated_fires_count >= 1
        for cand in result.candidate_sources:
            assert cand.category == SourceCategory.BIOMASS_BURNING
            assert "DOES NOT establish specific material" in cand.description


@pytest.mark.asyncio
async def test_satellite_credentials_missing_returns_explicit_status():
    correlator = SatelliteFireCorrelator()
    with patch.object(correlator.firms_client, "is_available", return_value=False):
        res = await correlator.correlate_fires(28.0, 77.0)
        assert res.status == "CREDENTIALS_MISSING"
        assert res.data_source_mode == "UNAVAILABLE"
        assert len(res.candidate_sources) == 0


# ==============================================================================
# 4. EVIDENCE CORRELATOR TESTS
# ==============================================================================

def test_evidence_correlator_directions():
    correlator = EvidenceCorrelator()
    event_lat, event_lon = 28.6315, 77.2167

    ind_cand = CandidateSource(
        source_id="osm_way_999",
        category=SourceCategory.INDUSTRIAL_EMISSIONS,
        name="Mayapuri Industrial Area",
        latitude=28.6400,
        longitude=77.2100,
        provider="OpenStreetMap Overpass API",
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

    transport_res = TransportAssessment(
        start_latitude=event_lat,
        start_longitude=event_lon,
        event_timestamp=datetime.now(timezone.utc),
        lookback_hours=12,
        dominant_upwind_bearing_deg=90.0,
        dominant_upwind_compass="E",
        uncertainty_description="Test uncertainty",
        trajectory_points=[
            TrajectoryPoint(
                step_hours_back=0,
                timestamp=datetime.now(timezone.utc),
                latitude=event_lat,
                longitude=event_lon,
                wind_speed_kmh=12.0,
                wind_direction_deg=90.0
            )
        ]
    )

    fire_cand = CandidateSource(
        source_id="fire_888",
        category=SourceCategory.BIOMASS_BURNING,
        name="Satellite Active Fire",
        latitude=28.6315,
        longitude=77.3500,
        provider="NASA FIRMS",
        verification_status="CORRELATED_THERMAL_ANOMALY"
    )
    fire_record = FireDetectionRecord(
        fire_id="fire_888",
        latitude=28.6315,
        longitude=77.3500,
        distance_from_event_km=15.0,
        bearing_from_event_deg=90.0,
        bearing_compass="E",
        brightness=330.0,
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
        pm10=180.0,
        pm25=120.0
    )

    assert dossier.report.evidence_supporting_count >= 1
    fire_items = [e for e in dossier.investigation.evidence_ledger if e.source_reference == "fire_888"]
    assert len(fire_items) >= 1
    assert fire_items[0].direction == EvidenceDirection.SUPPORTS

    ind_items = [e for e in dossier.investigation.evidence_ledger if e.source_reference == "osm_way_999"]
    assert len(ind_items) >= 1
    assert ind_items[0].direction in (EvidenceDirection.CONTEXT_ONLY, EvidenceDirection.CONTRADICTS)

    # Verify no quantitative contribution percentages are invented
    assert "100%" not in dossier.report.confidence_assessment


# ==============================================================================
# 5. API ENDPOINTS TESTS
# ==============================================================================

def test_api_local_sources_endpoint(client):
    res = client.get("/api/investigation/local-sources?latitude=28.6315&longitude=77.2167&radius_km=2.0")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "candidates" in data
    assert "search_radius_km" in data


def test_api_transport_endpoint(client):
    res = client.get("/api/investigation/transport?latitude=28.6315&longitude=77.2167&lookback_hours=6")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "trajectory_points" in data
    assert "method_name" in data


def test_api_satellite_fires_endpoint(client):
    res = client.get("/api/investigation/satellite-fires?latitude=28.6315&longitude=77.2167&radius_km=25.0")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "total_fires_in_region" in data


def test_api_analyze_zone_post_and_get(client):
    payload = {
        "zone_id": "DEL-AV-01",
        "pollutant": "PM2.5",
        "lookback_hours": 6,
        "radius_km": 3.0
    }
    post_res = client.post("/api/investigation/analyze", json=payload)
    assert post_res.status_code == 200
    dossier = post_res.json()
    assert "investigation_id" in dossier
    assert "report" in dossier
    assert "local_sources" in dossier
    assert "transport" in dossier
    assert "satellite" in dossier
    inv_id = dossier["investigation_id"]

    get_res = client.get(f"/api/investigation/dossiers/{inv_id}")
    assert get_res.status_code == 200
    assert get_res.json()["investigation_id"] == inv_id

    list_res = client.get("/api/investigation/dossiers")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1


def test_api_analyze_validation_errors(client):
    res = client.post("/api/investigation/analyze", json={})
    assert res.status_code == 422

    res = client.post("/api/investigation/analyze", json={"latitude": 120.0, "longitude": 77.0})
    assert res.status_code == 422

    res = client.post("/api/investigation/analyze", json={"zone_id": "NON-EXISTENT-ZONE-99"})
    assert res.status_code == 404

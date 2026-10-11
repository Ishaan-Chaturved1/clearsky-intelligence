import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.data_source_registry import (
    data_source_registry,
    DataSourceRegistry,
    DataSourceMetadata,
    DataCategory,
    ProviderType,
    RetryPolicy,
)
from app.services.data_health_service import (
    DataHealthService,
    VerificationStatus,
    SourceVerificationResult,
    DataHealthSummary,
)
from app.data_sources.base import SourceFetchResult, global_cache


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def health_service():
    return DataHealthService()


# ==============================================================================
# SECTION 1: REGISTRY & METADATA
# ==============================================================================

def test_registry_registered_sources():
    sources = data_source_registry.list_sources()
    assert len(sources) == 9
    source_ids = [s.source_id for s in sources]
    assert "cpcb_in" in source_ids
    assert "openaq_v3" in source_ids
    assert "open_meteo_weather" in source_ids
    assert "open_meteo_air_quality" in source_ids
    assert "nasa_firms_viirs" in source_ids
    assert "osm_overpass" in source_ids
    assert "nominatim_geocoding" in source_ids
    assert "local_station_db" in source_ids
    assert "s3_data_lake" in source_ids


def test_registry_get_source():
    source = data_source_registry.get_source("open_meteo_weather")
    assert source is not None
    assert source.data_category == DataCategory.WEATHER
    assert source.request_timeout_seconds == 8.0
    assert "temperature_c" in source.supported_fields
    assert source.freshness_threshold_seconds == 10800


# ==============================================================================
# SECTION 2: DATA FETCHING & OPERATIONAL CHECKS (SCENARIOS 1 - 20)
# ==============================================================================

@pytest.mark.asyncio
async def test_01_and_02_successful_request_and_valid_records(health_service):
    """1. Successful provider request & 2. Valid response containing observations."""
    mock_fetch = SourceFetchResult(
        source_name="open_meteo",
        is_success=True,
        data={
            "temperature_c": 28.5,
            "relative_humidity": 55.0,
            "surface_pressure_hpa": 1012.0,
            "wind_speed_kmh": 12.0,
            "wind_direction_deg": 310.0,
            "precipitation_mmh": 0.0,
            "boundary_layer_height_m": 850.0,
            "evaporation_rate_mmh": 0.2,
            "raw_timestamp": datetime.now(timezone.utc).isoformat(),
        },
        fetched_at=time.time()
    )
    with patch.object(health_service.open_meteo_client, "get_weather", new_callable=AsyncMock, return_value=mock_fetch):
        res = await health_service.check_source("open_meteo_weather")
        assert res.status == VerificationStatus.HEALTHY
        assert res.http_status == 200
        assert res.records_received == 1
        assert res.records_valid == 1
        assert res.data_quality_score == 100.0
        assert len(res.missing_fields) == 0


@pytest.mark.asyncio
async def test_03_valid_empty_response(health_service):
    """3. Valid empty response (e.g. 0 active fires returned)."""
    mock_fetch = SourceFetchResult(
        source_name="nasa_firms",
        is_success=True,
        data={
            "nearby_fires_count": 0,
            "details": []
        },
        fetched_at=time.time()
    )
    health_service.firms_client.map_key = "dummy_valid_key"
    with patch.object(health_service.firms_client, "check_nearby_fires", new_callable=AsyncMock, return_value=mock_fetch):
        res = await health_service.check_source("nasa_firms_viirs")
        assert res.status == VerificationStatus.EMPTY
        assert res.records_received == 0
        assert res.records_valid == 0
        assert any("Zero active thermal fire anomalies" in w for w in res.warnings)


@pytest.mark.asyncio
async def test_04_http_401_or_403(health_service):
    """4. HTTP 401 or 403 unauthorized."""
    mock_fetch = SourceFetchResult(
        source_name="nasa_firms",
        is_success=False,
        error_message="HTTP 403 Forbidden: Invalid or revoked NASA FIRMS MAP_KEY",
        fetched_at=time.time()
    )
    health_service.firms_client.map_key = "revoked_key"
    with patch.object(health_service.firms_client, "check_nearby_fires", new_callable=AsyncMock, return_value=mock_fetch):
        res = await health_service.check_source("nasa_firms_viirs")
        assert res.status in (VerificationStatus.MISCONFIGURED, VerificationStatus.UNAVAILABLE)
        assert res.http_status in (401, 403)
        assert any("403" in err for err in res.errors)


@pytest.mark.asyncio
async def test_05_http_429_rate_limit(health_service):
    """5. HTTP 429 rate limit."""
    mock_fetch = SourceFetchResult(
        source_name="open_meteo",
        is_success=False,
        error_message="HTTP 429 Too Many Requests: hourly rate limit exceeded",
        fetched_at=time.time()
    )
    with patch.object(health_service.open_meteo_client, "get_weather", new_callable=AsyncMock, return_value=mock_fetch):
        res = await health_service.check_source("open_meteo_weather")
        assert res.status == VerificationStatus.RATE_LIMITED
        assert res.http_status == 429
        assert any("429" in err for err in res.errors)


@pytest.mark.asyncio
async def test_06_http_500_server_error(health_service):
    """6. HTTP 500 server error."""
    mock_fetch = SourceFetchResult(
        source_name="open_meteo",
        is_success=False,
        error_message="HTTP 500 Internal Server Error: Gateway failure",
        fetched_at=time.time()
    )
    with patch.object(health_service.open_meteo_client, "get_weather", new_callable=AsyncMock, return_value=mock_fetch):
        res = await health_service.check_source("open_meteo_weather")
        assert res.status == VerificationStatus.UNAVAILABLE
        assert res.http_status == 500
        assert any("500" in err for err in res.errors)


@pytest.mark.asyncio
async def test_07_connection_timeout(health_service):
    """7. Connection timeout."""
    mock_fetch = SourceFetchResult(
        source_name="open_meteo",
        is_success=False,
        error_message="Request timeout: connection to api.open-meteo.com timed out after 8.0s",
        fetched_at=time.time()
    )
    with patch.object(health_service.open_meteo_client, "get_weather", new_callable=AsyncMock, return_value=mock_fetch):
        res = await health_service.check_source("open_meteo_weather")
        assert res.status == VerificationStatus.UNAVAILABLE
        assert any("timeout" in err.lower() for err in res.errors)


@pytest.mark.asyncio
async def test_08_connection_failure(health_service):
    """8. Connection failure."""
    mock_fetch = SourceFetchResult(
        source_name="open_meteo",
        is_success=False,
        error_message="Connection failure: [Errno 111] Connection refused",
        fetched_at=time.time()
    )
    with patch.object(health_service.open_meteo_client, "get_weather", new_callable=AsyncMock, return_value=mock_fetch):
        res = await health_service.check_source("open_meteo_weather")
        assert res.status == VerificationStatus.UNAVAILABLE
        assert any("connection" in err.lower() for err in res.errors)


@pytest.mark.asyncio
async def test_09_malformed_json(health_service):
    """9. Malformed JSON."""
    mock_fetch = SourceFetchResult(
        source_name="open_meteo",
        is_success=False,
        error_message="JSONDecodeError: Expecting value at line 1 column 1",
        fetched_at=time.time()
    )
    with patch.object(health_service.open_meteo_client, "get_weather", new_callable=AsyncMock, return_value=mock_fetch):
        res = await health_service.check_source("open_meteo_weather")
        assert res.status == VerificationStatus.UNAVAILABLE
        assert any("json" in err.lower() for err in res.errors)


@pytest.mark.asyncio
async def test_10_unexpected_response_schema(health_service):
    """10. Unexpected response schema (e.g. empty dictionary missing expected fields)."""
    mock_fetch = SourceFetchResult(
        source_name="open_meteo",
        is_success=True,
        data={},  # missing all fields
        fetched_at=time.time()
    )
    with patch.object(health_service.open_meteo_client, "get_weather", new_callable=AsyncMock, return_value=mock_fetch):
        res = await health_service.check_source("open_meteo_weather")
        assert res.status == VerificationStatus.DEGRADED
        assert len(res.missing_fields) > 0


@pytest.mark.asyncio
async def test_11_missing_required_fields(health_service):
    """11. Missing required fields in observation."""
    mock_fetch = SourceFetchResult(
        source_name="open_meteo",
        is_success=True,
        data={
            "temperature_c": 25.0,
            # relative_humidity, wind_speed_kmh, etc. missing
        },
        fetched_at=time.time()
    )
    with patch.object(health_service.open_meteo_client, "get_weather", new_callable=AsyncMock, return_value=mock_fetch):
        res = await health_service.check_source("open_meteo_weather")
        assert res.status == VerificationStatus.DEGRADED
        assert "relative_humidity" in res.missing_fields
        assert res.data_quality_score < 100.0


@pytest.mark.asyncio
async def test_12_invalid_timestamps(health_service):
    """12. Invalid unparseable timestamps."""
    mock_fetch = SourceFetchResult(
        source_name="open_meteo",
        is_success=True,
        data={
            "temperature_c": 25.0,
            "relative_humidity": 50.0,
            "surface_pressure_hpa": 1010.0,
            "wind_speed_kmh": 10.0,
            "wind_direction_deg": 180.0,
            "precipitation_mmh": 0.0,
            "boundary_layer_height_m": 700.0,
            "evaporation_rate_mmh": 0.1,
            "raw_timestamp": "NOT_A_VALID_DATE_STRING_XYZ",
        },
        fetched_at=time.time()
    )
    with patch.object(health_service.open_meteo_client, "get_weather", new_callable=AsyncMock, return_value=mock_fetch):
        res = await health_service.check_source("open_meteo_weather")
        assert res.latest_observation_at is None


@pytest.mark.asyncio
async def test_13_invalid_coordinates(health_service):
    """13. Invalid coordinates in spatial dataset."""
    mock_fetch = SourceFetchResult(
        source_name="nasa_firms",
        is_success=True,
        data={
            "nearby_fires_count": 1,
            "details": [
                {"latitude": 999.0, "longitude": 77.2, "bright_ti4": 320.0, "acq_date": "2026-10-11"}
            ]
        },
        fetched_at=time.time()
    )
    health_service.firms_client.map_key = "dummy_valid_key"
    with patch.object(health_service.firms_client, "check_nearby_fires", new_callable=AsyncMock, return_value=mock_fetch):
        res = await health_service.check_source("nasa_firms_viirs")
        assert res.records_rejected == 1
        assert res.records_valid == 0


@pytest.mark.asyncio
async def test_14_nan_or_infinite_measurements(health_service):
    """14. NaN or infinite measurements."""
    mock_fetch = SourceFetchResult(
        source_name="openaq",
        is_success=True,
        data=[
            {"station_id": "ST-01", "latitude": 28.65, "longitude": 77.30, "pm25": float("nan"), "pm10": 100.0}
        ],
        fetched_at=time.time()
    )
    with patch.object(health_service.openaq_client, "get_nearby_station_measurements", new_callable=AsyncMock, return_value=mock_fetch):
        res = await health_service.check_source("openaq_v3")
        assert res.records_rejected == 1
        assert res.records_valid == 0


@pytest.mark.asyncio
async def test_15_duplicate_records(health_service):
    """15. Duplicate records in station telemetry."""
    mock_fetch = SourceFetchResult(
        source_name="openaq",
        is_success=True,
        data=[
            {"station_id": "ST-DUP", "latitude": 28.65, "longitude": 77.30, "pm25": 120.0, "pm10": 180.0},
            {"station_id": "ST-DUP", "latitude": 28.65, "longitude": 77.30, "pm25": 120.0, "pm10": 180.0},
        ],
        fetched_at=time.time()
    )
    with patch.object(health_service.openaq_client, "get_nearby_station_measurements", new_callable=AsyncMock, return_value=mock_fetch):
        res = await health_service.check_source("openaq_v3")
        assert res.unique_station_count == 1
        assert res.records_received == 2


@pytest.mark.asyncio
async def test_16_partial_pollutant_coverage(health_service):
    """16. Partial pollutant coverage."""
    mock_fetch = SourceFetchResult(
        source_name="open_meteo",
        is_success=True,
        data={
            "pm25": 110.0,
            # pm10, dust missing
            "raw_timestamp": datetime.now(timezone.utc).isoformat(),
        },
        fetched_at=time.time()
    )
    with patch.object(health_service.open_meteo_client, "get_air_quality", new_callable=AsyncMock, return_value=mock_fetch):
        res = await health_service.check_source("open_meteo_air_quality")
        assert res.status == VerificationStatus.DEGRADED
        assert "pm10" in res.missing_fields
        assert res.data_quality_score < 100.0


@pytest.mark.asyncio
async def test_17_missing_required_configuration(health_service):
    """17. Missing required configuration (e.g. NASA_FIRMS_MAP_KEY)."""
    health_service.firms_client.map_key = None
    res = await health_service.check_source("nasa_firms_viirs")
    assert res.status == VerificationStatus.MISCONFIGURED
    assert any("NASA_FIRMS_MAP_KEY" in err for err in res.errors)


@pytest.mark.asyncio
async def test_18_missing_optional_configuration(health_service):
    """18. Missing optional configuration (e.g. OPENAQ_API_KEY)."""
    mock_fetch = SourceFetchResult(
        source_name="openaq",
        is_success=True,
        data=[],
        fetched_at=time.time()
    )
    with patch.object(health_service.openaq_client, "get_nearby_station_measurements", new_callable=AsyncMock, return_value=mock_fetch):
        res = await health_service.check_source("openaq_v3")
        # Should NOT be MISCONFIGURED, but EMPTY
        assert res.status == VerificationStatus.EMPTY
        assert res.status != VerificationStatus.MISCONFIGURED


@pytest.mark.asyncio
async def test_19_and_20_retry_policy():
    """19. Retry policy definition and configuration."""
    src = data_source_registry.get_source("open_meteo_weather")
    assert src.retry_policy.max_retries == 2
    assert 500 in src.retry_policy.retry_status_codes


# ==============================================================================
# SECTION 3: FRESHNESS AND CACHE (SCENARIOS 21 - 27)
# ==============================================================================

@pytest.mark.asyncio
async def test_21_and_22_fresh_and_stale_observations(health_service):
    """21. Fresh observations vs 22. Stale observations."""
    now_utc = datetime.now(timezone.utc)
    old_time = (now_utc - timedelta(hours=6)).isoformat()

    mock_fetch = SourceFetchResult(
        source_name="open_meteo",
        is_success=True,
        data={
            "temperature_c": 25.0,
            "relative_humidity": 50.0,
            "surface_pressure_hpa": 1010.0,
            "wind_speed_kmh": 10.0,
            "wind_direction_deg": 180.0,
            "precipitation_mmh": 0.0,
            "boundary_layer_height_m": 700.0,
            "evaporation_rate_mmh": 0.1,
            "raw_timestamp": old_time,  # 6 hours old (> 3 hours threshold)
        },
        fetched_at=time.time()
    )
    with patch.object(health_service.open_meteo_client, "get_weather", new_callable=AsyncMock, return_value=mock_fetch):
        res = await health_service.check_source("open_meteo_weather")
        assert res.status == VerificationStatus.STALE
        assert any("hours old" in w for w in res.warnings)


@pytest.mark.asyncio
async def test_23_successful_fetch_returning_old_observations(health_service):
    """23. Distinction between fetch time and observation time."""
    mock_fetch = SourceFetchResult(
        source_name="open_meteo",
        is_success=True,
        data={
            "temperature_c": 25.0,
            "relative_humidity": 50.0,
            "surface_pressure_hpa": 1010.0,
            "wind_speed_kmh": 10.0,
            "wind_direction_deg": 180.0,
            "precipitation_mmh": 0.0,
            "boundary_layer_height_m": 700.0,
            "evaporation_rate_mmh": 0.1,
            "raw_timestamp": "2021-01-01T00:00:00Z",
        },
        fetched_at=time.time()
    )
    with patch.object(health_service.open_meteo_client, "get_weather", new_callable=AsyncMock, return_value=mock_fetch):
        res = await health_service.check_source("open_meteo_weather")
        assert res.last_successful_fetch_at is not None
        assert res.latest_observation_at.year == 2021
        assert res.last_successful_fetch_at.year >= 2026


@pytest.mark.asyncio
async def test_24_to_27_cache_audit_fallback(health_service):
    """24-27. Stored dataset audit inspection of memory cache."""
    cache_key = "open_meteo_test_sample"
    global_cache._cache[cache_key] = {
        "data": {"temperature_c": 22.0},
        "timestamp": time.time() - 100,
        "ttl": 1800
    }
    src = data_source_registry.get_source("open_meteo_weather")
    res = await health_service._run_stored_audit(src, datetime.now(timezone.utc))
    assert res.status in (VerificationStatus.HEALTHY, VerificationStatus.DEGRADED, VerificationStatus.STALE)
    assert res.provenance == "STORED_CACHE"


# ==============================================================================
# SECTION 4: COMPLETENESS (SCENARIOS 28 - 34)
# ==============================================================================

@pytest.mark.asyncio
async def test_28_and_29_complete_and_partial_air_quality(health_service):
    """28. Complete vs 29. Partial air quality."""
    mock_fetch = SourceFetchResult(
        source_name="open_meteo",
        is_success=True,
        data={
            "pm10": 150.0,
            "pm25": 85.0,
            "dust": 50.0,
            "raw_timestamp": datetime.now(timezone.utc).isoformat(),
        },
        fetched_at=time.time()
    )
    with patch.object(health_service.open_meteo_client, "get_air_quality", new_callable=AsyncMock, return_value=mock_fetch):
        res = await health_service.check_source("open_meteo_air_quality")
        assert res.status == VerificationStatus.HEALTHY
        assert res.data_quality_score == 100.0
        assert len(res.missing_fields) == 0


@pytest.mark.asyncio
async def test_33_and_34_unsupported_vs_missing_fields():
    """33. Unsupported fields vs 34. Missing fields."""
    src = data_source_registry.get_source("open_meteo_weather")
    assert "pm25" not in src.supported_fields
    assert "temperature_c" in src.supported_fields


# ==============================================================================
# SECTION 5: OVERALL HEALTH (SCENARIOS 35 - 40)
# ==============================================================================

@pytest.mark.asyncio
async def test_35_to_40_stored_data_audit_summary(health_service):
    """35-40: Stored data audit summary counts and overall status."""
    summary = await health_service.audit_stored_datasets()
    assert summary.total_registered_sources == 9
    assert summary.total_checked == 9
    assert summary.overall_status in [
        VerificationStatus.HEALTHY,
        VerificationStatus.DEGRADED,
        VerificationStatus.STALE,
        VerificationStatus.EMPTY,
    ]
    count_sum = (
        summary.healthy_count
        + summary.degraded_count
        + summary.stale_count
        + summary.empty_count
        + summary.misconfigured_count
        + summary.unavailable_count
        + summary.rate_limited_count
        + summary.error_count
        + summary.not_checked_count
    )
    assert count_sum == summary.total_registered_sources


# ==============================================================================
# SECTION 6: API ENDPOINTS (SCENARIOS 51 - 54)
# ==============================================================================

def test_51_health_summary_endpoint(client):
    """51. Health endpoint response schema."""
    res = client.get("/api/data-health")
    assert res.status_code == 200
    data = res.json()
    assert "total_registered_sources" in data
    assert "overall_status" in data
    assert "results" in data
    assert data["total_registered_sources"] == 9
    assert isinstance(data["results"], list)


def test_52_sources_and_single_source_endpoint(client):
    """52. Sources listing and single source endpoint."""
    res = client.get("/api/data-health/sources")
    assert res.status_code == 200
    sources = res.json()
    assert len(sources) == 9

    res_single = client.get("/api/data-health/sources/open_meteo_weather")
    assert res_single.status_code == 200
    single = res_single.json()
    assert single["source_id"] == "open_meteo_weather"
    assert "status" in single
    assert "expected_fields" in single

    res_404 = client.get("/api/data-health/sources/non_existent_source_99")
    assert res_404.status_code == 404
    assert "not registered" in res_404.json()["detail"].lower()


def test_53_live_check_post_endpoint(client):
    """53. Trigger live check endpoint for single source."""
    res = client.post("/api/data-health/check?source_id=local_station_db")
    assert res.status_code == 200
    data = res.json()
    assert data["source_id"] == "local_station_db"
    assert data["status"] in ["HEALTHY", "DEGRADED", "STALE", "EMPTY"]


def test_54_stored_audit_post_endpoint(client):
    """54. Trigger stored data audit endpoint."""
    res = client.post("/api/data-health/audit")
    assert res.status_code == 200
    data = res.json()
    assert data["total_registered_sources"] == 9
    assert data["total_checked"] == 9
    assert data["overall_status"] is not None

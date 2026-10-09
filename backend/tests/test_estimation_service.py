import pytest
from app.services.estimation_service import EstimationService
from app.models.domain import ConfidenceLevel

@pytest.fixture
def service():
    return EstimationService(max_station_distance_km=25.0, min_stations_for_idw=2)

def test_haversine_distance(service):
    # Distance between Connaught Place (28.6315, 77.2167) and India Gate (28.6129, 77.2295) is approx 2.4 km
    d = service.haversine_km(28.6315, 77.2167, 28.6129, 77.2295)
    assert 2.0 <= d <= 3.0

def test_nearest_station_observation(service):
    stations = [
        {"station_id": "STN-1", "latitude": 28.61, "longitude": 77.21, "pm25": 75.0, "distance_km": 3.2}
    ]
    pollutant, meta = service.estimate_pollutant("pm25", 28.60, 77.20, stations, modeled_value=50.0)
    assert pollutant.value == 75.0
    assert pollutant.data_type == "observed"
    assert meta["method"] == "nearest_station_observation"

def test_idw_interpolation(service):
    # Two stations farther than 5km but within 25km
    stations = [
        {"station_id": "STN-A", "latitude": 28.65, "longitude": 77.25, "pm10": 100.0, "distance_km": 8.0},
        {"station_id": "STN-B", "latitude": 28.55, "longitude": 77.15, "pm10": 200.0, "distance_km": 12.0}
    ]
    pollutant, meta = service.estimate_pollutant("pm10", 28.60, 77.20, stations, modeled_value=120.0)
    assert pollutant.data_type == "interpolated"
    assert 100.0 < pollutant.value < 200.0

def test_modeled_fallback_when_no_stations(service):
    pollutant, meta = service.estimate_pollutant("pm25", 28.60, 77.20, [], modeled_value=64.5)
    assert pollutant.value == 64.5
    assert pollutant.data_type == "modeled"
    assert meta["method"] == "numerical_atmospheric_model"

def test_confidence_assessment(service):
    conf_high = service.assess_confidence("observed", "observed", True, True, False, True)
    assert conf_high == ConfidenceLevel.HIGH

    conf_med = service.assess_confidence("modeled", "modeled", True, True, False, True)
    assert conf_med == ConfidenceLevel.MEDIUM

    conf_low_stale = service.assess_confidence("observed", "observed", True, True, True, True)
    assert conf_low_stale == ConfidenceLevel.LOW

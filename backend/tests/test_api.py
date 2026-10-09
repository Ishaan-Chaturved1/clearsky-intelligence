import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    # TestClient triggers lifespan automatically
    with TestClient(app) as c:
        yield c

def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "ClearSky" in data["app"]

def test_overview_endpoint(client):
    res = client.get("/api/overview")
    assert res.status_code == 200
    data = res.json()
    assert "total_monitored_zones" in data
    assert "estimated_water_saved_liters" in data
    assert "data_mode" in data

def test_zones_endpoint(client):
    res = client.get("/api/zones")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 10
    first_zone = data[0]
    assert "zone" in first_zone
    assert "zone_id" in first_zone["zone"]
    assert "latest_decision" in first_zone

def test_single_zone_endpoint(client):
    res = client.get("/api/zones/DEL-AV-01")
    assert res.status_code == 200
    data = res.json()
    assert data["zone"]["zone_id"] == "DEL-AV-01"

def test_zone_not_found(client):
    res = client.get("/api/zones/NON-EXISTENT-99")
    assert res.status_code == 404

def test_water_savings_endpoint(client):
    res = client.get("/api/analytics/water-savings?days=7")
    assert res.status_code == 200
    data = res.json()
    assert data["reporting_period_days"] == 7
    assert data["baseline_interventions"] > 0
    assert "daily_trend" in data

def test_water_savings_csv_export(client):
    res = client.get("/api/analytics/water-savings/export?days=7")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "ClearSky Intelligence" in res.text

def test_methodology_endpoint(client):
    res = client.get("/api/methodology")
    assert res.status_code == 200
    data = res.json()
    assert len(data["rules"]) >= 6
    assert "disclaimer" in str(data).lower() or "limitation" in str(data).lower()

def test_sources_status_endpoint(client):
    res = client.get("/api/sources/status")
    assert res.status_code == 200
    data = res.json()
    assert len(data["sources"]) >= 4

def test_daily_brief_endpoint(client):
    res = client.get("/api/brief/daily")
    assert res.status_code == 200
    data = res.json()
    assert "headline" in data
    assert "summary_text" in data

def test_atmospheric_analysis_endpoint(client):
    res = client.get("/api/zones/DEL-AV-01/atmospheric-analysis")
    assert res.status_code == 200
    data = res.json()
    assert data["zone_id"] == "DEL-AV-01"
    assert "aqi_estimate" in data
    assert "pressure_tendency" in data
    assert "wind_drift_risk" in data
    assert "decision" in data
    assert len(data["decision_rationale"]) > 0

def test_candidate_road_segments_endpoint(client):
    res = client.get("/api/zones/DEL-AV-01/candidate-segments")
    assert res.status_code == 200
    data = res.json()
    assert data["zone_id"] == "DEL-AV-01"
    assert data["total_segments"] >= 1
    assert data["total_water_required_liters"] > 0
    assert len(data["segments"]) >= 1
    first_seg = data["segments"][0]
    assert "surface_area_m2" in first_seg
    assert "tanker_trips_required" in first_seg
    assert "priority_score" in first_seg

def test_forecast_windows_endpoint(client):
    res = client.get("/api/zones/DEL-AV-01/forecast-windows")
    assert res.status_code == 200
    data = res.json()
    assert data["zone_id"] == "DEL-AV-01"
    assert len(data["windows"]) >= 5
    first_win = data["windows"][0]
    assert "suitability_score" in first_win
    assert "suitability_label" in first_win
    assert "forecast_temp_c" in first_win

def test_strategy_comparison_endpoint(client):
    res = client.get("/api/analytics/strategy-comparison?days=7")
    assert res.status_code == 200
    data = res.json()
    assert len(data["scenarios"]) == 4
    scen_ids = [s["strategy_id"] for s in data["scenarios"]]
    assert "SCEN-01-SCHEDULED" in scen_ids
    assert "SCEN-03-CLEARSKY-TARGETED" in scen_ids

def test_intervention_logging_and_effectiveness(client):
    # Test GET interventions
    res_list = client.get("/api/interventions")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    # Test POST intervention
    payload = {
        "zone_id": "DEL-AV-01",
        "timestamp_start": "2026-10-09T08:00:00Z",
        "timestamp_end": "2026-10-09T08:30:00Z",
        "water_volume_liters": 5000.0,
        "method": "MIST_CANNON",
        "pre_intervention_pm10": 290.0,
        "post_intervention_pm10_1h": 240.0,
        "notes": "Field trial validation run"
    }
    res_post = client.post("/api/interventions", json=payload)
    assert res_post.status_code == 200
    created = res_post.json()
    assert created["observed_delta_pm10"] == 50.0

    # Test summary
    res_sum = client.get("/api/interventions/effectiveness-summary")
    assert res_sum.status_code == 200
    sum_data = res_sum.json()
    assert sum_data["model_status"] == "EXPERIMENTAL_CALIBRATING"
    assert sum_data["sample_size"] >= 2

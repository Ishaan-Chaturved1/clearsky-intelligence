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

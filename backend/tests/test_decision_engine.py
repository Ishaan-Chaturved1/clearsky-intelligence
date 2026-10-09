import pytest
from app.models.domain import (
    Zone,
    EnvironmentalReading,
    PollutantValue,
    WeatherConditions,
    FireSummary,
    DecisionType,
    ConfidenceLevel,
    DataMode,
    NearbyInfrastructure
)
from app.services.decision_engine import DecisionEngine

@pytest.fixture
def engine():
    return DecisionEngine()

@pytest.fixture
def default_zone():
    return Zone(
        zone_id="TEST-01",
        name="Test Zone",
        latitude=28.6,
        longitude=77.2,
        description="Test sector",
        zone_type="Urban",
        nearby_infrastructure=NearbyInfrastructure(
            major_roads=["Ring Road"],
            construction_sites=[],
            has_construction_nearby=False,
            construction_distance_meters=1500
        )
    )

def make_reading(
    pm25: float = 60.0,
    pm10: float = 180.0,
    rh: float = 50.0,
    ws: float = 8.0,
    blh: float = 500.0,
    wd: float = 270.0,
    fires_count: int = 0,
    smoke: bool = False,
    is_stale: bool = False
) -> EnvironmentalReading:
    return EnvironmentalReading(
        reading_id="RD-TEST",
        zone_id="TEST-01",
        timestamp="2026-10-09T08:00:00Z",
        pm25=PollutantValue(value=pm25, unit="ug/m3", data_type="observed"),
        pm10=PollutantValue(value=pm10, unit="ug/m3", data_type="observed"),
        pm_ratio=round(pm10 / pm25, 2) if pm25 and pm25 > 0 else None,
        weather=WeatherConditions(
            temperature_c=28.0,
            relative_humidity=rh,
            wind_speed_kmh=ws,
            wind_direction_deg=wd,
            boundary_layer_height_m=blh
        ),
        fire_summary=FireSummary(
            nearby_fires_count=fires_count,
            closest_fire_distance_km=15.0 if fires_count > 0 else None,
            possible_smoke_transport=smoke
        ),
        data_mode=DataMode.DEMO,
        is_stale=is_stale
    )

def test_dust_dominance_triggers_recommendation(engine, default_zone):
    # Ratio = 180 / 60 = 3.0 >= 2.0, PM10 >= 120 -> RECOMMENDED
    reading = make_reading(pm25=60.0, pm10=180.0, rh=50.0, ws=8.0)
    decision = engine.evaluate(default_zone, reading, "2026-10-09T08:00:00Z")
    assert decision.decision == DecisionType.INTERVENTION_RECOMMENDED
    assert decision.priority in [2, 3, 4, 5]
    assert any("coarse fugitive dust" in r for r in decision.reasons)

def test_smoke_influence_discourages_intervention(engine, default_zone):
    # Even if PM10 is high, active smoke transport suppresses spraying
    reading = make_reading(pm25=90.0, pm10=250.0, fires_count=3, smoke=True)
    decision = engine.evaluate(default_zone, reading, "2026-10-09T08:00:00Z")
    assert decision.decision == DecisionType.INTERVENTION_NOT_RECOMMENDED
    assert any("smoke" in r.lower() for r in decision.reasons)

def test_high_humidity_discourages_intervention(engine, default_zone):
    reading = make_reading(pm25=60.0, pm10=200.0, rh=88.0, ws=8.0)
    decision = engine.evaluate(default_zone, reading, "2026-10-09T08:00:00Z")
    assert decision.decision == DecisionType.INTERVENTION_NOT_RECOMMENDED
    assert any("humidity" in r.lower() for r in decision.reasons)

def test_high_wind_discourages_intervention(engine, default_zone):
    reading = make_reading(pm25=60.0, pm10=200.0, rh=50.0, ws=24.0)
    decision = engine.evaluate(default_zone, reading, "2026-10-09T08:00:00Z")
    assert decision.decision == DecisionType.INTERVENTION_NOT_RECOMMENDED
    assert any("wind" in r.lower() for r in decision.reasons)

def test_stale_data_yields_advisory_only(engine, default_zone):
    reading = make_reading(pm25=60.0, pm10=200.0, is_stale=True)
    decision = engine.evaluate(default_zone, reading, "2026-10-09T08:00:00Z")
    assert decision.decision == DecisionType.ADVISORY_ONLY
    assert decision.confidence == ConfidenceLevel.LOW
    assert any("stale" in r.lower() for r in decision.reasons)

def test_missing_pollutant_yields_advisory_only(engine, default_zone):
    reading = make_reading(pm25=50.0, pm10=100.0)
    reading.pm10.value = None
    decision = engine.evaluate(default_zone, reading, "2026-10-09T08:00:00Z")
    assert decision.decision == DecisionType.ADVISORY_ONLY
    assert decision.confidence == ConfidenceLevel.LOW

def test_contradictory_readings_pm10_less_than_pm25(engine, default_zone):
    # Physical anomaly: PM10 reported lower than PM2.5
    reading = make_reading(pm25=120.0, pm10=40.0)
    decision = engine.evaluate(default_zone, reading, "2026-10-09T08:00:00Z")
    assert decision.decision == DecisionType.ADVISORY_ONLY
    assert any("contradict" in w.lower() for w in decision.warnings)

def test_zero_denominator_safe_handling(engine, default_zone):
    reading = make_reading(pm25=0.0, pm10=80.0)
    decision = engine.evaluate(default_zone, reading, "2026-10-09T08:00:00Z")
    assert decision.decision in [DecisionType.ADVISORY_ONLY, DecisionType.INTERVENTION_NOT_RECOMMENDED]
    assert any("zero" in w.lower() for w in decision.warnings)

def test_construction_proximity_escalates_priority(engine):
    construction_zone = Zone(
        zone_id="CONST-01",
        name="Construction Corridor",
        latitude=28.6,
        longitude=77.2,
        description="Active flyover site",
        zone_type="Transit",
        nearby_infrastructure=NearbyInfrastructure(
            major_roads=["Main Road"],
            construction_sites=["Excavation site"],
            has_construction_nearby=True,
            construction_distance_meters=180
        )
    )
    reading = make_reading(pm25=70.0, pm10=280.0, rh=45.0, ws=6.0)
    decision = engine.evaluate(construction_zone, reading, "2026-10-09T08:00:00Z")
    assert decision.decision in [DecisionType.INTERVENTION_RECOMMENDED, DecisionType.TARGETED_INTERVENTION_RECOMMENDED]
    assert decision.priority >= 4
    assert any("construction" in r.lower() for r in decision.reasons)

def test_inversion_conditions_add_warning(engine, default_zone):
    # BLH <= 300 and ws <= 5.0
    reading = make_reading(pm25=70.0, pm10=210.0, blh=220.0, ws=3.0)
    decision = engine.evaluate(default_zone, reading, "2026-10-09T08:00:00Z")
    assert any("inversion" in w.lower() for w in decision.warnings)

def test_high_pm25_alone_does_not_trigger_intervention(engine, default_zone):
    # Pure combustion soot / vehicle exhaust (high PM2.5 = 140, PM10 = 160 -> ratio 1.14 < 2.0)
    reading = make_reading(pm25=140.0, pm10=160.0, rh=50.0, ws=8.0)
    decision = engine.evaluate(default_zone, reading, "2026-10-09T08:00:00Z")
    assert decision.decision == DecisionType.INTERVENTION_NOT_RECOMMENDED
    assert any("soot" in r.lower() or "combustion" in r.lower() for r in decision.reasons)

def test_active_precipitation_discourages_intervention(engine, default_zone):
    reading = make_reading(pm25=50.0, pm10=220.0, rh=65.0, ws=7.0)
    reading.weather.precipitation_mmh = 0.8
    decision = engine.evaluate(default_zone, reading, "2026-10-09T08:00:00Z")
    assert decision.decision == DecisionType.INTERVENTION_NOT_RECOMMENDED
    assert "GATE-ACTIVE-PRECIPITATION" in decision.triggered_rules
    assert any("precipitation" in r.lower() or "rain" in r.lower() for r in decision.reasons)

def test_severe_rapid_drying_suggests_alternative_dust_control(engine, default_zone):
    reading = make_reading(pm25=60.0, pm10=240.0, rh=30.0, ws=12.0)
    reading.weather.estimated_surface_drying_time_min = 8
    decision = engine.evaluate(default_zone, reading, "2026-10-09T08:00:00Z")
    assert decision.decision == DecisionType.ALTERNATIVE_DUST_CONTROL_SUGGESTED
    assert "OPT-RAPID-DRYING-ALTERNATIVE" in decision.triggered_rules
    assert any("drying" in r.lower() or "evaporation" in r.lower() for r in decision.reasons)

def test_pressure_trend_included_as_supporting_context(engine, default_zone):
    reading = make_reading(pm25=60.0, pm10=200.0, rh=50.0, ws=8.0)
    reading.weather.surface_pressure_hpa = 1014.2
    reading.weather.pressure_trend_3h_hpa = 1.8
    reading.weather.pressure_tendency = "RISING"
    decision = engine.evaluate(default_zone, reading, "2026-10-09T08:00:00Z")
    assert any("1014.2" in r and "RISING" in r for r in decision.reasons)
    assert len(decision.conditions_to_change) > 0
    assert len(decision.triggered_rules) > 0

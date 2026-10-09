import pytest
from app.analytics.water_efficiency import WaterEfficiencyAnalytics
from app.models.domain import DecisionRecord, DecisionType, ConfidenceLevel, PollutantValue, WeatherConditions, DataMode

@pytest.fixture
def analytics():
    return WaterEfficiencyAnalytics(
        default_baseline_per_zone_per_day=3.0,
        default_liters_per_intervention=5000.0
    )

def test_water_savings_standard_calculation(analytics):
    # 10 zones over 7 days = 10 * 3 * 7 = 210 baseline ops
    # 30 recommended ops -> 180 avoided ops
    # baseline water: 210 * 5000 = 1,050,000 L
    # recommended water: 30 * 5000 = 150,000 L
    # saved water: 900,000 L
    # reduction %: (210 - 30)/210 * 100 = 85.7%

    dummy_decisions = []
    for i in range(30):
        dummy_decisions.append(
            DecisionRecord(
                decision_id=f"D-{i}",
                zone_id="Z1",
                decision=DecisionType.INTERVENTION_RECOMMENDED,
                confidence=ConfidenceLevel.HIGH,
                pollutants={},
                weather=WeatherConditions(),
                scored_at="2026-10-09T08:00:00Z",
                observed_at="2026-10-09T08:00:00Z"
            )
        )

    res = analytics.calculate_savings(
        number_of_zones=10,
        number_of_days=7,
        decision_records=dummy_decisions,
        baseline_per_zone_per_day=3.0,
        assumed_liters_per_intervention=5000.0
    )

    assert res.baseline_interventions == 210
    assert res.recommended_interventions == 30
    assert res.avoided_interventions == 180
    assert res.baseline_water_liters == 1050000.0
    assert res.recommended_water_liters == 150000.0
    assert res.estimated_water_saved_liters == 900000.0
    assert res.intervention_reduction_percent == 85.7

def test_zero_baseline_safe_handling(analytics):
    res = analytics.calculate_savings(
        number_of_zones=0,
        number_of_days=0,
        decision_records=[],
        baseline_per_zone_per_day=0.0
    )
    assert res.baseline_interventions >= 0
    assert res.intervention_reduction_percent >= 0.0

def test_csv_export_format(analytics):
    res = analytics.calculate_savings(
        number_of_zones=5,
        number_of_days=3,
        decision_records=[]
    )
    csv_str = analytics.generate_csv_export(res)
    assert "ClearSky Intelligence - Water Efficiency Audit Report" in csv_str
    assert "Baseline Operations" in csv_str
    assert "Water Saved (Liters)" in csv_str

import math
from datetime import datetime, timezone, timedelta
import pytest
from pydantic import ValidationError

from app.models.investigation import (
    ProvenanceType,
    SourceCategory,
    EvidenceDirection,
    PollutantReading,
    EnvironmentalObservation,
    WeatherObservation,
    PollutionEvent,
    CandidateSource,
    EvidenceItem,
    SourceContributionAssessment,
    Investigation,
    InvestigationReport,
)
from app.investigation.normalization import (
    normalize_timestamp,
    validate_coordinates,
    validate_numeric_measurement,
    evaluate_freshness,
    convert_pollutant_concentration,
)
from app.investigation.aqi_service import (
    calculate_indian_aqi,
    calculate_cpcb_aqi_details,
    calculate_sub_index,
    get_cpcb_category,
    PM10_BREAKPOINTS,
    PM25_BREAKPOINTS,
)
from app.investigation.event_detector import (
    PollutionEventDetector,
    EventDetectionConfig,
)


# ==============================================================================
# 1. DOMAIN MODEL TESTS
# ==============================================================================

def test_pollutant_reading_valid():
    reading = PollutantReading(
        pollutant="PM2.5",
        concentration=45.5,
        unit="ug/m3",
        provenance=ProvenanceType.GROUND_MEASUREMENT,
        uncertainty=2.1
    )
    assert reading.pollutant == "PM2.5"
    assert reading.concentration == 45.5
    assert reading.provenance == ProvenanceType.GROUND_MEASUREMENT
    assert reading.uncertainty == 2.1


def test_pollutant_reading_rejects_negative_or_nan():
    with pytest.raises(ValidationError):
        PollutantReading(pollutant="PM10", concentration=-15.0)

    with pytest.raises(ValidationError):
        PollutantReading(pollutant="PM10", concentration=float("nan"))

    with pytest.raises(ValidationError):
        PollutantReading(pollutant="PM10", concentration=float("inf"))


def test_environmental_observation_coordinates():
    # Valid coordinates
    obs = EnvironmentalObservation(
        observation_id="obs_001",
        category="air_quality",
        provider_id="openaq",
        observation_timestamp=datetime(2026, 10, 11, 8, 0, tzinfo=timezone.utc),
        retrieval_timestamp=datetime(2026, 10, 11, 8, 5, tzinfo=timezone.utc),
        latitude=28.6139,
        longitude=77.2090,
        provenance=ProvenanceType.GROUND_MEASUREMENT,
        pollutant="PM2.5",
        value=65.0
    )
    assert obs.latitude == 28.6139
    assert obs.longitude == 77.2090

    # Optional coordinates for gridded/regional data
    regional_obs = EnvironmentalObservation(
        observation_id="obs_002",
        category="air_quality",
        provider_id="cams_regional",
        observation_timestamp=datetime(2026, 10, 11, 8, 0, tzinfo=timezone.utc),
        retrieval_timestamp=datetime(2026, 10, 11, 8, 5, tzinfo=timezone.utc),
        latitude=None,
        longitude=None,
        provenance=ProvenanceType.MODELED,
        value=50.0
    )
    assert regional_obs.latitude is None
    assert regional_obs.longitude is None

    # Invalid coordinates
    with pytest.raises(ValidationError):
        EnvironmentalObservation(
            observation_id="obs_invalid_lat",
            category="air_quality",
            provider_id="openaq",
            observation_timestamp=datetime.now(timezone.utc),
            retrieval_timestamp=datetime.now(timezone.utc),
            latitude=95.0,  # > 90
            longitude=77.0,
            provenance=ProvenanceType.GROUND_MEASUREMENT
        )

    with pytest.raises(ValidationError):
        EnvironmentalObservation(
            observation_id="obs_invalid_lon",
            category="air_quality",
            provider_id="openaq",
            observation_timestamp=datetime.now(timezone.utc),
            retrieval_timestamp=datetime.now(timezone.utc),
            latitude=28.0,
            longitude=-190.0,  # < -180
            provenance=ProvenanceType.GROUND_MEASUREMENT
        )


def test_weather_observation_separation_of_forecast():
    now = datetime.now(timezone.utc)
    obs = WeatherObservation(
        observation_id="wx_001",
        observation_timestamp=now,
        retrieval_timestamp=now,
        provider_id="open_meteo",
        is_forecast=False,
        wind_speed_kmh=12.5,
        wind_direction_deg=270.0,
        temperature_c=28.0,
        relative_humidity=65.0,
        provenance=ProvenanceType.GROUND_MEASUREMENT
    )
    assert not obs.is_forecast
    assert obs.inversion_detected is None  # Not fabricated


def test_candidate_source_and_evidence():
    src = CandidateSource(
        source_id="src_anand_vihar_const",
        category=SourceCategory.CONSTRUCTION_DUST,
        name="Metro Expansion Package 3",
        provider="osm_overpass",
        verification_status="UNVERIFIED"
    )
    assert src.category == SourceCategory.CONSTRUCTION_DUST
    assert src.verification_status == "UNVERIFIED"

    ev = EvidenceItem(
        evidence_id="ev_001",
        evidence_type="GROUND_TELEMETRY",
        provider="openaq",
        timestamp_start=datetime.now(timezone.utc),
        source_reference="station_dl_004",
        description="Localized coarse particulate PM10 elevation with PM2.5/PM10 ratio of 0.38",
        direction=EvidenceDirection.SUPPORTS,
        provenance=ProvenanceType.GROUND_MEASUREMENT
    )
    assert ev.direction == EvidenceDirection.SUPPORTS


def test_source_contribution_assessment_constraints():
    # Qualitative: cannot fabricate percentages, must have methodology reference
    qual = SourceContributionAssessment(
        pollutant="PM10",
        source_category=SourceCategory.ROAD_DUST,
        is_quantitative=False,
        unit_or_basis="qualitative_rank",
        geographic_scope="DELHI_ANAND_VIHAR",
        time_period="2026-10-11T06:00:00Z/2026-10-11T12:00:00Z",
        methodology_reference="Qualitative PM2.5/PM10 coarse ratio screening"
    )
    assert not qual.is_quantitative
    assert qual.estimated_contribution_value is None

    # Quantitative: requires explicit methodology and values
    quant = SourceContributionAssessment(
        pollutant="PM2.5",
        source_category=SourceCategory.AGRICULTURAL_BURNING,
        is_quantitative=True,
        estimated_contribution_range=(45.0, 65.0),
        unit_or_basis="percent_range",
        geographic_scope="DELHI_NCR",
        time_period="2026-10-11",
        methodology_reference="Chemical speciation organic carbon tracer model",
        uncertainty_info="Confidence interval 95%"
    )
    assert quant.is_quantitative
    assert quant.estimated_contribution_range == (45.0, 65.0)

    # Quantitative missing methodology should fail
    with pytest.raises(ValidationError):
        SourceContributionAssessment(
            pollutant="PM2.5",
            source_category=SourceCategory.AGRICULTURAL_BURNING,
            is_quantitative=True,
            estimated_contribution_value=55.0,
            unit_or_basis="percent",
            geographic_scope="DELHI_NCR",
            time_period="2026-10-11",
            methodology_reference=""  # Missing!
        )


def test_investigation_report_unresolved():
    now = datetime.now(timezone.utc)
    rep = InvestigationReport(
        report_id="rep_20261011_001",
        investigation_id="inv_20261011_001",
        summary_of_observed_event="Sudden PM2.5 spike detected across north-west Delhi monitoring nodes",
        main_measured_facts=["PM2.5 rose from 42 to 185 ug/m3 in 2.5 hours", "Wind direction NW at 14 km/h"],
        confidence_assessment="Preliminary, insufficient tracer speciation to confirm combustion origin",
        data_gaps=["No active ground speciation sensor within 5km radius"],
        recommended_next_steps=["Cross-reference MODIS/VIIRS overpass at 13:30 IST"],
        generated_at=now
    )
    assert rep.investigation_id == "inv_20261011_001"
    assert len(rep.potential_contributing_sources) == 0  # May remain empty/unresolved


# ==============================================================================
# 2. NORMALIZATION HELPER TESTS
# ==============================================================================

def test_normalize_timestamp_utc():
    # Timezone-aware UTC datetime
    dt_utc = datetime(2026, 10, 11, 10, 0, tzinfo=timezone.utc)
    assert normalize_timestamp(dt_utc) == dt_utc

    # Timezone-aware IST (+05:30) datetime
    ist = timezone(timedelta(hours=5, minutes=30))
    dt_ist = datetime(2026, 10, 11, 15, 30, tzinfo=ist)
    normalized = normalize_timestamp(dt_ist)
    assert normalized.tzinfo == timezone.utc
    assert normalized.hour == 10
    assert normalized.minute == 0

    # Naive datetime is safely assumed UTC
    dt_naive = datetime(2026, 10, 11, 10, 0)
    norm_naive = normalize_timestamp(dt_naive)
    assert norm_naive.tzinfo == timezone.utc
    assert norm_naive.hour == 10

    # ISO string with Z
    iso_z = "2026-10-11T10:00:00Z"
    assert normalize_timestamp(iso_z) == dt_utc

    # ISO string with offset
    iso_ist = "2026-10-11T15:30:00+05:30"
    assert normalize_timestamp(iso_ist) == dt_utc

    # Numeric epoch
    epoch = 1791626400.0
    assert normalize_timestamp(epoch).tzinfo == timezone.utc

    # Invalid timestamp
    with pytest.raises(ValueError):
        normalize_timestamp("not-a-timestamp")
    with pytest.raises(ValueError):
        normalize_timestamp(None)


def test_validate_coordinates():
    lat, lon = validate_coordinates(28.61, 77.23)
    assert lat == 28.61
    assert lon == 77.23

    # Both None allowed
    assert validate_coordinates(None, None, allow_none=True) == (None, None)

    # One None should fail
    with pytest.raises(ValueError):
        validate_coordinates(28.61, None)

    # Out of range
    with pytest.raises(ValueError):
        validate_coordinates(91.0, 77.0)
    with pytest.raises(ValueError):
        validate_coordinates(28.0, 181.0)


def test_validate_numeric_measurement():
    assert validate_numeric_measurement(50.0, "PM2.5") == 50.0
    assert validate_numeric_measurement(None, "PM2.5") is None

    with pytest.raises(ValueError):
        validate_numeric_measurement(-5.0, "PM2.5", allow_negative=False)

    with pytest.raises(ValueError):
        validate_numeric_measurement(float("nan"), "PM2.5")

    # Range enforcement
    assert validate_numeric_measurement(85.0, "humidity", min_val=0.0, max_val=100.0) == 85.0
    with pytest.raises(ValueError):
        validate_numeric_measurement(115.0, "humidity", min_val=0.0, max_val=100.0)


def test_evaluate_freshness():
    now = datetime(2026, 10, 11, 10, 0, tzinfo=timezone.utc)
    obs_time = datetime(2026, 10, 11, 9, 30, tzinfo=timezone.utc)
    is_fresh, age = evaluate_freshness(obs_time, max_age_seconds=3600, reference_time=now)
    assert is_fresh is True
    assert age == 1800.0

    stale_time = datetime(2026, 10, 11, 8, 0, tzinfo=timezone.utc)
    is_stale, stale_age = evaluate_freshness(stale_time, max_age_seconds=3600, reference_time=now)
    assert is_stale is False
    assert stale_age == 7200.0


def test_convert_pollutant_concentration():
    # Mass to mass
    assert convert_pollutant_concentration(0.05, "mg/m3", "ug/m3", "PM10") == 50.0
    assert convert_pollutant_concentration(50.0, "ug/m3", "mg/m3", "PM10") == 0.05

    # Gas conversion without temperature & pressure must be rejected
    with pytest.raises(ValueError):
        convert_pollutant_concentration(20.0, "ppb", "ug/m3", "NO2")

    # Gas conversion with temperature & pressure
    val = convert_pollutant_concentration(
        value=20.0,
        from_unit="ppb",
        to_unit="ug/m3",
        pollutant="NO2",
        temperature_c=25.0,
        pressure_hpa=1013.25
    )
    assert val > 30.0 and val < 45.0  # Approx 37.6 ug/m3


# ==============================================================================
# 3. CPCB AQI SERVICE TESTS
# ==============================================================================

def test_cpcb_sub_index_breakpoints():
    # PM10 exact boundary checks
    assert calculate_sub_index(0.0, PM10_BREAKPOINTS) == 0
    assert calculate_sub_index(50.0, PM10_BREAKPOINTS) == 50
    assert calculate_sub_index(100.0, PM10_BREAKPOINTS) == 100
    assert calculate_sub_index(250.0, PM10_BREAKPOINTS) == 200
    assert calculate_sub_index(350.0, PM10_BREAKPOINTS) == 300
    assert calculate_sub_index(430.0, PM10_BREAKPOINTS) == 400
    assert calculate_sub_index(500.0, PM10_BREAKPOINTS) == 500

    # PM2.5 exact boundary checks
    assert calculate_sub_index(0.0, PM25_BREAKPOINTS) == 0
    assert calculate_sub_index(30.0, PM25_BREAKPOINTS) == 50
    assert calculate_sub_index(60.0, PM25_BREAKPOINTS) == 100
    assert calculate_sub_index(90.0, PM25_BREAKPOINTS) == 200
    assert calculate_sub_index(120.0, PM25_BREAKPOINTS) == 300
    assert calculate_sub_index(250.0, PM25_BREAKPOINTS) == 400
    assert calculate_sub_index(380.0, PM25_BREAKPOINTS) == 500


def test_cpcb_extrapolation_beyond_severe():
    # Extreme PM10 concentration (> 500 ug/m3)
    aqi_extreme = calculate_sub_index(600.0, PM10_BREAKPOINTS)
    assert aqi_extreme is not None
    assert aqi_extreme == 500  # Capped at 500


def test_cpcb_categories():
    assert get_cpcb_category(35) == "Good"
    assert get_cpcb_category(80) == "Satisfactory"
    assert get_cpcb_category(150) == "Moderate"
    assert get_cpcb_category(250) == "Poor"
    assert get_cpcb_category(350) == "Very Poor"
    assert get_cpcb_category(450) == "Severe"


def test_calculate_indian_aqi_backward_compatibility():
    # Must preserve exact behavior of original function
    assert calculate_indian_aqi(None, None) is None
    assert calculate_indian_aqi(-10, -5) is None
    assert calculate_indian_aqi(100.0, None) == 100
    assert calculate_indian_aqi(None, 60.0) == 100
    assert calculate_indian_aqi(150.0, 75.0) is not None


def test_calculate_cpcb_aqi_details_dominant_pollutant():
    # Case where PM2.5 dominates
    res1 = calculate_cpcb_aqi_details(pm10=80.0, pm25=75.0)  # PM10 sub-idx ~80, PM2.5 sub-idx ~150
    assert res1.dominant_pollutant == "PM2.5"
    assert res1.category == "Moderate"
    assert res1.minimum_pollutants_met is True

    # Case where PM10 dominates
    res2 = calculate_cpcb_aqi_details(pm10=300.0, pm25=40.0)  # PM10 sub-idx ~250, PM2.5 sub-idx ~67
    assert res2.dominant_pollutant == "PM10"
    assert res2.category == "Poor"

    # Missing one pollutant yields warning
    res3 = calculate_cpcb_aqi_details(pm10=120.0, pm25=None)
    assert len(res3.warnings) > 0
    assert "PM2.5 measurement is missing" in res3.warnings[0]


# ==============================================================================
# 4. POLLUTION EVENT DETECTOR TESTS
# ==============================================================================

def test_detector_sudden_spike():
    detector = PollutionEventDetector(
        EventDetectionConfig(rate_threshold_ug_m3_h=20.0, max_observation_age_hours=24.0)
    )
    t0 = datetime(2026, 10, 11, 6, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 11, 8, 0, tzinfo=timezone.utc)  # 2 hours later

    obs = [
        EnvironmentalObservation(
            observation_id="o1",
            category="air_quality",
            provider_id="openaq",
            observation_timestamp=t0,
            retrieval_timestamp=t0,
            pollutant="PM2.5",
            value=30.0,
            provenance=ProvenanceType.GROUND_MEASUREMENT
        ),
        EnvironmentalObservation(
            observation_id="o2",
            category="air_quality",
            provider_id="openaq",
            observation_timestamp=t1,
            retrieval_timestamp=t1,
            pollutant="PM2.5",
            value=110.0,  # +80 ug/m3 in 2 hours -> 40 ug/m3/h > threshold 20
            provenance=ProvenanceType.GROUND_MEASUREMENT
        ),
    ]

    events = detector.detect_events_from_series(
        obs,
        pollutant="PM2.5",
        geographic_scope="ANAND_VIHAR",
        reference_time=t1
    )
    assert len(events) == 1
    evt = events[0]
    assert evt.event_category == "CONCENTRATION_SPIKE"
    assert evt.affected_pollutants == ["PM2.5"]
    assert "RATE_OF_RISE" in evt.detection_method
    assert evt.baseline_metadata["rate_of_rise_per_hour"] == 40.0
    assert evt.severity in ("SIGNIFICANT", "SEVERE")
    # Verify no fabricated cause
    assert "stubble" not in evt.summary.lower()
    assert "construction" not in evt.summary.lower()


def test_detector_gradual_trend_below_threshold():
    detector = PollutionEventDetector(
        EventDetectionConfig(rate_threshold_ug_m3_h=25.0, relative_change_threshold=0.80)
    )
    t0 = datetime(2026, 10, 11, 6, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 11, 10, 0, tzinfo=timezone.utc)  # 4 hours later

    obs = [
        EnvironmentalObservation(
            observation_id="o1",
            category="air_quality",
            provider_id="openaq",
            observation_timestamp=t0,
            retrieval_timestamp=t0,
            pollutant="PM10",
            value=100.0,
            provenance=ProvenanceType.GROUND_MEASUREMENT
        ),
        EnvironmentalObservation(
            observation_id="o2",
            category="air_quality",
            provider_id="openaq",
            observation_timestamp=t1,
            retrieval_timestamp=t1,
            pollutant="PM10",
            value=130.0,  # +30 ug/m3 in 4 hours = 7.5 ug/m3/h < 25.0
            provenance=ProvenanceType.GROUND_MEASUREMENT
        ),
    ]

    events = detector.detect_events_from_series(obs, pollutant="PM10", reference_time=t1)
    assert len(events) == 0


def test_detector_stable_or_decreasing_readings():
    detector = PollutionEventDetector()
    t0 = datetime(2026, 10, 11, 6, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 11, 7, 0, tzinfo=timezone.utc)

    obs = [
        EnvironmentalObservation(
            observation_id="o1",
            category="air_quality",
            provider_id="openaq",
            observation_timestamp=t0,
            retrieval_timestamp=t0,
            pollutant="PM2.5",
            value=80.0,
            provenance=ProvenanceType.GROUND_MEASUREMENT
        ),
        EnvironmentalObservation(
            observation_id="o2",
            category="air_quality",
            provider_id="openaq",
            observation_timestamp=t1,
            retrieval_timestamp=t1,
            pollutant="PM2.5",
            value=75.0,  # Decreasing!
            provenance=ProvenanceType.GROUND_MEASUREMENT
        ),
    ]

    events = detector.detect_events_from_series(obs, pollutant="PM2.5", reference_time=t1)
    assert len(events) == 0


def test_detector_zero_baseline_safe_handling():
    detector = PollutionEventDetector(
        EventDetectionConfig(min_baseline_for_relative=10.0, rate_threshold_ug_m3_h=50.0)
    )
    t0 = datetime(2026, 10, 11, 6, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 11, 7, 0, tzinfo=timezone.utc)

    obs = [
        EnvironmentalObservation(
            observation_id="o1",
            category="air_quality",
            provider_id="openaq",
            observation_timestamp=t0,
            retrieval_timestamp=t0,
            pollutant="PM2.5",
            value=0.0,  # Zero baseline
            provenance=ProvenanceType.GROUND_MEASUREMENT
        ),
        EnvironmentalObservation(
            observation_id="o2",
            category="air_quality",
            provider_id="openaq",
            observation_timestamp=t1,
            retrieval_timestamp=t1,
            pollutant="PM2.5",
            value=15.0,  # Rate = 15 < 50
            provenance=ProvenanceType.GROUND_MEASUREMENT
        ),
    ]

    # Must not raise ZeroDivisionError
    events = detector.detect_events_from_series(obs, pollutant="PM2.5", reference_time=t1)
    assert len(events) == 0


def test_detector_monotonic_time_ordering_and_duplicates():
    detector = PollutionEventDetector()
    t0 = datetime(2026, 10, 11, 6, 0, tzinfo=timezone.utc)

    obs = [
        EnvironmentalObservation(
            observation_id="o1",
            category="air_quality",
            provider_id="openaq",
            observation_timestamp=t0,
            retrieval_timestamp=t0,
            pollutant="PM2.5",
            value=40.0,
            provenance=ProvenanceType.GROUND_MEASUREMENT
        ),
        EnvironmentalObservation(
            observation_id="o2",
            category="air_quality",
            provider_id="openaq",
            observation_timestamp=t0,  # Duplicate!
            retrieval_timestamp=t0,
            pollutant="PM2.5",
            value=120.0,
            provenance=ProvenanceType.GROUND_MEASUREMENT
        ),
    ]

    with pytest.raises(ValueError) as exc:
        detector.detect_events_from_series(obs, pollutant="PM2.5")
    assert "duplicate or non-increasing" in str(exc.value)


def test_detector_stale_data_rejection():
    detector = PollutionEventDetector(
        EventDetectionConfig(max_observation_age_hours=2.0)
    )
    t0 = datetime(2026, 10, 11, 2, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 11, 4, 0, tzinfo=timezone.utc)
    ref = datetime(2026, 10, 11, 10, 0, tzinfo=timezone.utc)  # 6 hours after t1 -> STALE

    obs = [
        EnvironmentalObservation(
            observation_id="o1",
            category="air_quality",
            provider_id="openaq",
            observation_timestamp=t0,
            retrieval_timestamp=t0,
            pollutant="PM2.5",
            value=30.0,
            provenance=ProvenanceType.GROUND_MEASUREMENT
        ),
        EnvironmentalObservation(
            observation_id="o2",
            category="air_quality",
            provider_id="openaq",
            observation_timestamp=t1,
            retrieval_timestamp=t1,
            pollutant="PM2.5",
            value=150.0,
            provenance=ProvenanceType.GROUND_MEASUREMENT
        ),
    ]

    events = detector.detect_events_from_series(obs, pollutant="PM2.5", reference_time=ref)
    assert len(events) == 0  # Ignored because stale

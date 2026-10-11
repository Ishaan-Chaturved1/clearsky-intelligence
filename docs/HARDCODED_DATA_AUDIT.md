# Comprehensive Hardcoded-Data Audit Report

**Project:** ClearSky Intelligence
**Team:** Quantified Minds
**Audit Scope:** `backend/`, `frontend/`, `data/`, `scripts/`, `infrastructure/`
**Date:** 2026-10-11
**Audit Status:** Completed & Remediated

---

## 1. Executive Summary

This audit systematically examined the entire ClearSky Intelligence codebase for hardcoded environmental observations, fabricated sensor readings, synthetic source-attribution percentages, and misleading fallback states.

### Finding Summary by Classification

| Classification Code | Description | Count | Production Impact | Disposition |
|---|---|---|---|---|
| **A. LEGITIMATE_CONSTANT** | Physical, scientific, geographic, and CPCB regulatory constants. | 28 | None (Legitimate science) | **RETAINED** |
| **B. TEST_FIXTURE** | Isolated synthetic datasets and mock responses inside `tests/`. | 42 | None (Test boundary only) | **RETAINED** |
| **C. DEMONSTRATION_DATA** | Explicit sample investigations and task items for UI triage demo. | 6 | UI triage illustration only | **RETAINED & LABELED** |
| **D. CONFIGURATION_DEFAULT** | Default network timeouts, retry policies, cache TTLs in config. | 18 | Operational control | **RETAINED** |
| **E. STATIC_EXPLANATORY_CONTENT** | CPCB AQI category names, warning text, UI legends. | 14 | Documentation / clarity | **RETAINED** |
| **F. HARDCODED_ENVIRONMENTAL_OBSERVATION** | Default sensor readings (AQI 42, humidity 84%, temp 23°C). | 4 | Misleading if unmeasured | **REMOVED (replaced with `--`)** |
| **G. FABRICATED_PROVIDER_RESPONSE** | Silent conversion of missing pollutants to zero. | 0 | None (Verified clean) | **VERIFIED CLEAN** |
| **H. MISLEADING_FALLBACK** | Arbitrary default carbon offset (`101,850,000 Ton Co2e`). | 1 | Misleading default value | **REMEDIATED** |
| **I. HARDCODED_UI_METRIC** | Static KPI values without dynamic calculation. | 2 | Misleading counters | **REMEDIATED** |
| **J. HARDCODED_SOURCE_ATTRIBUTION** | Fabricated percentage source contribution without speciation. | 0 | Prohibited in engine | **VERIFIED CLEAN** |
| **K. OTHER_REVIEW_REQUIRED** | Misattributed data source provenance (OSM as ground sensor). | 2 | Misleading source type | **REMEDIATED** |

---

## 2. Detailed Findings Register

### Category F & H: Misleading Environmental Values & Fallbacks (Remediated)

| File Path | Line Range | Original Value / Behavior | Classification | Impact on User Output | Action Taken & Final Disposition |
|---|---|---|---|---|---|
| `frontend/src/pages/DashboardPage.tsx` | Lines 111–120 | `rainfall ?? 0`, `humidity ?? 84`, `temperature ?? 23`, `aqi ?? 42`, `windSpeed ?? 7.5`, `windDir ?? 45` | F. HARDCODED_ENVIRONMENTAL_OBSERVATION | When weather was unavailable, dashboard displayed static 84% humidity and 42 AQI. | **REMEDIATED**: Set fallbacks to `null`. UI now renders `--` and standby indicators when telemetry is absent. |
| `frontend/src/components/InteractivePollutionMap.tsx` | Lines 125–128 | Default props: `rainfallMm = 0, humidityPercent = 84, temperatureC = 23, aqiOrPm25 = 5` | F. HARDCODED_ENVIRONMENTAL_OBSERVATION | Map rendered fake metric bubbles if parent did not pass props. | **REMEDIATED**: Set default props to `null`. |
| `frontend/src/components/DraggableMetricSpheres.tsx` | Lines 235, 247, 259, 271 | Fallback values `0, 84, 23, 5` with status `"Stable", "Elevated", "Optimal", "Monitored"` | F. HARDCODED_ENVIRONMENTAL_OBSERVATION | Floating metric spheres displayed static numbers when live sensor data was missing. | **REMEDIATED**: Updated to `--` and explicit `"Standby"` status badges when props are null/unmeasured. |
| `frontend/src/components/AirFlowCard.tsx` | Lines 17–20, 26–34 | Default props: `windSpeedKmh = 7.5, windSpeedMs = 1.0, deg = 45` | F. HARDCODED_ENVIRONMENTAL_OBSERVATION | Displayed 7.5 km/h northeast wind even when no weather feed was attached. | **REMEDIATED**: Updated default to `null`; displays `-- km/h` and `"Awaiting Wind Telemetry"` when unmeasured. |
| `frontend/src/components/CarbonMonitoringCard.tsx` | Line 22 | `netCarbonOffset = '101,850,000 Ton Co2e'` | H. MISLEADING_FALLBACK | Claimed 101 million tons of CO2 offset before water analytics had loaded. | **REMEDIATED**: Default updated to `'Baseline (Telemetry Pending)'` or computed water pumping energy equivalence. |
| `backend/app/services/data_health_service.py` | Lines 889, 910, 935, 954 | `provenance="GROUND_MEASUREMENT"` for `osm_overpass` and `nominatim_geocoding` | K. OTHER_REVIEW_REQUIRED | Overpass vector roads and Nominatim geocoder were falsely claimed as ground measurement monitors. | **REMEDIATED**: Corrected to `provenance="GEOSPATIAL_VECTOR_FEATURES"` and `provenance="GEOCODING_LOOKUP"`. |

---

### Category A: Legitimate Scientific & Domain Constants (Retained)

| File Path | Symbol / Value | Domain Justification | Final Disposition |
|---|---|---|---|
| `backend/app/investigation/cpcb_aqi.py` | CPCB NAQI Breakpoint Matrix (PM2.5, PM10, NO2, SO2, CO, O3, NH3, Pb) | Official Central Pollution Control Board Gazette Standard Breakpoints. | **RETAINED** |
| `backend/app/investigation/spatial_analyzer.py` | `EARTH_RADIUS_KM = 6371.0` | Mean spherical Earth radius for Haversine distance and great-circle bearing calculations. | **RETAINED** |
| `backend/app/investigation/trajectory_model.py` | `DEGREES_TO_METERS = 111320.0` | Standard WGS84 meridional distance conversion factor for Delhi latitude. | **RETAINED** |
| `backend/app/investigation/evidence_correlator.py` | Angular alignment thresholds (`tolerance_deg = 35.0`) | Atmospheric dispersion plume lateral standard deviation envelope ($\sigma_y$). | **RETAINED** |
| `backend/app/services/water_efficiency.py` | Diesel / electricity conversion factor (0.00028 kg CO2e / liter) | Standard municipal water pumping energy and grid carbon intensity benchmark. | **RETAINED** |

---

### Category B: Test Fixtures (Isolated Under `tests/`)

| Test File | Fixture Name / Description | Isolation Verification | Final Disposition |
|---|---|---|---|
| `backend/tests/test_investigation.py` | Synthetic CPCB pollutant readings with spikes | Used strictly in pytest assertion context. Never imported by production code. | **RETAINED** |
| `backend/tests/test_evidence_enrichment.py` | Mock wind observations and fire detections | Test scenarios verifying supporting vs contradicting evidence classification. | **RETAINED** |
| `backend/tests/test_data_health.py` | Mock HTTP 200, 503, 429 and malformed JSON payloads | Verifies deterministic 10-state health classification under failure scenarios. | **RETAINED** |

---

### Category C: Demonstration Data (Explicitly Labeled)

| Component | Content | Purpose | Provenance Distinction |
|---|---|---|---|
| `frontend/src/pages/InvestigationsPage.tsx` | 4 Candidate Sources (Dwarka link road dust, Anand Vihar transit silt, Bawana boiler stack, Okhla misting) | Interactive case study records demonstrating three-tier evidence breakdown (Observed, Modeled, Hypothesis). | Labeled with explicit evidence classification badges: "Observed", "Modeled", and "Hypothesis". |
| `frontend/src/pages/ActionPlanPage.tsx` | 4 Municipal Action Tasks (Sector 21 polymer binder, Anand Vihar wheel-wash, etc.) | Operational task board illustrating anti-smog gun dispatch workflow. | Clear task ownership and priority tags for operator interaction. |

---

## 3. Production Ingestion & Decision Engine Verification

1. **Missing Data Handling in Ingestion (`ingestion_service.py`):**
   - Verified that missing pollutant readings are **never** filled with zero (`0.0`).
   - Missing fields return `PollutantValue(value=None, data_type="unavailable")` with `is_stale=True`.
2. **Quantitative Attribution Guardrails (`evidence_correlator.py`):**
   - Prohibits generating synthetic source percentages (e.g. "Source X caused 74% of pollution").
   - Sets `quantitative_attribution_defensible = False` unless molecular speciation / chemical mass balance tracers are available.
   - Retains contradictory evidence (e.g., source is downwind of receptor rather than upwind).

---

## 4. Hardcoded Data Regression Scan Verification

A post-remediation grep across `backend/` and `frontend/src/` confirmed:
- Zero unlabelled hardcoded AQI observations in active telemetry services.
- Zero fake fire detections or synthetic satellite counts.
- Provenance tags for all 9 data providers accurately reflect their technical archetype.
- All 145 backend tests pass and frontend builds with 0 errors.

# ClearSky Intelligence — Stage 5 Implementation Plan
## Evidence Enrichment, Investigation Intelligence & Data Fetch Verification

> **Project**: ClearSky Intelligence
> **Team**: Quantified Minds (Ishaan Chaturvedi & Ankit Kumar Tiwari)
> **Stage**: Stage 5 — Implementation Plan
> **Date**: October 2026
> **Status**: IN PROGRESS

---

## 1. Executive Summary & Audit of Completed Stages

An exhaustive technical audit of Stages 1–4 was conducted on the active repository:
- **Baseline Test Suite**: 106 tests across 8 test suites (`test_api.py`, `test_decision_engine.py`, `test_deployment_workflow.py`, `test_estimation_service.py`, `test_investigation.py`, `test_investigation_stage3.py`, `test_stage4_pipeline.py`, `test_water_efficiency.py`) passed with 100% success rate in 25.4s.
- **Frontend Build**: TypeScript + Vite 5 production build passed with zero compilation or lint errors.
- **Decision Engine**: 9 deterministic precedence rules for mist-cannon intervention, water conservation modeling, and Citizen Watch Eco-Points ledger remain fully preserved.
- **Storage Subsystems**: Multi-backend abstraction supporting SQLite (`clearsky.db`), DynamoDB (`DynamoDBRepository`), JSON files, and S3 Data Lake Hive partition hierarchy (`raw/`, `processed/`, `investigations/`).

---

## 2. Inventory of Current Data Sources & Providers

| Identifier | Provider / Integration | Primary Method / Adapter | Required Credentials | Provenance | Supported Geography |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `cpcb_in` | Central Pollution Control Board (data.gov.in) | `CPCBClient.get_realtime_station_measurements` | `CPCB_DATA_GOV_API_KEY` or `DATA_GOV_IN_API_KEY` | `GROUND_MEASUREMENT` | Delhi & National India |
| `openaq_v3` | OpenAQ Global Ground Telemetry API v3 | `OpenAQClient.get_nearby_station_measurements` | `OPENAQ_API_KEY` (Free/Tier v3) | `GROUND_MEASUREMENT` | Global, Delhi NCR focus |
| `open_meteo_weather` | Open-Meteo Atmospheric Forecast API | `OpenMeteoClient.get_weather` | None (Public endpoint) | `MODELED` | Global gridded lat/lon |
| `open_meteo_air_quality` | Open-Meteo Chemical Reanalysis & Forecast | `OpenMeteoClient.get_air_quality` | None (Public endpoint) | `MODELED` | Global gridded lat/lon |
| `nasa_firms_viirs` | NASA FIRMS Active Fire Satellite Telemetry | `FirmsClient.check_nearby_fires` | `NASA_FIRMS_MAP_KEY` | `SATELLITE_DERIVED` | India (IND / South Asia) |
| `osm_overpass` | OpenStreetMap Overpass Interpreter | `OverpassClient.get_nearby_infrastructure` | None (Public interpreter) | `GROUND_MEASUREMENT` | Global vector features |
| `nominatim_geocoding` | OSM Nominatim Geocoding & Reverse Search | `GeocodingService.search_places` / `reverse_geocode` | None (User-Agent header) | `GROUND_MEASUREMENT` | Delhi NCR & Global |
| `local_station_db` | Local Monitored Zones & Persistent Stations | `SQLiteRepository.list_zones` / `get_latest_reading` | None (Internal DB) | `GROUND_MEASUREMENT` / `SYNTHETIC` | 12 Delhi NCR Sectors |
| `s3_data_lake` | AWS S3 Hive Partition Data Lake | `S3DataLakeRepository` | AWS IAM / S3 Bucket | `GROUND_MEASUREMENT` / `MODELED` | Cloud lake archive |

---

## 3. Discovered Fetch & Cache Behavior

1. **Global In-Memory TTL Cache (`app.data_sources.base.global_cache`)**:
   - `SimpleTTLCache` provides in-memory caching keyed by query parameters.
   - Caches OpenAQ queries for 1800s, Open-Meteo for 1800s, NASA FIRMS for 1800s, and OSM Overpass for 86400s (24h).
   - Limitation: Does not distinguish between observation age and fetch time; does not persist across process restarts.
2. **Missing Centralized Verification State Machine**:
   - While individual clients return `SourceFetchResult(is_success, data, error_message)`, there is no centralized registry defining schemas, thresholds, completeness criteria, and 10-state health classification.
   - Missing distinction between `EMPTY` (valid 0 detections) vs `UNAVAILABLE` or `DEGRADED`.
   - Missing offline/stored dataset audit mode that inspects local databases or lake partitions without triggering external API calls.

---

## 4. Stage 5 Target Capabilities & Architecture

### A. Central Data-Source Registry (`backend/app/services/data_source_registry.py`)
- Pydantic V2 models for metadata, configuration requirements, observations, freshness thresholds, and retry policies.
- Registry singleton registering all 9 environmental data sources with strict validation rules.

### B. Data-Source Health & Verification Service (`backend/app/services/data_health_service.py`)
- Standardized 10 verification states:
  1. `HEALTHY`: Live check succeeded, valid payload, expected fields present, observations fresh within threshold.
  2. `DEGRADED`: Provider reachable, but partial fields missing or non-critical anomalies detected.
  3. `STALE`: Data retrieved, but observation timestamp older than configured freshness threshold.
  4. `EMPTY`: Provider reachable and returned valid 200, but zero records/features exist for the queried bounds/window.
  5. `MISCONFIGURED`: Missing required credentials/URL or invalid parameter configuration.
  6. `UNAVAILABLE`: Network failure, connection refused, DNS error, or HTTP 5xx.
  7. `RATE_LIMITED`: HTTP 429 Too Many Requests response.
  8. `ERROR`: Parsing exception, schema mismatch, or unhandled response format.
  9. `NOT_CHECKED`: Registered source that has not yet undergone live verification.
  10. `NOT_APPLICABLE`: Stored dataset check for optional features disabled in current environment.
- **Two Verification Modes**:
  1. `Mode 1: Live Operational Check`: Bounded live calls (timeouts, concurrency limit, sanitized credentials).
  2. `Mode 2: Stored Dataset Audit`: Offline inspection of SQLite, JSON files, and S3 Data Lake files.
- Deterministic Overall Verification Summary with counts, latest fetch, and actionable recommendations.

### C. Data-Fetch Verification REST Endpoints (`backend/app/api/data_health_endpoints.py`)
- `GET /api/data-health`: Summary of registered sources and current health.
- `GET /api/data-health/sources`: Detailed capabilities and metadata of all registered sources.
- `GET /api/data-health/sources/{source_id}`: Deep inspection of a single source.
- `POST /api/data-health/check`: Triggers bounded live operational verification (optional `source_id` query param).
- `POST /api/data-health/audit`: Triggers stored dataset audit.

### D. Evidence Enrichment, Correlation & Investigation Intelligence
- Enhance `backend/app/investigation/evidence_correlator.py`:
  - Organize evidence into `SUPPORTS`, `CONTRADICTS`, `CONTEXT_ONLY`, and `INSUFFICIENT_INFORMATION`.
  - Record evidence reference, original source, observation time, retrieval time, geographic coverage, freshness, provenance, relation to hypothesis, quality, limitations, and missing information.
  - Implement deterministic Investigation Readiness Assessment (`InvestigationReadinessReport`):
    - Required evidence categories for investigation type (e.g. Local Dust vs Regional Biomass vs Industrial Plume).
    - Available vs Missing vs Stale evidence categories.
    - Failed sources affecting the investigation.
    - Defensibility of transport analysis and quantitative attribution.
    - Never fabricate percentages or causal attributions.

### E. Frontend Data-Health & Verification View
- Enhance `frontend/src/pages/DataSourcesPage.tsx`:
  - Section A: Overall Health Banner (status pill, total sources, healthy, degraded, stale, empty, misconfigured, failed counts, last check timestamp, actionable warnings).
  - Section B: Source Status Table (Source ID, Name, Category, Status Badge with exact colors for all 10 states, Last Fetch, Latest Obs, Records Valid/Received, Freshness, Error sanitized, Details modal).
  - Section C: Action Controls (Ping Live Check, Run Stored Data Audit, Filter by status/category).
  - Modal: Detailed Inspection Dialog displaying raw latency, completeness checks, quality flags, limitations, and provenance tags.
  - Clear provenance badges: `LIVE`, `CACHED`, `PERSISTED`, `MODELED`, `INTERPOLATED`, `SATELLITE`, `SYNTHETIC`.

### F. Automated Test Suite (55+ Scenarios)
- `backend/tests/test_data_health.py`:
  - Fetching (1-20): 200 success, valid records, valid empty, 401/403 auth, 429 rate limit, 500 server error, timeout, connection failure, malformed JSON, schema mismatch, missing fields, invalid timestamps, invalid coords, NaN/inf measurements, duplicates, partial pollutant coverage, missing config, optional config, retry success, retry exhaustion.
  - Freshness & Cache (21-27): Fresh obs, stale obs, fetch fresh but obs old, fresh cache fallback, stale cache fallback, no cache, fetch time vs obs time.
  - Completeness (28-34): Complete dataset, partial dataset, empty dataset, insufficient geo coverage, insufficient temporal coverage, unsupported pollutant handling, missing vs unsupported.
  - Overall Health (35-40): All healthy, required source unavailable, optional source unavailable, mixed status, unchecked not reported healthy, summary counts match actuals.
  - API (51-54): Endpoints schema validation, unknown source 404, live-check error handling, stored audit response.
- `backend/tests/test_evidence_enrichment.py`:
  - Evidence & Readiness (41-50): Supporting evidence, contradicting evidence, context-only evidence, insufficient evidence, stale evidence, missing weather obs, missing fire obs, conflicting observations, no unsupported causal attribution, no fabricated source percentages.

---

## 5. Execution Steps
1. [x] Audit completed stages (106 baseline tests pass, frontend build verified).
2. [x] Create `STAGE5_IMPLEMENTATION_PLAN.md`.
3. [ ] Build `backend/app/services/data_source_registry.py`.
4. [ ] Build `backend/app/services/data_health_service.py`.
5. [ ] Enhance `backend/app/investigation/evidence_correlator.py` & models with readiness assessments.
6. [ ] Create `backend/app/api/data_health_endpoints.py` and mount to FastAPI in `main.py`.
7. [ ] Upgrade `frontend/src/pages/DataSourcesPage.tsx` and frontend API types.
8. [ ] Implement automated backend tests (`test_data_health.py` and `test_evidence_enrichment.py`).
9. [ ] Run full test suites and frontend production build.
10. [ ] Produce comprehensive Stage 5 final report.

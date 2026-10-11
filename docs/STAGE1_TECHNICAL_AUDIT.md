# ClearSky Intelligence — Stage 1 Technical Audit & Target Architecture Plan

> **Project**: ClearSky Intelligence  
> **Engineering Team**: Quantified Minds (Ishaan Chaturvedi & Ankit Kumar Tiwari)  
> **Repository**: `Ishaan-Chaturved1/clearsky-intelligence`  
> **Stage**: Stage 1 — Discovery, Technical Audit & Architectural Blueprint  
> **Date**: October 2026  
> **Status**: APPROVED AUDIT (No feature modifications or deletions performed in Stage 1)

---

## 1. Executive Summary & Audit Context

ClearSky Intelligence is transitioning from an operational dust-suppression decision-support tool to a comprehensive, **evidence-driven air-pollution source intelligence and investigation platform**.

### Core Evolution Objectives
1. **Explainability**: Diagnose *why* pollutant concentrations and AQI are surging.
2. **Attribution**: Identify local (construction, traffic, industrial) and regional (stubble burning, transboundary dust, brick kilns) candidate sources.
3. **Transport Modeling**: Establish whether pollutants were transported from upwind jurisdictions via back-trajectory and wind vector dispersion.
4. **Satellite Evidence**: Correlate ground telemetry with thermal anomalies (MODIS/VIIRS) and aerosol optical depth (AOD/Sentinel).
5. **Atmospheric Physics**: Quantify boundary layer compression, thermal inversion, relative humidity, and secondary aerosol chemistry.
6. **Provenance & Uncertainty**: Preserve strict measurement vs modeled provenance and report explicit uncertainty bounds rather than speculative percentages.
7. **Preservation**: Retain 100% of existing functional capabilities (Command Center, 9-Rule Decision Engine, Citizen Watch & Eco-Points, Water Conservation Analytics, Multi-Storage Backends).

---

## 2. Technical Audit of Current Architecture

### 2.1 Technology Stack & Runtime Environment

| Dimension | Real Implementation in Codebase |
| :--- | :--- |
| **Backend Framework** | FastAPI `0.111.0+` with ASGI Uvicorn `0.30.0+` |
| **Python Runtime** | Python 3.10 / 3.11 / 3.13 compatible |
| **Data & Serialization** | Pydantic V2 (`>=2.7.0`), NumPy (`>=1.26.0`), Pandas (`>=2.2.0`) |
| **HTTP Client** | HTTPX (`>=0.27.0`) asynchronous client |
| **Cloud SDK** | Boto3 (`>=1.34.0`) |
| **Frontend Framework** | React `18.3.1`, TypeScript `5.4.5`, Vite `5.2.12` |
| **Frontend Styling** | Tailwind CSS `3.4.4`, Lucide-React `0.395.0` |
| **GIS & Mapping** | Leaflet `1.9.4`, React-Leaflet `4.2.1`, OpenStreetMap Carto tiles |
| **Visualization** | Recharts `2.12.7` |
| **Testing** | Pytest `8.3.2`, Pytest-Asyncio `0.24.0`, AnyIO `4.10.0` |

### 2.2 Entry Points & Startup Mechanisms

1. **Local Unified Runner**:
   - `python run.py`: Spawns FastAPI on port 8000 and Vite on port 5173 with automated port conflict detection and socket cleanup.
   - `main.py`: Forwarder executing `run.py`.
2. **Standalone Backend**:
   - `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload`
3. **Cloud Elastic Beanstalk Entry Point**:
   - `application.py`: Defines `application = backend.app.main.app`.
   - `Procfile`: `web: uvicorn backend.app.main:app --host 0.0.0.0 --port 5000`.
   - `.ebextensions/01_app.config`: Sets `PYTHONPATH`, `ENVIRONMENT=production`, and `WSGIPath: application:application`.
4. **Serverless Lambda Entry Point**:
   - `backend/lambda_handler.py`: Uses `Mangum(app, lifespan="off")` to expose FastAPI to AWS API Gateway.
5. **Frontend Client Entry Point**:
   - `frontend/src/main.tsx` mounts `<App />` into `frontend/index.html`.

---

## 3. Existing Inventory of Components, Services & Routes

### 3.1 API Endpoints (32 Total Routes in `backend/app/api/endpoints.py`)

| Method | Path | Response Model | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | `dict` | Service health, version, environment, and active storage engine. |
| `GET` | `/api/overview` | `SystemOverviewResponse` | Aggregated system metrics, candidate counts, water savings, data mode. |
| `GET` | `/api/zones` | `List[ZoneWithLatest]` | List of 12 Delhi NCR monitored sectors with latest readings & decisions. |
| `GET` | `/api/zones/{zone_id}` | `ZoneWithLatest` | Specific sector details, sensor observations, and decision status. |
| `GET` | `/api/zones/{zone_id}/history` | `dict` | Historical sequence of sensor readings and decision audits. |
| `GET` | `/api/zones/{zone_id}/atmospheric-analysis` | `AtmosphericAnalysisResponse` | Evaporation rate, drying time, CPCB AQI, and inversion analysis. |
| `GET` | `/api/zones/{zone_id}/candidate-segments` | `CandidateRoadSegmentsResponse` | Highway/road segments proximate to zone via Overpass API. |
| `GET` | `/api/zones/{zone_id}/forecast-windows` | `ForecastWindowsResponse` | Multi-hour meteorological suitability windows for mist guns. |
| `GET` | `/api/analytics/strategy-comparison` | `StrategyComparisonResponse` | 4-scenario comparison matrix (scheduled vs AQI vs targeted vs alternative). |
| `GET` | `/api/interventions` | `List[InterventionOutcomeRecord]` | Logged mist gun and dust control interventions. |
| `POST`| `/api/interventions` | `InterventionOutcomeRecord` | Log new field intervention with pre/post particulate measurements. |
| `GET` | `/api/interventions/effectiveness-summary` | `dict` | Empirical statistical reduction efficiency ($\Delta \text{PM}_{10}, \Delta \text{PM}_{2.5}$). |
| `GET` | `/api/decisions/latest` | `List[DecisionRecord]` | Latest scored decision records across all sectors. |
| `GET` | `/api/decisions/history` | `List[DecisionRecord]` | Historical decision audit trail. |
| `GET` | `/api/analytics/water-savings` | `WaterSavingsAnalyticsResponse` | Audited water saved vs configurable baseline schedule. |
| `GET` | `/api/analytics/water-savings/export` | `StreamingResponse (CSV)` | CSV stream of daily water savings ledger. |
| `GET` | `/api/analytics/overview` | `dict` | High-level summary of water and emission indicators. |
| `GET` | `/api/sources/status` | `SourcesStatusResponse` | Live telemetry status for OpenAQ, Open-Meteo, FIRMS, Overpass. |
| `GET` | `/api/methodology` | `MethodologyResponse` | Structured documentation of the 9 precedence rules and limitations. |
| `GET` | `/api/brief/daily` | `AiDailyBriefResponse` | Daily operational briefing synthesized from regional conditions. |
| `GET` | `/api/alerts` | `List[AlertRecord]` | Active operational alerts and priority escalations. |
| `POST`| `/api/admin/refresh` | `AdminRefreshResponse` | Ingestion pipeline trigger to re-poll and score all zones. |
| `GET` | `/api/reports` | `List[CitizenReport]` | Public community infraction reports. |
| `POST`| `/api/reports` | `CitizenReport` | Submit citizen report with category, location, photos, and voice note. |
| `POST`| `/api/reports/{id}/verify` | `CitizenReport` | Admin endpoint to verify violation and award points to citizen wallet. |
| `GET` | `/api/rewards/catalog` | `List[RewardItem]` | Certified clean air equipment and masks available for redemption. |
| `GET` | `/api/rewards/wallet` | `CitizenWalletResponse` | Citizen point balance and verified report count. |
| `POST`| `/api/rewards/redeem` | `RewardRedeemResponse` | Redeem eco-points for item vouchers. |
| `GET` | `/api/geo/search` | `List[GeocodingPlace]` | OpenStreetMap Nominatim locality discovery search. |
| `GET` | `/api/geo/reverse` | `GeocodingPlace` | Reverse geocode coordinates to neighborhood address. |
| `GET` | `/api/stations` | `List[StationObservation]` | Live CPCB/DPCC monitoring stations within given radius. |
| `GET` | `/api/locations/analyze` | `LocationAnalysisResponse` | On-the-fly dynamic particulate and meteorological evaluation for any coordinate. |

---

## 4. External Data Provider Integrations Audit

| Provider | Client Implementation | Auth Requirements | Current Code Status | Behavior if Unavailable / Missing Key |
| :--- | :--- | :--- | :--- | :--- |
| **OpenAQ v3** | `OpenAQClient` (`backend/app/data_sources/openaq_client.py`) | API Key (`OPENAQ_API_KEY`) via header `X-API-Key` | **Partially Implemented**. Real HTTP client to `/v3/locations`. | Graceful error result: returns empty station list; triggers fallback to modeled CAMS data or cached observations. |
| **Open-Meteo Weather** | `OpenMeteoClient` (`backend/app/data_sources/open_meteo_client.py`) | None (Free open API) | **Fully Implemented**. Queries `api.open-meteo.com/v1/forecast` for wind, humidity, pressure, BLH, precipitation. | Returns cached data if within TTL (30 min); logs warning and marks source unavailable. |
| **Open-Meteo Air Quality** | `OpenMeteoClient` (`backend/app/data_sources/open_meteo_client.py`) | None (Free open API) | **Fully Implemented**. Queries `air-quality-api.open-meteo.com/v1/air-quality` for PM10, PM2.5, dust models. | Marks source unavailable; falls back to cached/demo data. |
| **NASA FIRMS** | `FirmsClient` (`backend/app/data_sources/firms_client.py`) | Map Key (`NASA_FIRMS_MAP_KEY`) | **Partially Implemented**. Real CSV download for `VIIRS_SNPP_NRT/IND/1`. | Gracefully returns empty fire set (count 0, transport false); never fabricates fake fire detections. |
| **OpenStreetMap Overpass** | `OverpassClient` (`backend/app/data_sources/overpass_client.py`) | None (Public Overpass interpreter) | **Fully Implemented**. Queries construction landuse and major highways within 350m. | Caches responses for 24h; on failure, returns empty infrastructure arrays. |
| **OpenStreetMap Nominatim** | `GeocodingService` (`backend/app/services/geocoding_service.py`) | None (User-Agent header required) | **Fully Implemented**. Search and reverse geocoding with 60m rate limiting and 24h cache. | Returns empty place results on network failure. |

---

## 5. Trace of Analytical Calculations

### 5.1 CPCB AQI Calculation
- **Source**: `endpoints.py` (lines 76–118) and `LocationAnalysisResponse` computation (lines 854–890).
- **Formula**: Piecewise linear sub-index interpolation:
  $$I_p = \frac{I_{\text{high}} - I_{\text{low}}}{C_{\text{high}} - C_{\text{low}}} \cdot (C_p - C_{\text{low}}) + I_{\text{low}}$$
  using official CPCB breakpoints for PM10 and PM2.5.
- **Limitation**: Currently implemented inline inside route handlers rather than an isolated, testable domain service.

### 5.2 Deterministic Decision Precedence Engine
- **Source**: `backend/app/services/decision_engine.py`.
- **Precedence Order**:
  1. Precipitation (`rain > 0.1 mm`) $\to$ `INTERVENTION_DISCOURAGED`
  2. Missing Pollutants (`PM10` or `PM2.5` missing) $\to$ `ADVISORY_ONLY`
  3. Contradictory Inverted Sensors (`PM10 < PM2.5 - 5`) $\to$ `ADVISORY_ONLY`
  4. Stale Telemetry (`> 3h`) $\to$ `ADVISORY_ONLY`
  5. High Humidity (`> 75%`) $\to$ `INTERVENTION_DISCOURAGED`
  6. High Wind Drift (`> 20 km/h`) $\to$ `INTERVENTION_DISCOURAGED`
  7. Smoke / Fire Dominance (`PM2.5/PM10 > 0.65` or active fire $\le 5\text{ km}$) $\to$ `INTERVENTION_DISCOURAGED`
  8. Coarse Dust Hotspot (`PM10 >= 250` and `PM2.5/PM10 < 0.50`) $\to$ `INTERVENTION_RECOMMENDED`
  9. Rapid Drying (`WS 15-20, RH < 30%, Temp > 38°C`) $\to$ `ALTERNATIVE_DUST_CONTROL_SUGGESTED`
- **Priority Escalation**: Scales from 1 to 5 based on PM10 severity, boosted by **+1 to +2** if proximate construction exists within 1 km.

### 5.3 Geospatial Interpolation (IDW)
- **Source**: `backend/app/services/estimation_service.py`.
- **Logic**:
  - Distance $\le 10$ km: Selects nearest ground observation (`HIGH` confidence).
  - Distance 10–25 km: Calculates Inverse Distance Weighting across up to 3 ground stations (`MEDIUM` confidence).
  - Distance $> 25$ km: Falls back to modeled numeric forecast (`MEDIUM`/`LOW` confidence).

### 5.4 Water Efficiency Accounting
- **Source**: `backend/app/analytics/water_efficiency.py`.
- **Logic**: Avoided operations = $\max(0, \text{Baseline Runs} - \text{Recommended Runs})$. Water saved = $\text{Avoided Runs} \times \text{Liters per Run}$. Includes 4-scenario comparative modeling against scheduled and AQI-threshold policies.

---

## 6. Technical Integrity, Limitations & Risks

### 6.1 Gaps Between Current State & Target Vision

1. **Absence of Source Attribution**: The current engine identifies coarse dust dominance vs combustion smoke dominance via simple bulk ratio (`PM2.5 / PM10`), but cannot identify *which* specific sources (e.g., specific construction corridors, industrial estates, biomass burning clusters) caused the elevation.
2. **Absence of Atmospheric Transport / Back-Trajectory**: The current system only checks whether an active fire is upwind based on current local wind bearing; it lacks backward dispersion trajectory modeling (e.g., HYSPLIT-style lagrangian parcel tracing).
3. **Absence of Satellite Imagery Metadata**: Thermal fire counts from FIRMS exist, but there is no integration with Aerosol Optical Depth (AOD from Sentinel-5P / MODIS) or surface change detection.
4. **Calculations in HTTP Handlers**: `calculate_indian_aqi` and dynamic location analysis are implemented inside `endpoints.py`, mixing transport/routing with scientific business logic.
5. **No CI/CD Pipeline**: `.github/workflows/` is currently absent from the repository.

### 6.2 Preserved Elements (Zero Regression Guarantee)
- **All 32 existing REST endpoints** will remain 100% active and backward-compatible.
- **The 9 deterministic decision rules** and priority escalation logic will remain intact.
- **The Water Efficiency Analytics** and CSV export will continue to function without alteration.
- **Citizen Watch & Eco-Points** wallet and verification will remain fully operational.

---

## 7. Target Architecture: Modular Component Specification (Modules A through O)

The target architecture organizes the system into 15 decoupled, testable modules:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FastAPI REST Gateway                            │
│                        (backend/app/api/)                              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
    ┌───────────────────────────────┼───────────────────────────────┐
    ▼                               ▼                               ▼
┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐
│ [A] Provider Adapters │ │ [D] Event Detection   │ │ [H] Evidence Correl.  │
│ [B] Normalization     │ │ [E] Local Sources     │ │ [I] Source Contrib.   │
│ [C] Storage Layer     │ │ [F] Transport Models  │ │ [J] Uncertainty/Prov. │
│                       │ │ [G] Satellite Metadata│ │ [K] Report Generation │
└───────────────────────┘ └───────────────────────┘ └───────────────────────┘
                                    │
    ┌───────────────────────────────┴───────────────────────────────┐
    ▼                                                               ▼
┌───────────────────────┐                               ┌───────────────────┐
│ [L] Citizen Reporting │                               │ [M] Water Engine  │
└───────────────────────┘                               └───────────────────┘
```

### Module A: Data Ingestion & Provider Adapters (`app/ingestion/`)
- **Responsibility**: Fetch raw observations and forecast datasets from external providers through standardized interface contracts.
- **Inputs**: Bounding boxes, coordinates, radius, temporal query windows.
- **Outputs**: Provider-specific raw response envelopes with metadata headers (HTTP status, latency, rate limits).
- **Dependencies**: HTTPX, Base Provider Protocol.
- **Required Data Models**: `RawTelemetryPayload`, `ProviderMetadata`.
- **Integrations**: OpenAQ v3, Open-Meteo, NASA FIRMS, OSM Overpass, Sentinel-5P Hub / Open Copernicus.
- **Testing Requirements**: Mocked HTTP responses for 200, 429, 500, and timeout scenarios.
- **Existing Affected**: Replaces ad-hoc calls in `ingestion_service.py`.

### Module B: Environmental Observation Normalization & Validation (`app/normalization/`)
- **Responsibility**: Clean, validate, timestamp, and normalize raw telemetry into immutable domain observation records.
- **Inputs**: `RawTelemetryPayload`.
- **Outputs**: `NormalizedObservation`, `SensorQualityAudit`.
- **Dependencies**: Pydantic V2, Python `datetime` (UTC enforcement).
- **Required Data Models**: `NormalizedPollutantReading`, `AtmosphericObservation`, `SensorFlag`.
- **Integrations**: None (pure domain logic).
- **Testing Requirements**: Boundary checks, negative value filtering, unit conversion ($\mu\text{g/m}^3$, ppm, ppb).

### Module C: Environmental Data Storage (`app/storage/`)
- **Responsibility**: Abstract persistence across SQLite, JSON/S3, and Amazon DynamoDB.
- **Inputs**: Domain models.
- **Outputs**: Persisted entity records, query collections.
- **Dependencies**: Boto3, SQLite3, S3Service.
- **Required Data Models**: `BaseRepository` implementations.
- **Integrations**: Amazon DynamoDB, AWS S3.
- **Testing Requirements**: Full CRUD test suite run against SQLite and in-memory mock DynamoDB.

### Module D: Pollution Event Detection (`app/investigation/event_detector.py`)
- **Responsibility**: Detect statistically significant sudden elevations in AQI, PM2.5, PM10, NO2, or SO2 over rolling 1h, 3h, and 24h baselines.
- **Inputs**: Time series of `NormalizedObservation`.
- **Outputs**: `PollutionEvent` (severity, primary driver pollutant, rate of increase $dC/dt$, duration).
- **Dependencies**: NumPy.
- **Required Data Models**: `PollutionEvent`, `EventTriggerType`.
- **Testing Requirements**: Unit tests with synthetic spikes, gradual diurnal drifts, and sensor noise.

### Module E: Local Pollution Source Investigation (`app/investigation/local_sources.py`)
- **Responsibility**: Cross-reference geographic coordinates of detected events against local emission inventories (construction projects, arterial congestion, industrial pockets, unpaved roads).
- **Inputs**: Coordinates, spatial radius (500m–5km), OSM Overpass landuse data.
- **Outputs**: `LocalSourceCandidateList` with distance, bearing, and activity status.
- **Dependencies**: `spatial_service.py`, `OverpassClient`.
- **Required Data Models**: `LocalSourceCandidate`, `SourceCategory`.

### Module F: Regional Pollution Transport & Origin Analysis (`app/investigation/transport_model.py`)
- **Responsibility**: Estimate upwind pollutant origin using Lagrangian backward wind vectors, boundary layer height, and regional station gradient comparisons.
- **Inputs**: Wind velocity, wind direction time series, boundary layer height, upwind station readings.
- **Outputs**: `TransportTrajectory` (bearing, distance traveled over 6h/12h/24h, transboundary likelihood score).
- **Dependencies**: NumPy, math.
- **Required Data Models**: `TransportTrajectory`, `UpwindSourceRegion`.

### Module G: Satellite Imagery Metadata & Change Detection (`app/investigation/satellite_service.py`)
- **Responsibility**: Query thermal fire anomalies (VIIRS/MODIS) and regional Aerosol Optical Depth (AOD) metadata for surrounding agricultural and industrial zones.
- **Inputs**: Bounding box, observation time window.
- **Outputs**: `SatelliteEvidenceSummary` (active thermal fire count, fire radiative power, AOD index).
- **Dependencies**: `firms_client.py`, Open Copernicus/Sentinel adapter.
- **Required Data Models**: `SatelliteEvidenceSummary`, `ThermalAnomaly`.

### Module H: Source Evidence Correlation (`app/investigation/evidence_correlator.py`)
- **Responsibility**: Correlate detected events, local candidates, transport vectors, and satellite observations into a coherent evidence ledger.
- **Inputs**: Outputs of Modules D, E, F, G.
- **Outputs**: `CorrelatedEvidenceLedger` linking each piece of evidence to candidate explanations.
- **Dependencies**: None (pure business logic).
- **Required Data Models**: `EvidenceItem`, `EvidenceTier` (Direct Observed, Transport Inferred, Satellite Proxy).

### Module I: Source Contribution Analysis (`app/investigation/attribution_service.py`)
- **Responsibility**: Perform scientifically conservative qualitative and semi-quantitative contribution ranking (e.g., Primary Driver: Stubble Smoke 60–75%, Secondary: Local Fugitive Dust 20–30%).
- **Rule**: Never present single decimal-point percentages without chemical speciation data; provide explicit ranges and confidence intervals.
- **Inputs**: `CorrelatedEvidenceLedger`, PM ratio, chemical proxies.
- **Outputs**: `SourceContributionAssessment`.

### Module J: Confidence, Uncertainty & Provenance (`app/investigation/provenance.py`)
- **Responsibility**: Attach cryptographic data hashes, station IDs, observation timestamps, model versions, and explicit uncertainty disclaimers to every investigation output.
- **Inputs**: All analytical outputs.
- **Outputs**: `ProvenanceEnvelope` with audit trail.

### Module K: Investigation Report Generation (`app/investigation/report_generator.py`)
- **Responsibility**: Compile findings into an executive and technical investigation dossier for municipal pollution control boards.
- **Inputs**: Investigation outputs.
- **Outputs**: Structured JSON dossier and markdown/HTML export.

### Module L: Citizen Reporting & Verification (`app/citizen/`)
- **Responsibility**: Maintain existing community reporting, audit verification, and eco-points rewards store (*Preserved without alteration*).

### Module M: Water-Efficiency Analytics (`app/analytics/`)
- **Responsibility**: Maintain existing baseline models, avoided operations, and comparative strategy matrix (*Preserved without alteration*).

### Module N: API & Frontend Integration (`app/api/`)
- **Responsibility**: Expose new investigation endpoints while retaining all 32 existing endpoints.

### Module O: Configuration, Logging & Monitoring (`app/core/`)
- **Responsibility**: Environment management, structured logging, and health observability.

---

## 8. Proposed Target File Structure

```
clearsky-intelligence/
├── application.py                         # AWS Elastic Beanstalk ASGI entrypoint (preserved)
├── Procfile                               # EB process definition (preserved)
├── run.py / main.py                       # Unified local development runners (preserved)
├── memory.md                              # Living system state (preserved)
├── data/                                  # Externalized seed data (preserved)
│   ├── calibration.json
│   ├── citizen_reports.json
│   ├── methodology.json
│   ├── rewards.json
│   ├── scenarios.json
│   └── zones.json
├── backend/
│   ├── lambda_handler.py                  # Serverless AWS Lambda handler (preserved)
│   ├── requirements.txt                   # Dependency definitions
│   ├── app/
│       ├── main.py                        # FastAPI application instance
│       ├── core/                          # Settings, logging, security
│       ├── models/                        # Domain entities
│       │   ├── domain.py                  # Core models (preserved)
│       │   └── investigation.py           # [NEW] Source intelligence models
│       ├── schemas/                       # Request/Response schemas
│       │   ├── api_models.py              # Existing schemas (preserved)
│       │   └── investigation_schemas.py   # [NEW] Investigation schemas
│       ├── repositories/                  # Storage implementations (preserved)
│       ├── data_sources/                  # Existing provider adapters (preserved)
│       ├── services/                      # Existing services (preserved)
│       │   ├── decision_engine.py
│       │   ├── estimation_service.py
│       │   └── ...
│       ├── investigation/                 # [NEW Stage 2 Modular Package]
│       │   ├── __init__.py
│       │   ├── aqi_service.py             # Isolated CPCB AQI service (extracted)
│       │   ├── event_detector.py          # Module D
│       │   ├── local_sources.py           # Module E
│       │   ├── transport_model.py         # Module F
│       │   ├── satellite_service.py       # Module G
│       │   ├── evidence_correlator.py     # Module H
│       │   ├── attribution_service.py     # Module I
│       │   └── report_generator.py        # Module K
│       ├── analytics/                     # Water efficiency (preserved)
│       └── api/
│           ├── endpoints.py               # Existing 32 endpoints (preserved)
│           └── investigation_routes.py    # [NEW] Source investigation routes
├── frontend/
│   └── src/
│       ├── App.tsx                        # Root layout
│       ├── services/api.ts                # API client
│       ├── pages/                         # Existing pages (preserved)
│       └── components/                    # Existing components (preserved)
└── backend/tests/
    ├── test_api.py                        # 43 existing tests (preserved)
    ├── test_decision_engine.py
    ├── test_estimation_service.py
    ├── test_water_efficiency.py
    └── test_investigation.py              # [NEW] Comprehensive test suite
```

---

## 9. Staged Implementation Plan (Stage 2 Onward)

### Stage 2: Normalization, Domain Modeling & CPCB Engine Isolation
- Create `backend/app/models/investigation.py` with typed schemas for pollution events, source candidates, transport trajectories, and evidence records.
- Extract `calculate_indian_aqi` from `endpoints.py` into `backend/app/investigation/aqi_service.py` to ensure unit testability and eliminate code duplication.
- Create `backend/app/investigation/event_detector.py` to identify rate-of-rise ($dC/dt$) pollution surges.
- Ensure 100% pass rate on all 43 existing backend tests.

### Stage 3: Source Evidence & Atmospheric Transport Models
- Implement `backend/app/investigation/transport_model.py` calculating Lagrangian back-trajectory dispersion vectors.
- Implement `backend/app/investigation/local_sources.py` linking coordinates to proximate construction, industrial corridors, and highway congestion via Overpass.
- Implement `backend/app/investigation/satellite_service.py` aggregating VIIRS/MODIS fire hotspots and AOD metadata.

### Stage 4: Attribution, Correlation & Uncertainty Analytics
- Implement `backend/app/investigation/evidence_correlator.py` and `attribution_service.py`.
- Implement `backend/app/investigation/report_generator.py` producing explainable municipal dossiers.
- Implement `backend/app/api/investigation_routes.py` with clean REST endpoints.

### Stage 5: Frontend Intelligence UI & Comprehensive E2E Verification
- Add new "Source Intelligence & Investigation" dashboard view to the React frontend.
- Provide interactive back-trajectory wind rose and satellite hotspot layer on the Leaflet map.
- Validate through complete Pytest and Vite build suites.

---

## 10. Stage 1 Final Findings Summary

1. **Actual Current Architecture**: FastAPI backend + React 18/TypeScript/Vite frontend with an abstract multi-backend persistence layer (SQLite, JSON+S3, DynamoDB) and an AWS Elastic Beanstalk deployment setup.
2. **Existing Working Functionality**: 32 REST endpoints, 9-rule deterministic decision engine, spatial IDW interpolation, CPCB AQI calculations, water efficiency simulations, Citizen Watch community reporting, and eco-rewards wallet.
3. **Missing Functionality for Vision**: Automated pollution spike event detection, wind back-trajectory transport modeling, multi-source evidence correlation, satellite AOD change metadata, and structured source attribution reports.
4. **Critical Technical Risks**:
   - Risk of coupling source attribution to raw AQI numbers without chemical speciation.
   - Risk of breaking backward compatibility for existing municipal water-savings contracts if routes are modified directly instead of added modularly.
   - Provider rate limits (OpenAQ v3, Overpass) requiring robust tiered caching.
5. **Proposed Target Architecture**: Additive, modular package under `backend/app/investigation/` cleanly separated from HTTP route handlers and existing decision engines.
6. **Exact Files Changing in Stage 2**:
   - `backend/app/models/investigation.py` (New)
   - `backend/app/schemas/investigation_schemas.py` (New)
   - `backend/app/investigation/__init__.py` (New)
   - `backend/app/investigation/aqi_service.py` (New)
   - `backend/app/investigation/event_detector.py` (New)
   - `backend/app/api/endpoints.py` (Extract CPCB calculation to use `aqi_service.py`)
   - `backend/tests/test_investigation.py` (New test suite)

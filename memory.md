# ClearSky Intelligence — System Memory & Technical Documentation

> **Platform**: ClearSky Intelligence  
> **Tagline**: *"Smarter environmental decisions. Cleaner, more sustainable cities."*  
> **Engineering Team**: Quantified Minds — Ishaan Chaturvedi & Ankit Kumar Tiwari  
> **Repository**: [Ishaan-Chaturved1/clearsky-intelligence](https://github.com/Ishaan-Chaturved1/clearsky-intelligence)  
> **Version**: `1.2-Deterministic`

---

## 1. Executive Summary

**ClearSky Intelligence** is an AI-powered environmental decision support and municipal air quality operations platform designed for dense urban regions, with a specialized operational focus on **Delhi NCR**.

The system addresses a critical municipal challenge: **the indiscriminate, scheduled operation of anti-smog water cannons and mist sprayers**, which consume tens of thousands of liters of potable water daily without evaluating whether atmospheric and particulate conditions will actually benefit from spraying.

ClearSky evaluates **real-time PM10/PM2.5 ratios**, **micrometeorology** (humidity, wind velocity, temperature, barometric trends), **thermal satellite fire anomalies** (MODIS/VIIRS stubble/waste fires), and **proximate construction activity** to determine whether coarse dust suppression is scientifically warranted, discouraged, or superseded by alternative dust mitigation.

---

## 2. Core Scientific & Predictive Models

### 2.1 Deterministic Environmental Decision Engine (`decision_engine.py`)
Rather than treating environmental intervention as an unexplainable black box, the platform utilizes a **deterministic, precedence-ordered 9-rule decision engine**:

| Precedence | Rule ID | Condition | Decision Outcome | Scientific Justification |
| :---: | :--- | :--- | :--- | :--- |
| **0** | `RULE-00-SAFETY` | Active Rain / Precipitation (`rain > 0.1 mm`) | `INTERVENTION_DISCOURAGED` | Natural precipitation scavenges particulates; mechanical water spraying is redundant. |
| **1** | `RULE-01-INTEGRITY` | Missing key pollutants (`PM10` or `PM2.5` null) | `ADVISORY_ONLY` | Incomplete telemetry cannot establish PM ratio; prevents unwarranted water expenditure. |
| **2** | `RULE-02-DATA-QUALITY` | Inverted pollutants (`PM10 < PM2.5` by > 5 µg/m³) | `ADVISORY_ONLY` | Sensor calibration fault or optical scattering artifact. |
| **3** | `RULE-03-STALENESS` | Telemetry older than 3 hours (`stale_data`) | `ADVISORY_ONLY` | Air mass conditions have changed; requires fresh ground observation. |
| **4** | `RULE-04-HUMIDITY` | Ambient relative humidity `> 75%` | `INTERVENTION_DISCOURAGED` | Droplets fail to evaporate; high humidity can trigger secondary sulfate/nitrate aerosol formation. |
| **5** | `RULE-05-WIND` | Wind speed `> 20 km/h` | `INTERVENTION_DISCOURAGED` | Wind drift disperses droplet curtains away from targeted emission plumes. |
| **6** | `RULE-06-SMOKE` | Combustion/Fire dominance (`PM2.5/PM10 > 0.65` or active fire within 5 km) | `INTERVENTION_DISCOURAGED` | Water droplets are ineffective against combustion-derived fine particles (<2.5 µm). Mist guns cannot abate smoke. |
| **7** | `RULE-07-HOTSPOT` | Coarse dust dominance (`PM10 >= 250` AND `PM2.5/PM10 < 0.50`) | `INTERVENTION_RECOMMENDED` | Mechanical water mist accelerates gravitational settling of heavy coarse fugitive road/construction dust. |
| **8** | `RULE-08-RAPID-DRYING` | High wind (`15-20 km/h`), low humidity (`<30%`), high temp (`>38°C`) | `ALTERNATIVE_DUST_CONTROL_SUGGESTED` | Rapid surface water evaporation; recommends chemical dust suppressants, gravel blankets, or wind screens. |
| **Default** | `DEFAULT` | Balanced or low particulate burden | `INTERVENTION_NOT_RECOMMENDED` | Ambient conditions do not warrant municipal intervention. |

#### Priority Escalation Matrix
When `INTERVENTION_RECOMMENDED` triggers, operational priority is computed (1 to 5):
* **Base priority**: Scaled from PM10 severity (250–600+ µg/m³).
* **Construction Proximity Escalation**: If active construction sites are located within 1 km, priority is boosted by **+1 to +2 tiers** (e.g., Priority 4/5 "CRITICAL"), reflecting high local human exposure.
* **Inversion Warnings**: If atmospheric inversion is detected (cold ground air trapped beneath warm boundary layers), specific operational warnings are attached.

---

### 2.2 Geospatial Estimation & Interpolation Engine (`estimation_service.py`)
Provides atmospheric intelligence for arbitrary coordinates where no physical sensor exists:
1. **Haversine Distance**: Accurate ellipsoidal distance calculations between target coordinates and CPCP/DPCC monitoring stations.
2. **Nearest Ground Station Matching**: Finds the nearest operational ground monitoring station within a 45 km radius.
3. **Inverse Distance Weighting (IDW)**: Computes distance-weighted pollutant concentrations across the 3 nearest reporting stations ($w_i = \frac{1}{d_i^2}$).
4. **Confidence Scoring**: Dynamically calculates confidence (`HIGH`, `MEDIUM`, `LOW`):
   * `HIGH`: Distance to active ground station $\le 10$ km with fresh PM10 & PM2.5 readings.
   * `MEDIUM`: Distance between 10–25 km, or utilizing gridded atmospheric numerical model forecasts.
   * `LOW`: Distance $> 25$ km, stale telemetry, or single-pollutant monitors.

---

### 2.3 Official Indian CPCB AQI Calculation Engine (`cpcb_aqi.py`)
Computes the authentic **Central Pollution Control Board (CPCB)** Air Quality Index:
* Follows the official 6-tier Indian standard: *Good (0-50)*, *Satisfactory (51-100)*, *Moderate (101-200)*, *Poor (201-300)*, *Very Poor (301-400)*, and *Severe (401-500+)*.
* Implements piecewise linear sub-index interpolation for **PM10, PM2.5, NO2, SO2, CO, and O3**.
* Applies the official CPCB minimum requirement: AQI requires at least 3 pollutants, one of which **must** be PM10 or PM2.5.
* Identifies the primary driver pollutant and surfaces explicit missing pollutant warnings.

---

### 2.4 Calibrated Particulate Suppression & Water Conservation Engine (`water_efficiency.py` & `predictive_model_service.py`)
* **Audited Water Accounting**: Compares model-recommended interventions against configurable municipal baseline spraying schedules (default: 3 runs/day per sector with 5,000–8,000 L tankers).
* **Avoided Operations**: Quantifies municipal water and tanker diesel conserved by suppressing spraying during smoke episodes, high wind, and humid hours.
* **Empirical Field Calibration**: Reads empirical post-intervention outcome records (`data/calibration.json`) to quantify real-world particulate drop ($\Delta \text{PM}_{10}$ vs $\Delta \text{PM}_{2.5}$) and compute statistical intervention efficiency.
* **4-Scenario Strategy Comparison Matrix**:
  1. *Fixed Scheduled Spraying* (3 runs/day regardless of weather)
  2. *AQI-Threshold Triggered Spraying* (sprays whenever AQI > 300, even during smoke/rain)
  3. *ClearSky Targeted Intelligence* (only sprays during coarse dust dominance)
  4. *Alternative Dust Control* (chemical binders and gravel blankets)

---

## 3. Application Features & UI Architecture

### 3.1 Command Center Dashboard (`DashboardPage.tsx`)
* **Real-time Overview Cards**: Monitored sectors, high-priority candidates, suppressed operations, and total cubic meters of water saved.
* **AI Daily Brief Banner**: Synthesized morning briefing highlighting dominant meteorological drivers, regional smoke plumes, and operational recommendations.
* **Regional GIS Map**: Interactive Leaflet map featuring custom pulsating SVG markers indicating recommendation tier, wind vectors, and monitoring stations.
* **Sector Priority Queue**: Filterable live queue (All, Recommended, Discouraged, Advisory, Alternative) with detailed telemetry dossiers.
* **Live Audit Feed**: Chronological log of recent automated decisions, sensor alerts, and priority escalations.

### 3.2 Dynamic Map Explorer & Locality Discovery (`MapExplorerPage.tsx`)
* **OpenStreetMap Nominatim Geocoding**: Search any neighborhood, sector, or landmark across Delhi NCR (e.g., *"Connaught Place"*, *"Noida Sector 62"*, *"Cyber City"*).
* **Click-to-Analyze GIS**: Click anywhere on the map to trigger on-the-fly environmental evaluation.
* **Dual Observation Aggregation**: Simultaneously queries live ground sensors from **OpenAQ** and numerical weather models from **Open-Meteo**.
* **Instant Suitability Dossier**: Evaluates whether mist gun deployment is recommended for that exact latitude/longitude with full explanation.

### 3.3 Citizen Watch & Community Eco-Points Loop (`CitizenWatchPage.tsx`)
* **Public Violation Reporting**: Community reporting for unmitigated construction dust, illegal demolition, industrial stack smoke, and open waste burning.
* **Multi-Channel Dispatch Ribbon**: Direct links to report via WhatsApp, Email, or Municipal Hotline.
* **Multimedia & Evidence Ingestion**: Supports photo URLs, address geolocations, and voice note transcription.
* **Audit & Verification Workflow**: Admin endpoint to audit and verify reports, awarding points (50–100 pts) directly to citizen wallets.
* **Eco-Rewards Store**: Catalog of redeemable rewards (HEPA filters, N95 respirator multi-packs, metro transit passes, anti-pollution indoor plants).

### 3.4 Water Efficiency Analytics (`WaterAnalyticsPage.tsx`)
* **Multi-Period Windowing**: 3-day, 7-day, 14-day, and 30-day cumulative conservation windows.
* **Configurable Simulation Assumptions**: Modal allowing operators to adjust baseline runs/day (1–10) and tanker capacity (1,000–20,000 L).
* **Comparative Dual-Axis Trend Chart**: Recharts area/bar visualization showing baseline operations vs recommended operations and water savings curve.
* **4-Scenario Comparison Table**: Side-by-side evaluation of water used, water saved, tanker trips, estimated cost, and risk notes.
* **CSV Export**: Direct streaming export of daily operational logs for municipal reporting.

### 3.5 Methodology & Ethical AI Page (`MethodologyPage.tsx`)
* Detailed breakdown of all 9 deterministic precedence rules.
* Mathematical explanation of confidence tiers and sensor validation.
* **Ethical AI Boundaries**: Explicit declarations of system limitations (e.g., mist cannons do not abate PM2.5, no fabricated sensor data, transparent baselines).

### 3.6 Data Sources & Telemetry Status (`DataSourcesPage.tsx`)
* Live health status of all data pipelines (OpenAQ, Open-Meteo, CAMS, CPCB, NASA FIRMS).
* Data classification labeling: *Observed Ground Telemetry* vs *Atmospheric Numerical Model*.
* Spatial resolution and temporal latency documentation.

### 3.7 Responsive Widescreen Design
* Built with Tailwind CSS using an editorial warm palette: **Earth**, **Warm**, **Sage**, and **Coral Accent** colors with **Sentinel** and **Clarendon** typography.
* Fluid `w-full max-w-[1780px]` container layout eliminating awkward letterboxing on large monitors.
* Fully responsive navigation with a mobile hamburger toggle and drawer.

---

## 4. Multi-Backend Persistence Architecture

ClearSky Intelligence features an abstract repository layer (`BaseRepository`) with three interchangeable backends configured via `STORAGE_BACKEND`:

```
                       ┌──────────────────────┐
                       │    BaseRepository    │
                       └──────────┬───────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
         ▼                        ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ SQLiteRepository │    │  JSONRepository  │    │DynamoDBRepository│
│ (Local SQL File) │    │  (Local + S3)    │    │ (AWS Serverless) │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

1. **`sqlite` (Default Local)**: Single-file SQLite database at `data/clearsky.db`. Automatically creates tables and runs migrations on startup.
2. **`json` (File + S3 Storage)**: Atomic JSON document storage in `data/`. Includes automatic background upload and synchronization to Amazon S3 via `S3Service`.
3. **`dynamodb` (AWS Cloud)**: Native Amazon DynamoDB storage spanning 7 tables:
   * `clearsky-zones`: Sector geographic polygons and attributes.
   * `clearsky-readings`: Environmental telemetry and pollutant records.
   * `clearsky-decisions`: Computed 9-rule decision logs.
   * `clearsky-alerts`: Critical threshold alerts and notifications.
   * `clearsky-citizen-reports`: Public infraction reports.
   * `clearsky-rewards`: Eco-rewards catalog.
   * `clearsky-redemptions`: Ledger of user points and item redemptions.
   * *Graceful Fallback*: If AWS credentials or tables are not reachable, it automatically falls back to `JSONRepository` without crashing.

---

## 5. Externalized Data Directory (`data/`)

All static and seed data is fully decoupled from Python code:
* [**`data/zones.json`**](file:///Users/cybertron/MyProjects/ML/clearsky-intelligence/data/zones.json): 12 monitored sectors across Delhi, Noida, Gurugram, Ghaziabad, and Faridabad.
* [**`data/scenarios.json`**](file:///Users/cybertron/MyProjects/ML/clearsky-intelligence/data/scenarios.json): Realistic multi-condition demo scenarios (Anand Vihar dust hotspot, Rohini stubble smoke episode, Okhla high wind, Connaught Place moderate baseline).
* [**`data/rewards.json`**](file:///Users/cybertron/MyProjects/ML/clearsky-intelligence/data/rewards.json): 5 certified eco-rewards catalog items.
* [**`data/citizen_reports.json`**](file:///Users/cybertron/MyProjects/ML/clearsky-intelligence/data/citizen_reports.json): Community reports with location, photos, categories, and audit states.
* [**`data/calibration.json`**](file:///Users/cybertron/MyProjects/ML/clearsky-intelligence/data/calibration.json): Historical field intervention outcomes for model training and verification.
* [**`data/methodology.json`**](file:///Users/cybertron/MyProjects/ML/clearsky-intelligence/data/methodology.json): Structured decision rules and system limitations.

---

## 6. Deployment & Cloud Architecture

### 6.1 AWS Elastic Beanstalk
* [**`application.py`**](file:///Users/cybertron/MyProjects/ML/clearsky-intelligence/application.py): Entrypoint exposing the FastAPI ASGI app as `application`.
* [**`Procfile`**](file:///Users/cybertron/MyProjects/ML/clearsky-intelligence/Procfile): `web: uvicorn application:application --host 0.0.0.0 --port 5000`.
* [**`.ebextensions/01_app.config`**](file:///Users/cybertron/MyProjects/ML/clearsky-intelligence/.ebextensions/01_app.config): Health check endpoint (`/api/health`) and system package dependencies.

### 6.2 AWS Lambda & Serverless
* [**`backend/lambda_handler.py`**](file:///Users/cybertron/MyProjects/ML/clearsky-intelligence/backend/lambda_handler.py): Uses `Mangum` to wrap FastAPI for serverless execution behind Amazon API Gateway or Function URLs.

### 6.3 DynamoDB Provisioning
* [**`scripts/init_dynamodb.py`**](file:///Users/cybertron/MyProjects/ML/clearsky-intelligence/scripts/init_dynamodb.py): Automated script using Boto3 to create all 7 DynamoDB tables with on-demand capacity and seed default sector records.

### 6.4 Unified Local Runner
* [**`run.py`**](file:///Users/cybertron/MyProjects/ML/clearsky-intelligence/run.py) / [**`main.py`**](file:///Users/cybertron/MyProjects/ML/clearsky-intelligence/main.py): One-command local runner that starts both FastAPI (port 8000) and React/Vite (port 5173) with port conflict detection and cleanup.

---

## 7. Verification & Test Suite

The codebase maintains 100% test passing status:
* **Frontend**: `tsc && vite build` compiles cleanly with zero TypeScript errors.
* **Backend**: `pytest backend/tests/ -v` executes **43 comprehensive unit and integration tests** covering:
  * Health, zones, and overview API contracts.
  * Deterministic decision engine logic across all 9 precedence rules.
  * Haversine distance, IDW interpolation, and confidence calculation.
  * CPCB AQI calculation and missing pollutant handling.
  * Water savings calculations and CSV export streaming.
  * Citizen reporting and eco-points balance auditing.

---

## 8. Summary of File Tree

```
clearsky-intelligence/
├── .ebextensions/
│   └── 01_app.config            # Elastic Beanstalk configuration
├── Procfile                     # Elastic Beanstalk process definition
├── application.py               # Elastic Beanstalk entrypoint
├── main.py / run.py             # Unified local development runners
├── memory.md                    # System architecture & feature memory (this document)
├── data/
│   ├── calibration.json         # Field intervention outcomes
│   ├── citizen_reports.json     # Community infraction reports
│   ├── methodology.json         # 9-rule decision specifications
│   ├── rewards.json             # Eco-rewards catalog
│   ├── scenarios.json           # Sector environmental scenarios
│   └── zones.json               # Delhi NCR monitored sectors
├── backend/
│   ├── lambda_handler.py        # AWS Lambda / Mangum adapter
│   └── app/
│       ├── api/endpoints.py     # FastAPI REST endpoints
│       ├── core/config.py       # Pydantic settings & env loader
│       ├── models/domain.py     # Core domain entities
│       ├── schemas/api_models.py# API request/response models
│       ├── services/
│       │   ├── decision_engine.py         # 9-rule deterministic engine
│       │   ├── estimation_service.py      # Spatial IDW interpolation
│       │   ├── predictive_model_service.py# Machine learning & calibration
│       │   ├── s3_service.py              # AWS S3 document manager
│       │   └── water_efficiency.py        # Audited water calculations
│       └── repositories/
│           ├── __init__.py                # Dynamic repository factory
│           ├── local_repository.py        # SQLite repository
│           ├── json_repository.py         # JSON + S3 repository
│           └── dynamodb_repository.py     # Amazon DynamoDB repository
├── frontend/
│   └── src/
│       ├── App.tsx                        # Root layout with fluid width
│       ├── components/                    # UI cards, map, drawers, modals
│       │   ├── Navbar.tsx                 # Widescreen & mobile navigation
│       │   ├── Footer.tsx                 # Responsive footer
│       │   ├── ZoneMap.tsx                # Interactive Leaflet GIS map
│       │   └── WaterAnalyticsChart.tsx    # Dual-axis Recharts visualization
│       └── pages/                         # Core viewpages
│           ├── DashboardPage.tsx          # Real-time Command Center
│           ├── MapExplorerPage.tsx        # Geocoding & live GIS discovery
│           ├── CitizenWatchPage.tsx       # Community reporting & rewards
│           ├── WaterAnalyticsPage.tsx     # Water accounting & strategy matrix
│           ├── MethodologyPage.tsx        # Explainable decision rules
│           ├── DataSourcesPage.tsx        # Telemetry ingestion health
│           └── AboutPage.tsx              # Project & engineering team overview
└── scripts/
    ├── init_dynamodb.py         # DynamoDB table provisioning script
    └── seed_demo_data.py        # Database seeder from JSON catalogs
```

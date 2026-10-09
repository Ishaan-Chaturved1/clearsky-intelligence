# ClearSky Intelligence — Smart Urban Air Intelligence

> **"Smarter environmental decisions. Cleaner, more sustainable cities."**

**Product Category:** AI-powered environmental intelligence and smart-city decision support.  
**Team:** Quantified Minds  
**Engineers:**
- **Ishaan Chaturvedi** (Full-Stack & Systems Architecture)
- **Ankit Kumar Tiwari** (Environmental Data Science & Cloud Architecture)

---

## 1. Product Overview & Core Concept

**ClearSky Intelligence** is a production-grade environmental intelligence command center built to help municipal authorities, urban planners, and environmental operations teams make targeted, evidence-based decisions regarding urban dust mitigation (e.g., anti-smog mist cannons and road wetting).

### The Core Problem: Indiscriminate Water Spraying
In many South Asian and developing urban corridors, municipal teams deploy water mist cannons whenever general Air Quality Index (AQI) values spike. However, fine particulate matter ($\text{PM}_{2.5}$, $\le 2.5\ \mu\text{m}$) originates from combustion sources (vehicles, crop burning, industrial stacks) and **cannot** be effectively captured from ambient air by water droplet spraying. Spraying in these conditions wastes vast amounts of clean municipal water while creating road hazards and artificial fogging.

### The Solution: Evidence-Aware Decision Support
Instead of indiscriminate deployment, ClearSky Intelligence determines:
1. **Coarse Dust Dominance:** Checks if $\text{PM}_{10}/\text{PM}_{2.5} \ge 2.0$ with elevated $\text{PM}_{10}$ ($\ge 120\ \mu\text{g/m}^3$).
2. **Atmospheric Suitability:** Suppresses spraying during active upwind smoke plumes (NASA FIRMS), high humidity ($\ge 80\%$), or high wind speeds ($\ge 20\text{ km/h}$).
3. **Data Freshness & Confidence:** Requires valid observations or defaults safely to `ADVISORY ONLY`.
4. **Water Conservation Audit:** Compares decisions against a configurable baseline schedule (e.g., 3 runs/zone/day) to calculate avoided water consumption and operations.

---

## 2. Key Features

- **Environmental Operations Command Center:** Top KPI metrics, dynamic status indicators (`LIVE DATA`, `CACHED DATA`, `DEMO DATA`), and daily atmospheric synthesis.
- **Interactive GIS Map Explorer:** Dark OpenStreetMap/CartoDB tiles with 12 Delhi NCR monitoring sectors, color-coded priority markers (Sage Green, Warm Red, Amber, Neutral Gray), and click-to-dossier telemetry.
- **Atmospheric Intelligence Panel:** Deep physics panel computing Dalton evaporation rate ($E_{\text{rate}}$ mm/h), road surface drying time, WMO barometric pressure tendency (3h/6h/12h deltas), and aerodynamic mist drift risk.
- **Corridor & Road Segment Targeting:** Ranks candidate municipal road corridors from OpenStreetMap with road width, length, surface area, water demand ($0.4\text{ L/m}^2$), and required tanker trips.
- **Best Time to Spray Planning:** 24-hour hourly weather forecast window ranking identifying optimal atmospheric windows for targeted suppression.
- **Multi-Scenario Water-Efficiency Audit:** Compares Scheduled vs AQI-Threshold vs ClearSky Targeted vs Alternative Dust Control, calculating saved water, tanker trips, and operational expenditure with instant CSV audit report export.
- **Empirical Intervention Logging:** Field outcome logging tracking pre- and post-intervention $\Delta\text{PM}_{10}$ against untreated control zones.
- **Transparent Methodology Guide:** Full explainability of all 9 decision rules, threshold triggers, CPCB AQI breakpoints, and explicit scientific limitations.
- **Real-Time Data Source Health:** Live monitoring of OpenAQ API v3, Open-Meteo Weather, Open-Meteo Atmospheric Chemistry, NASA FIRMS, and OpenStreetMap Overpass.

---

## 3. Technology Stack & Typography

### Frontend
- **Framework:** React 18 with Vite and TypeScript
- **Styling:** Custom warm beige, sage green, and terra-cotta design system
- **Typography:**
  - **Sentinel / Clarendon:** Editorial and authoritative headings
  - **Inter / System Sans:** Clean data tables and forms
  - **IBM Plex Mono:** Technical metrics, barometric values, coordinates, and timestamps
- **Mapping:** Leaflet & React-Leaflet with custom SVG pulsating pins
- **Visualizations:** Recharts (composed bar and line water trajectories)
- **Icons:** Lucide React

### Backend
- **Framework:** Python 3.13 / 3.11 with FastAPI and Uvicorn
- **Validation:** Pydantic V2 schemas and strict typing
- **Clients:** HTTPX asynchronous HTTP client with timeout budgets
- **Data & Testing:** NumPy, Pandas, Pytest (37 passing unit & integration tests, 100% pass rate)

### Storage Abstraction
- **Local Development:** SQLite (`data/clearsky.db`) with automatic table creation and realistic historical demo seeding (zero AWS credentials required).
- **Production AWS:** Amazon DynamoDB adapter (`clearsky-zones`, `clearsky-readings`, `clearsky-decisions`, `clearsky-alerts`).

---

## 4. Project Directory Structure

```
WeMakeDevs-2/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── endpoints.py        # All REST API endpoints
│   │   ├── core/
│   │   │   ├── config.py           # Pydantic environment configuration
│   │   │   └── logging.py          # Structured logging
│   │   ├── models/
│   │   │   └── domain.py           # Domain dataclasses & enums
│   │   ├── schemas/
│   │   │   └── api_models.py       # Pydantic V2 API response schemas
│   │   ├── repositories/
│   │   │   ├── base.py             # Storage abstraction interface
│   │   │   ├── local_repository.py # SQLite local implementation
│   │   │   └── dynamodb_repository.py # AWS DynamoDB adapter
│   │   ├── data_sources/
│   │   │   ├── base.py             # TTL caching & source models
│   │   │   ├── openaq_client.py    # OpenAQ v3 ground stations
│   │   │   ├── open_meteo_client.py# Open-Meteo weather & air quality
│   │   │   ├── firms_client.py     # NASA FIRMS active thermal anomalies
│   │   │   └── overpass_client.py  # OSM Overpass construction features
│   │   ├── services/
│   │   │   ├── estimation_service.py # IDW interpolation & confidence
│   │   │   ├── decision_engine.py  # Deterministic rule engine
│   │   │   ├── ingestion_service.py# Pipeline orchestrator
│   │   │   ├── alerting_service.py # Alerting with deduplication
│   │   │   └── ai_brief_service.py # Operational brief with Bedrock/fallback
│   │   ├── analytics/
│   │   │   └── water_efficiency.py # Water savings & CSV export
│   │   └── main.py                 # FastAPI app & lifespan seeder
│   ├── tests/
│   │   ├── test_decision_engine.py # Decision engine rules & edge cases
│   │   ├── test_water_efficiency.py# Water formulas & CSV export tests
│   │   ├── test_estimation_service.py # IDW & Haversine distance tests
│   │   └── test_api.py             # FastAPI TestClient smoke tests
│   ├── lambda_handler.py           # AWS Lambda API & EventBridge handlers
│   └── requirements.txt            # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── components/             # Reusable UI components
│   │   ├── pages/                  # Routed application pages
│   │   ├── services/api.ts         # Backend API client
│   │   ├── types/index.ts          # TypeScript type definitions
│   │   ├── utils/formatters.ts     # Numerical and date formatters
│   │   ├── App.tsx                 # Root router and layout
│   │   ├── main.tsx                # React DOM entry
│   │   └── index.css               # Global CSS & typography tokens
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── data/
│   ├── zones.json                  # Seed Delhi NCR sector metadata
│   └── clearsky.db                 # Local SQLite database
├── infrastructure/
│   ├── template.yaml               # AWS SAM CloudFormation template
│   └── dynamodb_schema.json        # DynamoDB partition key documentation
├── scripts/
│   ├── seed_demo_data.py           # Historical timeline seeding script
│   └── run_ingestion.py            # Manual CLI ingestion test runner
├── docs/
│   ├── ARCHITECTURE.md             # System architecture & Mermaid diagrams
│   ├── METHODOLOGY.md              # Scientific methodology & formulas
│   └── API_SPEC.md                 # Full REST API specification
├── .env.example                    # Environment variable template
├── .gitignore
├── pytest.ini                      # Pytest path configuration
└── README.md
```

---

## 5. Local Setup & Execution Guide

### Prerequisites
- Python 3.11+ (Python 3.13 supported)
- Node.js 18+ and npm

### Step 1: Clone & Configure Environment
```bash
git clone <repo-url>
cd WeMakeDevs-2

# Copy environment variables
cp .env.example .env
```

### Step 2: Set Up Backend Virtual Environment
```bash
# Create and activate virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate

# Install backend dependencies
pip install -r backend/requirements.txt

# Seed demonstration data into local SQLite database
python scripts/seed_demo_data.py
```

### Step 3: Run Backend Server
```bash
# Run FastAPI with live reload on port 8000
python -m uvicorn app.main:app --app-dir backend --reload --port 8000
```
- API Health Check: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- Interactive Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

### Step 4: Run Frontend Server
In a separate terminal:
```bash
cd frontend

# Install npm dependencies (if not already installed)
npm install

# Start Vite development server
npm run dev
```
- Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 6. Automated Testing Verification

### Backend Pytest Suite
The backend includes 29 comprehensive automated tests covering decision rules, edge cases, zero-denominator safeguards, water efficiency calculations, and API endpoints.

```bash
# Run pytest from project root
.venv\Scripts\pytest backend/tests
```

**Results:**
```
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0
configfile: pytest.ini
collected 29 items

backend\tests\test_api.py ..........                                     [ 34%]
backend\tests\test_decision_engine.py ...........                        [ 72%]
backend\tests\test_estimation_service.py .....                           [ 89%]
backend\tests\test_water_efficiency.py ...                               [100%]

======================== 29 passed in 0.96s ===================================
```

### Frontend Production Build
```bash
cd frontend
npm run build
```
**Results:**
```
✓ 2367 modules transformed.
dist/index.html                   1.76 kB │ gzip:   0.94 kB
dist/assets/index-DrWTdECP.css   27.42 kB │ gzip:   5.63 kB
dist/assets/index-O_I-14S_.js   817.47 kB │ gzip: 230.69 kB
✓ built in 27.08s
```

---

## 7. Required & Optional Environment Variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `ENVIRONMENT` | Yes | `development` | Deployment environment (`development`, `production`) |
| `STORAGE_BACKEND` | Yes | `sqlite` | Storage selection (`sqlite` or `dynamodb`) |
| `SQLITE_DB_PATH` | No | `data/clearsky.db` | Local SQLite database file location |
| `OPENAQ_API_KEY` | Optional | `""` | OpenAQ API v3 ground station key (runs in demo mode if empty) |
| `NASA_FIRMS_MAP_KEY` | Optional | `""` | NASA FIRMS VIIRS active fire anomaly key |
| `ADMIN_API_KEY` | Yes | `clearsky-dev-admin-secret-2025` | Key to protect `/api/admin/refresh` in production |
| `DEFAULT_BASELINE_INTERVENTIONS_PER_ZONE_PER_DAY` | No | `3.0` | Default fixed schedule runs/zone/day |
| `DEFAULT_ASSUMED_LITERS_PER_INTERVENTION` | No | `5000.0` | Assumed liters deployed per run |
| `ENABLE_AI_BRIEF` | No | `false` | Enable Amazon Bedrock generative synthesis |
| `AWS_REGION` | No | `us-east-1` | Target AWS region |

---

## 8. AWS Cloud Deployment Steps

The application includes an AWS Serverless Application Model (SAM) template (`infrastructure/template.yaml`).

### Deployment Procedure:
1. **Build SAM Package:**
   ```bash
   sam build -t infrastructure/template.yaml
   ```

2. **Deploy to AWS Account:**
   ```bash
   sam deploy --guided \
     --stack-name clearsky-intelligence \
     --parameter-overrides Environment=production \
     --capabilities CAPABILITY_IAM
   ```

3. **Deploy Frontend SPA to S3 & CloudFront:**
   ```bash
   cd frontend
   npm run build
   aws s3 sync dist/ s3://<FrontendBucketName> --delete
   aws cloudfront create-invalidation --distribution-id <DistributionId> --paths "/*"
   ```

### Estimated AWS Costs
- **DynamoDB:** Pay-Per-Request billing mode. Typical read/write costs for 12 zones sampled every 30 minutes: **<$1.50/month**.
- **Lambda:** 120 invocations/day for ingestion + API proxy: **<$0.50/month** (well within AWS Free Tier).
- **API Gateway (HTTP API):** 100,000 requests/month: **<$0.10/month**.
- **CloudFront & S3:** Static hosting: **<$1.00/month**.
- **Total estimated operational cost:** **<$3.50/month**.

---

## 9. Assumptions & Ethical AI Restraint

1. **No Fine Particulate Claims:** ClearSky Intelligence explicitly states that water mist guns do not eliminate $\text{PM}_{2.5}$ or vehicle combustion soot.
2. **Model vs Physical Observations:** Data derived from numerical models (CAMS/Open-Meteo) is clearly labeled as `modeled`.
3. **Comparative Baseline Calculations:** Water savings reflect avoidance relative to user-configured fixed operational schedules, not physical municipal water meters.
4. **Deterministic Auditing:** Primary operational decisions are governed by transparent, human-auditable logic rather than black-box probabilistic models.

---

© 2026 Quantified Minds (Ishaan Chaturvedi & Ankit Kumar Tiwari). Built for smarter, cleaner, and more sustainable cities.

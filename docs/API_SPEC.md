# ClearSky Intelligence — API Specification

**Base URL:** `http://localhost:8000/api` (Local Dev) / AWS API Gateway endpoint (Production)  
**Interactive Docs:** `/docs` (Swagger UI), `/redoc` (ReDoc)  

---

## 1. Endpoints Summary

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | System health, version, storage backend status |
| `GET` | `/overview` | Top-level monitored zones, candidates, water savings KPI |
| `GET` | `/zones` | All monitored zones with latest telemetry & decisions |
| `GET` | `/zones/{zone_id}` | Detailed telemetry and decision for a single zone |
| `GET` | `/zones/{zone_id}/history` | Historical readings and decisions for a zone |
| `GET` | `/decisions/latest` | Latest scored decision across all zones |
| `GET` | `/decisions/history` | Paginated decision audit records |
| `GET` | `/analytics/water-savings` | Configurable water-efficiency calculations & trends |
| `GET` | `/analytics/water-savings/export` | Download water efficiency audit report as CSV |
| `GET` | `/analytics/overview` | 7-day and 30-day comparative water analytics summary |
| `GET` | `/sources/status` | Connection health, variables, and mode for data sources |
| `GET` | `/methodology` | Core rules, thresholds, and scientific limitations |
| `GET` | `/brief/daily` | Operational atmospheric brief (Bedrock / Deterministic) |
| `GET` | `/alerts` | Recent operational alerts feed |
| `POST` | `/admin/refresh` | Trigger ingestion pipeline & re-score zones (Protected) |

---

## 2. Selected Schemas & Examples

### `GET /api/overview`
```json
{
  "total_monitored_zones": 12,
  "intervention_candidates": 4,
  "intervention_discouraged": 5,
  "advisory_only_zones": 3,
  "estimated_water_saved_liters": 850000.0,
  "intervention_reduction_percent": 80.9,
  "last_data_refresh": "2026-10-09T08:30:00Z",
  "data_mode": "LIVE",
  "sources_coverage": {
    "openaq": "Available (Ground Stations)",
    "open_meteo": "Active (Forecast & Models)",
    "nasa_firms": "Active (Thermal Anomaly Grid)",
    "osm_overpass": "Cached (Infrastructure GIS)"
  }
}
```

### `GET /api/decisions/latest`
```json
[
  {
    "decision_id": "DEC-DEL-AV-01-20261009T0830",
    "zone_id": "DEL-AV-01",
    "decision": "INTERVENTION_RECOMMENDED",
    "priority": 4,
    "confidence": "HIGH",
    "pollutants": {
      "pm25": { "value": 75.0, "unit": "ug/m3", "data_type": "observed", "station_id": "STN-DEL-AV" },
      "pm10": { "value": 265.0, "unit": "ug/m3", "data_type": "observed", "station_id": "STN-DEL-AV" }
    },
    "weather": {
      "temperature_c": 28.5,
      "relative_humidity": 48.0,
      "wind_speed_kmh": 8.0,
      "wind_direction_deg": 280.0,
      "boundary_layer_height_m": 450.0
    },
    "reasons": [
      "PM10 is elevated (265.0 µg/m³) with high PM10/PM2.5 ratio (3.53), indicating potential coarse fugitive dust dominance.",
      "Severe PM10 concentration (>= 250 µg/m³).",
      "Identified nearby construction site within 180m contributes to localized fugitive road/earth dust."
    ],
    "warnings": [
      "Recommend contractor environmental compliance review and perimeter wetting."
    ],
    "source_status": { "openaq": "available", "open_meteo_weather": "available" },
    "data_mode": "LIVE",
    "observed_at": "2026-10-09T08:30:00Z",
    "scored_at": "2026-10-09T08:30:00Z"
  }
]
```

### `GET /api/analytics/water-savings`
**Query Parameters:**
- `days` (integer, default: 7, range: 1–30)
- `baseline_rate` (float, optional, default: 3.0)
- `liters_per_op` (float, optional, default: 5000.0)

**Response:**
```json
{
  "reporting_period_days": 7,
  "number_of_zones": 12,
  "baseline_interventions_per_zone_per_day": 3.0,
  "assumed_liters_per_intervention": 5000.0,
  "baseline_interventions": 252,
  "recommended_interventions": 48,
  "avoided_interventions": 204,
  "baseline_water_liters": 1260000.0,
  "recommended_water_liters": 240000.0,
  "estimated_water_saved_liters": 1020000.0,
  "intervention_reduction_percent": 81.0,
  "daily_trend": [ ... ],
  "is_simulation": false,
  "data_source_mode": "LIVE",
  "assumptions_note": "Assumptions: Baseline fixed schedule = 3.0 runs/zone/day..."
}
```

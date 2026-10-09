# ClearSky Intelligence — API Specification

**System:** ClearSky Intelligence Environmental Decision Engine  
**Version:** 2.0.0-Production  
**Base URL:** `http://localhost:8000/api` (Local Dev) / AWS API Gateway endpoint (Production)  
**Interactive Docs:** `/docs` (OpenAPI Swagger UI), `/redoc` (ReDoc)  

---

## 1. Endpoints Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | System health, database connection, and data mode |
| `GET` | `/overview` | 12-sector overview, candidate count, water savings, data provider health |
| `GET` | `/zones` | Monitored sectors with latest atmospheric telemetry & decision records |
| `GET` | `/zones/{zone_id}` | Detailed telemetry and active decision for a specific sector |
| `GET` | `/zones/{zone_id}/history` | Historical readings and decisions time-series |
| `GET` | `/zones/{zone_id}/atmospheric-analysis` | Atmospheric physics breakdown (CPCB AQI, Dalton drying time, barometric tendency, wind drift risk) |
| `GET` | `/zones/{zone_id}/candidate-segments` | Ranked candidate road segments (geometry, water demand, tanker trips, priority) |
| `GET` | `/zones/{zone_id}/forecast-windows` | Hourly forecast operating windows ranked by suitability (12–24h) |
| `GET` | `/decisions/latest` | Latest decisions for all 12 monitored sectors |
| `GET` | `/decisions/history` | Paginated decision audit log |
| `GET` | `/analytics/water-savings` | Configurable water-efficiency calculations & daily trends |
| `GET` | `/analytics/water-savings/export` | Download complete audit report with scenario breakdown as CSV |
| `GET` | `/analytics/strategy-comparison` | 4-scenario comparative audit (Scheduled vs AQI-Threshold vs ClearSky vs Alternative) |
| `GET` | `/interventions` | Retrieve logged field intervention records |
| `POST` | `/interventions` | Log a completed municipal water spraying run |
| `GET` | `/interventions/effectiveness-summary` | Summary of empirical intervention outcomes and model status |
| `GET` | `/sources/status` | Connection health, latency, last successful update, and data mode |
| `GET` | `/methodology` | All 9 decision rules, thresholds, rationale, and scientific limitations |
| `GET` | `/brief/daily` | Meteorological executive operational briefing |
| `GET` | `/alerts` | Operational alerts feed |
| `POST` | `/admin/refresh` | Trigger external telemetry ingestion & re-scoring (Protected) |

---

## 2. Detailed Endpoints

### 2.1 Atmospheric Physics Analysis
`GET /api/zones/{zone_id}/atmospheric-analysis`

**Response Example:**
```json
{
  "zone_id": "DEL-AV-01",
  "zone_name": "Anand Vihar, East Delhi",
  "latitude": 28.6508,
  "longitude": 77.3153,
  "timestamp": "2026-10-09T08:30:00Z",
  "aqi_estimate": 285,
  "aqi_standard": "Indian National CPCB (8-Sub-Index)",
  "pm10_value": 240.0,
  "pm25_value": 65.0,
  "pm_ratio": 3.69,
  "pm_ratio_interpretation": "Coarse dust dominant (PM10/PM2.5 >= 2.0)",
  "temperature_c": 29.5,
  "relative_humidity": 45.0,
  "surface_pressure_hpa": 1012.8,
  "pressure_trend_3h_hpa": 0.3,
  "pressure_trend_6h_hpa": 0.8,
  "pressure_trend_12h_hpa": -0.5,
  "pressure_tendency": "STEADY",
  "pressure_interpretation": "Stable anticyclonic stagnation; calm surface conditions.",
  "wind_speed_kmh": 7.5,
  "wind_direction_deg": 290.0,
  "wind_drift_risk": "LOW (<10 km/h: favorable mist retention)",
  "precipitation_mmh": 0.0,
  "evaporation_rate_mmh": 0.28,
  "estimated_drying_time_minutes": 85.7,
  "data_freshness_seconds": 1200,
  "nearest_station_distance_km": 1.2
}
```

### 2.2 Ranked Candidate Road Segments
`GET /api/zones/{zone_id}/candidate-segments`

**Response Example:**
```json
{
  "zone_id": "DEL-AV-01",
  "zone_name": "Anand Vihar, East Delhi",
  "total_segments": 3,
  "total_water_required_liters": 20400.0,
  "total_tanker_trips": 5,
  "segments": [
    {
      "segment_id": "DEL-AV-01-SEG-01",
      "zone_id": "DEL-AV-01",
      "road_name": "Vikas Marg Inner Corridor",
      "road_classification": "primary",
      "length_km": 2.2,
      "estimated_width_m": 12.0,
      "surface_area_m2": 26400.0,
      "traffic_index": "HIGH",
      "construction_adjacent": true,
      "construction_distance_m": 120.0,
      "water_required_liters": 10560.0,
      "tanker_trips_required": 3,
      "priority_score": 5,
      "recommended_action": "TARGETED_WATER_SPRAYING",
      "estimated_cost_inr": 2100.0
    }
  ]
}
```

### 2.3 Forecast Operating Windows
`GET /api/zones/{zone_id}/forecast-windows?hours=24`

**Response Example:**
```json
{
  "zone_id": "DEL-AV-01",
  "zone_name": "Anand Vihar, East Delhi",
  "forecast_source": "Open-Meteo Hourly Numerical Weather Prediction",
  "optimal_windows_count": 5,
  "best_window": {
    "window_id": "WIN-06:00",
    "start_time": "2026-10-10T06:00:00Z",
    "end_time": "2026-10-10T07:00:00Z",
    "hour_label": "06:00 - 07:00",
    "suitability_score": 88,
    "suitability_label": "OPTIMAL",
    "forecast_temp_c": 22.5,
    "forecast_rh_percent": 62.0,
    "forecast_wind_kmh": 6.0,
    "forecast_precipitation_mmh": 0.0,
    "rationale": "High suitability for targeted coarse dust suppression. Mild temperatures and low wind ensure long surface dampness.",
    "safety_concerns": []
  },
  "windows": [...],
  "forecasting_disclaimer": "Forecast evaluated using meteorological suitability. Future ambient pollutant concentrations are not synthetically projected."
}
```

### 2.4 Multi-Scenario Strategy Comparison
`GET /api/analytics/strategy-comparison?days=7&tanker_liters=5000`

**Response Example:**
```json
{
  "number_of_zones": 12,
  "reporting_period_days": 7,
  "tanker_capacity_liters": 5000.0,
  "scenarios": [
    {
      "strategy_id": "fixed_schedule",
      "strategy_name": "Fixed Scheduled Spraying (Status Quo)",
      "water_used_liters": 1260000.0,
      "water_saved_vs_baseline_liters": 0.0,
      "water_saved_percent": 0.0,
      "total_trips": 252,
      "estimated_cost_inr": 189000.0,
      "cost_savings_inr": 0.0,
      "intervention_frequency": "3 runs / zone / day",
      "suitability_notes": "High water waste; sprays indiscriminately into rain, smoke, and fine soot."
    },
    {
      "strategy_id": "clearsky_targeted",
      "strategy_name": "ClearSky Precision Atmospheric Targeting",
      "water_used_liters": 240000.0,
      "water_saved_vs_baseline_liters": 1020000.0,
      "water_saved_percent": 80.9,
      "total_trips": 48,
      "estimated_cost_inr": 36000.0,
      "cost_savings_inr": 153000.0,
      "intervention_frequency": "Dynamic, coarse dust & weather gated",
      "suitability_notes": "Optimal water efficiency. Suppresses interventions during smoke, high humidity, or high wind."
    }
  ],
  "methodology_summary": "ClearSky Targeted reduces water usage by 80.9% and saves ₹153,000 across 12 sectors over 7 days.",
  "audit_notes": "Modeled estimates assuming non-potable STP treated water at ₹150 per kL."
}
```

### 2.5 Field Intervention Logging & Outcome Framework
`POST /api/interventions`

**Request Body:**
```json
{
  "zone_id": "DEL-AV-01",
  "road_segment_id": "DEL-AV-01-SEG-01",
  "intervention_type": "WATER_MISTING_CANON",
  "water_volume_liters": 5000.0,
  "treated_length_km": 2.2,
  "notes": "Targeted wetting of Anand Vihar unpaved shoulder."
}
```

**Response:**
```json
{
  "intervention_id": "INT-20261009123000-DEL-AV-01",
  "zone_id": "DEL-AV-01",
  "road_segment_id": "DEL-AV-01-SEG-01",
  "intervention_type": "WATER_MISTING_CANON",
  "water_volume_liters": 5000.0,
  "treated_length_km": 2.2,
  "timestamp": "2026-10-09T12:30:00Z",
  "weather_conditions": { "temperature_c": 28.0, "relative_humidity": 46.0, "wind_speed_kmh": 8.0 },
  "notes": "Targeted wetting of Anand Vihar unpaved shoulder."
}
```

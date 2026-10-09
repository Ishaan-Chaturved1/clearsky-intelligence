export type DecisionType =
  | 'INTERVENTION_RECOMMENDED'
  | 'TARGETED_INTERVENTION_RECOMMENDED'
  | 'INTERVENTION_NOT_RECOMMENDED'
  | 'INTERVENTION_DISCOURAGED'
  | 'ADVISORY_ONLY'
  | 'ALTERNATIVE_DUST_CONTROL_SUGGESTED';

export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export type DataMode = 'LIVE' | 'CACHED' | 'DEMO';

export interface NearbyInfrastructure {
  major_roads: string[];
  construction_sites: string[];
  has_construction_nearby: boolean;
  construction_distance_meters?: number | null;
}

export interface Zone {
  zone_id: string;
  name: string;
  latitude: number;
  longitude: number;
  description: string;
  zone_type: string;
  nearby_infrastructure: NearbyInfrastructure;
}

export interface PollutantValue {
  value: number | null;
  unit: string;
  data_type: 'observed' | 'modeled' | 'interpolated' | 'unavailable';
  station_id?: string | null;
  station_distance_km?: number | null;
}

export interface WeatherConditions {
  temperature_c?: number | null;
  relative_humidity?: number | null;
  surface_pressure_hpa?: number | null;
  pressure_trend_3h_hpa?: number | null;
  pressure_trend_6h_hpa?: number | null;
  pressure_trend_12h_hpa?: number | null;
  pressure_tendency?: string | null;
  wind_speed_kmh?: number | null;
  wind_direction_deg?: number | null;
  precipitation_mmh?: number | null;
  evaporation_rate_mmh?: number | null;
  estimated_surface_drying_time_min?: number | null;
  boundary_layer_height_m?: number | null;
  data_type?: string;
}

export interface FireSummary {
  nearby_fires_count: number;
  closest_fire_distance_km?: number | null;
  possible_smoke_transport: boolean;
  details?: Array<{
    latitude: number;
    longitude: number;
    distance_km: number;
    bearing_deg: number;
    is_upwind_smoke_path: boolean;
    brightness: string;
  }>;
}

export interface EnvironmentalReading {
  reading_id: string;
  zone_id: string;
  timestamp: string;
  pm25: PollutantValue;
  pm10: PollutantValue;
  pm_ratio?: number | null;
  weather: WeatherConditions;
  fire_summary: FireSummary;
  data_mode: DataMode;
  is_stale: boolean;
}

export interface DecisionRecord {
  decision_id: string;
  zone_id: string;
  decision: DecisionType;
  priority?: number | null;
  confidence: ConfidenceLevel;
  pollutants: {
    pm25: PollutantValue;
    pm10: PollutantValue;
  };
  weather: WeatherConditions;
  reasons: string[];
  warnings: string[];
  triggered_rules?: string[];
  conditions_to_change?: string[];
  source_status: Record<string, string>;
  data_mode: DataMode;
  observed_at: string;
  scored_at: string;
  station_distance_km?: number | null;
  data_freshness_seconds?: number | null;
}

export interface ZoneWithLatest {
  zone: Zone;
  latest_reading?: EnvironmentalReading | null;
  latest_decision?: DecisionRecord | null;
}

export interface SystemOverview {
  total_monitored_zones: number;
  intervention_candidates: number;
  intervention_discouraged: number;
  advisory_only_zones: number;
  estimated_water_saved_liters: number;
  intervention_reduction_percent: number;
  last_data_refresh: string;
  data_mode: DataMode;
  sources_coverage: Record<string, string>;
}

export interface DailyTrendItem {
  date: string;
  label: string;
  baseline_ops: number;
  recommended_ops: number;
  avoided_ops: number;
  water_saved_liters: number;
  baseline_water_liters: number;
  actual_water_liters: number;
}

export interface WaterSavingsAnalytics {
  reporting_period_days: number;
  number_of_zones: number;
  baseline_interventions_per_zone_per_day: number;
  assumed_liters_per_intervention: number;
  baseline_interventions: number;
  recommended_interventions: number;
  avoided_interventions: number;
  baseline_water_liters: number;
  recommended_water_liters: number;
  estimated_water_saved_liters: number;
  intervention_reduction_percent: number;
  daily_trend: DailyTrendItem[];
  is_simulation: boolean;
  data_source_mode: DataMode;
  assumptions_note: string;
}

export interface StrategyComparisonScenario {
  strategy_id: string;
  strategy_name: string;
  water_used_liters: number;
  water_saved_vs_baseline_liters: number;
  water_saved_percent: number;
  total_trips: number;
  estimated_cost_inr: number;
  cost_savings_inr: number;
  intervention_frequency: string;
  suitability_notes: string;
}

export interface StrategyComparisonResponse {
  number_of_zones: number;
  reporting_period_days: number;
  tanker_capacity_liters: number;
  scenarios: StrategyComparisonScenario[];
  methodology_summary: string;
  audit_notes: string;
}

export interface CandidateRoadSegment {
  segment_id: string;
  zone_id: string;
  road_name: string;
  road_classification: string;
  length_km: number;
  estimated_width_m: number;
  surface_area_m2: number;
  traffic_index: string;
  construction_adjacent: boolean;
  construction_distance_m?: number | null;
  water_required_liters: number;
  tanker_trips_required: number;
  priority_score: number;
  recommended_action: string;
  estimated_cost_inr: number;
}

export interface CandidateRoadSegmentsResponse {
  zone_id: string;
  zone_name: string;
  total_segments: number;
  total_water_required_liters: number;
  total_tanker_trips: number;
  segments: CandidateRoadSegment[];
}

export interface ForecastWindow {
  window_id: string;
  start_time: string;
  end_time: string;
  hour_label: string;
  suitability_score: number;
  suitability_label: string;
  forecast_temp_c: number;
  forecast_rh_percent: number;
  forecast_wind_kmh: number;
  forecast_precipitation_mmh: number;
  forecast_pressure_hpa?: number | null;
  rationale: string;
  safety_concerns: string[];
}

export interface ForecastWindowsResponse {
  zone_id: string;
  zone_name: string;
  forecast_source: string;
  optimal_windows_count: number;
  best_window?: ForecastWindow | null;
  windows: ForecastWindow[];
  forecasting_disclaimer: string;
}

export interface AtmosphericAnalysis {
  zone_id: string;
  zone_name: string;
  latitude: number;
  longitude: number;
  timestamp: string;
  aqi_estimate: number;
  aqi_standard: string;
  pm10_value: number | null;
  pm25_value: number | null;
  pm_ratio: number | null;
  pm_ratio_interpretation: string;
  temperature_c: number | null;
  relative_humidity: number | null;
  surface_pressure_hpa: number | null;
  pressure_trend_3h_hpa: number | null;
  pressure_trend_6h_hpa: number | null;
  pressure_trend_12h_hpa: number | null;
  pressure_tendency: string;
  pressure_interpretation: string;
  wind_speed_kmh: number | null;
  wind_direction_deg: number | null;
  wind_drift_risk: string;
  precipitation_mmh: number;
  rain_suppression_active: boolean;
  evaporation_rate_mmh: number | null;
  estimated_surface_drying_time_min: number | null;
  boundary_layer_height_m: number | null;
  inversion_detected: boolean;
  contributing_stations_count: number;
  nearest_station_distance_km: number | null;
  spatial_coverage_rating: string;
  data_freshness_seconds: number;
  decision: string;
  decision_rationale: string[];
  triggered_rules: string[];
  conditions_to_change_decision: string[];
}

export interface SourceDetail {
  source_name: string;
  status: string;
  last_successful_retrieval?: string | null;
  last_error?: string | null;
  available_variables: string[];
  data_classification: string;
  coverage_limitations: string;
}

export interface SourcesStatus {
  system_health: string;
  data_mode: DataMode;
  last_checked_at: string;
  sources: SourceDetail[];
}

export interface MethodologyRule {
  rule_id: string;
  name: string;
  rationale: string;
  threshold: string;
  decision_impact: string;
  scientific_limitation: string;
}

export interface MethodologyResponse {
  title: string;
  version: string;
  core_premise: string;
  rules: MethodologyRule[];
  confidence_calculation: string;
  system_limitations: string[];
}

export interface AlertRecord {
  alert_id: string;
  zone_id: string;
  zone_name: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  alert_type: string;
  message: string;
  decision: DecisionType;
  priority?: number | null;
  created_at: string;
}

export interface AiDailyBrief {
  generated_at: string;
  headline: string;
  summary_text: string;
  high_priority_zones: string[];
  cautions_and_disclaimers: string[];
  provider: string;
}

export type ViolationCategory =
  | 'UNCOVERED_CONSTRUCTION'
  | 'ILLEGAL_DEMOLITION'
  | 'INDUSTRIAL_EMISSION'
  | 'OPEN_WASTE_BURNING'
  | 'UNPAVED_ROAD_DUST';

export type ReportStatus =
  | 'PENDING_AUDIT'
  | 'VERIFIED_VIOLATION'
  | 'ACTION_DISPATCHED'
  | 'RESOLVED'
  | 'REJECTED';

export interface CitizenReport {
  report_id: string;
  created_at: string;
  category: ViolationCategory;
  category_label: string;
  zone_id?: string | null;
  zone_name?: string | null;
  latitude: number;
  longitude: number;
  location_address: string;
  description: string;
  photo_url?: string | null;
  has_voice_note: boolean;
  voice_note_transcript?: string | null;
  reporter_name: string;
  reporter_contact: string;
  channel: 'WEB' | 'WHATSAPP' | 'TELEGRAM' | 'EMAIL';
  status: ReportStatus;
  points_awarded: number;
  evidence_correlation?: string | null;
  verification_notes?: string | null;
}

export interface RewardItem {
  item_id: string;
  title: string;
  category: string;
  points_cost: number;
  description: string;
  sponsor: string;
  in_stock: boolean;
  badge_label?: string | null;
}

export interface CitizenWallet {
  reporter_contact: string;
  reporter_name: string;
  total_points: number;
  lifetime_points: number;
  verified_reports_count: number;
  reports: CitizenReport[];
  redeemed_vouchers: Array<{
    redemption_id: string;
    contact: string;
    item_id: string;
    voucher_code: string;
    redeemed_at: string;
    points_spent: number;
  }>;
}

export interface CitizenReportCreateInput {
  category: string;
  zone_id?: string;
  latitude: number;
  longitude: number;
  location_address: string;
  description: string;
  photo_url?: string;
  has_voice_note?: boolean;
  voice_note_transcript?: string;
  reporter_name?: string;
  reporter_contact?: string;
  channel?: string;
}

export interface InterventionOutcomeRecord {
  intervention_id: string;
  zone_id: string;
  zone_name?: string | null;
  road_segment_id?: string | null;
  timestamp_start: string;
  timestamp_end: string;
  water_volume_liters: number;
  tanker_capacity_liters: number;
  method: string;
  pre_intervention_pm10: number;
  post_intervention_pm10_1h?: number | null;
  post_intervention_pm10_3h?: number | null;
  control_zone_pm10?: number | null;
  observed_delta_pm10?: number | null;
  weather_at_intervention: WeatherConditions;
  status: string;
  notes?: string | null;
}

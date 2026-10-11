import {
  SystemOverview,
  ZoneWithLatest,
  DecisionRecord,
  WaterSavingsAnalytics,
  SourcesStatus,
  MethodologyResponse,
  AiDailyBrief,
  AlertRecord,
  CitizenReport,
  RewardItem,
  CitizenWallet,
  CitizenReportCreateInput,
  AtmosphericAnalysis,
  CandidateRoadSegmentsResponse,
  ForecastWindowsResponse,
  StrategyComparisonResponse,
  InterventionOutcomeRecord,
  GeocodingPlace,
  StationObservation,
  LocationAnalysisResponse,
  InvestigationDossier,
  InvestigationAnalyzeParams,
  LocalSourceInvestigationResult,
  TransportAssessment,
  SatelliteFireCorrelationResult,
  DataHealthSummary,
  SourceVerificationResult,
  DataSourceMetadata
} from '../types';

const rawBase = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim();
const API_BASE = rawBase ? `${rawBase.replace(/\/+$/, '')}/api` : '/api';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const errObj = await res.json();
      if (errObj.detail) errorDetail = errObj.detail;
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

export const api = {
  getHealth: () => fetchJson<{ status: string; app: string; version: string }>(`${API_BASE}/health`),
  
  getOverview: () => fetchJson<SystemOverview>(`${API_BASE}/overview`),
  
  getZones: () => fetchJson<ZoneWithLatest[]>(`${API_BASE}/zones`),

  searchGeo: (query: string, limit = 6) =>
    fetchJson<GeocodingPlace[]>(`${API_BASE}/geo/search?q=${encodeURIComponent(query)}&limit=${limit}`),

  reverseGeo: (lat: number, lon: number) =>
    fetchJson<GeocodingPlace>(`${API_BASE}/geo/reverse?lat=${lat}&lon=${lon}`),

  getStations: (lat = 28.6139, lon = 77.2090, radiusKm = 35) =>
    fetchJson<StationObservation[]>(`${API_BASE}/stations?lat=${lat}&lon=${lon}&radius_km=${radiusKm}`),

  analyzeLocation: (lat: number, lon: number, name?: string) =>
    fetchJson<LocationAnalysisResponse>(
      `${API_BASE}/locations/analyze?lat=${lat}&lon=${lon}${name ? `&name=${encodeURIComponent(name)}` : ''}`
    ),
  
  getZone: (zoneId: string) => fetchJson<ZoneWithLatest>(`${API_BASE}/zones/${zoneId}`),
  
  getZoneHistory: (zoneId: string, limit = 50) =>
    fetchJson<{ zone_id: string; readings: any[]; decisions: DecisionRecord[] }>(
      `${API_BASE}/zones/${zoneId}/history?limit=${limit}`
    ),

  getZoneAtmosphericAnalysis: (zoneId: string) =>
    fetchJson<AtmosphericAnalysis>(`${API_BASE}/zones/${zoneId}/atmospheric-analysis`),

  getZoneCandidateSegments: (zoneId: string) =>
    fetchJson<CandidateRoadSegmentsResponse>(`${API_BASE}/zones/${zoneId}/candidate-segments`),

  getZoneForecastWindows: (zoneId: string) =>
    fetchJson<ForecastWindowsResponse>(`${API_BASE}/zones/${zoneId}/forecast-windows`),

  getStrategyComparison: (days = 7, tankerLiters = 5000.0) =>
    fetchJson<StrategyComparisonResponse>(`${API_BASE}/analytics/strategy-comparison?days=${days}&tanker_liters=${tankerLiters}`),

  getInterventions: (zoneId?: string) =>
    fetchJson<InterventionOutcomeRecord[]>(`${API_BASE}/interventions${zoneId ? `?zone_id=${zoneId}` : ''}`),

  logIntervention: (data: any) =>
    fetchJson<InterventionOutcomeRecord>(`${API_BASE}/interventions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }),

  getInterventionEffectiveness: () =>
    fetchJson<any>(`${API_BASE}/interventions/effectiveness-summary`),
  
  getLatestDecisions: () => fetchJson<DecisionRecord[]>(`${API_BASE}/decisions/latest`),
  
  getWaterSavings: (days = 7, baselineRate?: number, litersPerOp?: number) => {
    const params = new URLSearchParams({ days: days.toString() });
    if (baselineRate !== undefined) params.append('baseline_rate', baselineRate.toString());
    if (litersPerOp !== undefined) params.append('liters_per_op', litersPerOp.toString());
    return fetchJson<WaterSavingsAnalytics>(`${API_BASE}/analytics/water-savings?${params.toString()}`);
  },

  getWaterSavingsExportUrl: (days = 7, baselineRate?: number, litersPerOp?: number) => {
    const params = new URLSearchParams({ days: days.toString() });
    if (baselineRate !== undefined) params.append('baseline_rate', baselineRate.toString());
    if (litersPerOp !== undefined) params.append('liters_per_op', litersPerOp.toString());
    return `${API_BASE}/analytics/water-savings/export?${params.toString()}`;
  },
  
  getSourcesStatus: () => fetchJson<SourcesStatus>(`${API_BASE}/sources/status`),
  
  getMethodology: () => fetchJson<MethodologyResponse>(`${API_BASE}/methodology`),
  
  getDailyBrief: () => fetchJson<AiDailyBrief>(`${API_BASE}/brief/daily`),
  
  getAlerts: (limit = 20) => fetchJson<AlertRecord[]>(`${API_BASE}/alerts?limit=${limit}`),
  
  adminRefresh: (adminKey?: string, forceMock = false) =>
    fetchJson<{ success: boolean; message: string; refreshed_zones_count: number; data_mode: string }>(
      `${API_BASE}/admin/refresh`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ admin_key: adminKey, force_mock: forceMock })
      }
    ),

  // Citizen Reporting Loop & Eco-Rewards
  getCitizenReports: (limit = 50) =>
    fetchJson<CitizenReport[]>(`${API_BASE}/reports?limit=${limit}`),

  submitCitizenReport: (data: CitizenReportCreateInput) =>
    fetchJson<CitizenReport>(`${API_BASE}/reports`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }),

  verifyCitizenReport: (reportId: string, status: string, points = 100, notes?: string) =>
    fetchJson<CitizenReport>(`${API_BASE}/reports/${reportId}/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        status,
        points_to_award: points,
        verification_notes: notes
      })
    }),

  getRewardsCatalog: () =>
    fetchJson<RewardItem[]>(`${API_BASE}/rewards/catalog`),

  getCitizenWallet: (contact = '+91 98112 43210') =>
    fetchJson<CitizenWallet>(`${API_BASE}/rewards/wallet?contact=${encodeURIComponent(contact)}`),

  redeemRewardItem: (contact: string, itemId: string) =>
    fetchJson<{
      success: boolean;
      voucher_code: string;
      item_title: string;
      points_spent: number;
      remaining_points: number;
      instructions: string;
    }>(`${API_BASE}/rewards/redeem`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        reporter_contact: contact,
        item_id: itemId
      })
    }),

  // Stage 3 Investigation Endpoints
  getInvestigationLocalSources: (lat: number, lon: number, radiusKm = 3.0) =>
    fetchJson<LocalSourceInvestigationResult>(
      `${API_BASE}/investigation/local-sources?latitude=${lat}&longitude=${lon}&radius_km=${radiusKm}`
    ),

  getInvestigationTransport: (lat: number, lon: number, lookbackHours = 12, referenceTime?: string) =>
    fetchJson<TransportAssessment>(
      `${API_BASE}/investigation/transport?latitude=${lat}&longitude=${lon}&lookback_hours=${lookbackHours}${referenceTime ? `&reference_time=${encodeURIComponent(referenceTime)}` : ''}`
    ),

  getInvestigationFires: (lat: number, lon: number, radiusKm = 50.0) =>
    fetchJson<SatelliteFireCorrelationResult>(
      `${API_BASE}/investigation/satellite-fires?latitude=${lat}&longitude=${lon}&radius_km=${radiusKm}`
    ),

  analyzeInvestigation: (params: InvestigationAnalyzeParams) =>
    fetchJson<InvestigationDossier>(`${API_BASE}/investigation/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    }),

  getInvestigationDossier: (investigationId: string) =>
    fetchJson<InvestigationDossier>(`${API_BASE}/investigation/dossiers/${investigationId}`),

  getInvestigationDossiers: () =>
    fetchJson<Array<{
      investigation_id: string;
      target_scope: string;
      target_latitude: number;
      target_longitude: number;
      pollutants: string[];
      supporting_evidence_count: number;
      contradicting_evidence_count: number;
      confidence_assessment: string;
      generated_at: string;
    }>>(`${API_BASE}/investigation/dossiers`),

  getDataHealth: () => fetchJson<DataHealthSummary>(`${API_BASE}/data-health`),

  getDataHealthSources: () => fetchJson<DataSourceMetadata[]>(`${API_BASE}/data-health/sources`),

  getSourceHealthDetail: (sourceId: string) =>
    fetchJson<SourceVerificationResult>(`${API_BASE}/data-health/sources/${encodeURIComponent(sourceId)}`),

  runLiveCheck: (sourceId?: string) =>
    fetchJson<DataHealthSummary | SourceVerificationResult>(
      `${API_BASE}/data-health/check${sourceId ? `?source_id=${encodeURIComponent(sourceId)}` : ''}`,
      { method: 'POST' }
    ),

  runStoredDataAudit: () =>
    fetchJson<DataHealthSummary>(`${API_BASE}/data-health/audit`, { method: 'POST' })
};

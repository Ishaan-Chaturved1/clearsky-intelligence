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
  InterventionOutcomeRecord
} from '../types';

const API_BASE = '/api';

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
    })
};

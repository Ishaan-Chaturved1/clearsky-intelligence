import {
  SystemOverview,
  ZoneWithLatest,
  DecisionRecord,
  WaterSavingsAnalytics,
  SourcesStatus,
  MethodologyResponse,
  AiDailyBrief,
  AlertRecord
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
    )
};

import { DecisionType, ConfidenceLevel, DataMode } from '../types';

export function formatNumber(num: number | null | undefined, decimals = 1): string {
  if (num === null || num === undefined || isNaN(num)) return '—';
  return num.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
}

export function formatInteger(num: number | null | undefined): string {
  if (num === null || num === undefined || isNaN(num)) return '—';
  return Math.round(num).toLocaleString('en-US');
}

export function formatDateTime(isoString: string | null | undefined): string {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  } catch {
    return isoString;
  }
}

export function formatCoordinates(lat: number, lon: number): string {
  const latDir = lat >= 0 ? 'N' : 'S';
  const lonDir = lon >= 0 ? 'E' : 'W';
  return `${Math.abs(lat).toFixed(4)}° ${latDir}, ${Math.abs(lon).toFixed(4)}° ${lonDir}`;
}

export function getDecisionBadgeInfo(decision?: DecisionType | null): {
  label: string;
  shortLabel: string;
  bgClass: string;
  textClass: string;
  borderClass: string;
  dotColor: string;
} {
  switch (decision) {
    case 'INTERVENTION_RECOMMENDED':
      return {
        label: 'Intervention Recommended',
        shortLabel: 'Recommended',
        bgClass: 'bg-emerald-950/40',
        textClass: 'text-emerald-400',
        borderClass: 'border-emerald-500/40',
        dotColor: '#10B981'
      };
    case 'INTERVENTION_NOT_RECOMMENDED':
      return {
        label: 'Intervention Discouraged',
        shortLabel: 'Discouraged',
        bgClass: 'bg-rose-950/40',
        textClass: 'text-rose-400',
        borderClass: 'border-rose-500/40',
        dotColor: '#EF4444'
      };
    case 'ADVISORY_ONLY':
    default:
      return {
        label: 'Advisory Only (Uncertain)',
        shortLabel: 'Advisory Only',
        bgClass: 'bg-slate-800/50',
        textClass: 'text-slate-300',
        borderClass: 'border-slate-600/40',
        dotColor: '#94A3B8'
      };
  }
}

export function getConfidenceBadgeInfo(confidence?: ConfidenceLevel | null): {
  label: string;
  badgeClass: string;
} {
  switch (confidence) {
    case 'HIGH':
      return { label: 'High Confidence', badgeClass: 'bg-emerald-900/30 text-emerald-400 border-emerald-500/30' };
    case 'MEDIUM':
      return { label: 'Medium Confidence', badgeClass: 'bg-amber-900/30 text-amber-400 border-amber-500/30' };
    case 'LOW':
    default:
      return { label: 'Low Confidence', badgeClass: 'bg-slate-800 text-slate-400 border-slate-700' };
  }
}

export function getDataModeBadge(dataMode?: DataMode | null): {
  label: string;
  badgeClass: string;
  tooltip: string;
} {
  switch (dataMode) {
    case 'LIVE':
      return {
        label: 'LIVE DATA',
        badgeClass: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
        tooltip: 'Real-time observation from active stations & numerical forecast models.'
      };
    case 'CACHED':
      return {
        label: 'CACHED DATA',
        badgeClass: 'bg-sky-500/10 text-sky-400 border-sky-500/30',
        tooltip: 'Preserved latest valid environmental readings within caching TTL.'
      };
    case 'DEMO':
    default:
      return {
        label: 'DEMO DATA',
        badgeClass: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
        tooltip: 'Simulated demonstration scenarios for evaluating decision rules.'
      };
  }
}

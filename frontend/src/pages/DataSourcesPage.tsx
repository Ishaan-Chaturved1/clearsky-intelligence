import React, { useState, useEffect } from 'react';
import {
  Database,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  RefreshCw,
  Radio,
  Clock,
  XCircle,
  AlertOctagon,
  FileSearch,
  Activity,
  Layers,
  Info,
  CheckCircle,
  HelpCircle,
  ExternalLink,
  Zap,
  HardDrive
} from 'lucide-react';
import { api } from '../services/api';
import {
  DataHealthSummary,
  SourceVerificationResult,
  VerificationStatus,
  DataSourceMetadata
} from '../types';
import { formatDateTime } from '../utils/formatters';

export const DataSourcesPage: React.FC = () => {
  const [healthSummary, setHealthSummary] = useState<DataHealthSummary | null>(null);
  const [sourcesMetadata, setSourcesMetadata] = useState<DataSourceMetadata[]>([]);
  const [selectedSource, setSelectedSource] = useState<SourceVerificationResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCheckingLive, setIsCheckingLive] = useState(false);
  const [isAuditingStored, setIsAuditingStored] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('table');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const loadDataHealth = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [health, meta] = await Promise.all([
        api.getDataHealth(),
        api.getDataHealthSources()
      ]);
      setHealthSummary(health);
      setSourcesMetadata(meta);
    } catch (err: any) {
      console.error('Failed to load data health:', err);
      setErrorMessage(err.message || 'Unable to connect to data health endpoint');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunLiveCheck = async (sourceId?: string) => {
    setIsCheckingLive(true);
    setErrorMessage(null);
    try {
      const res = await api.runLiveCheck(sourceId);
      if (sourceId) {
        // Updated single source
        const updatedSource = res as SourceVerificationResult;
        setSelectedSource(updatedSource);
        // Refresh full summary
        const refreshed = await api.getDataHealth();
        setHealthSummary(refreshed);
      } else {
        setHealthSummary(res as DataHealthSummary);
      }
    } catch (err: any) {
      console.error('Live check failed:', err);
      setErrorMessage(err.message || 'Live operational check failed');
    } finally {
      setIsCheckingLive(false);
    }
  };

  const handleRunStoredAudit = async () => {
    setIsAuditingStored(true);
    setErrorMessage(null);
    try {
      const res = await api.runStoredDataAudit();
      setHealthSummary(res);
    } catch (err: any) {
      console.error('Stored dataset audit failed:', err);
      setErrorMessage(err.message || 'Stored dataset audit failed');
    } finally {
      setIsAuditingStored(false);
    }
  };

  useEffect(() => {
    loadDataHealth();
  }, []);

  const getStatusBadge = (status: VerificationStatus) => {
    switch (status) {
      case 'HEALTHY':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-300">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            HEALTHY
          </span>
        );
      case 'DEGRADED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-amber-50 text-amber-700 border border-amber-300">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
            DEGRADED
          </span>
        );
      case 'STALE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-yellow-50 text-yellow-800 border border-yellow-300">
            <Clock className="w-3.5 h-3.5 text-yellow-600" />
            STALE
          </span>
        );
      case 'EMPTY':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-sky-50 text-sky-700 border border-sky-300">
            <Info className="w-3.5 h-3.5 text-sky-600" />
            EMPTY
          </span>
        );
      case 'MISCONFIGURED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-orange-50 text-orange-700 border border-orange-300">
            <AlertOctagon className="w-3.5 h-3.5 text-orange-600" />
            MISCONFIGURED
          </span>
        );
      case 'UNAVAILABLE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-red-50 text-red-700 border border-red-300">
            <XCircle className="w-3.5 h-3.5 text-red-600" />
            UNAVAILABLE
          </span>
        );
      case 'RATE_LIMITED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-purple-50 text-purple-700 border border-purple-300">
            <Zap className="w-3.5 h-3.5 text-purple-600" />
            RATE_LIMITED
          </span>
        );
      case 'ERROR':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-rose-50 text-rose-700 border border-rose-300">
            <XCircle className="w-3.5 h-3.5 text-rose-600" />
            ERROR
          </span>
        );
      case 'NOT_CHECKED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-slate-100 text-slate-700 border border-slate-300">
            <HelpCircle className="w-3.5 h-3.5 text-slate-500" />
            NOT_CHECKED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-warm-100 text-earth-700 border border-warm-300">
            {status}
          </span>
        );
    }
  };

  const getProvenanceBadge = (prov: string) => {
    let colorClass = 'bg-warm-100 text-earth-700 border-warm-300';
    if (prov.includes('GROUND') || prov.includes('STATION')) {
      colorClass = 'bg-emerald-50 text-emerald-800 border-emerald-200';
    } else if (prov.includes('MODELED')) {
      colorClass = 'bg-blue-50 text-blue-800 border-blue-200';
    } else if (prov.includes('SATELLITE')) {
      colorClass = 'bg-indigo-50 text-indigo-800 border-indigo-200';
    } else if (prov.includes('LOCAL') || prov.includes('PERSISTENT')) {
      colorClass = 'bg-amber-50 text-amber-800 border-amber-200';
    }
    return (
      <span className={`text-[10px] font-mono px-2 py-0.5 rounded border uppercase font-medium ${colorClass}`}>
        {prov}
      </span>
    );
  };

  const filteredResults = healthSummary?.results.filter((r) => {
    if (statusFilter === 'ALL') return true;
    return r.status === statusFilter;
  }) || [];

  return (
    <div className="w-full space-y-8 animate-fade-up">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-warm-200 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="font-mono text-xs px-2.5 py-0.5 rounded-full bg-sage-500/10 text-sage-600 border border-sage-500/20 font-semibold">
              Stage 5 Verification Gateway
            </span>
            <span className="text-xs font-clarendon text-earth-500">Live Health &amp; Dataset Integrity</span>
          </div>
          <h1 className="font-sentinel font-bold text-3xl text-earth-900 tracking-tight">
            Data Fetch Verification &amp; Ingestion Health
          </h1>
          <p className="text-sm font-clarendon text-earth-600 mt-1 max-w-3xl">
            Deterministic monitoring of environmental data sources across Delhi NCR. Validates connectivity, schema compliance,
            freshness thresholds, completeness bounds, and provenance classification.
          </p>
        </div>

        {/* Verification Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={() => handleRunLiveCheck()}
            disabled={isCheckingLive || isAuditingStored}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-sans font-semibold text-white bg-earth-800 hover:bg-earth-900 shadow-warm-sm transition-all disabled:opacity-50"
            title="Execute live operational check pinging all providers with bounded timeouts"
          >
            <Zap className={`w-3.5 h-3.5 ${isCheckingLive ? 'animate-spin text-amber-400' : 'text-amber-300'}`} />
            <span>{isCheckingLive ? 'Running Live Check...' : 'Run Live Check'}</span>
          </button>

          <button
            onClick={handleRunStoredAudit}
            disabled={isCheckingLive || isAuditingStored}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-sans font-semibold text-earth-800 hover:text-earth-900 bg-white hover:bg-warm-100 border border-warm-300 shadow-warm-sm transition-all disabled:opacity-50"
            title="Audit stored SQLite records, JSON files, cache, and S3 Data Lake offline"
          >
            <HardDrive className={`w-3.5 h-3.5 ${isAuditingStored ? 'animate-spin text-sage-600' : 'text-earth-500'}`} />
            <span>{isAuditingStored ? 'Auditing Stored Data...' : 'Stored Data Audit'}</span>
          </button>

          <button
            onClick={loadDataHealth}
            disabled={isLoading || isCheckingLive || isAuditingStored}
            className="p-2.5 rounded-xl text-earth-600 hover:text-earth-900 bg-white hover:bg-warm-100 border border-warm-300 shadow-warm-sm transition-all disabled:opacity-50"
            title="Refresh current verification status"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-accent-500' : ''}`} />
          </button>
        </div>
      </div>

      {/* Error alert if backend unreachable */}
      {errorMessage && (
        <div className="bg-red-50 border border-red-300 rounded-2xl p-4 flex items-start gap-3 text-red-800">
          <XCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <p className="font-bold">Data Health Verification Error</p>
            <p>{errorMessage}</p>
          </div>
        </div>
      )}

      {/* OVERALL HEALTH BANNER */}
      {healthSummary && (
        <div className="bg-white rounded-2xl p-6 border border-warm-200 shadow-warm-sm space-y-5">
          <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 border-b border-warm-200 pb-5">
            <div className="flex items-center gap-4">
              <div className={`w-12 h-12 rounded-2xl flex items-center justify-center border ${
                healthSummary.overall_status === 'HEALTHY'
                  ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20'
                  : healthSummary.overall_status === 'DEGRADED'
                  ? 'bg-amber-500/10 text-amber-600 border-amber-500/20'
                  : 'bg-rose-500/10 text-rose-600 border-rose-500/20'
              }`}>
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-3">
                  <h2 className="font-sentinel font-bold text-earth-900 text-xl">
                    System Verification Overview
                  </h2>
                  {getStatusBadge(healthSummary.overall_status)}
                </div>
                <p className="text-xs font-clarendon text-earth-600 mt-1">
                  Verification Mode: <span className="font-mono font-semibold">{healthSummary.verification_mode}</span>
                  {' '}• Total Registered: <span className="font-mono font-semibold">{healthSummary.total_registered_sources}</span> sources
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4 text-xs font-mono text-earth-600 bg-warm-100 px-4 py-2 rounded-xl border border-warm-200">
              <Clock className="w-4 h-4 text-earth-400" />
              <span>
                Most Recent Fetch:{' '}
                {healthSummary.most_recent_successful_fetch
                  ? formatDateTime(healthSummary.most_recent_successful_fetch)
                  : 'None Recorded'}
              </span>
            </div>
          </div>

          {/* Metric Counters Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
            <div className="bg-warm-50 p-3 rounded-xl border border-warm-200 text-center">
              <span className="text-[11px] font-sans text-earth-500 block">Healthy</span>
              <span className="font-mono text-lg font-bold text-emerald-700">{healthSummary.healthy_count}</span>
            </div>
            <div className="bg-warm-50 p-3 rounded-xl border border-warm-200 text-center">
              <span className="text-[11px] font-sans text-earth-500 block">Degraded</span>
              <span className="font-mono text-lg font-bold text-amber-700">{healthSummary.degraded_count}</span>
            </div>
            <div className="bg-warm-50 p-3 rounded-xl border border-warm-200 text-center">
              <span className="text-[11px] font-sans text-earth-500 block">Stale</span>
              <span className="font-mono text-lg font-bold text-yellow-700">{healthSummary.stale_count}</span>
            </div>
            <div className="bg-warm-50 p-3 rounded-xl border border-warm-200 text-center">
              <span className="text-[11px] font-sans text-earth-500 block">Empty</span>
              <span className="font-mono text-lg font-bold text-sky-700">{healthSummary.empty_count}</span>
            </div>
            <div className="bg-warm-50 p-3 rounded-xl border border-warm-200 text-center">
              <span className="text-[11px] font-sans text-earth-500 block">Misconfigured</span>
              <span className="font-mono text-lg font-bold text-orange-700">{healthSummary.misconfigured_count}</span>
            </div>
            <div className="bg-warm-50 p-3 rounded-xl border border-warm-200 text-center">
              <span className="text-[11px] font-sans text-earth-500 block">Unavailable</span>
              <span className="font-mono text-lg font-bold text-rose-700">{healthSummary.unavailable_count}</span>
            </div>
            <div className="bg-warm-50 p-3 rounded-xl border border-warm-200 text-center">
              <span className="text-[11px] font-sans text-earth-500 block">Errors</span>
              <span className="font-mono text-lg font-bold text-red-700">{healthSummary.error_count}</span>
            </div>
            <div className="bg-warm-50 p-3 rounded-xl border border-warm-200 text-center">
              <span className="text-[11px] font-sans text-earth-500 block">Not Checked</span>
              <span className="font-mono text-lg font-bold text-slate-600">{healthSummary.not_checked_count}</span>
            </div>
          </div>

          {/* Recommended Actions */}
          {healthSummary.recommended_actions.length > 0 && (
            <div className="bg-amber-50/70 border border-amber-200/80 rounded-xl p-4 text-xs">
              <span className="font-sans font-bold text-amber-900 block mb-1.5 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                Operational Action Recommendations:
              </span>
              <ul className="list-disc list-inside space-y-1 text-amber-800 font-clarendon">
                {healthSummary.recommended_actions.map((act, idx) => (
                  <li key={idx}>{act}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* FILTER & VIEW TOGGLES */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-sans font-semibold text-earth-500 mr-1">Filter by Status:</span>
          {['ALL', 'HEALTHY', 'DEGRADED', 'STALE', 'EMPTY', 'MISCONFIGURED', 'UNAVAILABLE', 'ERROR', 'NOT_CHECKED'].map(
            (st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-2.5 py-1 rounded-lg text-xs font-mono transition-all ${
                  statusFilter === st
                    ? 'bg-earth-800 text-white font-bold'
                    : 'bg-white text-earth-600 border border-warm-200 hover:bg-warm-100'
                }`}
              >
                {st}
              </button>
            )
          )}
        </div>

        <div className="flex items-center gap-1 bg-warm-100 p-1 rounded-xl border border-warm-200">
          <button
            onClick={() => setViewMode('table')}
            className={`px-3 py-1 rounded-lg text-xs font-sans font-medium transition-all ${
              viewMode === 'table' ? 'bg-white text-earth-900 shadow-warm-xs font-bold' : 'text-earth-600'
            }`}
          >
            Table View
          </button>
          <button
            onClick={() => setViewMode('grid')}
            className={`px-3 py-1 rounded-lg text-xs font-sans font-medium transition-all ${
              viewMode === 'grid' ? 'bg-white text-earth-900 shadow-warm-xs font-bold' : 'text-earth-600'
            }`}
          >
            Card Grid
          </button>
        </div>
      </div>

      {/* SOURCE STATUS TABLE / GRID */}
      {viewMode === 'table' ? (
        <div className="bg-white rounded-2xl border border-warm-200 shadow-warm-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-warm-50/80 border-b border-warm-200 text-earth-700 text-[11px] font-mono uppercase tracking-wider">
                  <th className="py-3 px-4">Data Source</th>
                  <th className="py-3 px-3">Category</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3">Provenance</th>
                  <th className="py-3 px-3">Last Fetch</th>
                  <th className="py-3 px-3">Latest Obs</th>
                  <th className="py-3 px-3 text-right">Records</th>
                  <th className="py-3 px-3 text-right">Quality</th>
                  <th className="py-3 px-4 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-warm-100 text-xs">
                {filteredResults.map((src) => (
                  <tr key={src.source_id} className="hover:bg-warm-50/60 transition-colors">
                    <td className="py-3.5 px-4 font-sans font-semibold text-earth-900">
                      <div>
                        <span>{src.source_name}</span>
                        <span className="block font-mono text-[10px] text-earth-400 font-normal">
                          {src.source_id}
                        </span>
                      </div>
                    </td>
                    <td className="py-3.5 px-3">
                      <span className="text-[11px] font-mono text-earth-600 bg-warm-100 px-2 py-0.5 rounded">
                        {src.geographic_coverage || 'Regional'}
                      </span>
                    </td>
                    <td className="py-3.5 px-3">{getStatusBadge(src.status)}</td>
                    <td className="py-3.5 px-3">{getProvenanceBadge(src.provenance)}</td>
                    <td className="py-3.5 px-3 font-mono text-[11px] text-earth-600">
                      {src.last_successful_fetch_at ? formatDateTime(src.last_successful_fetch_at) : '—'}
                    </td>
                    <td className="py-3.5 px-3 font-mono text-[11px] text-earth-600">
                      {src.latest_observation_at ? formatDateTime(src.latest_observation_at) : '—'}
                    </td>
                    <td className="py-3.5 px-3 text-right font-mono text-[11px] text-earth-800">
                      {src.records_valid} / {src.records_received}
                    </td>
                    <td className="py-3.5 px-3 text-right font-mono text-[11px]">
                      {src.data_quality_score != null ? (
                        <span className={src.data_quality_score >= 80 ? 'text-emerald-700 font-bold' : 'text-amber-700 font-bold'}>
                          {src.data_quality_score}%
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <button
                        onClick={() => setSelectedSource(src)}
                        className="px-3 py-1 rounded-lg text-xs font-sans font-semibold text-earth-800 bg-warm-100 hover:bg-warm-200 border border-warm-300 transition-all"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {filteredResults.map((src) => (
            <div
              key={src.source_id}
              className="bg-white rounded-2xl p-6 border border-warm-200 shadow-warm-sm space-y-4 flex flex-col justify-between hover:shadow-warm transition-all"
            >
              <div>
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div>
                    <h3 className="font-sentinel font-bold text-lg text-earth-900">
                      {src.source_name}
                    </h3>
                    <div className="flex items-center gap-2 mt-1.5">
                      <span className="text-[10px] font-mono text-earth-500 font-normal">
                        {src.source_id}
                      </span>
                      {getProvenanceBadge(src.provenance)}
                    </div>
                  </div>
                  <div>{getStatusBadge(src.status)}</div>
                </div>

                {/* Metrics */}
                <div className="grid grid-cols-2 gap-2 mt-4 pt-3 border-t border-warm-100 text-xs font-mono">
                  <div>
                    <span className="text-[10px] text-earth-400 font-sans block">Latency</span>
                    <span>{src.response_time_ms ? `${src.response_time_ms.toFixed(0)} ms` : '—'}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-earth-400 font-sans block">Valid Records</span>
                    <span>{src.records_valid} / {src.records_received}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-earth-400 font-sans block">Latest Observation</span>
                    <span className="truncate block">
                      {src.latest_observation_at ? formatDateTime(src.latest_observation_at) : '—'}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-earth-400 font-sans block">Quality Score</span>
                    <span>{src.data_quality_score !== null ? `${src.data_quality_score}%` : '—'}</span>
                  </div>
                </div>

                {/* Errors or Warnings */}
                {src.errors.length > 0 && (
                  <div className="mt-3 p-2.5 rounded-lg bg-red-50 border border-red-200 text-[11px] text-red-700">
                    <span className="font-bold block">Sanitized Error:</span>
                    <p className="truncate">{src.errors[0]}</p>
                  </div>
                )}
              </div>

              <div className="pt-3 border-t border-warm-200 flex items-center justify-between">
                <span className="text-[11px] text-earth-500 font-mono">
                  Checked: {formatDateTime(src.checked_at)}
                </span>
                <button
                  onClick={() => setSelectedSource(src)}
                  className="px-3 py-1 rounded-lg text-xs font-sans font-semibold text-earth-800 bg-warm-100 hover:bg-warm-200 border border-warm-300 transition-all"
                >
                  Inspect Details
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* INSPECTION MODAL */}
      {selectedSource && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-earth-950/40 backdrop-blur-sm animate-fade-in">
          <div className="bg-white rounded-2xl max-w-2xl w-full border border-warm-300 shadow-warm-lg p-6 space-y-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between border-b border-warm-200 pb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-xs px-2 py-0.5 rounded bg-warm-100 text-earth-600">
                    {selectedSource.source_id}
                  </span>
                  {getStatusBadge(selectedSource.status)}
                  {getProvenanceBadge(selectedSource.provenance)}
                </div>
                <h3 className="font-sentinel font-bold text-2xl text-earth-900">
                  {selectedSource.source_name}
                </h3>
              </div>
              <button
                onClick={() => setSelectedSource(null)}
                className="p-1.5 rounded-lg text-earth-400 hover:text-earth-700 hover:bg-warm-100 transition-all"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            {/* Diagnostic Specs */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="bg-warm-50 p-3 rounded-xl border border-warm-200">
                <span className="text-[10px] text-earth-500 font-sans block">Response Latency</span>
                <span className="font-mono font-bold text-earth-900">
                  {selectedSource.response_time_ms ? `${selectedSource.response_time_ms.toFixed(1)} ms` : '—'}
                </span>
              </div>
              <div className="bg-warm-50 p-3 rounded-xl border border-warm-200">
                <span className="text-[10px] text-earth-500 font-sans block">HTTP Status</span>
                <span className="font-mono font-bold text-earth-900">
                  {selectedSource.http_status || 'N/A'}
                </span>
              </div>
              <div className="bg-warm-50 p-3 rounded-xl border border-warm-200">
                <span className="text-[10px] text-earth-500 font-sans block">Valid / Received</span>
                <span className="font-mono font-bold text-earth-900">
                  {selectedSource.records_valid} / {selectedSource.records_received}
                </span>
              </div>
              <div className="bg-warm-50 p-3 rounded-xl border border-warm-200">
                <span className="text-[10px] text-earth-500 font-sans block">Quality Score</span>
                <span className="font-mono font-bold text-earth-900">
                  {selectedSource.data_quality_score !== null ? `${selectedSource.data_quality_score}%` : '—'}
                </span>
              </div>
            </div>

            {/* Temporal & Freshness Metrics */}
            <div className="bg-warm-50 p-4 rounded-xl border border-warm-200 space-y-2 text-xs font-mono">
              <div className="flex justify-between">
                <span className="text-earth-500">Last Attempt:</span>
                <span className="text-earth-800">{formatDateTime(selectedSource.last_attempt_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-earth-500">Last Successful Fetch:</span>
                <span className="text-earth-800">
                  {selectedSource.last_successful_fetch_at ? formatDateTime(selectedSource.last_successful_fetch_at) : 'None'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-earth-500">Latest Observation:</span>
                <span className="text-earth-800">
                  {selectedSource.latest_observation_at ? formatDateTime(selectedSource.latest_observation_at) : 'None'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-earth-500">Freshness Threshold:</span>
                <span className="text-earth-800">{(selectedSource.freshness_threshold_seconds / 3600).toFixed(1)} hours</span>
              </div>
            </div>

            {/* Expected vs Missing Fields */}
            <div className="space-y-2 text-xs">
              <span className="font-sans font-bold text-earth-800 block">Expected Schema Fields:</span>
              <div className="flex flex-wrap gap-1.5">
                {selectedSource.expected_fields.map((f, i) => (
                  <span
                    key={i}
                    className={`font-mono text-[11px] px-2 py-0.5 rounded border ${
                      selectedSource.missing_fields.includes(f)
                        ? 'bg-rose-50 text-rose-700 border-rose-300 line-through'
                        : 'bg-warm-100 text-earth-700 border-warm-200'
                    }`}
                  >
                    {f}
                  </span>
                ))}
              </div>
              {selectedSource.missing_fields.length > 0 && (
                <p className="text-rose-600 text-[11px] font-sans">
                  Missing Fields: {selectedSource.missing_fields.join(', ')}
                </p>
              )}
            </div>

            {/* Sanitized Errors & Warnings */}
            {selectedSource.errors.length > 0 && (
              <div className="bg-rose-50 border border-rose-200 rounded-xl p-3 text-xs text-rose-800 space-y-1">
                <span className="font-bold block flex items-center gap-1.5">
                  <XCircle className="w-3.5 h-3.5 text-rose-600" />
                  Sanitized Error Log:
                </span>
                {selectedSource.errors.map((e, i) => (
                  <p key={i} className="font-mono text-[11px]">{e}</p>
                ))}
              </div>
            )}

            {selectedSource.warnings.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-xs text-amber-800 space-y-1">
                <span className="font-bold block flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                  Warnings &amp; Integrity Alerts:
                </span>
                {selectedSource.warnings.map((w, i) => (
                  <p key={i} className="font-clarendon text-[11px]">{w}</p>
                ))}
              </div>
            )}

            {/* Known Limitations */}
            {selectedSource.limitations.length > 0 && (
              <div className="border-t border-warm-200 pt-3 text-xs font-clarendon text-earth-600 space-y-1">
                <span className="font-sans font-bold text-earth-700 block">Scientific &amp; Technical Limitations:</span>
                <ul className="list-disc list-inside space-y-0.5">
                  {selectedSource.limitations.map((lim, i) => (
                    <li key={i}>{lim}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Modal Actions */}
            <div className="border-t border-warm-200 pt-4 flex items-center justify-between">
              <button
                onClick={() => handleRunLiveCheck(selectedSource.source_id)}
                disabled={isCheckingLive}
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-sans font-semibold text-white bg-earth-800 hover:bg-earth-900 transition-all disabled:opacity-50"
              >
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                <span>Re-Check This Source</span>
              </button>

              <button
                onClick={() => setSelectedSource(null)}
                className="px-4 py-2 rounded-xl text-xs font-sans font-semibold text-earth-700 bg-warm-100 hover:bg-warm-200 transition-all"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

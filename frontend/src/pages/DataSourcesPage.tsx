import React, { useState, useEffect } from 'react';
import { Database, CheckCircle2, AlertTriangle, ShieldCheck, RefreshCw, Radio, Clock } from 'lucide-react';
import { api } from '../services/api';
import { SourcesStatus, SourceDetail } from '../types';
import { formatDateTime } from '../utils/formatters';

export const DataSourcesPage: React.FC = () => {
  const [statusData, setStatusData] = useState<SourcesStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadStatus = () => {
    setIsLoading(true);
    api.getSourcesStatus()
      .then((data) => setStatusData(data))
      .catch((err) => console.error(err))
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    loadStatus();
  }, []);

  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-fade-up">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-warm-200 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="font-mono text-xs px-2.5 py-0.5 rounded-full bg-sage-500/10 text-sage-600 border border-sage-500/20 font-semibold">
              Telemetry Ingestion Gateway
            </span>
            <span className="text-xs font-clarendon text-earth-500">Open Data Integration Layer</span>
          </div>
          <h1 className="font-sentinel font-bold text-3xl text-earth-900 tracking-tight">
            Data Sources &amp; Telemetry Status
          </h1>
          <p className="text-sm font-clarendon text-earth-600 mt-1 max-w-2xl">
            Live connection telemetry, scientific classification (Observed vs Modeled), and spatial coverage resolution across Delhi NCR.
          </p>
        </div>

        <button
          onClick={loadStatus}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-sans font-semibold text-earth-800 hover:text-earth-900 bg-white hover:bg-warm-100 border border-warm-300 shadow-warm-sm transition-all disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-accent-500' : 'text-earth-500'}`} />
          <span>Ping Sources</span>
        </button>
      </div>

      {/* System Health Summary Banner */}
      <div className="bg-white rounded-2xl p-6 border border-warm-200 shadow-warm-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-sage-500/10 border border-sage-500/20 flex items-center justify-center text-sage-600">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <span className="font-sentinel font-bold text-earth-900 text-lg">
                Operational Ingestion Pipeline
              </span>
              <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-sage-500/10 text-sage-700 border border-sage-500/20 font-semibold">
                {statusData?.system_health || 'OPTIMAL'}
              </span>
            </div>
            <p className="text-xs font-clarendon text-earth-500 mt-1">
              EventBridge cron scheduled for 30-minute automated polling intervals.
            </p>
          </div>
        </div>

        <div className="text-xs font-mono text-earth-500 flex items-center gap-2 bg-warm-100 px-3.5 py-1.5 rounded-xl border border-warm-200">
          <Clock className="w-3.5 h-3.5 text-earth-400" />
          <span>Last Audited: {formatDateTime(statusData?.last_checked_at)}</span>
        </div>
      </div>

      {/* Sources Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {statusData?.sources.map((src, idx) => (
          <div
            key={idx}
            className="bg-white rounded-2xl p-6 border border-warm-200 shadow-warm-sm space-y-4 flex flex-col justify-between hover:shadow-warm transition-all"
          >
            <div>
              <div className="flex items-start justify-between gap-3 mb-2">
                <div>
                  <h3 className="font-sentinel font-bold text-lg text-earth-900">
                    {src.source_name}
                  </h3>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-lg bg-warm-100 text-earth-600 border border-warm-300">
                      {src.data_classification}
                    </span>
                    <span className={`text-[10px] font-mono uppercase font-bold px-2 py-0.5 rounded-lg border ${
                      src.status === 'HEALTHY'
                        ? 'bg-sage-50 text-sage-700 border-sage-200'
                        : 'bg-amber-50 text-amber-700 border-amber-200'
                    }`}>
                      {src.status}
                    </span>
                  </div>
                </div>

                <div className={`p-2 rounded-xl ${src.status === 'HEALTHY' ? 'bg-sage-50 text-sage-600' : 'bg-amber-50 text-amber-600'}`}>
                  <Radio className="w-4 h-4 animate-pulse" />
                </div>
              </div>

              {/* Variables */}
              <div className="mt-4">
                <span className="text-[11px] font-sans font-semibold text-earth-500 block mb-2">
                  Provided Environmental Variables:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {src.available_variables.map((v, vIdx) => (
                    <span
                      key={vIdx}
                      className="text-[11px] font-mono px-2.5 py-0.5 rounded-lg bg-warm-100 border border-warm-200 text-earth-700"
                    >
                      {v}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Coverage Limits */}
            <div className="pt-4 border-t border-warm-200 text-xs">
              <span className="text-[11px] font-sans font-semibold text-earth-500 block mb-1">
                Coverage Constraints &amp; Resolution:
              </span>
              <p className="font-clarendon text-[11px] text-earth-600 leading-relaxed">
                {src.coverage_limitations}
              </p>
            </div>
          </div>
        ))}
      </div>

    </div>
  );
};

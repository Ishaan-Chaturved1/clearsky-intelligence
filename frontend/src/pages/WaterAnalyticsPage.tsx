import React, { useState, useEffect } from 'react';
import {
  Droplets,
  TrendingDown,
  Download,
  Sliders,
  Calendar,
  AlertCircle,
  FileSpreadsheet,
  CheckCircle2,
  BarChart2
} from 'lucide-react';
import { KpiCard } from '../components/KpiCard';
import { WaterAnalyticsChart } from '../components/WaterAnalyticsChart';
import { AssumptionModal } from '../components/AssumptionModal';
import { api } from '../services/api';
import { WaterSavingsAnalytics, StrategyComparisonResponse, StrategyComparisonScenario } from '../types';
import { formatNumber, formatInteger } from '../utils/formatters';

export const WaterAnalyticsPage: React.FC = () => {
  const [analytics, setAnalytics] = useState<WaterSavingsAnalytics | null>(null);
  const [strategyComparison, setStrategyComparison] = useState<StrategyComparisonResponse | null>(null);
  const [days, setDays] = useState(7);
  const [baselineRate, setBaselineRate] = useState(3.0);
  const [litersPerOp, setLitersPerOp] = useState(5000.0);
  const [isLoading, setIsLoading] = useState(true);
  const [isAssumptionModalOpen, setIsAssumptionModalOpen] = useState(false);

  const loadData = async () => {
    try {
      setIsLoading(true);
      const [data, strat] = await Promise.all([
        api.getWaterSavings(days, baselineRate, litersPerOp),
        api.getStrategyComparison(days, litersPerOp).catch(() => null)
      ]);
      setAnalytics(data);
      if (strat) setStrategyComparison(strat);
    } catch (err) {
      console.error('Failed to load water savings analytics:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [days, baselineRate, litersPerOp]);

  const handleApplyAssumptions = (newRate: number, newLiters: number) => {
    setBaselineRate(newRate);
    setLitersPerOp(newLiters);
  };

  const handleDownloadCsv = () => {
    const url = api.getWaterSavingsExportUrl(days, baselineRate, litersPerOp);
    window.open(url, '_blank');
  };

  return (
    <div className="space-y-8 animate-fade-up">
      
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-warm-200 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-sans text-[11px] font-semibold px-2 py-0.5 rounded-full bg-sage-500/10 text-sage-600 border border-sage-500/20">
              Audited Conservation Engine
            </span>
            <span className="text-xs text-earth-500 font-clarendon">Delhi NCR Municipal Baseline</span>
          </div>
          <h1 className="font-sentinel font-bold text-3xl text-earth-900 tracking-tight">
            Water Efficiency Analytics
          </h1>
          <p className="text-sm font-clarendon text-earth-600 mt-1 max-w-2xl">
            Comparing targeted particulate interventions against indiscriminate fixed-schedule municipal spraying across monitored sectors.
          </p>
        </div>

        {/* Action Controls: Period + Assumptions + Export */}
        <div className="flex flex-wrap items-center gap-2.5">
          
          {/* Period selector */}
          <div className="flex items-center bg-white border border-warm-300 rounded-xl p-1 shadow-warm-sm text-xs font-sans">
            {[3, 7, 14, 30].map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`px-3 py-1 rounded-lg font-medium transition-all ${
                  days === d
                    ? 'bg-accent-500 text-white font-semibold shadow-warm-sm'
                    : 'text-earth-500 hover:text-earth-800'
                }`}
              >
                {d}d
              </button>
            ))}
          </div>

          {/* Assumption button */}
          <button
            onClick={() => setIsAssumptionModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-sans font-medium text-earth-700 hover:text-earth-900 bg-white hover:bg-warm-100 border border-warm-300 shadow-warm-sm transition-all"
          >
            <Sliders className="w-3.5 h-3.5 text-accent-500" />
            <span>Assumptions</span>
          </button>

          {/* Export CSV button */}
          <button
            onClick={handleDownloadCsv}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-sans font-semibold text-white bg-accent-500 hover:bg-accent-600 shadow-warm hover:shadow-warm-lg transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>

        </div>
      </div>

      {/* KPI Cards Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <KpiCard
          title="Baseline Schedule"
          value={analytics ? `${analytics.baseline_interventions} runs` : '—'}
          subtitle={`${analytics?.number_of_zones || 12} zones × ${baselineRate} runs/day`}
          icon={Calendar}
          badge="Fixed Model"
        />

        <KpiCard
          title="Targeted Interventions"
          value={analytics ? `${analytics.recommended_interventions} runs` : '—'}
          subtitle="Evidence-based coarse dust"
          icon={BarChart2}
          badge="Triggered"
          badgeColor="rose"
        />

        <KpiCard
          title="Avoided Operations"
          value={analytics ? `${analytics.avoided_interventions} runs` : '—'}
          subtitle="Suppressed unneeded spraying"
          icon={TrendingDown}
          badge="Avoided"
          badgeColor="emerald"
        />

        <KpiCard
          title="Estimated Water Saved"
          value={
            analytics
              ? `${(analytics.estimated_water_saved_liters / 1000).toFixed(0)}k L`
              : '—'
          }
          subtitle={`Reduction: ${analytics?.intervention_reduction_percent || 0}%`}
          icon={Droplets}
          badge="Water Saved"
          badgeColor="emerald"
          accentBorder={true}
        />
      </div>

      {/* Main Chart Card */}
      <div className="bg-white rounded-2xl p-6 border border-warm-200 shadow-warm-sm space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 pb-3 border-b border-warm-200">
          <div>
            <h3 className="font-sentinel font-bold text-lg text-earth-900">
              Daily Operation Comparison &amp; Avoided Water Trajectory
            </h3>
            <p className="text-xs font-clarendon text-earth-500">
              Daily baseline operations (sand) vs recommended targeted operations (bright coral) and water volume saved (sage)
            </p>
          </div>

          <div className="text-xs font-mono text-earth-500 bg-warm-100 px-3 py-1 rounded-xl border border-warm-200">
            Assumed tank volume: <span className="text-accent-600 font-semibold">{formatInteger(litersPerOp)} L/run</span>
          </div>
        </div>

        {analytics && (
          <WaterAnalyticsChart
            data={analytics.daily_trend}
            litersPerOp={analytics.assumed_liters_per_intervention}
          />
        )}
      </div>

      {/* 4-Scenario Strategy Comparison Matrix */}
      {strategyComparison && (
        <div className="bg-white rounded-2xl border border-warm-200 shadow-warm-sm overflow-hidden space-y-4 p-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 pb-4 border-b border-warm-200">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="font-sans text-[11px] font-semibold px-2 py-0.5 rounded-full bg-accent-500/10 text-accent-600 border border-accent-500/20">
                  Multimodal Operational Models
                </span>
                <span className="text-xs text-earth-500 font-clarendon">
                  {strategyComparison.reporting_period_days}-Day Strategic Evaluation ({strategyComparison.number_of_zones} Sectors)
                </span>
              </div>
              <h3 className="font-sentinel font-bold text-lg text-earth-900">
                Comparative Intervention Strategies Matrix
              </h3>
              <p className="text-xs font-clarendon text-earth-500">
                Evaluating Scheduled spraying vs AQI-threshold spraying vs ClearSky targeted intelligence vs Alternative dust control.
              </p>
            </div>
            <div className="text-xs font-mono text-earth-600 bg-warm-100 px-3 py-1.5 rounded-xl border border-warm-200">
              Tanker: {formatInteger(strategyComparison.tanker_capacity_liters)} L
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-warm-100/70 text-earth-600 font-sans font-semibold uppercase text-[10px] tracking-wider border-b border-warm-200">
                <tr>
                  <th className="py-3 px-4">Strategy</th>
                  <th className="py-3 px-3 text-right">Frequency / Policy</th>
                  <th className="py-3 px-3 text-right">Water Used</th>
                  <th className="py-3 px-3 text-right">Water Saved</th>
                  <th className="py-3 px-3 text-right">Tanker Trips</th>
                  <th className="py-3 px-3 text-right">Est. Cost (₹)</th>
                  <th className="py-3 px-3 text-right">Cost Saved (₹)</th>
                  <th className="py-3 px-4">Suitability / Risk Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-warm-200">
                {strategyComparison.scenarios.map((sc: StrategyComparisonScenario, i: number) => {
                  const isClearSky = sc.strategy_id.includes('clearsky') || sc.strategy_name.includes('ClearSky');
                  return (
                    <tr
                      key={i}
                      className={`hover:bg-warm-50 transition-colors ${
                        isClearSky ? 'bg-sage-50/60 font-semibold' : ''
                      }`}
                    >
                      <td className="py-3.5 px-4">
                        <div className="font-sentinel text-earth-900 font-bold flex items-center gap-1.5">
                          {sc.strategy_name}
                          {isClearSky && (
                            <span className="text-[9px] font-sans font-bold bg-sage-500 text-white px-1.5 py-0.5 rounded">
                              RECOMMENDED
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3.5 px-3 text-right font-clarendon text-earth-700">
                        {sc.intervention_frequency}
                      </td>
                      <td className="py-3.5 px-3 text-right font-mono font-tabular text-earth-800">
                        {formatInteger(sc.water_used_liters)} L
                      </td>
                      <td className={`py-3.5 px-3 text-right font-mono font-tabular ${
                        sc.water_saved_vs_baseline_liters > 0 ? 'text-sage-600 font-bold' : 'text-earth-400'
                      }`}>
                        {sc.water_saved_vs_baseline_liters > 0 ? `+${formatInteger(sc.water_saved_vs_baseline_liters)} L` : '0 L'}
                      </td>
                      <td className="py-3.5 px-3 text-right font-mono font-tabular text-earth-700">
                        {sc.total_trips} trips
                      </td>
                      <td className="py-3.5 px-3 text-right font-mono font-tabular text-earth-800">
                        ₹{formatInteger(sc.estimated_cost_inr)}
                      </td>
                      <td className={`py-3.5 px-3 text-right font-mono font-tabular ${
                        sc.cost_savings_inr > 0 ? 'text-sage-600 font-bold' : 'text-earth-400'
                      }`}>
                        {sc.cost_savings_inr > 0 ? `₹${formatInteger(sc.cost_savings_inr)}` : '₹0'}
                      </td>
                      <td className="py-3.5 px-4 font-clarendon text-[11px] text-earth-600 max-w-[260px]">
                        {sc.suitability_notes}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="p-4 bg-warm-100/70 rounded-xl border border-warm-200 text-xs font-clarendon text-earth-600 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <strong className="text-earth-800 font-sentinel">Audit Summary: </strong>
              {strategyComparison.methodology_summary}
            </div>
            <div className="text-[10px] text-earth-400 italic font-mono flex-shrink-0">
              {strategyComparison.audit_notes}
            </div>
          </div>
        </div>
      )}

      {/* Assumptions & Formula Callout */}
      <div className="bg-warm-100/70 rounded-2xl p-5 border border-warm-300/80 text-xs text-earth-700">
        <div className="flex items-center gap-2 mb-2 font-semibold text-earth-900">
          <AlertCircle className="w-4 h-4 text-accent-500" />
          <span className="font-sentinel font-bold text-sm">Baseline Audit Formula &amp; Scientific Restraint</span>
        </div>
        <p className="font-clarendon text-earth-600 leading-relaxed text-xs mb-3">
          {analytics?.assumptions_note}
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono bg-white p-3.5 rounded-xl border border-warm-200 text-earth-600">
          <div>
            <strong className="text-earth-900">Baseline Operations:</strong> zones × baseline_per_zone_per_day × days
          </div>
          <div>
            <strong className="text-earth-900">Estimated Water Saved:</strong> max(0, baseline_water - recommended_water)
          </div>
        </div>
      </div>

      {/* Detailed Daily Table */}
      <div className="bg-white rounded-2xl border border-warm-200 shadow-warm-sm overflow-hidden">
        <div className="p-5 border-b border-warm-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="w-4 h-4 text-earth-400" />
            <h4 className="font-sentinel font-bold text-base text-earth-900">
              Daily Interval Audit Ledger
            </h4>
          </div>

          <button
            onClick={handleDownloadCsv}
            className="text-xs font-sans font-semibold text-accent-600 hover:text-accent-700 flex items-center gap-1 transition-colors"
          >
            <span>Download CSV</span>
            <Download className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-warm-100/70 text-earth-600 font-sans font-semibold uppercase text-[10px] tracking-wider border-b border-warm-200">
              <tr>
                <th className="py-3 px-5">Date</th>
                <th className="py-3 px-4 text-right">Baseline Runs</th>
                <th className="py-3 px-4 text-right">Recommended Runs</th>
                <th className="py-3 px-4 text-right">Avoided Runs</th>
                <th className="py-3 px-4 text-right">Baseline Water</th>
                <th className="py-3 px-4 text-right">Targeted Water</th>
                <th className="py-3 px-5 text-right">Estimated Water Saved</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-warm-200 font-mono text-[11px]">
              {analytics?.daily_trend.map((row) => (
                <tr key={row.date} className="hover:bg-warm-50/80 transition-colors">
                  <td className="py-3 px-5 text-earth-800 font-clarendon font-medium">{row.label} ({row.date})</td>
                  <td className="py-3 px-4 text-right text-earth-500 font-tabular">{row.baseline_ops}</td>
                  <td className="py-3 px-4 text-right text-accent-600 font-bold font-tabular">{row.recommended_ops}</td>
                  <td className="py-3 px-4 text-right text-sage-600 font-bold font-tabular">{row.avoided_ops}</td>
                  <td className="py-3 px-4 text-right text-earth-500 font-tabular">{formatInteger(row.baseline_water_liters)} L</td>
                  <td className="py-3 px-4 text-right text-earth-700 font-tabular">{formatInteger(row.actual_water_liters)} L</td>
                  <td className="py-3 px-5 text-right text-sage-600 font-bold font-tabular">{formatInteger(row.water_saved_liters)} L</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Assumption Modal */}
      <AssumptionModal
        isOpen={isAssumptionModalOpen}
        onClose={() => setIsAssumptionModalOpen(false)}
        currentBaselineRate={baselineRate}
        currentLitersPerOp={litersPerOp}
        onApply={handleApplyAssumptions}
      />

    </div>
  );
};

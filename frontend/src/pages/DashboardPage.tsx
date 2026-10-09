import React, { useState, useEffect } from 'react';
import {
  Layers,
  CheckCircle2,
  AlertOctagon,
  HelpCircle,
  Droplets,
  TrendingDown,
  Clock,
  Radio,
  ArrowRight,
  Sliders,
} from 'lucide-react';
import { KpiCard } from '../components/KpiCard';
import { ZoneMap } from '../components/ZoneMap';
import { ZoneCard } from '../components/ZoneCard';
import { ZoneDetailDrawer } from '../components/ZoneDetailDrawer';
import { DailyBriefBanner } from '../components/DailyBriefBanner';
import { AlertsFeed } from '../components/AlertsFeed';
import { AssumptionModal } from '../components/AssumptionModal';
import { api } from '../services/api';
import {
  SystemOverview,
  ZoneWithLatest,
  WaterSavingsAnalytics,
  AiDailyBrief,
  AlertRecord,
  DecisionType
} from '../types';
import { formatInteger, formatDateTime } from '../utils/formatters';
import { Link } from 'react-router-dom';

export const DashboardPage: React.FC = () => {
  const [overview, setOverview] = useState<SystemOverview | null>(null);
  const [zones, setZones] = useState<ZoneWithLatest[]>([]);
  const [waterData, setWaterData] = useState<WaterSavingsAnalytics | null>(null);
  const [dailyBrief, setDailyBrief] = useState<AiDailyBrief | null>(null);
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  
  const [selectedZone, setSelectedZone] = useState<ZoneWithLatest | null>(null);
  const [activeFilter, setActiveFilter] = useState<'ALL' | DecisionType>('ALL');
  const [isLoading, setIsLoading] = useState(true);
  const [isAssumptionModalOpen, setIsAssumptionModalOpen] = useState(false);

  // Assumptions state
  const [baselineRate, setBaselineRate] = useState(3.0);
  const [litersPerOp, setLitersPerOp] = useState(5000.0);

  const loadData = async () => {
    try {
      setIsLoading(true);
      const [ov, zn, wt, br, al] = await Promise.all([
        api.getOverview().catch(() => null),
        api.getZones().catch(() => []),
        api.getWaterSavings(7, baselineRate, litersPerOp).catch(() => null),
        api.getDailyBrief().catch(() => null),
        api.getAlerts(10).catch(() => [])
      ]);

      if (ov) setOverview(ov);
      setZones(zn || []);
      if (wt) setWaterData(wt);
      if (br) setDailyBrief(br);
      setAlerts(al || []);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [baselineRate, litersPerOp]);

  // Filtered zones
  const filteredZones = zones.filter((item) => {
    if (activeFilter === 'ALL') return true;
    const dec = item.latest_decision?.decision;
    if (activeFilter === 'INTERVENTION_RECOMMENDED') {
      return dec === 'INTERVENTION_RECOMMENDED' || dec === 'TARGETED_INTERVENTION_RECOMMENDED';
    }
    if (activeFilter === 'INTERVENTION_NOT_RECOMMENDED' || activeFilter === 'INTERVENTION_DISCOURAGED') {
      return dec === 'INTERVENTION_DISCOURAGED' || dec === 'INTERVENTION_NOT_RECOMMENDED';
    }
    return dec === activeFilter;
  });

  const handleApplyAssumptions = (newRate: number, newLiters: number) => {
    setBaselineRate(newRate);
    setLitersPerOp(newLiters);
  };

  const handleAlertSelectZone = (zoneId: string) => {
    const target = zones.find((z) => z.zone.zone_id === zoneId);
    if (target) setSelectedZone(target);
  };

  return (
    <div className="space-y-6 animate-fade-up">
      
      {/* Page Title */}
      <div>
        <h1 className="font-sentinel font-bold text-3xl text-earth-900 tracking-tight">Command Center</h1>
        <p className="text-sm font-clarendon text-earth-600 mt-1">Real-time environmental monitoring &amp; targeted particulate suppression</p>
      </div>

      {/* KPI Cards — compact 4-column grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
        <KpiCard
          title="Zones"
          value={overview?.total_monitored_zones || zones.length || '—'}
          subtitle="Delhi NCR sectors"
          icon={Layers}
          badge="Active"
        />
        <KpiCard
          title="Candidates"
          value={overview?.intervention_candidates ?? '—'}
          subtitle="Coarse dust dominant"
          icon={CheckCircle2}
          badge="Priority"
          badgeColor="emerald"
          accentBorder={true}
        />
        <KpiCard
          title="Discouraged"
          value={overview?.intervention_discouraged ?? '—'}
          subtitle="Smoke / Humidity / Wind"
          icon={AlertOctagon}
          badge="Suppressed"
          badgeColor="rose"
        />
        <KpiCard
          title="Water Saved"
          value={
            waterData
              ? `${(waterData.estimated_water_saved_liters / 1000).toFixed(0)}k L`
              : '—'
          }
          subtitle={`vs ${baselineRate} runs/day`}
          icon={Droplets}
          badge="Model"
          badgeColor="sky"
        />
      </div>

      {/* Daily Brief */}
      <DailyBriefBanner brief={dailyBrief} />

      {/* Map & Zone Queue */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Map */}
        <div className="lg:col-span-8 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-sentinel font-bold text-lg text-earth-900">
              Regional Map
            </h2>
            <Link
              to="/map"
              className="text-xs font-sans font-semibold text-accent-500 hover:text-accent-600 flex items-center gap-1 transition-colors"
            >
              <span>Full Explorer</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
          <ZoneMap
            zones={zones}
            selectedZone={selectedZone}
            onSelectZone={setSelectedZone}
            height="480px"
          />
        </div>

        {/* Zone Priority Queue */}
        <div className="lg:col-span-4 flex flex-col h-[530px]">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-sentinel font-bold text-sm text-earth-900">
              Sector Queue
            </h3>
            {/* Filter Buttons */}
            <div className="flex items-center gap-1 bg-warm-100 p-0.5 rounded-xl border border-warm-200 text-[10px]">
              <button
                onClick={() => setActiveFilter('ALL')}
                className={`px-2 py-1 rounded-lg font-sans ${
                  activeFilter === 'ALL' ? 'bg-white text-earth-800 font-semibold shadow-warm-sm' : 'text-earth-400'
                }`}
              >
                All
              </button>
              <button
                onClick={() => setActiveFilter('INTERVENTION_RECOMMENDED')}
                className={`px-2 py-1 rounded-lg font-sans ${
                  activeFilter === 'INTERVENTION_RECOMMENDED' ? 'bg-sage-500/10 text-sage-700 font-semibold' : 'text-earth-400'
                }`}
                title="Recommended & Targeted"
              >
                Rec
              </button>
              <button
                onClick={() => setActiveFilter('INTERVENTION_NOT_RECOMMENDED')}
                className={`px-2 py-1 rounded-lg font-sans ${
                  activeFilter === 'INTERVENTION_NOT_RECOMMENDED' || activeFilter === 'INTERVENTION_DISCOURAGED' ? 'bg-accent-500/10 text-accent-700 font-semibold' : 'text-earth-400'
                }`}
                title="Discouraged"
              >
                Disc
              </button>
              <button
                onClick={() => setActiveFilter('ADVISORY_ONLY')}
                className={`px-2 py-1 rounded-lg font-sans ${
                  activeFilter === 'ADVISORY_ONLY' ? 'bg-warm-200 text-earth-800 font-semibold' : 'text-earth-400'
                }`}
                title="Advisory Only"
              >
                Adv
              </button>
              <button
                onClick={() => setActiveFilter('ALTERNATIVE_DUST_CONTROL_SUGGESTED')}
                className={`px-2 py-1 rounded-lg font-sans ${
                  activeFilter === 'ALTERNATIVE_DUST_CONTROL_SUGGESTED' ? 'bg-amber-500/10 text-amber-700 font-semibold' : 'text-earth-400'
                }`}
                title="Alternative Dust Control"
              >
                Alt
              </button>
            </div>
          </div>

          <p className="text-[11px] text-earth-400 mb-2">
            {filteredZones.length} of {zones.length} sectors
          </p>

          <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
            {filteredZones.map((item) => (
              <ZoneCard
                key={item.zone.zone_id}
                item={item}
                onSelect={setSelectedZone}
                isSelected={selectedZone?.zone.zone_id === item.zone.zone_id}
              />
            ))}
          </div>
        </div>

      </div>

      {/* Bottom: Alerts only (chart moved to dedicated page) */}
      <div className="bg-white rounded-2xl p-5 border border-warm-200 shadow-warm-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-sentinel font-bold text-base text-earth-900">
            Recent Alerts
          </h3>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-lg bg-warm-100 border border-warm-200 text-earth-400">
            Audit Trail
          </span>
        </div>
        <AlertsFeed alerts={alerts} onSelectZone={handleAlertSelectZone} />
      </div>

      {/* Zone Detail Drawer */}
      <ZoneDetailDrawer
        item={selectedZone}
        onClose={() => setSelectedZone(null)}
      />

      {/* Assumptions Configuration Modal */}
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

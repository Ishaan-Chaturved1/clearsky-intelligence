import React, { useState, useEffect } from 'react';
import {
  Search,
  Filter,
  Download,
  Plus,
  Layers,
  AlertTriangle,
  CheckCircle,
  HelpCircle,
  Calendar,
  MapPin,
  TrendingUp,
  Wind,
  Shield,
  Eye,
  Sliders,
  ChevronRight,
  Sparkles
} from 'lucide-react';
import { GlassCard } from '../components/GlassCard';
import { api } from '../services/api';
import { ZoneWithLatest } from '../types';

interface CandidateSource {
  id: string;
  title: string;
  type: string;
  locality: string;
  severity: 'High' | 'Medium' | 'Low';
  confidence: number; // percentage
  status: 'Active' | 'Investigating' | 'Mitigated';
  observedEvidence: string[];
  modeledEstimates: string[];
  hypotheses: string[];
  beforeImageLabel: string;
  afterImageLabel: string;
  recommendedAction: string;
  updatedAt: string;
}

export const InvestigationsPage: React.FC = () => {
  const [sources, setSources] = useState<CandidateSource[]>([
    {
      id: 'src-01',
      title: 'Sector 21 Arterial Road Resuspension',
      type: 'Unpaved Roadway / Heavy Transit',
      locality: 'Sector 21 & Dwarka Link',
      severity: 'High',
      confidence: 88,
      status: 'Active',
      observedEvidence: [
        'CPCB CAAQMS Station at Dwarka recorded PM10 spike to 384 µg/m³ at 09:30 AM',
        'Coarse-to-fine ratio (PM10/PM2.5) of 2.74 measured on ground sensor',
      ],
      modeledEstimates: [
        'WRF-Chem trajectory analysis shows 62% of dust plume localized to 450m road corridor',
        'Estimated mechanical resuspension rate of 12.4 kg/km-hr under current traffic velocity',
      ],
      hypotheses: [
        'Uncovered commercial dump trucks from nearby construction corridor depositing silt',
        'Overnight dew drying cycle accelerates mid-morning dry dust lift-off',
      ],
      beforeImageLabel: 'Baseline Dry Surface (08:00 AM)',
      afterImageLabel: 'Peak Dust Lift-Off (11:00 AM)',
      recommendedAction: 'Deploy targeted wet sweeping or low-volume polymer binder on 650m unpaved shoulders.',
      updatedAt: '25 mins ago',
    },
    {
      id: 'src-02',
      title: 'Anand Vihar Transit Terminal Silt Corridor',
      type: 'Industrial / Commercial Transport',
      locality: 'Anand Vihar ISBT & Railway Hub',
      severity: 'High',
      confidence: 92,
      status: 'Active',
      observedEvidence: [
        'Sentinel-5P tropospheric NO2 plume overlap and ground PM10 reading 412 µg/m³',
        'Traffic sensor count showing 1,420 heavy diesel vehicle movements per hour',
      ],
      modeledEstimates: [
        'Boundary layer height depressed to 320m, concentrating surface particulates',
        'Modeled dispersion indicates stagnation zone behind flyover embankment',
      ],
      hypotheses: [
        'Idling inter-state buses combined with unpaved turning loop dust accumulation',
      ],
      beforeImageLabel: 'Morning Clear Inversion',
      afterImageLabel: 'Concentrated Plume Trapping',
      recommendedAction: 'Restrict idling zones; apply immediate mechanical road washing during afternoon wind window.',
      updatedAt: '1 hour ago',
    },
    {
      id: 'src-03',
      title: 'Bawana Industrial Phase II Fugitive Emissions',
      type: 'Industrial Small-Scale Stacks',
      locality: 'Bawana Industrial Area',
      severity: 'Medium',
      confidence: 76,
      status: 'Investigating',
      observedEvidence: [
        'MODIS thermal anomaly detected at 28.79°N, 77.04°E (confidence 65%)',
        'Micro-sensor network reported PM2.5 elevation exceeding PM10 elevation',
      ],
      modeledEstimates: [
        'Plume dispersion model predicts downwind impact across 3.2km agricultural buffer',
      ],
      hypotheses: [
        'Fugitive waste combustion occurring outside permitted boiler operational hours',
      ],
      beforeImageLabel: 'Thermal Baseline',
      afterImageLabel: 'Detected Plume Signature',
      recommendedAction: 'Citizen Watch team dispatch for physical site verification and stack opacity inspection.',
      updatedAt: '3 hours ago',
    },
    {
      id: 'src-04',
      title: 'Okhla Waste Transfer Perimeter Siltation',
      type: 'Civic Infrastructure / Solid Waste',
      locality: 'Okhla Phase I Transfer Station',
      severity: 'Low',
      confidence: 68,
      status: 'Mitigated',
      observedEvidence: [
        'Vehicle wheel wash log indicates 94% compliance since 14:00 yesterday',
        'Local sensor PM10 decreased by 28% post perimeter misting',
      ],
      modeledEstimates: [
        'Remaining particulate levels attributable to regional background haze rather than local point source',
      ],
      hypotheses: [
        'Intermittent breeze from southeastern canal occasionally disturbs peripheral mounds',
      ],
      beforeImageLabel: 'Pre-Misting Baseline',
      afterImageLabel: 'Post-Misting Suppressed',
      recommendedAction: 'Maintain scheduled anti-smog gun perimeter passes; no additional emergency water spray needed.',
      updatedAt: '6 hours ago',
    },
  ]);

  const [selectedSource, setSelectedSource] = useState<CandidateSource>(sources[0]);
  const [sliderPos, setSliderPos] = useState(50);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newArea, setNewArea] = useState('');
  const [selectedTypes, setSelectedTypes] = useState<string[]>(['Road Dust']);

  return (
    <div className="space-y-6 animate-fade-up max-w-[1780px] mx-auto w-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Investigations
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-2xl">
            Explainable environmental source analysis. Observed sensor facts, modeled numerical estimates, and working hypotheses are strictly separated.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => alert('Investigation report generated and ready for export (PDF/JSON).')}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 shadow-xs transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Report</span>
          </button>
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-md transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>New Investigation</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        <GlassCard className="p-4">
          <div className="text-[11px] font-bold uppercase text-slate-400 tracking-wider">Candidate Sources</div>
          <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 mt-1 font-tabular">4</div>
          <div className="text-xs text-slate-500 mt-0.5">2 high priority active</div>
        </GlassCard>
        <GlassCard className="p-4">
          <div className="text-[11px] font-bold uppercase text-slate-400 tracking-wider">Observed Evidence</div>
          <div className="text-2xl sm:text-3xl font-extrabold text-emerald-600 mt-1 font-tabular">8 Points</div>
          <div className="text-xs text-slate-500 mt-0.5">Ground sensors &amp; satellites</div>
        </GlassCard>
        <GlassCard className="p-4">
          <div className="text-[11px] font-bold uppercase text-slate-400 tracking-wider">Model Precision</div>
          <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 mt-1 font-tabular">88.4%</div>
          <div className="text-xs text-slate-500 mt-0.5">WRF-Chem dispersion match</div>
        </GlassCard>
        <GlassCard className="p-4">
          <div className="text-[11px] font-bold uppercase text-slate-400 tracking-wider">Mitigation Rate</div>
          <div className="text-2xl sm:text-3xl font-extrabold text-teal-600 mt-1 font-tabular">75%</div>
          <div className="text-xs text-slate-500 mt-0.5">3 actions verified effective</div>
        </GlassCard>
      </div>

      {/* Evidence Legend */}
      <div className="flex flex-wrap items-center gap-2 p-3 bg-white/70 backdrop-blur-md rounded-2xl border border-white/80 shadow-xs text-xs">
        <span className="font-semibold text-slate-700 mr-2">Evidence Classification:</span>
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-100/80 text-emerald-800 font-semibold text-[11px] border border-emerald-200">
          <CheckCircle className="w-3 h-3 text-emerald-600" /> Observed
        </span>
        <span className="text-slate-500 text-[11px] mr-3">Measured by verified ground monitor or satellite</span>

        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-100/80 text-blue-800 font-semibold text-[11px] border border-blue-200">
          <Layers className="w-3 h-3 text-blue-600" /> Modeled
        </span>
        <span className="text-slate-500 text-[11px] mr-3">Computed from meteorological &amp; dispersion formulas</span>

        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-100/80 text-amber-800 font-semibold text-[11px] border border-amber-200">
          <HelpCircle className="w-3 h-3 text-amber-600" /> Hypothesis
        </span>
        <span className="text-slate-500 text-[11px]">Plausible explanation undergoing validation</span>
      </div>

      {/* Split Grid: Candidate Sources Sidebar + Rich Source Detail Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Sidebar: Candidate Sources (4 cols) */}
        <div className="lg:col-span-4 space-y-3">
          <h3 className="text-xs font-bold uppercase text-slate-400 tracking-wider px-1">
            Active Candidates ({sources.length})
          </h3>
          <div className="space-y-2.5">
            {sources.map((item) => {
              const isSelected = selectedSource.id === item.id;
              return (
                <div
                  key={item.id}
                  onClick={() => setSelectedSource(item)}
                  className={`p-4 rounded-2xl border cursor-pointer transition-all select-none ${
                    isSelected
                      ? 'bg-white shadow-md border-emerald-500/50 ring-2 ring-emerald-500/10'
                      : 'bg-white/80 hover:bg-white border-slate-200/80 hover:shadow-xs'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-slate-100 text-slate-600">
                      {item.type}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        item.severity === 'High'
                          ? 'bg-rose-100 text-rose-700'
                          : item.severity === 'Medium'
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-emerald-100 text-emerald-700'
                      }`}
                    >
                      {item.severity} Prio
                    </span>
                  </div>

                  <h4 className="font-bold text-sm text-slate-900 leading-snug">
                    {item.title}
                  </h4>
                  <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                    <MapPin className="w-3 h-3 text-slate-400" /> {item.locality}
                  </p>

                  <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-slate-100 text-[11px]">
                    <span className="text-slate-400 font-medium">Confidence</span>
                    <span className="font-bold text-emerald-600 font-tabular">{item.confidence}% Match</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Detail Pane (8 cols) */}
        <div className="lg:col-span-8 space-y-5">
          <GlassCard className="p-6">
            
            {/* Source Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md">
                    {selectedSource.id}
                  </span>
                  <span className="text-xs text-slate-400">• Updated {selectedSource.updatedAt}</span>
                </div>
                <h2 className="text-xl font-extrabold text-slate-900 tracking-tight mt-1">
                  {selectedSource.title}
                </h2>
                <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 text-emerald-600" /> {selectedSource.locality}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">Status:</span>
                <span className="px-3 py-1 rounded-full bg-slate-900 text-white font-bold text-xs">
                  {selectedSource.status}
                </span>
              </div>
            </div>

            {/* Interactive Before/After Visual Comparison Slider */}
            <div className="my-5">
              <div className="flex items-center justify-between text-xs font-bold text-slate-700 mb-2">
                <span className="flex items-center gap-1"><Eye className="w-3.5 h-3.5 text-slate-400" /> Multi-Temporal Satellite &amp; Plume Analysis</span>
                <span className="text-slate-400 text-[11px]">Drag slider to inspect plume dispersion</span>
              </div>

              {/* Slider Container */}
              <div className="relative h-56 sm:h-64 rounded-2xl overflow-hidden border border-slate-200 select-none shadow-inner">
                {/* Before Pane (Left Background) */}
                <div className="absolute inset-0 bg-gradient-to-br from-emerald-800 via-teal-900 to-slate-900 flex flex-col justify-end p-4 text-white">
                  <div className="absolute inset-0 opacity-25 bg-[radial-gradient(#34d399_1px,transparent_1px)] [background-size:16px_16px]" />
                  <div className="relative z-10 bg-slate-900/80 backdrop-blur-md px-3 py-1.5 rounded-xl text-xs font-semibold w-max border border-white/20">
                    {selectedSource.beforeImageLabel}
                  </div>
                </div>

                {/* After Pane (Right Overlay clipped at sliderPos) */}
                <div
                  className="absolute inset-0 bg-gradient-to-br from-amber-700 via-orange-800 to-rose-950 flex flex-col justify-end items-end p-4 text-white"
                  style={{ clipPath: `inset(0 0 0 ${sliderPos}%)` }}
                >
                  <div className="absolute inset-0 opacity-30 bg-[radial-gradient(#fbbf24_1px,transparent_1px)] [background-size:16px_16px]" />
                  <div className="relative z-10 bg-slate-900/80 backdrop-blur-md px-3 py-1.5 rounded-xl text-xs font-semibold w-max border border-white/20">
                    {selectedSource.afterImageLabel}
                  </div>
                </div>

                {/* Handle Line */}
                <div
                  className="absolute top-0 bottom-0 w-1 bg-white shadow-2xl pointer-events-none"
                  style={{ left: `${sliderPos}%` }}
                >
                  <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-7 h-7 rounded-full bg-white text-slate-800 shadow-xl flex items-center justify-center text-[10px] font-extrabold border-2 border-emerald-500">
                    ⇄
                  </div>
                </div>

                {/* Invisible Range Input */}
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={sliderPos}
                  onChange={(e) => setSliderPos(Number(e.target.value))}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-ew-resize z-20"
                />
              </div>
            </div>

            {/* Evidence Breakdown Grid */}
            <div className="space-y-4 pt-2">
              <h3 className="font-bold text-sm text-slate-900">
                Evidence Ledger &amp; Source Attribution
              </h3>

              {/* Observed Facts */}
              <div className="p-3.5 rounded-2xl bg-emerald-50/70 border border-emerald-200/60 space-y-1.5">
                <div className="flex items-center gap-2 text-xs font-bold text-emerald-900">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Observed Facts (High Confidence Sensors)</span>
                </div>
                <ul className="space-y-1 pl-5 list-disc text-xs text-emerald-800">
                  {selectedSource.observedEvidence.map((ev, idx) => (
                    <li key={idx}>{ev}</li>
                  ))}
                </ul>
              </div>

              {/* Modeled Estimates */}
              <div className="p-3.5 rounded-2xl bg-blue-50/70 border border-blue-200/60 space-y-1.5">
                <div className="flex items-center gap-2 text-xs font-bold text-blue-900">
                  <Layers className="w-3.5 h-3.5 text-blue-600" />
                  <span>Modeled Numerical Estimates (WRF-Chem / Dispersion)</span>
                </div>
                <ul className="space-y-1 pl-5 list-disc text-xs text-blue-800">
                  {selectedSource.modeledEstimates.map((ev, idx) => (
                    <li key={idx}>{ev}</li>
                  ))}
                </ul>
              </div>

              {/* Hypotheses */}
              <div className="p-3.5 rounded-2xl bg-amber-50/70 border border-amber-200/60 space-y-1.5">
                <div className="flex items-center gap-2 text-xs font-bold text-amber-900">
                  <HelpCircle className="w-3.5 h-3.5 text-amber-600" />
                  <span>Working Hypotheses (Plausible Causes)</span>
                </div>
                <ul className="space-y-1 pl-5 list-disc text-xs text-amber-800">
                  {selectedSource.hypotheses.map((ev, idx) => (
                    <li key={idx}>{ev}</li>
                  ))}
                </ul>
              </div>

              {/* Recommendation Callout */}
              <div className="p-4 rounded-2xl bg-slate-900 text-white flex items-start gap-3 shadow-md">
                <Sparkles className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <div className="text-xs font-bold text-emerald-400 uppercase tracking-wide">
                    Action Plan Recommendation
                  </div>
                  <p className="text-xs text-slate-200 mt-1 leading-relaxed">
                    {selectedSource.recommendedAction}
                  </p>
                </div>
              </div>

            </div>

          </GlassCard>
        </div>

      </div>

      {/* New Investigation Modal */}
      {isModalOpen && (
        <div
          className="fixed inset-0 z-[1200] flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-fade-up"
          onClick={() => setIsModalOpen(false)}
        >
          <div
            className="glass-panel max-w-lg w-full p-6 bg-white/95 text-slate-800 shadow-2xl relative"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-bold text-slate-900 mb-1">
              Initiate New Source Investigation
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Configure attribution bounds, ground sensor hooks, and dispersion modeling parameters.
            </p>

            <div className="space-y-3.5 text-xs">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Title / Spike Subject</label>
                <input
                  type="text"
                  placeholder="e.g., Sector 21 PM2.5 Elevated Plume"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Locality / Sector</label>
                  <input
                    type="text"
                    placeholder="e.g., Dwarka Sector 21"
                    value={newArea}
                    onChange={(e) => setNewArea(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Date</label>
                  <input
                    type="date"
                    defaultValue={new Date().toISOString().split('T')[0]}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                  />
                </div>
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1.5">Suspected Source Types</label>
                <div className="flex flex-wrap gap-1.5">
                  {['Road Dust', 'Construction Silt', 'Industrial Stack', 'Biomass / Crop', 'Vehicle Exhaust'].map((tp) => (
                    <button
                      key={tp}
                      type="button"
                      onClick={() => {
                        if (selectedTypes.includes(tp)) {
                          setSelectedTypes(selectedTypes.filter((t) => t !== tp));
                        } else {
                          setSelectedTypes([...selectedTypes, tp]);
                        }
                      }}
                      className={`px-2.5 py-1 rounded-full text-xs font-semibold border transition-all ${
                        selectedTypes.includes(tp)
                          ? 'bg-emerald-600 text-white border-emerald-600'
                          : 'bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-200'
                      }`}
                    >
                      {tp}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 mt-6 pt-3 border-t border-slate-100">
              <button
                onClick={() => setIsModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (newTitle) {
                    setSources([
                      {
                        id: `src-0${sources.length + 1}`,
                        title: newTitle,
                        type: selectedTypes.join(', ') || 'General Particulate',
                        locality: newArea || 'Delhi NCR',
                        severity: 'Medium',
                        confidence: 75,
                        status: 'Investigating',
                        observedEvidence: ['New report logged via command console'],
                        modeledEstimates: ['Running dispersion projection'],
                        hypotheses: ['Initial plume under assessment'],
                        beforeImageLabel: 'Baseline',
                        afterImageLabel: 'Current Observation',
                        recommendedAction: 'Awaiting model convergence',
                        updatedAt: 'Just now',
                      },
                      ...sources,
                    ]);
                  }
                  setIsModalOpen(false);
                }}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-md transition-all"
              >
                Create Investigation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default InvestigationsPage;

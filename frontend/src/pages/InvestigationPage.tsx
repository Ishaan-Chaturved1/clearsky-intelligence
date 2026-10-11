import React, { useState, useEffect } from 'react';
import {
  Compass,
  Search,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Flame,
  Factory,
  Wind,
  ShieldCheck,
  RefreshCw,
  Info,
  Calendar,
  Layers,
  FileText,
  Sliders,
  ChevronRight
} from 'lucide-react';
import { api } from '../services/api';
import {
  InvestigationDossier,
  ZoneWithLatest,
  EvidenceItem,
  EvidenceDirection,
  CandidateSource
} from '../types';
import { InvestigationMap } from '../components/InvestigationMap';

export const InvestigationPage: React.FC = () => {
  const [zones, setZones] = useState<ZoneWithLatest[]>([]);
  const [selectedZoneId, setSelectedZoneId] = useState<string>('DEL-AV-01');
  const [customLat, setCustomLat] = useState<number>(28.6469);
  const [customLon, setCustomLon] = useState<number>(77.3160);
  const [useCustomCoords, setUseCustomCoords] = useState<boolean>(false);
  const [pollutant, setPollutant] = useState<string>('PM2.5');
  const [lookbackHours, setLookbackHours] = useState<number>(12);
  const [radiusKm, setRadiusKm] = useState<number>(5.0);

  const [dossier, setDossier] = useState<InvestigationDossier | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load available zones on mount
  useEffect(() => {
    api.getZones()
      .then((data) => {
        setZones(data);
        if (data.length > 0 && !selectedZoneId) {
          const firstZone = data[0].zone;
          setSelectedZoneId(firstZone.zone_id);
          setCustomLat(firstZone.latitude);
          setCustomLon(firstZone.longitude);
        }
      })
      .catch((err) => console.error('Failed to load zones for investigation:', err));
  }, []);

  // Update coordinates when zone selection changes
  const handleZoneSelect = (zoneId: string) => {
    setSelectedZoneId(zoneId);
    const item = zones.find((entry) => entry.zone.zone_id === zoneId);
    if (item) {
      setCustomLat(item.zone.latitude);
      setCustomLon(item.zone.longitude);
    }
  };

  // Run the investigation
  const handleRunInvestigation = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params: any = {
        pollutant,
        lookback_hours: lookbackHours,
        radius_km: radiusKm,
      };

      if (useCustomCoords) {
        params.latitude = customLat;
        params.longitude = customLon;
      } else {
        params.zone_id = selectedZoneId;
      }

      const res = await api.analyzeInvestigation(params);
      setDossier(res);
    } catch (err: any) {
      console.error('Investigation error:', err);
      setError(err?.message || 'Failed to complete air pollution investigation.');
    } finally {
      setIsLoading(false);
    }
  };

  // Helper for evidence badge colors
  const getDirectionBadge = (dir: EvidenceDirection) => {
    switch (dir) {
      case 'SUPPORTS':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5" />
            SUPPORTS
          </span>
        );
      case 'CONTRADICTS':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-200">
            <XCircle className="w-3.5 h-3.5" />
            CONTRADICTS
          </span>
        );
      case 'CONTEXT_ONLY':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-warm-100 text-earth-700 border border-warm-300">
            <Info className="w-3.5 h-3.5" />
            CONTEXT ONLY
          </span>
        );
      case 'INSUFFICIENT_INFORMATION':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
            <AlertTriangle className="w-3.5 h-3.5" />
            INSUFFICIENT DATA
          </span>
        );
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Page Header */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-warm-200 shadow-warm-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent-500/10 text-accent-700 text-xs font-semibold tracking-wide uppercase">
              <Compass className="w-3.5 h-3.5" />
              Stage 3 Evidence Intelligence
            </div>
            <h1 className="font-sentinel text-2xl sm:text-3xl text-earth-900 tracking-tight">
              Pollution Source Investigation Studio
            </h1>
            <p className="text-sm text-earth-600 max-w-3xl">
              Systematically investigate candidate pollution origins using real geographic features (OpenStreetMap),
              kinematic backward atmospheric transport (Open-Meteo), and satellite active fire detections (NASA FIRMS).
              Distinguishes verified physical observations from candidate hypotheses without fabricating percentage contributions.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleRunInvestigation}
              disabled={isLoading}
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-accent-600 hover:bg-accent-700 text-white font-medium text-sm shadow-warm-sm transition-all disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Correlating Evidence...
                </>
              ) : (
                <>
                  <Search className="w-4 h-4" />
                  Launch Investigation
                </>
              )}
            </button>
          </div>
        </div>

        {/* Configuration Controls Bar */}
        <div className="mt-6 pt-6 border-t border-warm-100 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Target Location Selection */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-earth-700 uppercase tracking-wider">
              Investigation Target
            </label>
            {!useCustomCoords ? (
              <select
                value={selectedZoneId}
                onChange={(e) => handleZoneSelect(e.target.value)}
                className="w-full text-xs sm:text-sm bg-warm-50 border border-warm-300 rounded-xl px-3 py-2 text-earth-900 focus:outline-none focus:ring-2 focus:ring-accent-500"
              >
                {zones.map((z) => (
                  <option key={z.zone.zone_id} value={z.zone.zone_id}>
                    {z.zone.name} ({z.zone.zone_id})
                  </option>
                ))}
              </select>
            ) : (
              <div className="grid grid-cols-2 gap-1.5">
                <input
                  type="number"
                  step="0.001"
                  value={customLat}
                  onChange={(e) => setCustomLat(parseFloat(e.target.value))}
                  placeholder="Latitude"
                  className="w-full text-xs bg-warm-50 border border-warm-300 rounded-xl px-2.5 py-2"
                />
                <input
                  type="number"
                  step="0.001"
                  value={customLon}
                  onChange={(e) => setCustomLon(parseFloat(e.target.value))}
                  placeholder="Longitude"
                  className="w-full text-xs bg-warm-50 border border-warm-300 rounded-xl px-2.5 py-2"
                />
              </div>
            )}
            <button
              onClick={() => setUseCustomCoords(!useCustomCoords)}
              className="text-[11px] text-accent-700 hover:underline font-medium"
            >
              {useCustomCoords ? '← Switch to predefined monitoring zone' : 'Enter custom GPS coordinates →'}
            </button>
          </div>

          {/* Pollutant Selection */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-earth-700 uppercase tracking-wider">
              Target Pollutant
            </label>
            <div className="flex gap-2">
              {['PM2.5', 'PM10'].map((p) => (
                <button
                  key={p}
                  onClick={() => setPollutant(p)}
                  className={`flex-1 py-2 text-xs font-bold rounded-xl border transition-all ${
                    pollutant === p
                      ? 'bg-accent-500/10 border-accent-500 text-accent-700 shadow-sm'
                      : 'bg-warm-50 border-warm-200 text-earth-600 hover:bg-warm-100'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          {/* Lookback Window Slider */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center text-xs">
              <span className="font-semibold text-earth-700 uppercase tracking-wider">Wind Look-Back</span>
              <span className="font-bold text-accent-700">{lookbackHours} Hours</span>
            </div>
            <input
              type="range"
              min="1"
              max="48"
              step="1"
              value={lookbackHours}
              onChange={(e) => setLookbackHours(parseInt(e.target.value, 10))}
              className="w-full accent-accent-600 h-1.5 bg-warm-200 rounded-lg cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-earth-500">
              <span>1h (Local)</span>
              <span>24h (Mesoscale)</span>
              <span>48h (Regional)</span>
            </div>
          </div>

          {/* Search Radius Slider */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center text-xs">
              <span className="font-semibold text-earth-700 uppercase tracking-wider">Feature Radius</span>
              <span className="font-bold text-accent-700">{radiusKm.toFixed(1)} km</span>
            </div>
            <input
              type="range"
              min="1"
              max="25"
              step="0.5"
              value={radiusKm}
              onChange={(e) => setRadiusKm(parseFloat(e.target.value))}
              className="w-full accent-accent-600 h-1.5 bg-warm-200 rounded-lg cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-earth-500">
              <span>1 km</span>
              <span>10 km</span>
              <span>25 km</span>
            </div>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-800 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-red-600" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Investigation Dossier Display */}
      {dossier ? (
        <div className="space-y-8 animate-fade-in">
          {/* Executive Summary & Measured Facts Card */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-white rounded-3xl p-6 sm:p-7 border border-warm-200 shadow-warm-sm space-y-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-xs text-earth-500 font-medium">Investigation Dossier #{dossier.investigation_id}</div>
                  <h2 className="text-xl font-bold text-earth-900 mt-0.5">{dossier.target_scope}</h2>
                  <div className="text-xs text-earth-600 mt-1">
                    Coordinates: {dossier.target_latitude.toFixed(4)}°N, {dossier.target_longitude.toFixed(4)}°E &bull; Generated:{' '}
                    {new Date(dossier.generated_at).toLocaleString()}
                  </div>
                </div>

                <div className="text-right">
                  <div className="text-[10px] font-semibold text-earth-500 uppercase tracking-wider">Data Completeness</div>
                  <span
                    className={`inline-block mt-1 px-2.5 py-0.5 rounded-full text-xs font-bold ${
                      dossier.data_completeness_rating === 'HIGH'
                        ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                        : dossier.data_completeness_rating === 'MODERATE'
                        ? 'bg-blue-100 text-blue-800 border border-blue-300'
                        : 'bg-amber-100 text-amber-800 border border-amber-300'
                    }`}
                  >
                    {dossier.data_completeness_rating}
                  </span>
                </div>
              </div>

              {/* Observed Physical Facts */}
              <div className="space-y-2 pt-2">
                <div className="text-xs font-bold text-earth-800 uppercase tracking-wider flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-accent-600" />
                  Verified Empirical Measurements
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  {dossier.report.main_measured_facts.map((fact, idx) => (
                    <div key={idx} className="p-2.5 bg-warm-50 rounded-xl border border-warm-200 text-earth-800">
                      &bull; {fact}
                    </div>
                  ))}
                </div>
              </div>

              {/* Transport Assessment Summary */}
              {dossier.report.origin_and_transport_findings && (
                <div className="p-3 bg-sky-50 rounded-xl border border-sky-200 text-xs text-sky-900">
                  <div className="font-semibold flex items-center gap-1.5 text-sky-950 mb-1">
                    <Wind className="w-3.5 h-3.5" />
                    Atmospheric Transport Pathway
                  </div>
                  {dossier.report.origin_and_transport_findings}
                </div>
              )}
            </div>

            {/* Evidence Balance & Qualitative Confidence */}
            <div className="bg-white rounded-3xl p-6 sm:p-7 border border-warm-200 shadow-warm-sm flex flex-col justify-between space-y-4">
              <div>
                <div className="text-xs font-bold text-earth-800 uppercase tracking-wider">Evidence Balance</div>
                <div className="grid grid-cols-2 gap-3 mt-3">
                  <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-2xl text-center">
                    <div className="text-2xl font-bold text-emerald-700">
                      {dossier.report.evidence_supporting.length}
                    </div>
                    <div className="text-[11px] font-semibold text-emerald-800 uppercase tracking-wide mt-0.5">
                      Supporting Lines
                    </div>
                  </div>
                  <div className="p-3 bg-rose-50 border border-rose-200 rounded-2xl text-center">
                    <div className="text-2xl font-bold text-rose-700">
                      {dossier.report.evidence_contradicting.length}
                    </div>
                    <div className="text-[11px] font-semibold text-rose-800 uppercase tracking-wide mt-0.5">
                      Contradicting Lines
                    </div>
                  </div>
                </div>

                <div className="mt-4 p-3 bg-warm-50 rounded-xl border border-warm-200 text-xs text-earth-700">
                  <div className="font-bold text-earth-900 mb-1">Qualitative Assessment</div>
                  <p>{dossier.report.confidence_assessment}</p>
                </div>
              </div>

              {/* Scientific Guardrail Alert */}
              <div className="p-3 bg-warm-100 rounded-xl border border-warm-300 text-[11px] text-earth-600">
                <span className="font-semibold text-earth-800">Scientific Integrity:</span> Quantitative source contribution percentages are not invented without chemical speciation telemetry.
              </div>
            </div>
          </div>

          {/* Interactive Geospatial Investigation Map */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-earth-900 text-base flex items-center gap-2">
                <Layers className="w-4 h-4 text-accent-600" />
                Geospatial Source & Transport Visualization
              </h3>
              <div className="text-xs text-earth-500">
                Found {dossier.local_sources.total_candidates_found} mapped features &bull;{' '}
                {dossier.satellite.total_fires_in_region} satellite thermal anomalies
              </div>
            </div>

            <InvestigationMap
              centerLat={dossier.target_latitude}
              centerLon={dossier.target_longitude}
              radiusKm={dossier.local_sources.search_radius_km}
              candidateSources={dossier.local_sources.candidates}
              trajectoryPoints={dossier.transport.trajectory_points}
              fireRecords={dossier.satellite.fire_records}
              targetName={dossier.target_scope}
            />
          </div>

          {/* Evidence Ledger Table */}
          <div className="bg-white rounded-3xl p-6 sm:p-8 border border-warm-200 shadow-warm-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-bold text-earth-900 text-lg flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-accent-600" />
                  Investigation Evidence Ledger
                </h3>
                <p className="text-xs text-earth-600 mt-0.5">
                  Traceable multi-source findings evaluated against candidate hypotheses with explicit directionality.
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-earth-800">
                <thead className="bg-warm-100 text-earth-900 font-bold uppercase text-[10px] tracking-wider border-b border-warm-200">
                  <tr>
                    <th className="py-2.5 px-3">Direction</th>
                    <th className="py-2.5 px-3">Evidence Type</th>
                    <th className="py-2.5 px-3">Data Provider</th>
                    <th className="py-2.5 px-3">Provenance</th>
                    <th className="py-2.5 px-3">Findings & Physical Basis</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-warm-100">
                  {/* Supporting Evidence Items */}
                  {dossier.report.evidence_supporting.map((ev) => (
                    <tr key={ev.evidence_id} className="hover:bg-warm-50/50">
                      <td className="py-3 px-3">{getDirectionBadge(ev.direction)}</td>
                      <td className="py-3 px-3 font-semibold text-earth-900">{ev.evidence_type.replace(/_/g, ' ')}</td>
                      <td className="py-3 px-3 text-earth-600">{ev.provider}</td>
                      <td className="py-3 px-3">
                        <span className="px-2 py-0.5 rounded bg-warm-100 text-earth-700 text-[10px] font-medium border border-warm-200">
                          {ev.provenance}
                        </span>
                      </td>
                      <td className="py-3 px-3 max-w-md text-earth-700">{ev.description}</td>
                    </tr>
                  ))}

                  {/* Contradicting Evidence Items */}
                  {dossier.report.evidence_contradicting.map((ev) => (
                    <tr key={ev.evidence_id} className="hover:bg-warm-50/50">
                      <td className="py-3 px-3">{getDirectionBadge(ev.direction)}</td>
                      <td className="py-3 px-3 font-semibold text-earth-900">{ev.evidence_type.replace(/_/g, ' ')}</td>
                      <td className="py-3 px-3 text-earth-600">{ev.provider}</td>
                      <td className="py-3 px-3">
                        <span className="px-2 py-0.5 rounded bg-warm-100 text-earth-700 text-[10px] font-medium border border-warm-200">
                          {ev.provenance}
                        </span>
                      </td>
                      <td className="py-3 px-3 max-w-md text-earth-700">{ev.description}</td>
                    </tr>
                  ))}

                  {/* Context Only Items from Candidate Sources */}
                  {dossier.local_sources.candidates.slice(0, 10).map((cand) => (
                    <tr key={`ctx_${cand.source_id}`} className="hover:bg-warm-50/50">
                      <td className="py-3 px-3">{getDirectionBadge('CONTEXT_ONLY')}</td>
                      <td className="py-3 px-3 font-semibold text-earth-900">INFRASTRUCTURE PROXIMITY</td>
                      <td className="py-3 px-3 text-earth-600">{cand.provider}</td>
                      <td className="py-3 px-3">
                        <span className="px-2 py-0.5 rounded bg-warm-100 text-earth-700 text-[10px] font-medium border border-warm-200">
                          MAPPED_FEATURE
                        </span>
                      </td>
                      <td className="py-3 px-3 max-w-md text-earth-700">
                        <strong>{cand.name}</strong> ({cand.category.replace(/_/g, ' ')}) at ~
                        {cand.distance_km?.toFixed(1) || '?'} km {cand.compass_direction || ''}. Mapped feature in vicinity; emissions unverified without localized telemetry.
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Alternative Explanations, Data Gaps & Next Steps */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Alternative Explanations */}
            <div className="bg-white rounded-3xl p-6 border border-warm-200 shadow-warm-sm space-y-3">
              <h4 className="font-bold text-earth-900 text-sm flex items-center gap-1.5">
                <HelpCircle className="w-4 h-4 text-purple-600" />
                Alternative Explanations
              </h4>
              <ul className="text-xs text-earth-700 space-y-2">
                {dossier.report.alternative_explanations.map((alt, idx) => (
                  <li key={idx} className="flex items-start gap-1.5">
                    <span className="text-purple-600 font-bold">&bull;</span>
                    <span>{alt}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Data Gaps & Limitations */}
            <div className="bg-white rounded-3xl p-6 border border-warm-200 shadow-warm-sm space-y-3">
              <h4 className="font-bold text-earth-900 text-sm flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                Data Gaps & Limitations
              </h4>
              <ul className="text-xs text-earth-700 space-y-2">
                {dossier.report.data_gaps.map((gap, idx) => (
                  <li key={idx} className="flex items-start gap-1.5">
                    <span className="text-amber-600 font-bold">&bull;</span>
                    <span>{gap}</span>
                  </li>
                ))}
                {dossier.transport.limitations.map((lim, idx) => (
                  <li key={`lim_${idx}`} className="flex items-start gap-1.5">
                    <span className="text-amber-600 font-bold">&bull;</span>
                    <span>{lim}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Recommended Next Steps */}
            <div className="bg-white rounded-3xl p-6 border border-warm-200 shadow-warm-sm space-y-3">
              <h4 className="font-bold text-earth-900 text-sm flex items-center gap-1.5">
                <ChevronRight className="w-4 h-4 text-accent-600" />
                Recommended Next Steps
              </h4>
              <ul className="text-xs text-earth-700 space-y-2">
                {dossier.report.recommended_next_steps.map((step, idx) => (
                  <li key={idx} className="flex items-start gap-1.5">
                    <span className="text-accent-600 font-bold">&bull;</span>
                    <span>{step}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      ) : (
        /* Empty State / Initial Guide */
        <div className="bg-white rounded-3xl p-10 border border-warm-200 text-center shadow-warm-sm space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-accent-500/10 border border-accent-500/20 text-accent-600 flex items-center justify-center mx-auto">
            <Compass className="w-7 h-7" />
          </div>
          <div className="space-y-1">
            <h3 className="font-sentinel text-xl font-bold text-earth-900">
              No Investigation Active
            </h3>
            <p className="text-xs text-earth-600 max-w-lg mx-auto">
              Select a monitoring zone or enter GPS coordinates above, then click{' '}
              <strong className="text-earth-900">"Launch Investigation"</strong> to trace candidate emission sources,
              calculate backward wind trajectories, and cross-reference satellite thermal anomalies.
            </p>
          </div>

          <div className="pt-4 flex flex-wrap justify-center gap-2">
            {zones.slice(0, 4).map((z) => (
              <button
                key={z.zone.zone_id}
                onClick={() => {
                  setSelectedZoneId(z.zone.zone_id);
                  setCustomLat(z.zone.latitude);
                  setCustomLon(z.zone.longitude);
                  setUseCustomCoords(false);
                }}
                className={`px-3 py-1.5 rounded-xl border text-xs font-medium transition-all ${
                  selectedZoneId === z.zone.zone_id
                    ? 'bg-accent-500/10 border-accent-400 text-accent-700 font-bold'
                    : 'bg-warm-50 border-warm-200 text-earth-700 hover:bg-warm-100'
                }`}
              >
                Investigate {z.zone.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

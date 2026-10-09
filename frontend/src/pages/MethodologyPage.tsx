import React, { useState, useEffect } from 'react';
import {
  HelpCircle,
  ShieldCheck,
  AlertTriangle,
  Flame,
  Droplets,
  Wind,
  Layers,
  HardHat,
  Scale,
  CheckCircle2,
  BookOpen
} from 'lucide-react';
import { api } from '../services/api';
import { MethodologyResponse } from '../types';

export const MethodologyPage: React.FC = () => {
  const [methodology, setMethodology] = useState<MethodologyResponse | null>(null);

  useEffect(() => {
    api.getMethodology()
      .then((data) => setMethodology(data))
      .catch((err) => console.error(err));
  }, []);

  return (
    <div className="max-w-5xl mx-auto space-y-10 animate-fade-up">
      
      {/* Header */}
      <div className="border-b border-warm-200 pb-6">
        <div className="flex items-center gap-2 mb-2">
          <span className="font-mono text-xs px-2.5 py-0.5 rounded-full bg-accent-500/10 text-accent-600 border border-accent-500/20 font-semibold">
            {methodology?.version || 'v1.2-Deterministic'}
          </span>
          <span className="text-xs font-clarendon text-earth-500">Explainable Decision Architecture</span>
        </div>
        <h1 className="font-sentinel font-bold text-3xl sm:text-4xl text-earth-900 tracking-tight">
          How Recommendations Work
        </h1>
        <p className="font-clarendon text-base text-earth-600 mt-2 leading-relaxed max-w-3xl">
          {methodology?.core_premise}
        </p>
      </div>

      {/* Core Rules Grid */}
      <div className="space-y-6">
        <div className="flex items-center gap-2">
          <Scale className="w-5 h-5 text-accent-500" />
          <h2 className="font-sentinel font-bold text-xl text-earth-900">
            Configurable Decision Rules &amp; Precedence
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {methodology?.rules.map((rule) => (
            <div
              key={rule.rule_id}
              className="bg-white rounded-2xl p-6 border border-warm-200 shadow-warm-sm flex flex-col justify-between hover:shadow-warm transition-all"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="font-mono text-xs font-bold text-accent-600 bg-accent-500/10 px-2.5 py-0.5 rounded-lg border border-accent-500/20">
                    {rule.rule_id}
                  </span>
                  <span className="font-mono text-[11px] px-2.5 py-0.5 rounded-lg bg-warm-100 border border-warm-300 text-earth-600">
                    {rule.threshold}
                  </span>
                </div>

                <h3 className="font-sentinel font-bold text-lg text-earth-900 mb-2">
                  {rule.name}
                </h3>

                <p className="font-clarendon text-xs text-earth-600 leading-relaxed mb-4">
                  {rule.rationale}
                </p>
              </div>

              <div className="pt-4 border-t border-warm-200 space-y-3 text-xs">
                <div>
                  <span className="text-[11px] font-sans font-semibold text-earth-500 block mb-0.5">
                    Decision Impact:
                  </span>
                  <span className="font-clarendon text-earth-800 font-medium">
                    {rule.decision_impact}
                  </span>
                </div>

                <div className="p-3 rounded-xl bg-warm-100/70 border border-warm-300/80 text-[11px] text-earth-700">
                  <strong className="text-amber-700 font-sans font-semibold">Scientific Boundary:</strong> {rule.scientific_limitation}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Confidence Calculation */}
      <div className="bg-white rounded-2xl p-6 border border-warm-200 shadow-warm-sm space-y-4">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-sage-600" />
          <h2 className="font-sentinel font-bold text-xl text-earth-900">
            Confidence Assessment Framework
          </h2>
        </div>
        <p className="font-clarendon text-xs text-earth-600 leading-relaxed">
          {methodology?.confidence_calculation}
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 text-xs">
          <div className="p-4 rounded-xl bg-sage-50 border border-sage-200">
            <span className="font-sentinel font-bold text-sage-700 block mb-1">HIGH CONFIDENCE</span>
            <p className="font-clarendon text-[11px] text-earth-600 leading-relaxed">
              Valid ground station observations for both PM10 &amp; PM2.5 within 25km, active weather telemetry, and verified fire status.
            </p>
          </div>
          <div className="p-4 rounded-xl bg-amber-50 border border-amber-200">
            <span className="font-sentinel font-bold text-amber-700 block mb-1">MEDIUM CONFIDENCE</span>
            <p className="font-clarendon text-[11px] text-earth-600 leading-relaxed">
              Atmospheric numerical model estimates (CAMS/Open-Meteo) utilized with valid meteorological forecast data.
            </p>
          </div>
          <div className="p-4 rounded-xl bg-warm-100 border border-warm-300">
            <span className="font-sentinel font-bold text-earth-700 block mb-1">LOW CONFIDENCE</span>
            <p className="font-clarendon text-[11px] text-earth-600 leading-relaxed">
              Stale readings (&gt;3h old), missing critical pollutants, or conflicting sensor readings. Automatically forces ADVISORY ONLY.
            </p>
          </div>
        </div>
      </div>

      {/* Scientific Boundaries & What the System Cannot Claim */}
      <div className="bg-warm-100/70 rounded-2xl p-6 border border-warm-300/80 text-xs space-y-3">
        <div className="flex items-center gap-2 text-earth-900 font-sentinel font-bold text-base">
          <AlertTriangle className="w-4 h-4 text-accent-500 flex-shrink-0" />
          <span>Ethical AI Boundaries &amp; Scientific Restraint</span>
        </div>
        <p className="font-clarendon text-earth-600 leading-relaxed text-xs">
          Environmental operations require transparency regarding what sensors can and cannot establish:
        </p>
        <ul className="space-y-2 pl-4 list-disc font-clarendon text-earth-600 text-xs">
          {methodology?.system_limitations.map((limit, idx) => (
            <li key={idx} className="leading-relaxed">
              {limit}
            </li>
          ))}
        </ul>
      </div>

    </div>
  );
};

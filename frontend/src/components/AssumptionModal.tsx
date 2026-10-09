import React, { useState } from 'react';
import { X, Sliders, RotateCcw, Check } from 'lucide-react';

interface AssumptionModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentBaselineRate: number;
  currentLitersPerOp: number;
  onApply: (baselineRate: number, litersPerOp: number) => void;
}

export const AssumptionModal: React.FC<AssumptionModalProps> = ({
  isOpen,
  onClose,
  currentBaselineRate,
  currentLitersPerOp,
  onApply
}) => {
  const [baselineRate, setBaselineRate] = useState(currentBaselineRate);
  const [litersPerOp, setLitersPerOp] = useState(currentLitersPerOp);

  if (!isOpen) return null;

  const handleReset = () => {
    setBaselineRate(3.0);
    setLitersPerOp(5000.0);
  };

  const handleSave = () => {
    onApply(baselineRate, litersPerOp);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-earth-900/40 backdrop-blur-sm">
      <div className="bg-white border border-warm-200 rounded-2xl max-w-md w-full shadow-warm-xl p-6">
        
        <div className="flex items-center justify-between pb-4 border-b border-warm-200">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-accent-500/10 border border-accent-500/20 flex items-center justify-center text-accent-500">
              <Sliders className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-sentinel font-bold text-base text-earth-900">
                Baseline Assumptions
              </h3>
              <p className="text-xs text-earth-400 font-sans">Configure comparative metrics</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-earth-400 hover:text-earth-700 rounded-lg hover:bg-warm-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-5 my-6 text-xs text-earth-600">
          
          {/* Baseline Interventions / Zone / Day */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="font-sans font-medium text-earth-700">
                Baseline Runs per Zone per Day
              </label>
              <span className="font-mono font-bold text-sm text-accent-500">
                {baselineRate.toFixed(1)} runs
              </span>
            </div>
            <input
              type="range"
              min="0.5"
              max="8.0"
              step="0.5"
              value={baselineRate}
              onChange={(e) => setBaselineRate(parseFloat(e.target.value))}
              className="w-full accent-accent-500 bg-warm-200 h-2 rounded-lg cursor-pointer"
            />
            <p className="text-[11px] text-earth-400 mt-1">
              Standard municipal fixed schedule (typically 3 runs/day).
            </p>
          </div>

          {/* Volume per operation in Liters */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="font-sans font-medium text-earth-700">
                Assumed Water per Run (Liters)
              </label>
              <span className="font-mono font-bold text-sm text-sage-600">
                {litersPerOp.toLocaleString()} L
              </span>
            </div>
            <input
              type="range"
              min="1000"
              max="15000"
              step="500"
              value={litersPerOp}
              onChange={(e) => setLitersPerOp(parseFloat(e.target.value))}
              className="w-full accent-sage-500 bg-warm-200 h-2 rounded-lg cursor-pointer"
            />
            <p className="text-[11px] text-earth-400 mt-1">
              Estimated tanker capacity per run (typical: 5,000L).
            </p>
          </div>

          {/* Transparency note */}
          <div className="p-3 rounded-xl bg-warm-100 border border-warm-200 text-[11px] text-earth-500">
            <span className="font-sans font-semibold text-earth-700 block mb-1">
              Audit Transparency:
            </span>
            Values are operational baseline models for comparing targeted interventions vs indiscriminate spraying.
          </div>

        </div>

        <div className="flex items-center justify-between gap-3 pt-4 border-t border-warm-200">
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-earth-500 hover:text-earth-700 bg-warm-100 hover:bg-warm-200 text-xs transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Defaults</span>
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-xl text-earth-500 hover:text-earth-700 bg-transparent hover:bg-warm-100 text-xs transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl text-white bg-accent-500 hover:bg-accent-600 text-xs font-sans font-semibold shadow-warm transition-colors"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Apply Model</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};

import React, { useState, useEffect } from 'react';
import {
  Plus,
  ArrowRight,
  Droplets,
  CheckCircle2,
  AlertOctagon,
  Sliders,
  RotateCcw,
  Clock,
  User,
  Sparkles,
  Info,
  Calendar,
  AlertCircle
} from 'lucide-react';
import { GlassCard } from '../components/GlassCard';
import { api } from '../services/api';
import { WaterSavingsAnalytics } from '../types';

interface ActionTask {
  id: string;
  title: string;
  why: string;
  owner: string;
  priority: 'high' | 'medium' | 'low';
  column: 'todo' | 'inprogress' | 'completed';
}

export const ActionPlanPage: React.FC = () => {
  const [tasks, setTasks] = useState<ActionTask[]>([
    {
      id: 'act-1',
      title: 'Deploy Polymer Binder on Sector 21 Unpaved Berm',
      why: 'Coarse dust ratio > 2.74 with traffic resuspension rate 12.4 kg/km-hr.',
      owner: 'Dwarka Municipal Depot 3',
      priority: 'high',
      column: 'todo',
    },
    {
      id: 'act-2',
      title: 'Enforce Vehicle Wheel-Wash at Anand Vihar Terminal',
      why: 'Track-out silt responsible for 38% of localized PM10 peak around bus entry.',
      owner: 'DMRC Infrastructure Unit',
      priority: 'high',
      column: 'inprogress',
    },
    {
      id: 'act-3',
      title: 'Halt Aerial Smog Gun at Okhla Canal Bridge',
      why: 'Relative humidity > 82% and inversion layer at 310m render droplet misting ineffective.',
      owner: 'South Delhi Municipal Ops',
      priority: 'medium',
      column: 'completed',
    },
    {
      id: 'act-4',
      title: 'Inspect Bawana Phase II Boiler Stacks',
      why: 'Thermal anomaly cluster detected with elevated fine PM2.5 fractions.',
      owner: 'DPCC Field Inspection Team',
      priority: 'medium',
      column: 'todo',
    },
  ]);

  const [waterData, setWaterData] = useState<WaterSavingsAnalytics | null>(null);
  const [baselineRate, setBaselineRate] = useState(3.0);
  const [litersPerOp, setLitersPerOp] = useState(5000);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Form states
  const [newTitle, setNewTitle] = useState('');
  const [newWhy, setNewWhy] = useState('');
  const [newOwner, setNewOwner] = useState('');
  const [newPriority, setNewPriority] = useState<'high' | 'medium' | 'low'>('high');

  useEffect(() => {
    api.getWaterSavings(7, baselineRate, litersPerOp)
      .then((data) => setWaterData(data))
      .catch(() => {});
  }, [baselineRate, litersPerOp]);

  const moveTask = (taskId: string) => {
    setTasks(
      tasks.map((t) => {
        if (t.id !== taskId) return t;
        const nextCol =
          t.column === 'todo'
            ? 'inprogress'
            : t.column === 'inprogress'
            ? 'completed'
            : 'todo';
        return { ...t, column: nextCol };
      })
    );
  };

  const handleAddTask = () => {
    if (!newTitle.trim()) return;
    const newTask: ActionTask = {
      id: `act-${Date.now()}`,
      title: newTitle,
      why: newWhy || 'Evidence-backed by environmental model assessment',
      owner: newOwner || 'Operational Field Team',
      priority: newPriority,
      column: 'todo',
    };
    setTasks([...tasks, newTask]);
    setNewTitle('');
    setNewWhy('');
    setNewOwner('');
    setIsModalOpen(false);
  };

  const savedLiters = waterData?.estimated_water_saved_liters || 420000;
  const reductionPercent = waterData?.intervention_reduction_percent || 68;

  return (
    <div className="space-y-6 animate-fade-up max-w-[1780px] mx-auto w-full">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Action Plan
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-2xl">
            Evidence-backed next steps, and a water-efficiency model that determines{' '}
            <span className="font-semibold text-emerald-700">when spraying makes sense</span>{' '}
            — preventing wasted municipal water when conditions suppress efficacy.
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-md transition-all self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Add Action</span>
        </button>
      </div>

      {/* KPI Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        <GlassCard className="p-4">
          <div className="text-[11px] font-bold uppercase text-slate-400 tracking-wider">Active Tasks</div>
          <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 mt-1 font-tabular">
            {tasks.filter((t) => t.column !== 'completed').length}
          </div>
          <div className="text-xs text-slate-500 mt-0.5">{tasks.length} total queued</div>
        </GlassCard>

        <GlassCard className="p-4">
          <div className="text-[11px] font-bold uppercase text-slate-400 tracking-wider">Water Conserved</div>
          <div className="text-2xl sm:text-3xl font-extrabold text-emerald-600 mt-1 font-tabular">
            {(savedLiters / 1000).toFixed(0)}k L
          </div>
          <div className="text-xs text-slate-500 mt-0.5">vs standard {baselineRate} daily runs</div>
        </GlassCard>

        <GlassCard className="p-4">
          <div className="text-[11px] font-bold uppercase text-slate-400 tracking-wider">Reduction Rate</div>
          <div className="text-2xl sm:text-3xl font-extrabold text-teal-600 mt-1 font-tabular">
            {reductionPercent.toFixed(0)}%
          </div>
          <div className="text-xs text-slate-500 mt-0.5">Targeted spray efficiency</div>
        </GlassCard>

        <GlassCard className="p-4">
          <div className="text-[11px] font-bold uppercase text-slate-400 tracking-wider">Carbon Offset</div>
          <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 mt-1 font-tabular">
            {(savedLiters * 0.00028).toFixed(0)} kg
          </div>
          <div className="text-xs text-slate-500 mt-0.5">Pumping energy averted</div>
        </GlassCard>
      </div>

      {/* Kanban Board of Actions */}
      <GlassCard className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-base text-slate-900 tracking-tight">
            Recommended Action Items
          </h2>
          <span className="text-xs text-slate-400 font-medium">
            Click the arrow button to transition card status
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Column: To Do */}
          <div className="space-y-3">
            <div className="flex items-center justify-between px-2 text-xs font-bold uppercase tracking-wider text-slate-400">
              <span>To Do</span>
              <span>{tasks.filter((t) => t.column === 'todo').length}</span>
            </div>
            <div className="space-y-2.5">
              {tasks
                .filter((t) => t.column === 'todo')
                .map((task) => (
                  <div
                    key={task.id}
                    className="p-4 rounded-2xl bg-white/90 border border-slate-200/90 shadow-xs hover:shadow-md transition-all space-y-2 text-left"
                  >
                    <div className="flex items-center justify-between">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-md ${
                          task.priority === 'high'
                            ? 'bg-rose-100 text-rose-700'
                            : 'bg-amber-100 text-amber-700'
                        }`}
                      >
                        {task.priority.toUpperCase()}
                      </span>
                      <button
                        onClick={() => moveTask(task.id)}
                        className="w-6 h-6 rounded-full bg-slate-100 hover:bg-emerald-50 text-slate-500 hover:text-emerald-700 flex items-center justify-center transition-colors"
                        title="Move to In Progress"
                      >
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    <h4 className="font-bold text-xs sm:text-sm text-slate-900 leading-snug">
                      {task.title}
                    </h4>
                    <p className="text-xs text-slate-500">{task.why}</p>
                    <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
                      <span className="flex items-center gap-1"><User className="w-3 h-3" /> {task.owner}</span>
                    </div>
                  </div>
                ))}
            </div>
          </div>

          {/* Column: In Progress */}
          <div className="space-y-3">
            <div className="flex items-center justify-between px-2 text-xs font-bold uppercase tracking-wider text-slate-400">
              <span>In Progress</span>
              <span>{tasks.filter((t) => t.column === 'inprogress').length}</span>
            </div>
            <div className="space-y-2.5">
              {tasks
                .filter((t) => t.column === 'inprogress')
                .map((task) => (
                  <div
                    key={task.id}
                    className="p-4 rounded-2xl bg-white/90 border border-emerald-500/30 shadow-xs hover:shadow-md transition-all space-y-2 text-left"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-blue-100 text-blue-700">
                        IN PROGRESS
                      </span>
                      <button
                        onClick={() => moveTask(task.id)}
                        className="w-6 h-6 rounded-full bg-slate-100 hover:bg-emerald-50 text-slate-500 hover:text-emerald-700 flex items-center justify-center transition-colors"
                        title="Move to Completed"
                      >
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    <h4 className="font-bold text-xs sm:text-sm text-slate-900 leading-snug">
                      {task.title}
                    </h4>
                    <p className="text-xs text-slate-500">{task.why}</p>
                    <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
                      <span className="flex items-center gap-1"><User className="w-3 h-3" /> {task.owner}</span>
                    </div>
                  </div>
                ))}
            </div>
          </div>

          {/* Column: Completed */}
          <div className="space-y-3">
            <div className="flex items-center justify-between px-2 text-xs font-bold uppercase tracking-wider text-slate-400">
              <span>Completed</span>
              <span>{tasks.filter((t) => t.column === 'completed').length}</span>
            </div>
            <div className="space-y-2.5">
              {tasks
                .filter((t) => t.column === 'completed')
                .map((task) => (
                  <div
                    key={task.id}
                    className="p-4 rounded-2xl bg-slate-50/80 border border-slate-200/80 space-y-2 text-left opacity-85"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-emerald-100 text-emerald-800 flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" /> DONE
                      </span>
                      <button
                        onClick={() => moveTask(task.id)}
                        className="w-6 h-6 rounded-full bg-slate-200 hover:bg-slate-300 text-slate-500 flex items-center justify-center transition-colors"
                        title="Reset to To Do"
                      >
                        <RotateCcw className="w-3 h-3" />
                      </button>
                    </div>
                    <h4 className="font-bold text-xs sm:text-sm text-slate-800 line-through">
                      {task.title}
                    </h4>
                    <p className="text-xs text-slate-400">{task.why}</p>
                    <div className="pt-2 border-t border-slate-200/60 text-[11px] text-slate-400">
                      Completed by {task.owner}
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      </GlassCard>

      {/* Dust-Suppression & Water Analytics Model Section */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left: Model Verdict & Performance Bars (8 cols) */}
        <div className="lg:col-span-8 space-y-4">
          <GlassCard className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-base text-slate-900 tracking-tight">
                Dust-Suppression &amp; Water Analytics
              </h3>
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-blue-100 text-blue-700">
                Modeled Numerical Simulation
              </span>
            </div>

            {/* Verdict Banner */}
            <div className="p-4 rounded-2xl bg-gradient-to-r from-emerald-500/10 via-emerald-500/5 to-teal-500/10 border border-emerald-500/20 text-emerald-950 flex items-start gap-3 mb-5">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
              <div>
                <div className="font-bold text-sm">
                  Strategic Spraying Window Recommended (13:00 – 16:30)
                </div>
                <p className="text-xs text-emerald-800 mt-0.5 leading-relaxed">
                  Moderate surface wind (7.5 km/h) and coarse dust dominance ensure high suppression efficiency. Avoid misting past 17:00 when inversion layer drops.
                </p>
              </div>
            </div>

            {/* Savings Comparison Progress Bars */}
            <div className="space-y-4 my-4">
              <div>
                <div className="flex justify-between text-xs font-bold text-slate-700 mb-1">
                  <span>Targeted Smart Suppression Operations</span>
                  <span className="font-tabular text-emerald-700">32% of baseline volume</span>
                </div>
                <div className="w-full h-3 rounded-full bg-slate-100 overflow-hidden">
                  <div className="h-full rounded-full bg-emerald-500" style={{ width: '32%' }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-bold text-slate-700 mb-1">
                  <span>Avoided Ineffective Spray Runs (High Humidity / Smoke)</span>
                  <span className="font-tabular text-amber-700">68% conserved</span>
                </div>
                <div className="w-full h-3 rounded-full bg-slate-100 overflow-hidden">
                  <div className="h-full rounded-full bg-amber-500" style={{ width: '68%' }} />
                </div>
              </div>
            </div>

            {/* Assumptions List */}
            <div className="mt-6 pt-4 border-t border-slate-100">
              <h4 className="font-bold text-xs text-slate-800 uppercase tracking-wider mb-2">
                Operational Assumptions
              </h4>
              <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-slate-500">
                <li className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  Baseline: {baselineRate} runs per sector daily
                </li>
                <li className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  Tanker capacity: {litersPerOp.toLocaleString()} L per run
                </li>
                <li className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  RH &gt; 80% marks spraying ineffective
                </li>
                <li className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  Wind &gt; 25 km/h accelerates dry dissipation
                </li>
              </ul>
            </div>
          </GlassCard>
        </div>

        {/* Right: Simulation Sliders (4 cols) */}
        <div className="lg:col-span-4">
          <GlassCard className="p-6 sticky top-6">
            <div className="flex items-center justify-between mb-4">
              <h4 className="font-bold text-sm text-slate-900">Model Inputs</h4>
              <button
                onClick={() => {
                  setBaselineRate(3.0);
                  setLitersPerOp(5000);
                }}
                className="text-xs text-emerald-600 hover:underline flex items-center gap-1 font-semibold"
              >
                <RotateCcw className="w-3 h-3" /> Reset
              </button>
            </div>

            <div className="space-y-5 text-xs">
              <div>
                <div className="flex justify-between font-semibold text-slate-700 mb-1">
                  <span>Baseline Runs / Day</span>
                  <span className="font-bold text-slate-900 font-tabular">{baselineRate}</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="6"
                  step="0.5"
                  value={baselineRate}
                  onChange={(e) => setBaselineRate(parseFloat(e.target.value))}
                  className="w-full accent-emerald-600 cursor-pointer"
                />
                <span className="text-[10px] text-slate-400">Typical municipal schedule without dynamic guidance</span>
              </div>

              <div>
                <div className="flex justify-between font-semibold text-slate-700 mb-1">
                  <span>Water Volume Per Operation</span>
                  <span className="font-bold text-slate-900 font-tabular">{litersPerOp.toLocaleString()} L</span>
                </div>
                <input
                  type="range"
                  min="2000"
                  max="12000"
                  step="500"
                  value={litersPerOp}
                  onChange={(e) => setLitersPerOp(parseInt(e.target.value))}
                  className="w-full accent-emerald-600 cursor-pointer"
                />
                <span className="text-[10px] text-slate-400">Average water consumption per anti-smog tanker run</span>
              </div>

              <div className="p-3.5 rounded-2xl bg-slate-900 text-white mt-6">
                <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">
                  Simulated Weekly Water Savings
                </div>
                <div className="text-xl font-black text-emerald-400 mt-1 font-tabular">
                  {(savedLiters).toLocaleString()} Liters
                </div>
              </div>
            </div>
          </GlassCard>
        </div>

      </div>

      {/* Add Action Modal */}
      {isModalOpen && (
        <div
          className="fixed inset-0 z-[1200] flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-fade-up"
          onClick={() => setIsModalOpen(false)}
        >
          <div
            className="glass-panel max-w-md w-full p-6 bg-white/95 text-slate-800 shadow-2xl relative"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-bold text-slate-900 mb-1">
              Add Operational Action
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Create a targeted particulate suppression or enforcement task.
            </p>

            <div className="space-y-3.5 text-xs">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Action Title</label>
                <input
                  type="text"
                  placeholder="e.g., Deploy Misting Truck on Outer Ring Road"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">Why (Evidence / Reason)</label>
                <textarea
                  rows={2}
                  placeholder="e.g., Coarse particulate spike with high drying capacity."
                  value={newWhy}
                  onChange={(e) => setNewWhy(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Assigned Owner</label>
                  <input
                    type="text"
                    placeholder="e.g., Municipal Fleet 2"
                    value={newOwner}
                    onChange={(e) => setNewOwner(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Priority</label>
                  <select
                    value={newPriority}
                    onChange={(e: any) => setNewPriority(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                  >
                    <option value="high">High Priority</option>
                    <option value="medium">Medium Priority</option>
                    <option value="low">Low Priority</option>
                  </select>
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
                onClick={handleAddTask}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-md transition-all"
              >
                Add Action
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ActionPlanPage;

import React, { useState, useEffect } from 'react';
import { Search, HardHat, RotateCcw } from 'lucide-react';
import { ZoneMap } from '../components/ZoneMap';
import { ZoneCard } from '../components/ZoneCard';
import { ZoneDetailDrawer } from '../components/ZoneDetailDrawer';
import { api } from '../services/api';
import { ZoneWithLatest } from '../types';

export const MapExplorerPage: React.FC = () => {
  const [zones, setZones] = useState<ZoneWithLatest[]>([]);
  const [selectedZone, setSelectedZone] = useState<ZoneWithLatest | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [recommendationFilter, setRecommendationFilter] = useState<string>('ALL');
  const [onlyConstruction, setOnlyConstruction] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.getZones()
      .then((data) => setZones(data))
      .catch((err) => console.error(err))
      .finally(() => setIsLoading(false));
  }, []);

  const filteredZones = zones.filter((item) => {
    const matchesSearch =
      item.zone.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.zone.zone_id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesRec =
      recommendationFilter === 'ALL' ||
      item.latest_decision?.decision === recommendationFilter;
    const matchesConstruction =
      !onlyConstruction || item.zone.nearby_infrastructure.has_construction_nearby;
    return matchesSearch && matchesRec && matchesConstruction;
  });

  const handleResetFilters = () => {
    setSearchQuery('');
    setRecommendationFilter('ALL');
    setOnlyConstruction(false);
  };

  return (
    <div className="space-y-4 animate-fade-up">
      
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h1 className="font-sentinel font-bold text-2xl text-earth-900">Map Explorer</h1>
          <p className="text-xs font-clarendon text-earth-500 mt-0.5">Spatial distribution of intervention recommendations across Delhi NCR</p>
        </div>
        <div className="text-xs font-mono text-earth-500 bg-white px-3 py-1.5 rounded-xl border border-warm-200 shadow-warm-sm">
          <strong className="text-earth-800">{filteredZones.length}</strong> / {zones.length} sectors
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white p-3.5 rounded-2xl border border-warm-200 shadow-warm-sm flex flex-wrap items-center gap-3">
        
        <div className="relative flex-1 min-w-[200px]">
          <Search className="w-4 h-4 text-earth-300 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by name or ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-warm-50 border border-warm-200 rounded-xl text-xs text-earth-800 placeholder-earth-300 focus:outline-none focus:border-accent-400 font-sans"
          />
        </div>

        <select
          value={recommendationFilter}
          onChange={(e) => setRecommendationFilter(e.target.value)}
          className="bg-warm-50 border border-warm-200 rounded-xl px-3 py-1.5 text-xs text-earth-700 focus:outline-none focus:border-accent-400 font-sans"
        >
          <option value="ALL">All Outcomes</option>
          <option value="INTERVENTION_RECOMMENDED">Recommended</option>
          <option value="INTERVENTION_NOT_RECOMMENDED">Discouraged</option>
          <option value="ADVISORY_ONLY">Advisory Only</option>
        </select>

        <button
          onClick={() => setOnlyConstruction(!onlyConstruction)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs border transition-colors font-sans ${
            onlyConstruction
              ? 'bg-yellow-50 border-yellow-300 text-yellow-700 font-semibold'
              : 'bg-warm-50 border-warm-200 text-earth-400 hover:text-earth-600'
          }`}
        >
          <HardHat className="w-3.5 h-3.5" />
          <span>Construction</span>
        </button>

        {(searchQuery || recommendationFilter !== 'ALL' || onlyConstruction) && (
          <button
            onClick={handleResetFilters}
            className="flex items-center gap-1 text-xs text-earth-400 hover:text-earth-700 px-2 py-1 rounded-xl font-sans"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Reset</span>
          </button>
        )}
      </div>

      {/* Map + Sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-8">
          <ZoneMap
            zones={filteredZones}
            selectedZone={selectedZone}
            onSelectZone={setSelectedZone}
            height="580px"
          />
        </div>

        <div className="lg:col-span-4 h-[580px] flex flex-col">
          <div className="mb-2 text-xs font-sans font-semibold text-earth-400 uppercase tracking-wider">
            Sector Cards
          </div>

          <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
            {filteredZones.length === 0 ? (
              <div className="p-8 text-center text-xs text-earth-400 bg-white rounded-xl border border-warm-200">
                No sectors match current filters.
              </div>
            ) : (
              filteredZones.map((item) => (
                <ZoneCard
                  key={item.zone.zone_id}
                  item={item}
                  onSelect={setSelectedZone}
                  isSelected={selectedZone?.zone.zone_id === item.zone.zone_id}
                />
              ))
            )}
          </div>
        </div>
      </div>

      <ZoneDetailDrawer
        item={selectedZone}
        onClose={() => setSelectedZone(null)}
      />
    </div>
  );
};

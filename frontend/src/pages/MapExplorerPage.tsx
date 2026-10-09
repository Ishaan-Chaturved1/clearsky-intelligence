import React, { useState, useEffect, useRef } from 'react';
import { Search, HardHat, RotateCcw, MapPin, Radio, Loader2, Navigation, Info, Compass } from 'lucide-react';
import { ZoneMap } from '../components/ZoneMap';
import { ZoneCard } from '../components/ZoneCard';
import { ZoneDetailDrawer } from '../components/ZoneDetailDrawer';
import { api } from '../services/api';
import { ZoneWithLatest, GeocodingPlace, StationObservation, LocationAnalysisResponse } from '../types';

export const MapExplorerPage: React.FC = () => {
  const [zones, setZones] = useState<ZoneWithLatest[]>([]);
  const [stations, setStations] = useState<StationObservation[]>([]);
  const [selectedZone, setSelectedZone] = useState<ZoneWithLatest | null>(null);
  const [dynamicAnalysis, setDynamicAnalysis] = useState<LocationAnalysisResponse | null>(null);
  
  // Search & Geocoding state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<GeocodingPlace[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showSearchResults, setShowSearchResults] = useState(false);
  const searchTimeoutRef = useRef<any>(null);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  // Selected dynamic pin
  const [selectedCustomCoords, setSelectedCustomCoords] = useState<[number, number] | null>(null);
  const [selectedCustomName, setSelectedCustomName] = useState<string | null>(null);
  const [isAnalyzingLocation, setIsAnalyzingLocation] = useState(false);

  // Filters
  const [recommendationFilter, setRecommendationFilter] = useState<string>('ALL');
  const [onlyConstruction, setOnlyConstruction] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Load predefined zones and monitoring stations
  useEffect(() => {
    Promise.all([
      api.getZones().catch(() => []),
      api.getStations(28.6139, 77.2090, 45).catch(() => [])
    ])
      .then(([zonesData, stationsData]) => {
        setZones(zonesData);
        setStations(stationsData);
      })
      .catch((err) => console.error('Failed to load map data:', err))
      .finally(() => setIsLoading(false));
  }, []);

  // Handle outside click to dismiss search dropdown
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target as Node)) {
        setShowSearchResults(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Debounced geocoding search
  const handleSearchChange = (query: string) => {
    setSearchQuery(query);
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);

    if (query.trim().length < 2) {
      setSearchResults([]);
      setIsSearching(false);
      setShowSearchResults(false);
      return;
    }

    setIsSearching(true);
    setShowSearchResults(true);
    searchTimeoutRef.current = setTimeout(() => {
      api.searchGeo(query, 6)
        .then((places) => {
          setSearchResults(places);
        })
        .catch((err) => {
          console.warn('Geocoding search error:', err);
          setSearchResults([]);
        })
        .finally(() => setIsSearching(false));
    }, 350);
  };

  // Perform dynamic analysis for any selected coordinate
  const analyzeGeographicPoint = async (lat: number, lon: number, name?: string) => {
    try {
      setIsAnalyzingLocation(true);
      setSelectedCustomCoords([lat, lon]);
      setSelectedCustomName(name || `${lat.toFixed(3)}, ${lon.toFixed(3)}`);
      setSelectedZone(null); // Clear predefined zone selection to focus on dynamic point

      const analysis = await api.analyzeLocation(lat, lon, name);
      setDynamicAnalysis(analysis);
      setSelectedCustomName(analysis.location_name);
    } catch (err) {
      console.error('Failed to analyze location:', err);
    } finally {
      setIsAnalyzingLocation(false);
    }
  };

  // Select place from autocomplete
  const handleSelectPlace = (place: GeocodingPlace) => {
    setShowSearchResults(false);
    setSearchQuery(place.place_name);
    analyzeGeographicPoint(place.latitude, place.longitude, place.place_name);
  };

  // Map click handler (discover and analyze clicked coordinate)
  const handleMapClick = (lat: number, lon: number) => {
    analyzeGeographicPoint(lat, lon);
  };

  // Filtered zones list
  const filteredZones = zones.filter((item) => {
    const matchesSearch =
      item.zone.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.zone.zone_id.toLowerCase().includes(searchQuery.toLowerCase());
    const d = item.latest_decision?.decision;
    const matchesRec =
      recommendationFilter === 'ALL' ||
      d === recommendationFilter ||
      (recommendationFilter === 'INTERVENTION_RECOMMENDED' && d === 'TARGETED_INTERVENTION_RECOMMENDED') ||
      (recommendationFilter === 'INTERVENTION_DISCOURAGED' && (d === 'INTERVENTION_DISCOURAGED' || d === 'INTERVENTION_NOT_RECOMMENDED'));
    const matchesConstruction =
      !onlyConstruction || item.zone.nearby_infrastructure.has_construction_nearby;
    return (searchQuery ? matchesSearch : true) && matchesRec && matchesConstruction;
  });

  const handleResetFilters = () => {
    setSearchQuery('');
    setRecommendationFilter('ALL');
    setOnlyConstruction(false);
    setSelectedCustomCoords(null);
    setSelectedCustomName(null);
    setDynamicAnalysis(null);
  };

  const handleCloseDrawer = () => {
    setSelectedZone(null);
    setDynamicAnalysis(null);
  };

  return (
    <div className="space-y-4 animate-fade-up">
      
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-xs px-2.5 py-0.5 rounded-full bg-accent-500/10 text-accent-600 border border-accent-500/20 font-semibold">
              Live Geographic Intelligence
            </span>
            <span className="text-xs font-clarendon text-earth-500">OpenStreetMap Discovery</span>
          </div>
          <h1 className="font-sentinel font-bold text-2xl text-earth-900">Map Explorer &amp; Locality Discovery</h1>
          <p className="text-xs font-clarendon text-earth-500 mt-0.5">
            Search any city, neighborhood, or click anywhere on the map to evaluate real-time atmospheric and particulate suitability.
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <div className="text-xs font-mono text-earth-600 bg-white px-3 py-1.5 rounded-xl border border-warm-200 shadow-warm-sm flex items-center gap-1.5">
            <Radio className="w-3.5 h-3.5 text-indigo-500" />
            <span><strong className="text-earth-900">{stations.length}</strong> Active Stations</span>
          </div>
          <div className="text-xs font-mono text-earth-600 bg-white px-3 py-1.5 rounded-xl border border-warm-200 shadow-warm-sm">
            <strong className="text-earth-900">{filteredZones.length}</strong> / {zones.length} Sectors
          </div>
        </div>
      </div>

      {/* Filter & Geographic Search Toolbar */}
      <div className="bg-white p-3.5 rounded-2xl border border-warm-200 shadow-warm-sm flex flex-wrap items-center gap-3 relative z-30">
        
        {/* Real Geocoding Search Input with Dropdown */}
        <div ref={searchContainerRef} className="relative flex-1 min-w-[240px]">
          <Search className="w-4 h-4 text-earth-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search any locality, neighborhood, or city (e.g. Connaught Place, Noida Sector 62, Gurugram)..."
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            onFocus={() => {
              if (searchResults.length > 0) setShowSearchResults(true);
            }}
            className="w-full pl-9 pr-8 py-2 bg-warm-50 border border-warm-200 rounded-xl text-xs text-earth-800 placeholder-earth-400 focus:outline-none focus:border-accent-500 focus:bg-white font-sans transition-all"
          />
          {isSearching && (
            <Loader2 className="w-4 h-4 text-accent-500 animate-spin absolute right-3 top-1/2 -translate-y-1/2" />
          )}

          {/* Autocomplete Dropdown */}
          {showSearchResults && searchResults.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1.5 bg-white border border-warm-200 rounded-2xl shadow-xl overflow-hidden z-[1100] max-h-80 overflow-y-auto divide-y divide-warm-100">
              <div className="px-3.5 py-2 bg-warm-100/60 text-[11px] font-mono font-semibold text-earth-500 flex items-center justify-between">
                <span>Discovered Real Localities ({searchResults.length})</span>
                <span className="text-[10px] text-earth-400">OpenStreetMap Nominatim</span>
              </div>
              {searchResults.map((place, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSelectPlace(place)}
                  className="w-full text-left px-3.5 py-2.5 hover:bg-warm-100 transition-colors flex items-start gap-2.5 group"
                >
                  <MapPin className="w-4 h-4 text-accent-500 flex-shrink-0 mt-0.5 group-hover:scale-110 transition-transform" />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-sans font-semibold text-earth-900 truncate">
                      {place.place_name}
                    </div>
                    <div className="text-[11px] text-earth-500 truncate mt-0.5">
                      {place.display_name}
                    </div>
                    <div className="text-[10px] font-mono text-earth-400 mt-0.5">
                      {place.latitude.toFixed(4)}°N, {place.longitude.toFixed(4)}°E
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Outcome Filter */}
        <select
          value={recommendationFilter}
          onChange={(e) => setRecommendationFilter(e.target.value)}
          className="bg-warm-50 border border-warm-200 rounded-xl px-3 py-2 text-xs text-earth-700 focus:outline-none focus:border-accent-500 font-sans"
        >
          <option value="ALL">All Decision Outcomes</option>
          <option value="INTERVENTION_RECOMMENDED">Intervention Recommended</option>
          <option value="TARGETED_INTERVENTION_RECOMMENDED">Targeted Intervention</option>
          <option value="INTERVENTION_DISCOURAGED">Intervention Discouraged</option>
          <option value="ADVISORY_ONLY">Advisory Only</option>
          <option value="ALTERNATIVE_DUST_CONTROL_SUGGESTED">Alternative Dust Control</option>
        </select>

        {/* Construction toggle */}
        <button
          onClick={() => setOnlyConstruction(!onlyConstruction)}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs border transition-colors font-sans ${
            onlyConstruction
              ? 'bg-amber-50 border-amber-300 text-amber-700 font-semibold'
              : 'bg-warm-50 border-warm-200 text-earth-600 hover:text-earth-800'
          }`}
        >
          <HardHat className="w-3.5 h-3.5" />
          <span>Construction Adjacent</span>
        </button>

        {/* Reset */}
        {(searchQuery || recommendationFilter !== 'ALL' || onlyConstruction || selectedCustomCoords) && (
          <button
            onClick={handleResetFilters}
            className="flex items-center gap-1 text-xs text-earth-500 hover:text-earth-800 px-2.5 py-1.5 rounded-xl font-sans hover:bg-warm-100 transition-colors"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Reset</span>
          </button>
        )}
      </div>

      {/* Loading banner for dynamic location telemetry */}
      {isAnalyzingLocation && (
        <div className="bg-sky-50 border border-sky-200 text-sky-800 px-4 py-2.5 rounded-xl text-xs flex items-center justify-between shadow-warm-sm animate-pulse">
          <div className="flex items-center gap-2">
            <Loader2 className="w-4 h-4 text-sky-600 animate-spin" />
            <span>Retrieving live atmospheric telemetry &amp; sensor observations for {selectedCustomName || 'coordinates'}...</span>
          </div>
          <span className="font-mono text-[11px] text-sky-600">Open-Meteo &amp; OpenAQ Gateway</span>
        </div>
      )}

      {/* Map + Sidebar Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        
        {/* Interactive GIS Map */}
        <div className="lg:col-span-8">
          <ZoneMap
            zones={filteredZones}
            selectedZone={selectedZone}
            onSelectZone={(z) => {
              setSelectedZone(z);
              setDynamicAnalysis(null);
              setSelectedCustomCoords(null);
            }}
            onMapClick={handleMapClick}
            selectedCustomCoords={selectedCustomCoords}
            selectedCustomName={selectedCustomName}
            stations={stations}
            height="620px"
          />
        </div>

        {/* Sectors and Locations Sidebar */}
        <div className="lg:col-span-4 h-[620px] flex flex-col">
          
          {/* Active Selection Banner if dynamic point is chosen */}
          {dynamicAnalysis && (
            <div className="mb-3 bg-white p-3.5 rounded-2xl border-2 border-accent-400 shadow-warm space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] uppercase font-bold text-accent-600 bg-accent-50 px-2 py-0.5 rounded-md">
                  Dynamic Locality Analyzed
                </span>
                <span className="text-[10px] font-mono text-earth-400">
                  {dynamicAnalysis.data_mode}
                </span>
              </div>
              <h3 className="font-sentinel font-bold text-sm text-earth-900 truncate">
                {dynamicAnalysis.display_name}
              </h3>
              <div className="text-xs font-mono text-earth-500">
                {dynamicAnalysis.latitude.toFixed(4)}°N, {dynamicAnalysis.longitude.toFixed(4)}°E
              </div>
              <button
                onClick={() => setSelectedZone(null)}
                className="w-full text-center text-xs font-sans font-semibold py-1.5 px-3 rounded-xl bg-accent-500 hover:bg-accent-600 text-white transition-colors"
              >
                Inspect Full Analysis Dossier
              </button>
            </div>
          )}

          {/* Sectors List Header */}
          <div className="bg-warm-100/80 px-3.5 py-2 rounded-t-xl border-t border-x border-warm-200 text-xs font-sans font-semibold text-earth-700 flex items-center justify-between">
            <span>Operational Monitoring Sectors ({filteredZones.length})</span>
            <span className="text-[10px] font-mono text-earth-500">Delhi NCR</span>
          </div>

          {/* Scrollable Sector Cards */}
          <div className="flex-1 overflow-y-auto space-y-2.5 p-2 bg-warm-50 border border-warm-200 rounded-b-xl">
            {filteredZones.length === 0 ? (
              <div className="p-8 text-center text-xs text-earth-400 font-sans">
                <Info className="w-8 h-8 text-earth-300 mx-auto mb-2" />
                No sectors matched your current filter. Try clicking anywhere on the map or resetting filters.
              </div>
            ) : (
              filteredZones.map((item) => (
                <ZoneCard
                  key={item.zone.zone_id}
                  item={item}
                  isSelected={selectedZone?.zone.zone_id === item.zone.zone_id}
                  onSelect={() => {
                    setSelectedZone(item);
                    setDynamicAnalysis(null);
                    setSelectedCustomCoords(null);
                  }}
                />
              ))
            )}
          </div>
        </div>
      </div>

      {/* Detail Drawer (Supports both predefined Zone and Dynamic Locality Analysis) */}
      {(selectedZone || dynamicAnalysis) && (
        <ZoneDetailDrawer
          item={selectedZone}
          dynamicAnalysis={dynamicAnalysis}
          onClose={handleCloseDrawer}
        />
      )}

    </div>
  );
};

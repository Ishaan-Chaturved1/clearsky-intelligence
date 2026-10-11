import React, { useState, useEffect } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import {
  Search,
  SlidersHorizontal,
  Bell,
  Settings,
  ChevronDown,
  Menu,
  X,
  Layers,
  ShieldAlert,
  FileText,
  MapPin,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
  ExternalLink,
  User,
  LogOut,
  Building2,
  Sparkles
} from 'lucide-react';
import { DataMode, AlertRecord } from '../types';
import { api } from '../services/api';

interface TopNavigationProps {
  dataMode?: DataMode;
  onRefresh?: () => Promise<void>;
  isRefreshing?: boolean;
  onSearchSelectLocation?: (lat: number, lon: number, name: string) => void;
}

export const TopNavigation: React.FC<TopNavigationProps> = ({
  dataMode = 'DEMO',
  onRefresh,
  isRefreshing = false,
  onSearchSelectLocation,
}) => {
  const navigate = useNavigate();
  const location = useLocation();

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);

  const [showNotifications, setShowNotifications] = useState(false);
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [unreadCount, setUnreadCount] = useState(3);

  const [showSettings, setShowSettings] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showMobileMenu, setShowMobileMenu] = useState(false);

  // Fetch real alerts for notification drawer
  useEffect(() => {
    api.getAlerts(6)
      .then((data) => {
        if (data && data.length > 0) {
          setAlerts(data);
          setUnreadCount(Math.min(data.length, 5));
        }
      })
      .catch(() => {});
  }, []);

  // Handle Geo Search
  useEffect(() => {
    if (!searchQuery.trim() || searchQuery.length < 2) {
      setSearchResults([]);
      setIsSearching(false);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        setIsSearching(true);
        const results = await api.searchGeo(searchQuery, 5);
        setSearchResults(results || []);
        setShowSearchDropdown(true);
      } catch {
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleSelectPlace = (place: any) => {
    setShowSearchDropdown(false);
    setSearchQuery(place.display_name.split(',')[0]);
    if (onSearchSelectLocation) {
      onSearchSelectLocation(place.latitude, place.longitude, place.display_name);
    } else {
      navigate(`/dashboard?lat=${place.latitude}&lon=${place.longitude}&name=${encodeURIComponent(place.display_name)}`);
    }
  };

  const navLinks = [
    { to: '/dashboard', label: 'Dashboard' },
    { to: '/investigations', label: 'Investigations' },
    { to: '/citizen-watch', label: 'Citizen Watch' },
    { to: '/action-plan', label: 'Action Plan' },
    { to: '/documents', label: 'Documents' },
  ];

  const moreLinks = [
    { to: '/investigation', label: 'Investigation Engine' },
    { to: '/map', label: 'Map Explorer' },
    { to: '/water-analytics', label: 'Water Analytics' },
    { to: '/methodology', label: 'Methodology' },
    { to: '/data-sources', label: 'Data Sources' },
    { to: '/about', label: 'About' },
  ];

  return (
    <header className="w-full z-40 select-none">
      {/* Floating Glass Navigation Container */}
      <div className="glass-panel mx-auto px-4 sm:px-6 py-2.5 sm:py-3 flex items-center justify-between gap-3 shadow-lg border border-white/80 bg-white/85 backdrop-blur-xl rounded-2xl sm:rounded-3xl transition-all">
        
        {/* Brand & Wordmark */}
        <div className="flex items-center gap-6">
          <NavLink to="/" className="flex items-center gap-2.5 group">
            {/* Organic Logo Emblem matching aesthetic */}
            <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-2xl bg-gradient-to-tr from-emerald-600 via-teal-500 to-emerald-400 p-0.5 shadow-md group-hover:scale-105 transition-transform flex items-center justify-center">
              <div className="w-full h-full bg-white rounded-[14px] flex items-center justify-center p-1.5">
                <svg viewBox="0 0 24 24" className="w-full h-full" fill="none">
                  <path d="M4 16C7 9 17 9 20 16" stroke="#16a34a" strokeWidth="2.5" strokeLinecap="round" />
                  <path d="M6 12C9 7 15 7 18 12" stroke="#0f172a" strokeWidth="2" strokeLinecap="round" />
                  <circle cx="12" cy="7" r="2" fill="#16a34a" />
                </svg>
              </div>
            </div>
            
            {/* Wordmark */}
            <div className="flex items-baseline">
              <span className="font-bold text-lg sm:text-xl text-slate-900 tracking-tight">
                ClearSky
              </span>
              <span className="font-bold text-lg sm:text-xl text-emerald-600 tracking-tight ml-0.5">
                Intelligence
              </span>
            </div>
          </NavLink>

          {/* Pill Navigation Links (Desktop) */}
          <nav className="hidden xl:flex items-center gap-1">
            {navLinks.map((item) => {
              const isActive = location.pathname === item.to;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={`px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all ${
                    isActive
                      ? 'bg-slate-900 text-white shadow-sm'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'
                  }`}
                >
                  {item.label}
                </NavLink>
              );
            })}

            {/* Quick More Dropdown */}
            <div className="relative group">
              <button className="flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-semibold text-slate-500 hover:text-slate-900 transition-colors">
                <span>More</span>
                <ChevronDown className="w-3 h-3 group-hover:rotate-180 transition-transform" />
              </button>
              <div className="absolute top-full left-0 mt-1 w-44 bg-white/95 backdrop-blur-xl border border-slate-200/80 rounded-2xl shadow-xl p-1.5 hidden group-hover:block animate-fade-up">
                {moreLinks.map((sub) => (
                  <NavLink
                    key={sub.to}
                    to={sub.to}
                    className="block px-3 py-2 rounded-xl text-xs font-medium text-slate-700 hover:bg-emerald-50 hover:text-emerald-700 transition-colors"
                  >
                    {sub.label}
                  </NavLink>
                ))}
              </div>
            </div>
          </nav>
        </div>

        {/* Center / Right Controls */}
        <div className="flex items-center gap-2 sm:gap-3">
          
          {/* Global Search Bar */}
          <div className="relative hidden md:block w-48 lg:w-64">
            <div className="flex items-center bg-slate-100/80 border border-slate-200/80 rounded-full px-3 py-1.5 text-xs text-slate-700 focus-within:bg-white focus-within:border-emerald-500 focus-within:ring-2 focus-within:ring-emerald-500/20 transition-all">
              <Search className="w-3.5 h-3.5 text-slate-400 mr-2 shrink-0" />
              <input
                type="text"
                placeholder="Search..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => {
                  if (searchResults.length > 0) setShowSearchDropdown(true);
                }}
                className="w-full bg-transparent focus:outline-none text-xs placeholder:text-slate-400"
              />
              <button
                type="button"
                title="Filters"
                className="ml-1 p-0.5 rounded text-slate-400 hover:text-slate-700"
              >
                <SlidersHorizontal className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Search Autocomplete Results Dropdown */}
            {showSearchDropdown && searchResults.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-2 bg-white/95 backdrop-blur-xl border border-slate-200/90 rounded-2xl shadow-2xl p-2 z-50 animate-fade-up max-h-64 overflow-y-auto">
                <div className="text-[10px] uppercase font-bold text-slate-400 px-2 py-1">
                  Locations &amp; Sectors
                </div>
                {searchResults.map((place, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSelectPlace(place)}
                    className="w-full text-left px-2.5 py-2 rounded-xl text-xs text-slate-700 hover:bg-emerald-50 hover:text-emerald-800 flex items-center gap-2 transition-colors"
                  >
                    <MapPin className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                    <span className="truncate">{place.display_name}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Notifications Bell */}
          <div className="relative">
            <button
              onClick={() => setShowNotifications(!showNotifications)}
              className="w-8 h-8 sm:w-9 sm:h-9 rounded-full bg-slate-100/80 hover:bg-slate-200/70 border border-slate-200/80 flex items-center justify-center text-slate-600 hover:text-slate-900 transition-colors relative"
              title="Notifications"
            >
              <Bell className="w-4 h-4" />
              {unreadCount > 0 && (
                <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-rose-500 text-white text-[9px] font-bold flex items-center justify-center shadow-xs">
                  {unreadCount}
                </span>
              )}
            </button>

            {/* Notifications Popover */}
            {showNotifications && (
              <div className="absolute top-full right-0 mt-2 w-80 bg-white/95 backdrop-blur-xl border border-slate-200/90 rounded-2xl shadow-2xl p-3 z-50 animate-fade-up">
                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <h4 className="font-bold text-xs text-slate-800 flex items-center gap-1.5">
                    <Bell className="w-3.5 h-3.5 text-emerald-600" /> Notifications &amp; Alerts
                  </h4>
                  <button
                    onClick={() => setUnreadCount(0)}
                    className="text-[10px] text-emerald-600 hover:underline font-semibold"
                  >
                    Mark read
                  </button>
                </div>
                <div className="divide-y divide-slate-100 max-h-72 overflow-y-auto my-1">
                  {alerts.length > 0 ? (
                    alerts.map((al) => (
                      <div key={al.alert_id} className="py-2 text-xs">
                        <div className="font-semibold text-slate-800 flex items-center justify-between">
                          <span>{al.zone_name || al.zone_id}</span>
                          <span className="text-[10px] text-slate-400 font-normal">{new Date(al.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        </div>
                        <p className="text-[11px] text-slate-500 mt-0.5">{al.message}</p>
                      </div>
                    ))
                  ) : (
                    <div className="py-6 text-center text-xs text-slate-400">
                      No active alerts
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Settings Button */}
          <div className="relative">
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="w-8 h-8 sm:w-9 sm:h-9 rounded-full bg-slate-100/80 hover:bg-slate-200/70 border border-slate-200/80 flex items-center justify-center text-slate-600 hover:text-slate-900 transition-colors"
              title="Settings"
            >
              <Settings className="w-4 h-4" />
            </button>

            {/* Settings Modal */}
            {showSettings && (
              <div className="absolute top-full right-0 mt-2 w-72 bg-white/95 backdrop-blur-xl border border-slate-200/90 rounded-2xl shadow-2xl p-4 z-50 animate-fade-up">
                <h4 className="font-bold text-xs text-slate-800 mb-3 flex items-center gap-1.5">
                  <Settings className="w-3.5 h-3.5 text-emerald-600" /> Platform Settings
                </h4>
                <div className="space-y-3 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-600">Data Source Mode</span>
                    <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-mono font-bold text-[10px]">
                      {dataMode}
                    </span>
                  </div>
                  {onRefresh && (
                    <button
                      onClick={onRefresh}
                      disabled={isRefreshing}
                      className="w-full py-2 px-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-semibold flex items-center justify-center gap-2 transition-all disabled:opacity-50"
                    >
                      <RotateCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
                      <span>{isRefreshing ? 'Refreshing Data...' : 'Sync Ingestion Pipeline'}</span>
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* User / Organization Profile Menu (matching screenshot) */}
          <div className="relative">
            <button
              onClick={() => setShowProfileMenu(!showProfileMenu)}
              className="flex items-center gap-2 pl-1.5 pr-2.5 py-1 rounded-full bg-slate-100/80 hover:bg-slate-200/70 border border-slate-200/80 transition-all select-none"
            >
              {/* Green Clover / Emblem Avatar */}
              <div className="w-7 h-7 rounded-full bg-emerald-800 text-white flex items-center justify-center font-bold text-xs shadow-xs">
                <svg viewBox="0 0 24 24" className="w-4 h-4" fill="currentColor">
                  <path d="M12 2C9.5 2 7.5 4 7.5 6.5C7.5 7.9 8.2 9.1 9.2 9.9C8.4 8.9 7.2 8.2 5.8 8.2C3.3 8.2 1.3 10.2 1.3 12.7C1.3 15.2 3.3 17.2 5.8 17.2C7.2 17.2 8.4 16.5 9.2 15.5C8.2 16.3 7.5 17.5 7.5 18.9C7.5 21.4 9.5 23.4 12 23.4C14.5 23.4 16.5 21.4 16.5 18.9C16.5 17.5 15.8 16.3 14.8 15.5C15.6 16.5 16.8 17.2 18.2 17.2C20.7 17.2 22.7 15.2 22.7 12.7C22.7 10.2 20.7 8.2 18.2 8.2C16.8 8.2 15.6 8.9 14.8 9.9C15.8 9.1 16.5 7.9 16.5 6.5C16.5 4 14.5 2 12 2Z" />
                </svg>
              </div>

              {/* Agency Name & Domain */}
              <div className="hidden lg:flex flex-col text-left leading-tight">
                <span className="font-bold text-xs text-slate-800">
                  Cansaas Agency
                </span>
                <span className="text-[10px] text-slate-400">
                  cansaas.weather.com
                </span>
              </div>

              <ChevronDown className="w-3.5 h-3.5 text-slate-400 ml-0.5" />
            </button>

            {/* Profile Dropdown Menu */}
            {showProfileMenu && (
              <div className="absolute top-full right-0 mt-2 w-56 bg-white/95 backdrop-blur-xl border border-slate-200/90 rounded-2xl shadow-2xl p-2 z-50 animate-fade-up">
                <div className="px-3 py-2 border-b border-slate-100">
                  <div className="font-bold text-xs text-slate-900">Cansaas Agency</div>
                  <div className="text-[11px] text-slate-500">cansaas.weather.com</div>
                </div>
                <div className="py-1 text-xs">
                  <button
                    onClick={() => { setShowProfileMenu(false); navigate('/about'); }}
                    className="w-full text-left px-3 py-2 rounded-xl text-slate-700 hover:bg-slate-100 flex items-center gap-2"
                  >
                    <Building2 className="w-3.5 h-3.5 text-slate-400" /> Organization Profile
                  </button>
                  <button
                    onClick={() => { setShowProfileMenu(false); navigate('/methodology'); }}
                    className="w-full text-left px-3 py-2 rounded-xl text-slate-700 hover:bg-slate-100 flex items-center gap-2"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-slate-400" /> Operational Model
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Mobile Menu Hamburger */}
          <button
            onClick={() => setShowMobileMenu(!showMobileMenu)}
            className="xl:hidden w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-700"
          >
            {showMobileMenu ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {showMobileMenu && (
        <div className="xl:hidden glass-panel mt-2 p-4 bg-white/95 backdrop-blur-2xl shadow-2xl rounded-2xl space-y-2 animate-fade-up">
          {navLinks.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => setShowMobileMenu(false)}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-xl text-xs font-semibold ${
                  isActive ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-100'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
          <div className="pt-2 border-t border-slate-200">
            {moreLinks.map((sub) => (
              <NavLink
                key={sub.to}
                to={sub.to}
                onClick={() => setShowMobileMenu(false)}
                className="block px-3 py-2 rounded-xl text-xs text-slate-500 hover:bg-slate-100"
              >
                {sub.label}
              </NavLink>
            ))}
          </div>
        </div>
      )}
    </header>
  );
};

export default TopNavigation;

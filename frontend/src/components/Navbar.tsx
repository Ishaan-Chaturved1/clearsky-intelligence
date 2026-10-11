import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { RefreshCw, BarChart3, Map, HelpCircle, Database, Info, Layers, ShieldAlert, Menu, X } from 'lucide-react';
import { DataMode } from '../types';
import { getDataModeBadge } from '../utils/formatters';

interface NavbarProps {
  dataMode?: DataMode;
  onRefresh?: () => Promise<void>;
  isRefreshing?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  dataMode = 'DEMO',
  onRefresh,
  isRefreshing = false
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const modeInfo = getDataModeBadge(dataMode);

  const navItems = [
    { to: '/dashboard', label: 'Dashboard', icon: Layers },
    { to: '/map', label: 'Map', icon: Map },
    { to: '/citizen-watch', label: 'Citizen Watch', icon: ShieldAlert },
    { to: '/water-analytics', label: 'Water', icon: BarChart3 },
    { to: '/methodology', label: 'Methodology', icon: HelpCircle },
    { to: '/data-sources', label: 'Sources', icon: Database },
    { to: '/about', label: 'About', icon: Info },
  ];

  return (
    <header className="sticky top-0 z-40 bg-white/85 backdrop-blur-md border-b border-warm-200 shadow-warm-sm transition-colors">
      <div className="w-full max-w-[1780px] mx-auto px-4 sm:px-6 lg:px-8 xl:px-12">
        <div className="flex items-center justify-between h-16">
          
          {/* Logo & Product Identity */}
          <NavLink to="/" className="flex items-center gap-3 group">
            {/* Atmospheric horizon geometric logo */}
            <div className="w-9 h-9 rounded-xl bg-warm-100 border border-warm-300 flex items-center justify-center p-1.5 shadow-warm-sm group-hover:border-accent-400 transition-colors">
              <svg viewBox="0 0 32 32" className="w-full h-full" fill="none">
                <circle cx="16" cy="16" r="13" stroke="#D4C5B3" strokeWidth="1.5" strokeDasharray="2 2" />
                <path d="M6 21 Q 16 11 26 21" stroke="#F06B42" strokeWidth="2.5" strokeLinecap="round" />
                <path d="M8 15 Q 16 6 24 15" stroke="#3DA88E" strokeWidth="2" strokeLinecap="round" />
                <circle cx="16" cy="11" r="2.5" fill="#F06B42" />
              </svg>
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-sentinel font-bold text-lg tracking-tight text-earth-900">
                  ClearSky
                </span>
                <span className="font-sans font-semibold text-[10px] tracking-wider text-accent-600 uppercase px-1.5 py-0.5 rounded-md bg-accent-500/10 border border-accent-500/20">
                  Intelligence
                </span>
              </div>
            </div>
          </NavLink>

          {/* Navigation Links (Desktop) */}
          <nav className="hidden lg:flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-sans font-medium transition-all ${
                      isActive
                        ? 'bg-accent-500/10 text-accent-600 border border-accent-500/20 shadow-warm-sm font-semibold'
                        : 'text-earth-500 hover:text-earth-800 hover:bg-warm-100'
                    }`
                  }
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>

          {/* Right Controls: Mode Badge + Refresh Trigger + Mobile Hamburger */}
          <div className="flex items-center gap-2">
            {/* System Status Mode Badge */}
            <div
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-[11px] font-mono border font-semibold tracking-wider bg-warm-100 border-warm-300 text-earth-600"
              title={modeInfo.tooltip}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-sage-500 animate-pulse" />
              <span>{modeInfo.label}</span>
            </div>

            {/* Ingestion Refresh Action */}
            {onRefresh && (
              <button
                onClick={onRefresh}
                disabled={isRefreshing}
                className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-sans font-medium text-earth-500 hover:text-earth-800 bg-white hover:bg-warm-100 active:scale-95 border border-warm-300 rounded-xl transition-all disabled:opacity-50 shadow-warm-sm"
                title="Trigger ingestion pipeline and re-score monitored zones"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-accent-500' : ''}`} />
                <span className="hidden sm:inline">Refresh</span>
              </button>
            )}

            {/* Mobile Hamburger Menu Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden p-1.5 rounded-xl text-earth-500 hover:text-earth-800 hover:bg-warm-100 border border-warm-300 transition-colors ml-1"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>

        </div>

        {/* Mobile Navigation Dropdown */}
        {mobileMenuOpen && (
          <nav className="lg:hidden py-3 border-t border-warm-200 grid grid-cols-2 sm:grid-cols-3 gap-1.5 pb-4 animate-fade-down">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={() => setMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-sans font-medium transition-all ${
                      isActive
                        ? 'bg-accent-500/10 text-accent-600 border border-accent-500/20 font-semibold shadow-warm-sm'
                        : 'text-earth-600 hover:bg-warm-100'
                    }`
                  }
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>
        )}
      </div>
    </header>
  );
};

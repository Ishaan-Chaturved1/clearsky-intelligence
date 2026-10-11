import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { TopNavigation } from './components/TopNavigation';
import { Footer } from './components/Footer';
import { LandingPage } from './pages/LandingPage';
import { DashboardPage } from './pages/DashboardPage';
import { InvestigationsPage } from './pages/InvestigationsPage';
import { ActionPlanPage } from './pages/ActionPlanPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { MapExplorerPage } from './pages/MapExplorerPage';
import { WaterAnalyticsPage } from './pages/WaterAnalyticsPage';
import { MethodologyPage } from './pages/MethodologyPage';
import { DataSourcesPage } from './pages/DataSourcesPage';
import { AboutPage } from './pages/AboutPage';
import { CitizenWatchPage } from './pages/CitizenWatchPage';
import { InvestigationPage } from './pages/InvestigationPage';
import { api } from './services/api';
import { DataMode } from './types';

const AppLayout: React.FC = () => {
  const [dataMode, setDataMode] = useState<DataMode>('DEMO');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const location = useLocation();
  const isLanding = location.pathname === '/';

  useEffect(() => {
    api.getOverview()
      .then((ov) => {
        if (ov?.data_mode) setDataMode(ov.data_mode);
      })
      .catch(() => {});
  }, []);

  const handleRefresh = async () => {
    try {
      setIsRefreshing(true);
      const res = await api.adminRefresh();
      if (res?.data_mode) {
        setDataMode(res.data_mode as DataMode);
      }
      window.location.reload();
    } catch (err) {
      console.error('Refresh failed:', err);
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#f8fafc] text-slate-800 antialiased selection:bg-emerald-500 selection:text-white">
      
      {/* Floating Pill Top Navigation */}
      <div className="sticky top-3 z-50 px-3 sm:px-6 lg:px-8 max-w-[1780px] w-full mx-auto pointer-events-auto">
        <TopNavigation
          dataMode={dataMode}
          onRefresh={handleRefresh}
          isRefreshing={isRefreshing}
        />
      </div>

      {/* Main Routed Content */}
      <main className="flex-1 w-full max-w-[1780px] mx-auto px-3 sm:px-6 lg:px-8 py-2 sm:py-3">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/investigations" element={<InvestigationsPage />} />
          <Route path="/investigation" element={<InvestigationPage />} />
          <Route path="/citizen-watch" element={<CitizenWatchPage />} />
          <Route path="/action-plan" element={<ActionPlanPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          
          {/* Preserved Core Tools */}
          <Route path="/landing" element={<LandingPage />} />
          <Route path="/map" element={<MapExplorerPage />} />
          <Route path="/water-analytics" element={<WaterAnalyticsPage />} />
          <Route path="/methodology" element={<MethodologyPage />} />
          <Route path="/data-sources" element={<DataSourcesPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      {/* Persistent Footer */}
      {!isLanding && <Footer />}

    </div>
  );
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
};

export default App;

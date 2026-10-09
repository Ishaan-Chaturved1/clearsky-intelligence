import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';
import { LandingPage } from './pages/LandingPage';
import { DashboardPage } from './pages/DashboardPage';
import { MapExplorerPage } from './pages/MapExplorerPage';
import { WaterAnalyticsPage } from './pages/WaterAnalyticsPage';
import { MethodologyPage } from './pages/MethodologyPage';
import { DataSourcesPage } from './pages/DataSourcesPage';
import { AboutPage } from './pages/AboutPage';
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
    <div className="min-h-screen flex flex-col bg-warm-50 text-earth-700">
      
      {/* Hide Navbar on Landing Page */}
      {!isLanding && (
        <Navbar
          dataMode={dataMode}
          onRefresh={handleRefresh}
          isRefreshing={isRefreshing}
        />
      )}

      {/* Main Routed Content */}
      <main className={isLanding ? '' : 'flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8'}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/map" element={<MapExplorerPage />} />
          <Route path="/water-analytics" element={<WaterAnalyticsPage />} />
          <Route path="/methodology" element={<MethodologyPage />} />
          <Route path="/data-sources" element={<DataSourcesPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      {/* Persistent Footer for workspace pages */}
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

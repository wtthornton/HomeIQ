import React, { useState, useEffect } from 'react';
import { AlertBanner } from './AlertBanner';
import { ErrorBoundary } from './ErrorBoundary';
import * as Tabs from './tabs';

// Tab configuration
const TAB_COMPONENTS: Record<string, React.FC<Tabs.TabProps>> = {
  overview: Tabs.OverviewTab,
  setup: Tabs.SetupTab,
  services: Tabs.ServicesTab,
  dependencies: Tabs.DependenciesTab,
  devices: Tabs.DevicesTab,
  events: Tabs.EventsTab,
  logs: Tabs.LogsTab,
  sports: Tabs.SportsTab,
  'data-sources': Tabs.DataSourcesTab,
  energy: Tabs.EnergyTab,
  analytics: Tabs.AnalyticsTab,
  alerts: Tabs.AlertsTab,
  hygiene: Tabs.HygieneTab,
  configuration: Tabs.ConfigurationTab,
};

const TAB_CONFIG = [
  { id: 'overview', label: '📊 Overview', icon: '📊', shortLabel: 'Overview' },
  { id: 'setup', label: '🏥 Setup & Health', icon: '🏥', shortLabel: 'Setup' },
  { id: 'services', label: '🔧 Services', icon: '🔧', shortLabel: 'Services' },
  { id: 'dependencies', label: '🔗 Dependencies', icon: '🔗', shortLabel: 'Deps' },
  { id: 'devices', label: '📱 Devices', icon: '📱', shortLabel: 'Devices' },
  { id: 'events', label: '📡 Events', icon: '📡', shortLabel: 'Events' },
  { id: 'logs', label: '📜 Logs', icon: '📜', shortLabel: 'Logs' },
  { id: 'sports', label: '🏈 Sports', icon: '🏈', shortLabel: 'Sports' },
  { id: 'data-sources', label: '🌐 Data Sources', icon: '🌐', shortLabel: 'Data' },
  { id: 'energy', label: '⚡ Energy', icon: '⚡', shortLabel: 'Energy' },
  { id: 'analytics', label: '📈 Analytics', icon: '📈', shortLabel: 'Analytics' },
  { id: 'alerts', label: '🚨 Alerts', icon: '🚨', shortLabel: 'Alerts' },
  { id: 'hygiene', label: '🧼 Device Hygiene', icon: '🧼', shortLabel: 'Hygiene' },
  { id: 'configuration', label: '⚙️ Configuration', icon: '⚙️', shortLabel: 'Config' },
];

export const Dashboard: React.FC = () => {
  const automationUiUrl = import.meta.env.VITE_AI_AUTOMATION_UI_URL;
  // State management
  const [darkMode, setDarkMode] = useState(false);
  const [selectedTimeRange, setSelectedTimeRange] = useState('1h');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [selectedTab, setSelectedTab] = useState('overview');
  
  // Apply theme to document
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  // Handle custom navigation events from modals
  useEffect(() => {
    const handleNavigateToTab = (event: CustomEvent) => {
      const { tabId } = event.detail;
      setSelectedTab(tabId);
    };

    window.addEventListener('navigateToTab', handleNavigateToTab as EventListener);
    return () => window.removeEventListener('navigateToTab', handleNavigateToTab as EventListener);
  }, []);

  // One-time cleanup of deprecated Custom tab localStorage
  useEffect(() => {
    const cleanupKey = 'dashboard-layout-cleanup-v1';
    const hasCleanedUp = localStorage.getItem(cleanupKey);
    
    if (!hasCleanedUp) {
      const oldLayout = localStorage.getItem('dashboard-layout');
      if (oldLayout) {
        localStorage.removeItem('dashboard-layout');
        if (import.meta.env.MODE !== 'production') {
          console.log('✅ Cleaned up deprecated Custom tab layout from localStorage');
        }
      }
      localStorage.setItem(cleanupKey, 'true');
    }
  }, []);

  // Get the current tab component
  const TabComponent = TAB_COMPONENTS[selectedTab] || Tabs.OverviewTab;

  return (
    <div data-testid="dashboard-root" className={`min-h-screen ${darkMode ? 'bg-gradient-to-br from-gray-900 via-gray-900 to-gray-800' : 'bg-gradient-to-br from-gray-50 via-white to-gray-100'} transition-all duration-500`}>
      {/* Header - Mobile Optimized with gradient accent */}
      <div data-testid="dashboard-header" className={`${darkMode ? 'bg-gradient-to-r from-gray-800 to-gray-900 border-gray-700' : 'bg-gradient-to-r from-white to-gray-50 border-gray-200'} shadow-lg border-b transition-all duration-300 backdrop-blur-sm`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Mobile: Stacked Layout, Desktop: Side by Side */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center py-4 sm:py-6 gap-4">
            <div className="w-full sm:w-auto">
              <h1 data-testid="dashboard-title" className={`text-xl sm:text-2xl lg:text-3xl font-bold ${darkMode ? 'text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-300' : 'text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-cyan-600'} animate-fade-in`}>
                🏠 HomeIQ Dashboard
              </h1>
              <p className={`text-xs sm:text-sm ${darkMode ? 'text-gray-300' : 'text-gray-600'} hidden sm:block mt-1`}>
                AI-Powered Home Assistant Intelligence & Monitoring Platform
              </p>
              <p className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'} sm:hidden mt-1`}>
                AI-Powered HA Monitor
              </p>
            </div>
            
            {/* Controls - Mobile Optimized */}
            <div className="flex items-center justify-between sm:justify-end w-full sm:w-auto gap-2 sm:gap-3">
              {/* Theme Toggle */}
              <button
                data-testid="theme-toggle"
                onClick={() => setDarkMode(!darkMode)}
                className={`p-2.5 rounded-lg min-w-[44px] min-h-[44px] flex items-center justify-center ${darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-100 hover:bg-gray-200'} transition-colors duration-200`}
                title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
                aria-label={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
              >
                {darkMode ? '☀️' : '🌙'}
              </button>
              
              {/* Auto Refresh Toggle */}
              <button
                data-testid="auto-refresh-toggle"
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`p-2.5 rounded-lg min-w-[44px] min-h-[44px] flex items-center justify-center ${autoRefresh ? (darkMode ? 'bg-green-700 hover:bg-green-600' : 'bg-green-100 hover:bg-green-200') : (darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-100 hover:bg-gray-200')} transition-colors duration-200`}
                title={autoRefresh ? 'Auto Refresh: ON' : 'Auto Refresh: OFF'}
                aria-label={autoRefresh ? 'Auto Refresh: ON' : 'Auto Refresh: OFF'}
              >
                {autoRefresh ? '🔄' : '⏸️'}
              </button>
              
              {/* Time Range Selector */}
              <select
                data-testid="time-range-selector"
                value={selectedTimeRange}
                onChange={(e) => setSelectedTimeRange(e.target.value)}
                className={`px-2 sm:px-3 py-2 rounded-lg border text-sm min-h-[44px] ${darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300 text-gray-900'} transition-colors duration-200`}
                aria-label="Select time range"
              >
                <option value="15m">15m</option>
                <option value="1h">1h</option>
                <option value="6h">6h</option>
                <option value="24h">24h</option>
                <option value="7d">7d</option>
              </select>
              
                {/* AI Automation UI Link */}
                {automationUiUrl && (
                  <a
                    href={automationUiUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`px-3 py-2 rounded-lg border text-sm min-h-[44px] flex items-center gap-2 shadow-md hover:shadow-lg transform hover:scale-105 active:scale-95 ${darkMode ? 'bg-gradient-to-r from-blue-600 to-blue-700 border-blue-500 text-white hover:from-blue-500 hover:to-blue-600' : 'bg-gradient-to-r from-blue-500 to-blue-600 border-blue-400 text-white hover:from-blue-600 hover:to-blue-700'} transition-all duration-200`}
                    title="Open AI Automation UI"
                  >
                    <span className="text-lg">🤖</span>
                    <span className="hidden sm:inline font-semibold">AI Automations</span>
                  </a>
                )}
              
              {/* Last Updated - Hidden on mobile */}
              <div className="text-right hidden md:block">
                <p className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                  Last updated
                </p>
                <p className={`text-sm font-medium ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                  {new Date().toLocaleTimeString('en-US', {
                    hour12: true,
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                  })}
                </p>
              </div>
            </div>
          </div>
          
          {/* Navigation Tabs - Mobile Optimized with enhanced styling */}
          <div data-testid="tab-navigation" className="border-t border-gray-200 dark:border-gray-700 pt-4 -mx-4 px-4 sm:mx-0 sm:px-0">
            <div className="flex space-x-2 sm:space-x-3 overflow-x-auto pb-2 scrollbar-hide">
              {TAB_CONFIG.map((tab) => (
                <button
                  key={tab.id}
                  data-testid={`tab-${tab.id}`}
                  data-tab={tab.id}
                  onClick={() => setSelectedTab(tab.id)}
                  className={`flex-shrink-0 px-3 sm:px-4 py-2.5 rounded-lg font-medium transition-all duration-200 text-sm sm:text-base min-h-[44px] transform hover:scale-105 active:scale-95 ${
                    selectedTab === tab.id
                      ? darkMode
                        ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-lg'
                        : 'bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-lg'
                      : darkMode
                        ? 'text-gray-300 hover:text-white hover:bg-gray-700/50 bg-gray-800/30'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100 bg-white/50'
                  }`}
                >
                  <span className="hidden sm:inline">{tab.label}</span>
                  <span className="sm:hidden">{tab.icon} {tab.shortLabel}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main data-testid="dashboard-content" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Alert Banner (Epic 17.4) */}
        <AlertBanner darkMode={darkMode} />
        
        {/* Tab Content - Wrapped with Error Boundary */}
        <ErrorBoundary
          onError={(error, errorInfo) => {
            console.error('Tab rendering error:', error);
            console.error('Stack:', errorInfo.componentStack);
          }}
        >
          <TabComponent darkMode={darkMode} />
        </ErrorBoundary>
      </main>
    </div>
  );
};

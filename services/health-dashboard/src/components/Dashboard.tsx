import React, { useState, useEffect, useMemo, useCallback, Suspense, lazy } from 'react';
import { AlertBanner } from './AlertBanner';
import { ErrorBoundary } from './ErrorBoundary';
import { LoadingSpinner } from './LoadingSpinner';
import * as Tabs from './tabs';
import { TabIcons, ThemeIcons, Icon, RefreshCw, Pause } from './ui/icons';

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
  validation: Tabs.ValidationTab,
  synergies: Tabs.SynergiesTab,
  configuration: Tabs.ConfigurationTab,
};

const TAB_CONFIG = [
  { id: 'overview', label: 'Overview', shortLabel: 'Overview' },
  { id: 'setup', label: 'Setup & Health', shortLabel: 'Setup' },
  { id: 'services', label: 'Services', shortLabel: 'Services' },
  { id: 'dependencies', label: 'Dependencies', shortLabel: 'Deps' },
  { id: 'devices', label: 'Devices', shortLabel: 'Devices' },
  { id: 'events', label: 'Events', shortLabel: 'Events' },
  { id: 'logs', label: 'Logs', shortLabel: 'Logs' },
  { id: 'sports', label: 'Sports', shortLabel: 'Sports' },
  { id: 'data-sources', label: 'Data Sources', shortLabel: 'Data' },
  { id: 'energy', label: 'Energy', shortLabel: 'Energy' },
  { id: 'analytics', label: 'Analytics', shortLabel: 'Analytics' },
  { id: 'alerts', label: 'Alerts', shortLabel: 'Alerts' },
  { id: 'hygiene', label: 'Device Hygiene', shortLabel: 'Hygiene' },
  { id: 'validation', label: 'HA Validation', shortLabel: 'Validation' },
  { id: 'synergies', label: 'Synergies', shortLabel: 'Synergies' },
  { id: 'configuration', label: 'Configuration', shortLabel: 'Config' },
] as const;

export const Dashboard: React.FC = () => {
  const automationUiUrl = import.meta.env.VITE_AI_AUTOMATION_UI_URL;
  // State management
  const [darkMode, setDarkMode] = useState(() => {
    // Check localStorage for saved preference, or system preference
    // Wrapped in try-catch for SSR and localStorage errors
    try {
      if (typeof window !== 'undefined') {
        const saved = localStorage.getItem('darkMode');
        if (saved !== null) return saved === 'true';
        return window.matchMedia('(prefers-color-scheme: dark)').matches;
      }
    } catch (error) {
      console.warn('Failed to read darkMode from localStorage:', error);
    }
    return false; // Default to light mode
  });
  const [selectedTimeRange, setSelectedTimeRange] = useState('1h');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [selectedTab, setSelectedTab] = useState(() => {
    // Restore from URL hash or default to overview
    const hash = window.location.hash.slice(1);
    return hash && TAB_COMPONENTS[hash] ? hash : 'overview';
  });
  
  // Apply theme to document and persist preference
  useEffect(() => {
    try {
      if (darkMode) {
        document.documentElement.classList.add('dark');
        localStorage.setItem('darkMode', 'true');
      } else {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('darkMode', 'false');
      }
    } catch (error) {
      console.warn('Failed to save darkMode to localStorage:', error);
      // Still apply theme to document even if localStorage fails
      if (darkMode) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
    }
  }, [darkMode]);
  
  // Update URL hash when tab changes (for bookmarking/sharing)
  useEffect(() => {
    if (selectedTab && selectedTab !== 'overview') {
      window.history.replaceState(null, '', `#${selectedTab}`);
    } else {
      window.history.replaceState(null, '', window.location.pathname);
    }
  }, [selectedTab]);
  
  // Listen for system theme changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (e: MediaQueryListEvent) => {
      // Only auto-switch if user hasn't manually set preference
      try {
        const saved = localStorage.getItem('darkMode');
        if (saved === null) {
          setDarkMode(e.matches);
        }
      } catch (error) {
        console.warn('Failed to read darkMode from localStorage:', error);
        setDarkMode(e.matches);
      }
    };
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

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
    try {
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
    } catch (error) {
      console.warn('Failed to cleanup deprecated localStorage:', error);
    }
  }, []);

  // Memoize tab component to prevent unnecessary re-renders
  const TabComponent = useMemo(() => {
    return TAB_COMPONENTS[selectedTab] || Tabs.OverviewTab;
  }, [selectedTab]);
  
  // Memoize tab change handler
  const handleTabChange = useCallback((tabId: string) => {
    setSelectedTab(tabId);
    // Focus management for accessibility
    const tabButton = document.querySelector(`[data-tab="${tabId}"]`) as HTMLElement;
    if (tabButton) {
      tabButton.focus();
    }
  }, []);
  
  // Keyboard navigation for tabs
  const handleTabKeyDown = useCallback((e: React.KeyboardEvent, tabId: string, index: number) => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      e.preventDefault();
      const tabs = TAB_CONFIG;
      const currentIndex = tabs.findIndex(t => t.id === tabId);
      let nextIndex: number;
      
      if (e.key === 'ArrowRight') {
        nextIndex = currentIndex === tabs.length - 1 ? 0 : currentIndex + 1;
      } else {
        nextIndex = currentIndex === 0 ? tabs.length - 1 : currentIndex - 1;
      }
      
      handleTabChange(tabs[nextIndex].id);
    } else if (e.key === 'Home') {
      e.preventDefault();
      handleTabChange(TAB_CONFIG[0].id);
    } else if (e.key === 'End') {
      e.preventDefault();
      handleTabChange(TAB_CONFIG[TAB_CONFIG.length - 1].id);
    }
  }, [handleTabChange]);

  return (
    <div data-testid="dashboard-root" className={`min-h-screen bg-background transition-colors duration-150`}>
      {/* Header - Clean, minimal */}
      <div data-testid="dashboard-header" className={`bg-card border-b border-border`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Mobile: Stacked Layout, Desktop: Side by Side */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center py-4 sm:py-6 gap-4">
            <div className="w-full sm:w-auto">
              <h1 data-testid="dashboard-title" className={`text-xl sm:text-2xl lg:text-3xl font-bold ${darkMode ? 'text-white' : 'text-foreground'}`}>
                HomeIQ Dashboard
              </h1>
              <p className={`text-xs sm:text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'} hidden sm:block mt-0.5`}>
                Home Assistant Intelligence Platform
              </p>
              <p className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'} sm:hidden mt-0.5`}>
                HA Monitor
              </p>
            </div>
            
            {/* Controls - Mobile Optimized */}
            <div className="flex items-center justify-between sm:justify-end w-full sm:w-auto gap-2 sm:gap-2">
              {/* Theme Toggle */}
              <button
                data-testid="theme-toggle"
                onClick={() => setDarkMode(!darkMode)}
                className={`p-2 rounded min-w-[36px] min-h-[36px] flex items-center justify-center ${darkMode ? 'bg-secondary hover:bg-secondary/80' : 'bg-secondary hover:bg-secondary/80'} transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2`}
                title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
                aria-label={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
                aria-pressed={darkMode}
              >
                <Icon icon={darkMode ? ThemeIcons.light : ThemeIcons.dark} size="sm" />
              </button>
              
              {/* Auto Refresh Toggle */}
              <button
                data-testid="auto-refresh-toggle"
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`p-2 rounded min-w-[36px] min-h-[36px] flex items-center justify-center ${autoRefresh ? 'bg-status-healthy/20 text-status-healthy' : (darkMode ? 'bg-secondary' : 'bg-secondary')} transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2`}
                title={autoRefresh ? 'Auto Refresh: ON' : 'Auto Refresh: OFF'}
                aria-label={autoRefresh ? 'Auto Refresh: ON' : 'Auto Refresh: OFF'}
                aria-pressed={autoRefresh}
              >
                <Icon icon={autoRefresh ? RefreshCw : Pause} size="sm" className={autoRefresh ? 'animate-spin-slow' : ''} />
              </button>
              
              {/* Time Range Selector */}
              <select
                data-testid="time-range-selector"
                value={selectedTimeRange}
                onChange={(e) => setSelectedTimeRange(e.target.value)}
                className={`px-2 sm:px-3 py-2 rounded-lg border text-sm min-h-[44px] ${darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300 text-gray-900'} transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
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
                  className={`px-3 py-2 rounded text-sm min-h-[36px] flex items-center gap-2 bg-primary text-primary-foreground hover:bg-primary/90 transition-colors duration-150`}
                  title="Open AI Automation UI"
                >
                  <Icon icon={TabIcons.services} size="sm" />
                  <span className="hidden sm:inline font-medium">AI Automations</span>
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
          
          {/* Navigation Tabs - Clean, icon-based */}
          <nav data-testid="tab-navigation" role="tablist" aria-label="Dashboard navigation tabs" className="border-t border-border pt-3 -mx-4 px-4 sm:mx-0 sm:px-0">
            <div className="flex gap-1 overflow-x-auto pb-2 scrollbar-hide">
              {TAB_CONFIG.map((tab, index) => {
                const TabIcon = TabIcons[tab.id as keyof typeof TabIcons];
                return (
                  <button
                    key={tab.id}
                    data-testid={`tab-${tab.id}`}
                    data-tab={tab.id}
                    role="tab"
                    aria-selected={selectedTab === tab.id}
                    aria-controls={`tabpanel-${tab.id}`}
                    tabIndex={selectedTab === tab.id ? 0 : -1}
                    onClick={() => handleTabChange(tab.id)}
                    onKeyDown={(e) => handleTabKeyDown(e, tab.id, index)}
                    className={`flex-shrink-0 px-3 py-1.5 rounded text-sm font-medium transition-colors duration-150 min-h-[32px] flex items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1 ${
                      selectedTab === tab.id
                        ? 'bg-primary text-primary-foreground'
                        : darkMode
                          ? 'text-muted-foreground hover:text-foreground hover:bg-secondary'
                          : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
                    }`}
                  >
                    {TabIcon && <Icon icon={TabIcon} size="sm" />}
                    <span className="hidden sm:inline">{tab.label}</span>
                    <span className="sm:hidden">{tab.shortLabel}</span>
                  </button>
                );
              })}
            </div>
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <main data-testid="dashboard-content" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Alert Banner (Epic 17.4) */}
        <AlertBanner darkMode={darkMode} />
        
        {/* Tab Content - Wrapped with Error Boundary and Suspense for lazy loading */}
        <ErrorBoundary
          onError={(error, errorInfo) => {
            console.error('Tab rendering error:', error);
            console.error('Stack:', errorInfo.componentStack);
          }}
        >
          <div
            id={`tabpanel-${selectedTab}`}
            role="tabpanel"
            aria-labelledby={`tab-${selectedTab}`}
            className="focus:outline-none"
            tabIndex={0}
          >
            <Suspense fallback={<LoadingSpinner />}>
              <TabComponent darkMode={darkMode} />
            </Suspense>
          </div>
        </ErrorBoundary>
      </main>
    </div>
  );
};

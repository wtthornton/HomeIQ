import React, { useState, useEffect, useMemo, useCallback, Suspense } from 'react';
import { AlertBanner } from './AlertBanner';
import { ErrorBoundary } from './ErrorBoundary';
import { LoadingSpinner } from './LoadingSpinner';
import * as Tabs from './tabs';
import { TabIcons, ThemeIcons, Icon, RefreshCw, Pause } from './ui/icons';

/** Only allow http/https URLs to prevent javascript: or data: injection */
function sanitizeUrl(url: string | undefined, fallback: string): string {
  const value = url || fallback;
  try {
    const parsed = new URL(value, window.location.origin);
    if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
      return parsed.href;
    }
  } catch { /* invalid URL */ }
  return fallback;
}

// Grouped navigation structure (FR-3.1, FR-3.3, FR-3.4)
const NAV_GROUPS = [
  {
    id: 'overview',
    label: 'Overview',
    icon: 'overview',
    tabs: [{ id: 'overview', label: 'Overview' }],
  },
  {
    id: 'infrastructure',
    label: 'Infrastructure',
    icon: 'services',
    tabs: [
      { id: 'services', label: 'Services' },
      { id: 'groups', label: 'Groups' },
      { id: 'dependencies', label: 'Dependencies' },
      { id: 'configuration', label: 'Configuration' },
    ],
  },
  {
    id: 'devices-data',
    label: 'Devices & Data',
    icon: 'devices',
    tabs: [
      { id: 'devices', label: 'Devices' },
      { id: 'events', label: 'Events' },
      { id: 'data-sources', label: 'Data Feeds' },
      { id: 'energy', label: 'Energy' },
      { id: 'sports', label: 'Sports' },
    ],
  },
  {
    id: 'quality',
    label: 'Quality',
    icon: 'alerts',
    tabs: [
      { id: 'alerts', label: 'Alerts' },
      { id: 'hygiene', label: 'Device Health' },
      { id: 'validation', label: 'Automation Checks' },
      { id: 'evaluation', label: 'AI Performance' },
    ],
  },
  {
    id: 'logs-analytics',
    label: 'Logs & Analytics',
    icon: 'logs',
    tabs: [
      { id: 'logs', label: 'Logs' },
      { id: 'analytics', label: 'Analytics' },
    ],
  },
] as const;

// All valid tab IDs for URL hash validation
const ALL_TAB_IDS: string[] = NAV_GROUPS.flatMap(g => g.tabs.map(t => t.id));

// Tab components — synergies and setup removed from routing (FR-3.3, FR-3.2)
const TAB_COMPONENTS: Record<string, React.FC<Tabs.TabProps>> = {
  overview: Tabs.OverviewTab,
  services: Tabs.ServicesTab,
  groups: Tabs.GroupsTab,
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
  evaluation: Tabs.EvaluationTab,
  configuration: Tabs.ConfigurationTab,
};

/** Find the group that contains a given tab ID */
function findGroupForTab(tabId: string): string | undefined {
  return NAV_GROUPS.find(g => g.tabs.some(t => t.id === tabId))?.id;
}

export const Dashboard: React.FC = () => {
  const automationUiUrl = import.meta.env.VITE_AI_AUTOMATION_UI_URL;

  // State management
  const [darkMode, setDarkMode] = useState(() => {
    try {
      if (typeof window !== 'undefined') {
        const saved = localStorage.getItem('darkMode');
        if (saved !== null) return saved === 'true';
        return window.matchMedia('(prefers-color-scheme: dark)').matches;
      }
    } catch (error) {
      console.warn('Failed to read darkMode from localStorage:', error);
    }
    return false;
  });
  const [selectedTimeRange, setSelectedTimeRange] = useState('1h');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [selectedTab, setSelectedTab] = useState(() => {
    const hash = window.location.hash.slice(1);
    return hash && TAB_COMPONENTS[hash] ? hash : 'overview';
  });
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(() => new Date());

  // Sidebar group expand/collapse state
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(() => {
    const currentGroup = findGroupForTab(selectedTab);
    return new Set(currentGroup ? [currentGroup] : ['overview']);
  });

  const toggleGroup = useCallback((groupId: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  }, []);

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
      if (darkMode) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
    }
  }, [darkMode]);

  // Update URL hash when tab changes
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
            console.log('Cleaned up deprecated Custom tab layout from localStorage');
          }
        }
        localStorage.setItem(cleanupKey, 'true');
      }
    } catch (error) {
      console.warn('Failed to cleanup deprecated localStorage:', error);
    }
  }, []);

  // Memoize tab component
  const TabComponent = useMemo(() => {
    return TAB_COMPONENTS[selectedTab] || Tabs.OverviewTab;
  }, [selectedTab]);

  // Tab change handler — auto-expands the parent group
  const handleTabChange = useCallback((tabId: string) => {
    setSelectedTab(tabId);
    setMobileNavOpen(false);
    // Auto-expand the group containing the new tab
    const group = findGroupForTab(tabId);
    if (group) {
      setExpandedGroups(prev => {
        if (prev.has(group)) return prev;
        const next = new Set(prev);
        next.add(group);
        return next;
      });
    }
    // Focus management for accessibility
    const tabButton = document.querySelector(`[data-tab="${tabId}"]`) as HTMLElement;
    if (tabButton) {
      tabButton.focus();
    }
  }, []);

  // Keyboard navigation for sidebar items
  const handleTabKeyDown = useCallback((e: React.KeyboardEvent, tabId: string) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      const idx = ALL_TAB_IDS.indexOf(tabId);
      let nextIdx: number;
      if (e.key === 'ArrowDown') {
        nextIdx = idx === ALL_TAB_IDS.length - 1 ? 0 : idx + 1;
      } else {
        nextIdx = idx === 0 ? ALL_TAB_IDS.length - 1 : idx - 1;
      }
      handleTabChange(ALL_TAB_IDS[nextIdx]);
    } else if (e.key === 'Home') {
      e.preventDefault();
      handleTabChange(ALL_TAB_IDS[0]);
    } else if (e.key === 'End') {
      e.preventDefault();
      handleTabChange(ALL_TAB_IDS[ALL_TAB_IDS.length - 1]);
    }
  }, [handleTabChange]);

  // Update last refreshed timestamp periodically
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => setLastRefreshed(new Date()), 30_000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  /** Render the grouped nav list (shared between sidebar and mobile drawer) */
  const renderNavGroups = () => (
    <>
      {NAV_GROUPS.map((group) => (
        <div key={group.id} className="mb-1">
          {group.tabs.length === 1 ? (
            <button
              data-tab={group.tabs[0].id}
              onClick={() => handleTabChange(group.tabs[0].id)}
              onKeyDown={(e) => handleTabKeyDown(e, group.tabs[0].id)}
              className={`w-full text-left px-4 py-2 text-sm font-medium transition-colors ${
                selectedTab === group.tabs[0].id
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
              }`}
            >
              {group.label}
            </button>
          ) : (
            <>
              <button
                onClick={() => toggleGroup(group.id)}
                className="w-full flex items-center justify-between px-4 py-2 text-xs font-semibold tracking-wide text-muted-foreground hover:text-foreground"
              >
                {group.label}
                <span className="text-[10px]">{expandedGroups.has(group.id) ? '\u25BC' : '\u25B6'}</span>
              </button>
              {expandedGroups.has(group.id) && (
                <div className="ml-2">
                  {group.tabs.map((tab) => (
                    <button
                      key={tab.id}
                      data-tab={tab.id}
                      data-testid={`tab-${tab.id}`}
                      onClick={() => handleTabChange(tab.id)}
                      onKeyDown={(e) => handleTabKeyDown(e, tab.id)}
                      className={`w-full text-left px-4 py-1.5 text-sm transition-colors ${
                        selectedTab === tab.id
                          ? 'bg-primary text-primary-foreground rounded'
                          : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      ))}
    </>
  );

  /** Sidebar footer controls (theme, refresh, time range) */
  const renderControls = () => (
    <div className="p-3 border-t border-border space-y-2">
      <div className="flex items-center gap-2">
        {/* Theme Toggle */}
        <button
          data-testid="theme-toggle"
          onClick={() => setDarkMode(!darkMode)}
          className={`p-2 rounded min-w-[36px] min-h-[36px] flex items-center justify-center bg-secondary hover:bg-secondary/80 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2`}
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
          className={`p-2 rounded min-w-[36px] min-h-[36px] flex items-center justify-center ${
            autoRefresh ? 'bg-status-healthy/20 text-status-healthy' : 'bg-secondary'
          } transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2`}
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
          className={`flex-1 px-2 py-2 rounded-lg border text-sm min-h-[36px] ${
            darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300 text-gray-900'
          } transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
          aria-label="Select time range"
        >
          <option value="15m">15m</option>
          <option value="1h">1h</option>
          <option value="6h">6h</option>
          <option value="24h">24h</option>
          <option value="7d">7d</option>
        </select>
      </div>

      {/* Last Refreshed */}
      <div className="text-xs text-muted-foreground text-center">
        Updated {lastRefreshed.toLocaleTimeString('en-US', {
          hour12: true,
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        })}
      </div>

      {/* AI Automation UI Link */}
      {automationUiUrl && (
        <a
          href={automationUiUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-2 px-3 py-2 rounded text-sm bg-primary text-primary-foreground hover:bg-primary/90 transition-colors duration-150"
          title="Open AI Automation UI"
        >
          <Icon icon={TabIcons.services} size="sm" />
          <span className="font-medium">AI Automations</span>
        </a>
      )}
    </div>
  );

  return (
    <div data-testid="dashboard-root" className="flex min-h-screen bg-background transition-colors duration-150">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-0 focus:left-0 focus:z-50 focus:bg-primary focus:text-primary-foreground focus:px-4 focus:py-2">
        Skip to main content
      </a>
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex flex-col w-60 border-r border-border bg-card shrink-0 sticky top-0 h-screen">
        {/* Header */}
        <div className="p-4 border-b border-border">
          <h1 data-testid="dashboard-title" className="text-lg font-bold text-foreground">HomeIQ Health</h1>
          <p className="text-xs text-muted-foreground mt-0.5">Health Dashboard</p>
          {/* Cross-app switcher */}
          <div className="flex gap-1 mt-2">
            <a
              href={sanitizeUrl(import.meta.env.VITE_AI_AUTOMATION_UI_URL, 'http://localhost:3001')}
              className="px-2 py-1 text-xs font-medium rounded text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
            >
              HomeIQ
            </a>
            <span className="px-2 py-1 text-xs font-medium rounded bg-primary text-primary-foreground">
              Health
            </span>
            <a
              href={sanitizeUrl(import.meta.env.VITE_OBSERVABILITY_URL, 'http://localhost:8501')}
              className="px-2 py-1 text-xs font-medium rounded text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
            >
              Ops
            </a>
          </div>
        </div>

        {/* Nav groups */}
        <nav className="flex-1 overflow-y-auto py-2" aria-label="Dashboard navigation">
          {renderNavGroups()}
        </nav>

        {/* Controls in sidebar footer */}
        {renderControls()}
      </aside>

      {/* Mobile nav overlay */}
      {mobileNavOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setMobileNavOpen(false)}
          />
          {/* Drawer */}
          <aside className="absolute inset-y-0 left-0 w-72 bg-card border-r border-border flex flex-col shadow-lg">
            <div className="p-4 border-b border-border flex items-center justify-between">
              <div>
                <h1 className="text-lg font-bold text-foreground">HomeIQ Health</h1>
                <p className="text-xs text-muted-foreground mt-0.5">Health Dashboard</p>
              </div>
              <button
                onClick={() => setMobileNavOpen(false)}
                className="p-2 rounded hover:bg-secondary text-muted-foreground"
                aria-label="Close navigation"
              >
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M5 5l10 10M15 5L5 15" />
                </svg>
              </button>
            </div>
            <nav className="flex-1 overflow-y-auto py-2" aria-label="Dashboard navigation">
              {renderNavGroups()}
            </nav>
            {renderControls()}
          </aside>
        </div>
      )}

      {/* Main content */}
      <main id="main-content" className="flex-1 min-w-0 overflow-y-auto">
        {/* Mobile top bar */}
        <div data-testid="dashboard-header" className="md:hidden bg-card border-b border-border px-4 py-3 flex items-center justify-between">
          <button
            onClick={() => setMobileNavOpen(true)}
            className="p-2 rounded hover:bg-secondary text-foreground"
            aria-label="Open navigation"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 6h18M3 12h18M3 18h18" />
            </svg>
          </button>
          <h1 className="text-base font-bold text-foreground">HomeIQ Health</h1>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setDarkMode(!darkMode)}
              className="p-2 rounded bg-secondary hover:bg-secondary/80"
              aria-label={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            >
              <Icon icon={darkMode ? ThemeIcons.light : ThemeIcons.dark} size="sm" />
            </button>
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`p-2 rounded ${autoRefresh ? 'bg-status-healthy/20 text-status-healthy' : 'bg-secondary'}`}
              aria-label={autoRefresh ? 'Auto Refresh: ON' : 'Auto Refresh: OFF'}
            >
              <Icon icon={autoRefresh ? RefreshCw : Pause} size="sm" className={autoRefresh ? 'animate-spin-slow' : ''} />
            </button>
          </div>
        </div>

        {/* Tab content */}
        <div data-testid="dashboard-content" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Alert Banner */}
          <AlertBanner darkMode={darkMode} />

          {/* Tab Content */}
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
        </div>
      </main>
    </div>
  );
};

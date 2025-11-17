import React, { useEffect, useState } from 'react';

// TypeScript interfaces for type safety (Phase 2.1)
interface IntegrationHealth {
  status: 'healthy' | 'degraded' | 'unhealthy' | 'paused';
  issues: string[];
  lastUpdate: string;
  responseTime?: number;
  uptime?: string;
}

interface IntegrationAnalytics {
  platform: string;
  device_count: number;
  entity_count: number;
  entity_breakdown: Array<{
    domain: string;
    count: number;
  }>;
  timestamp: string;
}

interface IntegrationPerformance {
  platform: string;
  period: string;
  events_per_minute: number;
  error_rate: number;
  avg_response_time: number | null;
  device_discovery_status: 'active' | 'paused' | 'unknown';
  total_events: number;
  total_errors: number;
  timestamp: string;
}

interface IntegrationDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  platform: string;
  deviceCount: number;
  healthy: boolean;
  darkMode: boolean;
}

// Status color system helper
const getStatusColors = (status: 'healthy' | 'degraded' | 'unhealthy' | 'paused', darkMode: boolean) => {
  const colors = {
    healthy: {
      bg: darkMode ? 'bg-green-900/30' : 'bg-green-100',
      border: darkMode ? 'border-green-700' : 'border-green-300',
      text: darkMode ? 'text-green-200' : 'text-green-800',
      icon: '✅'
    },
    degraded: {
      bg: darkMode ? 'bg-yellow-900/30' : 'bg-yellow-100',
      border: darkMode ? 'border-yellow-700' : 'border-yellow-300',
      text: darkMode ? 'text-yellow-200' : 'text-yellow-800',
      icon: '⚠️'
    },
    unhealthy: {
      bg: darkMode ? 'bg-red-900/30' : 'bg-red-100',
      border: darkMode ? 'border-red-700' : 'border-red-300',
      text: darkMode ? 'text-red-200' : 'text-red-800',
      icon: '❌'
    },
    paused: {
      bg: darkMode ? 'bg-gray-700' : 'bg-gray-100',
      border: darkMode ? 'border-gray-600' : 'border-gray-300',
      text: darkMode ? 'text-gray-200' : 'text-gray-800',
      icon: '⏸️'
    }
  };
  return colors[status];
};

// Domain icon helper
const getDomainIcon = (domain: string): string => {
  const icons: Record<string, string> = {
    light: '💡',
    sensor: '📊',
    switch: '🔌',
    climate: '🌡️',
    camera: '📷',
    lock: '🔒',
    cover: '🚪',
    binary_sensor: '🔘',
    media_player: '🎵',
    vacuum: '🤖',
    fan: '🌀',
    automation: '⚙️',
    button: '🔳',
    number: '🔢',
    select: '📋',
  };
  return icons[domain] || '🔌';
};

export const IntegrationDetailsModal: React.FC<IntegrationDetailsModalProps> = ({
  isOpen,
  onClose,
  platform,
  deviceCount,
  healthy,
  darkMode
}) => {
  const [analytics, setAnalytics] = useState<IntegrationAnalytics | null>(null);
  const [performance, setPerformance] = useState<IntegrationPerformance | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [performancePeriod, setPerformancePeriod] = useState('1h');

  const status = healthy ? 'healthy' : 'degraded';
  const colors = getStatusColors(status, darkMode);

  // Fetch analytics and performance data
  useEffect(() => {
    if (!isOpen) return;

    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch analytics - use authenticated API client
        const API_KEY = import.meta.env.VITE_API_KEY || 'hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR';
        const analyticsResponse = await fetch(`/api/integrations/${platform}/analytics`, {
          headers: {
            'Authorization': `Bearer ${API_KEY}`,
            'X-HomeIQ-API-Key': API_KEY,
          },
        });
        if (!analyticsResponse.ok) {
          // If API endpoint doesn't exist or fails, create a default response
          setAnalytics({
            platform,
            device_count: deviceCount,
            entity_count: 0,
            entity_breakdown: [],
            timestamp: new Date().toISOString(),
          });
        } else {
          const analyticsData = await analyticsResponse.json();
          
          // Ensure all required fields exist with defaults
          const safeAnalyticsData = {
            platform: analyticsData?.platform || platform,
            device_count: analyticsData?.device_count ?? deviceCount,
            entity_count: analyticsData?.entity_count ?? 0,
            entity_breakdown: Array.isArray(analyticsData?.entity_breakdown) 
              ? analyticsData.entity_breakdown 
              : [],
            timestamp: analyticsData?.timestamp || new Date().toISOString(),
          };
          setAnalytics(safeAnalyticsData);
        }
        
        // Fetch performance metrics
        const performanceResponse = await fetch(`/api/integrations/${platform}/performance?period=${performancePeriod}`, {
          headers: {
            'Authorization': `Bearer ${API_KEY}`,
            'X-HomeIQ-API-Key': API_KEY,
          },
        });
        if (performanceResponse.ok) {
          const performanceData = await performanceResponse.json();
          setPerformance(performanceData);
        }
      } catch (err) {
        console.error('Error fetching integration data:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [isOpen, platform, performancePeriod]);

  // Auto-focus on open (accessibility)
  useEffect(() => {
    if (isOpen) {
      const firstFocusable = document.querySelector('[data-modal-focus]') as HTMLElement;
      firstFocusable?.focus();
    }
  }, [isOpen]);

  // Escape key handling
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
    }
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="integration-modal-title"
    >
      <div 
        className={`max-w-2xl w-full max-h-[90vh] overflow-auto rounded-lg shadow-2xl ${
          darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
        } border`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className={`sticky top-0 p-6 border-b ${
          darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
        }`}>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-3xl">{colors.icon}</span>
                <h2 
                  id="integration-modal-title"
                  className={`text-2xl font-bold ${darkMode ? 'text-gray-100' : 'text-gray-900'}`}
                >
                  {platform.charAt(0).toUpperCase() + platform.slice(1)} Integration
                </h2>
              </div>
              <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${colors.bg} ${colors.text}`}>
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </div>
            </div>
            <button
              onClick={onClose}
              data-modal-focus
              className={`text-3xl ${
                darkMode ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900'
              } transition-colors`}
              aria-label="Close modal"
            >
              ×
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
              <span className={`ml-4 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                Loading analytics...
              </span>
            </div>
          ) : error ? (
            <div className={`p-4 rounded-lg ${
              darkMode ? 'bg-red-900/20 border-red-800' : 'bg-red-50 border-red-200'
            } border`}>
              <p className="text-red-600 dark:text-red-400">
                ⚠️ Failed to load analytics: {error}
              </p>
            </div>
          ) : analytics ? (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className={`p-4 rounded-lg border ${
                  darkMode ? 'bg-gray-750 border-gray-600' : 'bg-gray-50 border-gray-200'
                }`}>
                  <div className={`text-sm mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    Devices
                  </div>
                  <div className="text-3xl font-bold">{analytics.device_count}</div>
                </div>
                <div className={`p-4 rounded-lg border ${
                  darkMode ? 'bg-gray-750 border-gray-600' : 'bg-gray-50 border-gray-200'
                }`}>
                  <div className={`text-sm mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    Entities
                  </div>
                  <div className="text-3xl font-bold">{analytics.entity_count}</div>
                </div>
              </div>

              {/* Performance Metrics - Phase 3.2 */}
              {performance && (
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className={`text-lg font-semibold ${
                      darkMode ? 'text-gray-200' : 'text-gray-800'
                    }`}>
                      Performance Metrics
                    </h3>
                    <select
                      value={performancePeriod}
                      onChange={(e) => setPerformancePeriod(e.target.value)}
                      className={`px-3 py-1 rounded-lg border text-sm ${
                        darkMode
                          ? 'bg-gray-700 border-gray-600 text-gray-200'
                          : 'bg-white border-gray-300 text-gray-900'
                      }`}
                    >
                      <option value="1h">Last Hour</option>
                      <option value="24h">Last 24 Hours</option>
                      <option value="7d">Last 7 Days</option>
                    </select>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    {/* Events per Minute */}
                    <div className={`p-4 rounded-lg border text-center ${
                      darkMode ? 'bg-gray-750 border-gray-600' : 'bg-gray-50 border-gray-200'
                    }`}>
                      <div className={`text-2xl font-bold mb-1 ${
                        darkMode ? 'text-blue-400' : 'text-blue-600'
                      }`}>
                        {performance.events_per_minute}
                      </div>
                      <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        Events/min
                      </div>
                    </div>
                    
                    {/* Error Rate */}
                    <div className={`p-4 rounded-lg border text-center ${
                      darkMode ? 'bg-gray-750 border-gray-600' : 'bg-gray-50 border-gray-200'
                    }`}>
                      <div className={`text-2xl font-bold mb-1 ${
                        performance.error_rate > 5 ? 'text-red-500' : 'text-green-500'
                      }`}>
                        {performance.error_rate}%
                      </div>
                      <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        Error Rate
                      </div>
                    </div>
                    
                    {/* Response Time */}
                    <div className={`p-4 rounded-lg border text-center ${
                      darkMode ? 'bg-gray-750 border-gray-600' : 'bg-gray-50 border-gray-200'
                    }`}>
                      <div className={`text-2xl font-bold mb-1 ${
                        darkMode ? 'text-yellow-400' : 'text-yellow-600'
                      }`}>
                        {performance.avg_response_time ? `${performance.avg_response_time}ms` : 'N/A'}
                      </div>
                      <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        Avg Response
                      </div>
                    </div>
                    
                    {/* Discovery Status */}
                    <div className={`p-4 rounded-lg border text-center ${
                      darkMode ? 'bg-gray-750 border-gray-600' : 'bg-gray-50 border-gray-200'
                    }`}>
                      <div className="text-2xl font-bold mb-1">
                        {performance.device_discovery_status === 'active' ? '✅' : 
                          performance.device_discovery_status === 'paused' ? '⏸️' : '❓'}
                      </div>
                      <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        Discovery
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Entity Breakdown */}
              <div className="mb-6">
                <h3 className={`text-lg font-semibold mb-3 ${
                  darkMode ? 'text-gray-200' : 'text-gray-800'
                }`}>
                  Entity Breakdown by Domain
                </h3>
                {analytics.entity_breakdown && analytics.entity_breakdown.length > 0 ? (
                  <div className="space-y-2">
                    {analytics.entity_breakdown.map(({ domain, count }) => (
                      <div
                        key={domain}
                        className={`flex items-center justify-between p-3 rounded-lg border ${
                          darkMode ? 'bg-gray-750 border-gray-600' : 'bg-gray-50 border-gray-200'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-xl">{getDomainIcon(domain)}</span>
                          <span className={`font-medium ${
                            darkMode ? 'text-gray-200' : 'text-gray-900'
                          }`}>
                            {domain}
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`text-sm ${
                            darkMode ? 'text-gray-400' : 'text-gray-600'
                          }`}>
                            {count} {count === 1 ? 'entity' : 'entities'}
                          </span>
                          <div className={`h-2 rounded-full ${
                            darkMode ? 'bg-gray-700' : 'bg-gray-200'
                          }`} style={{ width: '100px' }}>
                            <div 
                              className="h-2 rounded-full bg-blue-500"
                              style={{ 
                                width: `${Math.min(100, analytics.entity_count > 0 ? (count / analytics.entity_count) * 100 : 0)}%` 
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className={`text-center py-8 ${
                    darkMode ? 'text-gray-500' : 'text-gray-400'
                  }`}>
                    No entities found for this integration
                  </div>
                )}
              </div>

              {/* Quick Actions - Enhanced Phase 3.1 */}
              <div className="mb-4">
                <h3 className={`text-lg font-semibold mb-3 ${
                  darkMode ? 'text-gray-200' : 'text-gray-800'
                }`}>
                  Quick Actions
                </h3>
                <div className="grid grid-cols-2 gap-2">
                  {/* Primary Actions */}
                  <button
                    onClick={() => {
                      // Navigate to Devices tab with filter
                      const url = new URL(window.location.href);
                      url.searchParams.set('integration', platform);
                      window.history.replaceState({}, '', url.toString());
                      
                      // Trigger custom event for tab navigation
                      window.dispatchEvent(new CustomEvent('navigateToTab', { 
                        detail: { tabId: 'devices' } 
                      }));
                      onClose();
                    }}
                    className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
                      darkMode
                        ? 'bg-blue-600 hover:bg-blue-700 text-white'
                        : 'bg-blue-600 hover:bg-blue-700 text-white'
                    }`}
                    title="View all devices for this integration"
                  >
                    <span>📱</span>
                    <span>View Devices</span>
                  </button>
                  
                  <button
                    onClick={() => {
                      window.dispatchEvent(new CustomEvent('navigateToTab', { 
                        detail: { tabId: 'logs' } 
                      }));
                      onClose();
                    }}
                    className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
                      darkMode
                        ? 'bg-gray-700 hover:bg-gray-600 text-gray-200'
                        : 'bg-gray-100 hover:bg-gray-200 text-gray-800'
                    }`}
                    title="View logs for this integration"
                  >
                    <span>📜</span>
                    <span>View Logs</span>
                  </button>

                  {/* Secondary Actions */}
                  <button
                    onClick={() => {
                      window.dispatchEvent(new CustomEvent('navigateToTab', { 
                        detail: { tabId: 'events' } 
                      }));
                      onClose();
                    }}
                    className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
                      darkMode
                        ? 'bg-gray-700 hover:bg-gray-600 text-gray-200'
                        : 'bg-gray-100 hover:bg-gray-200 text-gray-800'
                    }`}
                    title="View events for this integration"
                  >
                    <span>📊</span>
                    <span>View Events</span>
                  </button>

                  <button
                    onClick={() => {
                      window.dispatchEvent(new CustomEvent('navigateToTab', { 
                        detail: { tabId: 'analytics' } 
                      }));
                      onClose();
                    }}
                    className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
                      darkMode
                        ? 'bg-gray-700 hover:bg-gray-600 text-gray-200'
                        : 'bg-gray-100 hover:bg-gray-200 text-gray-800'
                    }`}
                    title="View analytics for this integration"
                  >
                    <span>📈</span>
                    <span>Analytics</span>
                  </button>

                  {/* Utility Actions */}
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(platform);
                      // Could show a toast notification here
                    }}
                    className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
                      darkMode
                        ? 'bg-gray-700 hover:bg-gray-600 text-gray-200'
                        : 'bg-gray-100 hover:bg-gray-200 text-gray-800'
                    }`}
                    title="Copy integration name to clipboard"
                  >
                    <span>📋</span>
                    <span>Copy Name</span>
                  </button>

                  <button
                    onClick={() => {
                      window.open(`https://www.home-assistant.io/integrations/${platform}/`, '_blank');
                    }}
                    className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
                      darkMode
                        ? 'bg-gray-700 hover:bg-gray-600 text-gray-200'
                        : 'bg-gray-100 hover:bg-gray-200 text-gray-800'
                    }`}
                    title="Open Home Assistant documentation"
                  >
                    <span>📚</span>
                    <span>HA Docs</span>
                  </button>
                </div>
              </div>

              {/* Timestamp */}
              <div className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                Last updated: {new Date(analytics.timestamp).toLocaleString()}
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
};


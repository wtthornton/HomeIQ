/**
 * DataSourcesPanel Component
 * 
 * Displays status and metrics for all external data sources
 * Epic 13.1: Data Sources Status Dashboard
 */

import React, { useState, useEffect } from 'react';
import { useDataSources } from '../hooks/useDataSources';
import { DataSourcesHealthMap } from '../types';
import { SkeletonCard } from './skeletons';
import { DataSourceConfigModal } from './DataSourceConfigModal';
import { adminApi } from '../services/api';

interface DataSourcesPanelProps {
  darkMode: boolean;
}

// Data source definitions for display
type DataSourceKey = keyof DataSourcesHealthMap;

const DATA_SOURCE_DEFINITIONS: Array<{ id: DataSourceKey; name: string; icon: string; }> = [
  { id: 'weather', name: 'Weather API', icon: '☁️' },
  { id: 'sports', name: 'Sports API', icon: '⚽' },
  { id: 'carbonIntensity', name: 'Carbon Intensity', icon: '🌱' },
  { id: 'airQuality', name: 'Air Quality', icon: '💨' },
  { id: 'electricityPricing', name: 'Electricity Pricing', icon: '⚡' },
  { id: 'calendar', name: 'Calendar Service', icon: '📅' },
  { id: 'smartMeter', name: 'Smart Meter', icon: '📈' }
];

// Service port mapping
const SERVICE_PORTS: Record<string, number> = {
  weather: 8009,
  carbonIntensity: 8010,
  electricityPricing: 8011,
  airQuality: 8012,
  calendar: 8013,
  smartMeter: 8014,
};

export const DataSourcesPanel: React.FC<DataSourcesPanelProps> = ({ darkMode }) => {
  const { dataSources, loading, error, refetch } = useDataSources(30000);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [currentWeather, setCurrentWeather] = useState<any>(null);
  const [testingService, setTestingService] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ service: string; success: boolean; message: string } | null>(null);
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [configServiceId, setConfigServiceId] = useState<string>('');
  const [configServiceName, setConfigServiceName] = useState<string>('');

  useEffect(() => {
    setLastUpdate(new Date());
  }, [dataSources]);

  // Simple weather fetch (Epic 31, Story 31.5)
  useEffect(() => {
    const fetchWeather = async () => {
      try {
        const res = await fetch('/weather/current-weather');
        if (res.ok) {
          setCurrentWeather(await res.json());
        }
      } catch (e) {
        if (import.meta.env.MODE !== 'production') {
          console.log('Weather API unavailable');
        }
      }
    };

    fetchWeather();
    const interval = setInterval(fetchWeather, 15 * 60 * 1000); // 15 minutes
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'healthy':
        return darkMode ? 'text-green-400' : 'text-green-600';
      case 'degraded':
        return darkMode ? 'text-yellow-400' : 'text-yellow-600';
      case 'error':
        return darkMode ? 'text-red-400' : 'text-red-600';
      default:
        return darkMode ? 'text-gray-400' : 'text-gray-600';
    }
  };

  const getStatusIcon = (status: string, statusDetail?: string, credentialsConfigured?: boolean): string => {
    // Check for missing credentials first
    if (statusDetail === 'credentials_missing' || credentialsConfigured === false) {
      return '🔑';  // Key icon for missing credentials
    }
    
    switch (status) {
      case 'healthy':
        return '🟢';
      case 'degraded':
        return '🟡';
      case 'error':
        return '🔴';
      default:
        return '⚪';
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${Math.round(bytes / Math.pow(k, i))} ${sizes[i]}`;
  };

  const formatTimestamp = (timestamp?: string): string => {
    if (!timestamp) return 'Never';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} hr ago`;
    return `${Math.floor(diffHours / 24)} days ago`;
  };

  const handleTest = async (serviceId: string, serviceName: string) => {
    const port = SERVICE_PORTS[serviceId];
    if (!port) {
      setTestResult({
        service: serviceId,
        success: false,
        message: `Service port not configured for ${serviceId}`,
      });
      // Clear error message after 5 seconds
      setTimeout(() => {
        setTestResult(null);
      }, 5000);
      return;
    }

    setTestingService(serviceId);
    setTestResult(null);

    try {
      const result = await adminApi.testServiceHealth(serviceName, port);
      setTestResult({
        service: serviceId,
        success: result.success,
        message: result.message,
      });

      // Refresh data sources after successful test
      if (result.success) {
        setTimeout(() => {
          refetch();
        }, 1000);
      }
    } catch (err: any) {
      setTestResult({
        service: serviceId,
        success: false,
        message: err.message || 'Test failed with unknown error',
      });
    } finally {
      setTestingService(null);
      // Clear test result after 8 seconds (longer for errors)
      setTimeout(() => {
        setTestResult(null);
      }, 8000);
    }
  };

  const handleConfigure = (serviceId: string, serviceName: string) => {
    setConfigServiceId(serviceId);
    setConfigServiceName(serviceName);
    setConfigModalOpen(true);
  };

  const handleConfigSave = async (config: Record<string, any>) => {
    // In a real implementation, this would call the admin-api to update configuration
    // For now, we'll just show a message that .env needs to be updated
    throw new Error('Configuration must be updated in .env file. See documentation for details.');
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className={`rounded-lg shadow-md p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-48 mb-6 shimmer"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonCard key={`datasource-${i}`} variant="default" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`rounded-lg shadow-md p-6 ${
        darkMode ? 'bg-red-900/20 border border-red-500/30' : 'bg-red-50 border border-red-200'
      }`}>
        <div className="flex items-center gap-3">
          <span className="text-2xl">⚠️</span>
          <div className="flex-1">
            <h3 className={`font-semibold ${darkMode ? 'text-red-200' : 'text-red-800'}`}>
              Error Loading Data Sources
            </h3>
            <p className={`text-sm ${darkMode ? 'text-red-300' : 'text-red-600'}`}>
              {error}
            </p>
          </div>
          <button
            onClick={refetch}
            className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className={`rounded-lg shadow-md p-6 ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'} flex items-center gap-2`}>
              <span>🌐</span>
              External Data Sources
            </h2>
            <p className={`mt-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Monitor external API integrations and performance
            </p>
          </div>
          <div className={`text-right ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            <p className="text-sm">Last updated</p>
            <p className="text-sm font-medium">{lastUpdate.toLocaleTimeString()}</p>
          </div>
        </div>

        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span>🟢</span>
            <span className={darkMode ? 'text-gray-300' : 'text-gray-700'}>
              {dataSources ? Object.values(dataSources).filter(s => s?.status === 'healthy').length : 0} Healthy
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span>🟡</span>
            <span className={darkMode ? 'text-gray-300' : 'text-gray-700'}>
              {dataSources ? Object.values(dataSources).filter(s => s?.status === 'degraded').length : 0} Degraded
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span>🔴</span>
            <span className={darkMode ? 'text-gray-300' : 'text-gray-700'}>
              {dataSources ? Object.values(dataSources).filter(s => s?.status === 'error').length : 0} Error
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span>⚪</span>
            <span className={darkMode ? 'text-gray-300' : 'text-gray-700'}>
              {dataSources ? Object.values(dataSources).filter(s => s?.status === 'unknown' || s === null).length : 0} Unknown
            </span>
          </div>
        </div>
      </div>

      {/* Data Source Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {DATA_SOURCE_DEFINITIONS.map(sourceDef => {
          const source = dataSources?.[sourceDef.id] ?? null;
          const status = source?.status || 'unknown';
          const statusDetail = source?.status_detail;
          const credentialsConfigured = source?.credentials_configured;
          const apiUsage = source?.api_usage;

          return (
            <div
              key={sourceDef.id}
              className={`rounded-lg shadow-md p-6 transition-all hover:shadow-lg ${
                darkMode ? 'bg-gray-800' : 'bg-white'
              }`}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{sourceDef.icon}</span>
                  <div>
                    <h3 className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                      {sourceDef.name}
                    </h3>
                    <div className={`flex items-center gap-2 text-sm ${getStatusColor(status)}`}>
                      <span>{getStatusIcon(status, statusDetail, credentialsConfigured)}</span>
                      <span className="capitalize">
                        {statusDetail === 'credentials_missing' || credentialsConfigured === false
                          ? 'Credentials Needed'
                          : status}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Current Weather (Epic 31, Story 31.5) */}
              {sourceDef.id === 'weather' && currentWeather && (
                <div className="mb-4">
                  <div className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'} mb-2`}>
                  Current Conditions
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className={`text-3xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                      {currentWeather.temperature?.toFixed(1)}°C
                    </span>
                    <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      {currentWeather.condition}
                    </span>
                  </div>
                  <div className={`text-xs mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                  Humidity: {currentWeather.humidity}% • {currentWeather.location}
                  </div>
                </div>
              )}

              {/* API Usage */}
              {apiUsage && (
                <div className="mb-4">
                  <div className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'} mb-2`}>
                  API Usage Today
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                      {apiUsage.calls_today}
                    </span>
                    {apiUsage.quota_limit && (
                      <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      / {apiUsage.quota_limit}
                      </span>
                    )}
                  </div>
                  {apiUsage.quota_percentage !== undefined && apiUsage.quota_percentage > 0 && (
                    <div className="mt-2">
                      <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${
                            apiUsage.quota_percentage > 80
                              ? 'bg-red-500'
                              : apiUsage.quota_percentage > 60
                                ? 'bg-yellow-500'
                                : 'bg-green-500'
                          }`}
                          style={{ width: `${apiUsage.quota_percentage}%` }}
                        />
                      </div>
                      <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        {apiUsage.quota_percentage}% of quota used
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* Performance Metrics */}
              <div className="mb-4 space-y-2">
                <div className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                Performance
                </div>
                <div className="space-y-1 text-sm">
                  <div className={`flex justify-between ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    <span>Status:</span>
                    <span className={`font-medium capitalize ${getStatusColor(status)}`}>
                      {status}
                    </span>
                  </div>
                  <div className={`flex justify-between ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    <span>Service:</span>
                    <span className="font-medium">{source?.service || 'N/A'}</span>
                  </div>
                  <div className={`flex justify-between ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    <span>Last Check:</span>
                    <span className="font-medium">{formatTimestamp(source?.timestamp)}</span>
                  </div>
                  {source?.uptime_seconds !== undefined && source.uptime_seconds > 0 && (
                    <div className={`flex justify-between ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      <span>Uptime:</span>
                      <span className="font-medium">{formatTimestamp(source.uptime_seconds)}</span>
                    </div>
                  )}
                </div>
              </div>


              {/* Test Result Message */}
              {testResult && testResult.service === sourceDef.id && (
                <div className={`mt-4 p-3 rounded-lg text-sm ${
                  testResult.success
                    ? darkMode
                      ? 'bg-green-900/20 border border-green-500/30 text-green-200'
                      : 'bg-green-50 border border-green-200 text-green-800'
                    : darkMode
                      ? 'bg-red-900/20 border border-red-500/30 text-red-200'
                      : 'bg-red-50 border border-red-200 text-red-800'
                }`}>
                  {testResult.success ? '✅' : '❌'} {testResult.message}
                </div>
              )}

              {/* Actions */}
              <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex gap-2">
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    handleConfigure(sourceDef.id, sourceDef.name);
                  }}
                  className={`flex-1 px-3 py-2 text-sm rounded transition-colors ${
                    darkMode
                      ? 'bg-gray-700 hover:bg-gray-600 text-white'
                      : 'bg-gray-100 hover:bg-gray-200 text-gray-900'
                  }`}
                  title={`Configure ${sourceDef.name} settings`}
                >
                  Configure
                </button>
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    handleTest(sourceDef.id, source?.service || sourceDef.name);
                  }}
                  disabled={testingService === sourceDef.id}
                  className={`flex-1 px-3 py-2 text-sm rounded transition-colors ${
                    testingService === sourceDef.id
                      ? 'bg-gray-400 cursor-not-allowed text-white'
                      : darkMode
                        ? 'bg-blue-600 hover:bg-blue-700 text-white'
                        : 'bg-blue-500 hover:bg-blue-600 text-white'
                  }`}
                  title={testingService === sourceDef.id ? 'Testing service health...' : `Test ${sourceDef.name} service health`}
                >
                  {testingService === sourceDef.id ? 'Testing...' : 'Test'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Configuration Tip */}
      <div className={`rounded-lg p-4 ${darkMode ? 'bg-blue-900/20 border border-blue-500/30' : 'bg-blue-50 border border-blue-200'}`}>
        <div className="flex items-start gap-3">
          <span className="text-xl">💡</span>
          <div className={darkMode ? 'text-blue-200' : 'text-blue-800'}>
            <p className="font-medium">Configuration Tip</p>
            <p className="text-sm mt-1">
              Configure API credentials and settings using the Configure button on each service card, or update the .env file directly.
            </p>
          </div>
        </div>
      </div>

      {/* Configuration Modal */}
      <DataSourceConfigModal
        isOpen={configModalOpen}
        onClose={() => {
          setConfigModalOpen(false);
          setConfigServiceId('');
          setConfigServiceName('');
        }}
        serviceName={configServiceName}
        serviceId={configServiceId}
        darkMode={darkMode}
        onSave={handleConfigSave}
      />
    </div>
  );
};


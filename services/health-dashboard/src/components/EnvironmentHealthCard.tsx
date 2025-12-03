/**
 * Environment Health Card Component
 * 
 * Context7 Pattern: React component with useState/useEffect hooks and proper error handling
 */
import React from 'react';
import { useEnvironmentHealth } from '../hooks/useEnvironmentHealth';
import { HealthStatus, IntegrationStatus } from '../types/health';

export const EnvironmentHealthCard: React.FC = () => {
  const { health, loading, error, refetch } = useEnvironmentHealth();

  const formatCheckDetailLabel = (label: string) =>
    label
      .split('_')
      .map(part => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ');

  const formatCheckDetailValue = (value: unknown): string => {
    if (value === null || value === undefined) return 'N/A';
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (typeof value === 'number') return value.toString();
    if (typeof value === 'string') return value;
    if (Array.isArray(value)) {
      return value.length ? value.join(', ') : 'None';
    }

    try {
      return JSON.stringify(value);
    } catch (err) {
      console.warn('Failed to stringify check detail value', err);
      return 'Unavailable';
    }
  };

  if (loading && !health) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          <span className="ml-3 text-gray-600 dark:text-gray-400">Loading health status...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-start">
            <svg className="h-6 w-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="ml-3 flex-1">
              <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
                Error Loading Health Status
              </h3>
              <p className="mt-1 text-sm text-red-700 dark:text-red-300">{error}</p>
              <button
                onClick={refetch}
                className="mt-3 text-sm font-medium text-red-600 dark:text-red-400 hover:text-red-500"
              >
                Try Again →
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!health) return null;

  // Calculate health status color
  const getHealthColor = (status: HealthStatus) => {
    switch (status) {
      case HealthStatus.HEALTHY:
        return 'text-green-600 bg-green-100 dark:bg-green-900/30';
      case HealthStatus.WARNING:
        return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30';
      case HealthStatus.CRITICAL:
        return 'text-red-600 bg-red-100 dark:bg-red-900/30';
      default:
        return 'text-gray-600 bg-gray-100 dark:bg-gray-900/30';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 50) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getIntegrationStatusColor = (status: IntegrationStatus) => {
    switch (status) {
      case IntegrationStatus.HEALTHY:
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
      case IntegrationStatus.WARNING:
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
      case IntegrationStatus.ERROR:
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
      case IntegrationStatus.NOT_CONFIGURED:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <div className={`p-2 rounded-lg ${getHealthColor(health.ha_status ?? HealthStatus.UNKNOWN)}`}>
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Environment Health
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Last updated: {health.timestamp ? new Date(health.timestamp).toLocaleTimeString() : 'Unknown'}
            </p>
          </div>
        </div>
        
        {/* Refresh Button */}
        <button
          onClick={refetch}
          className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
          title="Refresh health status"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      {/* Health Score */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Overall Health Score</span>
          <span className={`text-2xl font-bold ${getScoreColor(health.health_score ?? 0)}`}>
            {health.health_score ?? 0}/100
          </span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
          <div
            className={`h-2.5 rounded-full transition-all duration-500 ${
              (health.health_score ?? 0) >= 80 ? 'bg-green-600' :
                (health.health_score ?? 0) >= 50 ? 'bg-yellow-600' : 'bg-red-600'
            }`}
            style={{ width: `${health.health_score ?? 0}%` }}
          ></div>
        </div>
      </div>

      {/* HA Core Status */}
      <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">Home Assistant Core</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {health.ha_version || 'Version unknown'}
            </p>
          </div>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getHealthColor(health.ha_status ?? HealthStatus.UNKNOWN)}`}>
            {health.ha_status ?? 'Unknown'}
          </span>
        </div>
      </div>

      {/* Integrations Status */}
      <div className="mb-6">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          Integrations ({health.integrations?.length ?? 0})
        </h3>
        <div className="space-y-2">
          {(health.integrations ?? []).map((integration, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg"
            >
              <div className="flex items-center space-x-3">
                <div className={`h-2 w-2 rounded-full ${
                  integration.status === IntegrationStatus.HEALTHY ? 'bg-green-500' :
                    integration.status === IntegrationStatus.WARNING ? 'bg-yellow-500' :
                      integration.status === IntegrationStatus.ERROR ? 'bg-red-500' :
                        'bg-gray-400'
                }`}></div>
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {integration.name}
                  </p>
                  {integration.error_message && (
                    <p className="text-xs text-red-600 dark:text-red-400">
                      {integration.error_message}
                    </p>
                  )}
                  {integration.check_details && Object.keys(integration.check_details).length > 0 && (
                    <dl className="mt-2 space-y-1 text-xs text-gray-500 dark:text-gray-400">
                      {Object.entries(integration.check_details)
                        .slice(0, 5)
                        .map(([key, value]) => {
                        // Highlight monitoring method for Zigbee2MQTT
                          const isMonitoringMethod = key === 'monitoring_method';
                          const isMqttSubscription = isMonitoringMethod && value === 'mqtt_subscription';
                        
                          return (
                            <div key={key} className={`flex justify-between gap-2 ${isMqttSubscription ? 'bg-green-50 dark:bg-green-900/20 px-2 py-1 rounded' : ''}`}>
                              <dt className={`font-medium ${isMqttSubscription ? 'text-green-700 dark:text-green-300' : 'text-gray-600 dark:text-gray-300'}`}>
                                {formatCheckDetailLabel(key)}
                                {isMqttSubscription && (
                                  <span className="ml-1 text-green-600 dark:text-green-400" title="Real-time MQTT subscription">
                                  ⚡
                                  </span>
                                )}
                              </dt>
                              <dd className={`text-right max-w-[180px] break-words ${isMqttSubscription ? 'text-green-700 dark:text-green-300 font-medium' : 'text-gray-500 dark:text-gray-400'}`}>
                                {formatCheckDetailValue(value)}
                              </dd>
                            </div>
                          );
                        })}
                    </dl>
                  )}
                </div>
              </div>
              <span className={`px-2 py-1 rounded text-xs font-medium ${getIntegrationStatusColor(integration.status)}`}>
                {integration.status.replace(/_/g, ' ')}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Performance Metrics */}
      {health.performance && (
        <div className="mb-6">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          Performance Metrics
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
              <p className="text-xs text-gray-500 dark:text-gray-400">Response Time</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">
                {health.performance.response_time_ms?.toFixed(1) ?? 'N/A'}ms
              </p>
            </div>
            {health.performance.cpu_usage_percent !== undefined && (
              <div className="p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                <p className="text-xs text-gray-500 dark:text-gray-400">CPU Usage</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">
                  {health.performance.cpu_usage_percent.toFixed(1)}%
                </p>
              </div>
            )}
            {health.performance.memory_usage_mb !== undefined && (
              <div className="p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                <p className="text-xs text-gray-500 dark:text-gray-400">Memory</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">
                  {health.performance.memory_usage_mb.toFixed(0)}MB
                </p>
              </div>
            )}
            {health.performance.uptime_seconds !== undefined && (
              <div className="p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                <p className="text-xs text-gray-500 dark:text-gray-400">Uptime</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">
                  {Math.floor(health.performance.uptime_seconds / 3600)}h
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Issues Detected */}
      {health.issues_detected && Array.isArray(health.issues_detected) && health.issues_detected.length > 0 && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-200 mb-2">
            ⚠️ Issues Detected ({health.issues_detected.length})
          </h3>
          <ul className="space-y-1">
            {health.issues_detected.map((issue, index) => (
              <li key={index} className="text-sm text-yellow-700 dark:text-yellow-300">
                • {issue}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};


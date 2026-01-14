/**
 * ServiceMetrics Component
 * 
 * Displays service-specific metrics in organized groups
 * 
 * Prototype: Basic implementation for websocket-ingestion
 */

import React from 'react';
import { useServiceMetrics } from '../hooks/useServiceMetrics';
import { getServiceMetricsConfig } from '../config/serviceMetricsConfig';
import { MetricGroup } from './MetricGroup';
import type { ServiceMetrics } from '../types/serviceMetrics';

export interface ServiceMetricsProps {
  serviceId: string;
  darkMode: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export const ServiceMetrics: React.FC<ServiceMetricsProps> = ({
  serviceId,
  darkMode,
  autoRefresh = false,
  refreshInterval = 5000,
}) => {
  // Debug logging
  console.log('[ServiceMetrics] Component rendering with serviceId:', serviceId);
  
  const { metrics, loading, error, lastUpdated, refresh } = useServiceMetrics({
    serviceId,
    autoRefresh,
    refreshInterval,
    enabled: true,
  });

  console.log('[ServiceMetrics] Hook state:', { loading, error, hasMetrics: !!metrics });

  const config = getServiceMetricsConfig(serviceId);
  console.log('[ServiceMetrics] Config found:', !!config);

  // If no configuration, show message
  if (!config) {
    return (
      <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
        Service-specific metrics not yet configured for this service.
      </div>
    );
  }

  // Loading state with skeleton
  if (loading && !metrics) {
    return (
      <div className="space-y-4">
        <div className="flex items-center space-x-2">
          <div className={`animate-spin rounded-full h-4 w-4 border-b-2 ${darkMode ? 'border-blue-400' : 'border-blue-600'}`}></div>
          <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Loading metrics...
          </span>
        </div>
        {/* Skeleton loading */}
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="space-y-2">
              <div className={`h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/3 animate-pulse`}></div>
              <div className={`h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2 animate-pulse`}></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Error state with retry
  if (error && !metrics) {
    return (
      <div className={`rounded-lg p-4 ${darkMode ? 'bg-red-900/20 border border-red-800' : 'bg-red-50 border border-red-200'}`}>
        <div className="flex items-start space-x-3">
          <svg className={`w-5 h-5 mt-0.5 ${darkMode ? 'text-red-400' : 'text-red-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="flex-1">
            <div className={`text-sm font-semibold ${darkMode ? 'text-red-300' : 'text-red-700'}`}>
              Error Loading Metrics
            </div>
            <div className={`text-xs mt-1 ${darkMode ? 'text-red-400' : 'text-red-600'}`}>
              {error}
            </div>
            <button
              onClick={refresh}
              className={`mt-3 px-3 py-1.5 text-xs rounded-lg font-medium transition-colors ${
                darkMode
                  ? 'bg-red-600 hover:bg-red-700 text-white'
                  : 'bg-red-600 hover:bg-red-700 text-white'
              }`}
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  // No metrics available
  if (!metrics) {
    return (
      <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
        Metrics not available for this service.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with refresh button */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          {loading && metrics && (
            <div className={`animate-spin rounded-full h-3 w-3 border-b-2 ${darkMode ? 'border-blue-400' : 'border-blue-600'}`}></div>
          )}
          <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            {loading && metrics ? 'Updating...' : lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString()}` : ''}
          </span>
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
            darkMode
              ? 'bg-blue-600 hover:bg-blue-700 text-white'
              : 'bg-blue-600 hover:bg-blue-700 text-white'
          }`}
          title="Refresh metrics"
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {/* Metrics Groups */}
      {config.groups.map((group, index) => (
        <MetricGroup
          key={index}
          title={group.title}
          metrics={group.metrics}
          data={metrics}
          darkMode={darkMode}
        />
      ))}
    </div>
  );
};

import React, { useState, useEffect } from 'react';
import { AnimatedDependencyGraph } from '../AnimatedDependencyGraph';
import { TabProps } from './types';
import { useRealTimeMetrics } from '../../hooks/useRealtimeMetrics';
import { adminApi } from '../../services/api';
import type { ServicesHealthResponse } from '../../types/health';

export const DependenciesTab: React.FC<TabProps> = ({ darkMode }) => {
  const [services, setServices] = useState<any[]>([]);
  
  // Use the new real-time metrics hook with 5-second polling
  const { metrics, loading, error } = useRealTimeMetrics(5000);

  // Fetch services data for dependencies graph
  useEffect(() => {
    const fetchServices = async () => {
      try {
        const health = await adminApi.getServicesHealth();
        const mapped = Object.entries(health as ServicesHealthResponse).map(([service, s]) => ({
          service,
          running: s.status === 'healthy' || s.status === 'pass' || s.status === 'degraded',
          status:
            s.status === 'healthy' || s.status === 'pass'
              ? 'running'
              : s.status === 'degraded'
                ? 'degraded'
                : s.status === 'unhealthy' || s.status === 'error'
                  ? 'error'
                  : 'stopped',
          timestamp: s.last_check,
        }));
        setServices(mapped);
      } catch (error) {
        console.error('Error fetching services:', error);
      }
    };

    fetchServices();
    const interval = setInterval(fetchServices, 30000);
    return () => clearInterval(interval);
  }, []);

  // Transform metrics for the dependency graph
  const realTimeData = metrics ? {
    eventsPerHour: metrics.events_per_hour,
    apiCallsActive: metrics.api_calls_active,
    dataSourcesActive: metrics.data_sources_active,
    apiMetrics: metrics.api_metrics,
    inactiveApis: metrics.inactive_apis,
    errorApis: metrics.error_apis,
    totalApis: metrics.total_apis,
    healthSummary: metrics.health_summary,
    lastUpdate: new Date(metrics.timestamp),
  } : {
    eventsPerHour: 0,
    apiCallsActive: 0,
    dataSourcesActive: [],
    apiMetrics: [],
    inactiveApis: 0,
    errorApis: 0,
    totalApis: 0,
    healthSummary: {
      healthy: 0,
      unhealthy: 0,
      total: 0,
      health_percentage: 0
    },
    lastUpdate: new Date(),
  };

  return (
    <div className="space-y-4">
      {/* Legend */}
      <div className={`flex flex-wrap items-center gap-4 px-4 py-3 rounded-lg text-sm ${
        darkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'
      }`}>
        <span className={`font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>Legend:</span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-green-500" />
          <span className={darkMode ? 'text-gray-400' : 'text-gray-600'}>Healthy</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-yellow-500" />
          <span className={darkMode ? 'text-gray-400' : 'text-gray-600'}>Degraded</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-red-500" />
          <span className={darkMode ? 'text-gray-400' : 'text-gray-600'}>Error / Down</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-gray-400" />
          <span className={darkMode ? 'text-gray-400' : 'text-gray-600'}>Unknown / Stopped</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-6 border-t-2 border-dashed border-red-400" />
          <span className={darkMode ? 'text-gray-400' : 'text-gray-600'}>Broken dependency</span>
        </span>
      </div>

      {/* Error State */}
      {error && (
        <div className={`p-4 rounded-lg border ${
          darkMode ? 'bg-red-900/20 border-red-700' : 'bg-red-50 border-red-200'
        }`} role="alert">
          <div className="flex items-center gap-3">
            <span className="text-2xl">⚠️</span>
            <div className="flex-1">
              <p className={`font-semibold ${darkMode ? 'text-red-300' : 'text-red-800'}`}>
                Error loading dependency data
              </p>
              <p className={`text-sm ${darkMode ? 'text-red-400' : 'text-red-600'}`}>{error}</p>
            </div>
          </div>
        </div>
      )}

      <AnimatedDependencyGraph
        services={services}
        darkMode={darkMode}
        realTimeData={realTimeData}
        loading={loading}
        error={error}
      />
    </div>
  );
};


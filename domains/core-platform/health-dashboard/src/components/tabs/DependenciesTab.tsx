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
    <AnimatedDependencyGraph 
      services={services}
      darkMode={darkMode}
      realTimeData={realTimeData}
      loading={loading}
      error={error}
    />
  );
};


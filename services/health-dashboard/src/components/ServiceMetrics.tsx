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
  const { metrics, loading, error, lastUpdated, refresh } = useServiceMetrics({
    serviceId,
    autoRefresh,
    refreshInterval,
    enabled: true,
  });

  const config = getServiceMetricsConfig(serviceId);

  // If no configuration, show message
  if (!config) {
    return (
      <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
        Service-specific metrics not yet configured for this service.
      </div>
    );
  }

  // Loading state
  if (loading && !metrics) {
    return (
      <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
        Loading metrics...
      </div>
    );
  }

  // Error state
  if (error && !metrics) {
    return (
      <div className={`text-sm ${darkMode ? 'text-red-400' : 'text-red-600'}`}>
        Error loading metrics: {error}
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
      {config.groups.map((group, index) => (
        <MetricGroup
          key={index}
          title={group.title}
          metrics={group.metrics}
          data={metrics}
          darkMode={darkMode}
        />
      ))}
      
      {lastUpdated && (
        <div className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'} mt-4 pt-4 border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
          Last updated: {lastUpdated.toLocaleTimeString()}
        </div>
      )}
    </div>
  );
};

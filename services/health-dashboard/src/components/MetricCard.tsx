/**
 * MetricCard Component
 * 
 * Displays a single metric with label, value, and status
 * 
 * Prototype: Basic implementation
 */

import React from 'react';
import type { MetricStatus } from '../types/serviceMetrics';
import type { MetricDefinition } from '../config/serviceMetricsConfig';
import { formatMetricValue, determineMetricStatus } from '../utils/metricFormatters';

export interface MetricCardProps {
  definition: MetricDefinition;
  value: any;
  darkMode: boolean;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  definition,
  value,
  darkMode,
}) => {
  const formattedValue = formatMetricValue(value, definition);
  const status = determineMetricStatus(value, definition.statusThresholds);

  const statusColors = {
    good: darkMode ? 'text-green-400' : 'text-green-600',
    warning: darkMode ? 'text-yellow-400' : 'text-yellow-600',
    error: darkMode ? 'text-red-400' : 'text-red-600',
    unknown: darkMode ? 'text-white' : 'text-gray-900',
  };

  return (
    <div className="flex justify-between items-center">
      <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
        {definition.label}
      </span>
      <span className={`text-base font-semibold ${statusColors[status]}`}>
        {formattedValue}
        {definition.unit && (
          <span className="text-sm font-normal ml-1">{definition.unit}</span>
        )}
      </span>
    </div>
  );
};

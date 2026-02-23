/**
 * MetricGroup Component
 * 
 * Displays a group of related metrics
 * 
 * Prototype: Basic implementation
 */

import React from 'react';
import { MetricCard } from './MetricCard';
import type { ServiceMetrics } from '../types/serviceMetrics';
import type { MetricDefinition } from '../config/serviceMetricsConfig';

export interface MetricGroupProps {
  title: string;
  metrics: MetricDefinition[];
  data: ServiceMetrics;
  darkMode: boolean;
}

export const MetricGroup: React.FC<MetricGroupProps> = ({
  title,
  metrics,
  data,
  darkMode,
}) => {
  return (
    <div>
      <h5 className={`text-sm font-semibold mb-3 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
        {title}
      </h5>
      <div className="space-y-3">
        {metrics.map((metric) => {
          // Get value from data using path
          const value = getValueByPath(data, metric.path);
          
          return (
            <MetricCard
              key={metric.key}
              definition={metric}
              value={value}
              darkMode={darkMode}
            />
          );
        })}
      </div>
    </div>
  );
};

/**
 * Get value from object using dot-notation path
 */
function getValueByPath(obj: any, path: string): any {
  return path.split('.').reduce((current, key) => {
    return current && current[key] !== undefined ? current[key] : null;
  }, obj);
}

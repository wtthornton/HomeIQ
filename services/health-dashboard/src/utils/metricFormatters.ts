/**
 * Metric Formatters
 * 
 * Utility functions for formatting metric values
 * 
 * Prototype: Basic implementation
 */

import type { MetricDefinition, MetricStatus } from '../types/serviceMetrics';

/**
 * Format metric value based on definition
 */
export function formatMetricValue(
  value: any,
  definition: MetricDefinition
): string {
  // Use custom formatter if provided
  if (definition.formatter) {
    return definition.formatter(value);
  }

  // Use default formatter based on type
  const type = definition.type || 'custom';
  
  switch (type) {
    case 'number':
      return formatNumber(value);
    case 'percentage':
      return formatPercentage(value);
    case 'time':
      return formatTime(value);
    case 'status':
      return formatStatus(value);
    case 'custom':
    default:
      return String(value ?? 'N/A');
  }
}

/**
 * Determine metric status based on value and thresholds
 */
export function determineMetricStatus(
  value: any,
  thresholds?: MetricDefinition['statusThresholds']
): MetricStatus {
  if (!thresholds) {
    return 'unknown';
  }

  // Check error threshold
  if (thresholds.error !== undefined) {
    const isError = typeof thresholds.error === 'function'
      ? thresholds.error(value)
      : (value >= thresholds.error);
    if (isError) return 'error';
  }

  // Check warning threshold
  if (thresholds.warning !== undefined) {
    const isWarning = typeof thresholds.warning === 'function'
      ? thresholds.warning(value)
      : (value >= thresholds.warning);
    if (isWarning) return 'warning';
  }

  // Check good threshold
  if (thresholds.good !== undefined) {
    const isGood = typeof thresholds.good === 'function'
      ? thresholds.good(value)
      : (value < thresholds.good);
    if (isGood) return 'good';
  }

  return 'unknown';
}

/**
 * Format number value
 */
function formatNumber(value: any): string {
  if (value === null || value === undefined) return 'N/A';
  if (typeof value !== 'number') return String(value);
  return value.toLocaleString();
}

/**
 * Format percentage value
 */
function formatPercentage(value: any): string {
  if (value === null || value === undefined) return 'N/A';
  if (typeof value !== 'number') return String(value);
  return `${value.toFixed(1)}%`;
}

/**
 * Format time value (ISO 8601 string)
 */
function formatTime(value: any): string {
  if (!value) return 'N/A';
  try {
    const date = new Date(value);
    return date.toLocaleString();
  } catch {
    return 'Invalid Date';
  }
}

/**
 * Format status value
 */
function formatStatus(value: any): string {
  if (!value) return 'Unknown';
  const str = String(value);
  return str.charAt(0).toUpperCase() + str.slice(1);
}

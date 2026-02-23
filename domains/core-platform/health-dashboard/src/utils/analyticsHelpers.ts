/**
 * Analytics Helper Functions
 * 
 * Utility functions for analytics display and formatting
 * Extracted from AnalyticsPanel to reduce complexity
 */

/**
 * Get the appropriate icon for a trend direction
 * 
 * @param trend - Trend direction ('up', 'down', or 'stable')
 * @returns Emoji icon representing the trend
 */
export function getTrendIcon(trend: string): string {
  switch (trend) {
    case 'up':
      return '📈';
    case 'down':
      return '📉';
    default:
      return '➡️';
  }
}

/**
 * Get the appropriate color class for a trend direction
 * 
 * @param trend - Trend direction ('up', 'down', or 'stable')
 * @param darkMode - Whether dark mode is enabled
 * @returns Tailwind CSS color class
 */
export function getTrendColor(trend: string, darkMode: boolean): string {
  if (trend === 'up') {
    return darkMode ? 'text-green-400' : 'text-green-600';
  }
  if (trend === 'down') {
    return darkMode ? 'text-red-400' : 'text-red-600';
  }
  return darkMode ? 'text-gray-400' : 'text-gray-600';
}

/**
 * Format a metric value for display
 * 
 * @param value - Numeric value to format
 * @param decimals - Number of decimal places (default: 2)
 * @returns Formatted string
 */
export function formatMetricValue(value: number, decimals: number = 2): string {
  if (value >= 1000) {
    return `${(value / 1000).toFixed(decimals)}k`;
  }
  return value.toFixed(decimals);
}

/**
 * Format a timestamp as a relative time string
 * 
 * @param date - Date to format
 * @returns Formatted relative time string
 */
export function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffMs / 60000);

  if (diffSecs < 60) {
    return `${diffSecs}s ago`;
  } else if (diffMins < 60) {
    return `${diffMins}m ago`;
  } else {
    return date.toLocaleTimeString();
  }
}


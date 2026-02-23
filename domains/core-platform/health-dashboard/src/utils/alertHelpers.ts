/**
 * Alert Helper Functions
 * 
 * Utility functions for alert display and formatting
 * Extracted from AlertsPanel to reduce complexity
 */

/**
 * Get the appropriate color classes for an alert severity
 * 
 * @param severity - Alert severity level
 * @param darkMode - Whether dark mode is enabled
 * @returns Tailwind CSS color classes
 */
export function getSeverityColor(severity: string, darkMode: boolean): string {
  switch (severity) {
    case 'critical':
      return darkMode 
        ? 'text-red-400 bg-red-900/30 border-red-500/50' 
        : 'text-red-700 bg-red-50 border-red-200';
    case 'error':
      return darkMode 
        ? 'text-red-300 bg-red-900/20 border-red-500/30' 
        : 'text-red-600 bg-red-50 border-red-200';
    case 'warning':
      return darkMode 
        ? 'text-yellow-300 bg-yellow-900/20 border-yellow-500/30' 
        : 'text-yellow-700 bg-yellow-50 border-yellow-200';
    case 'info':
      return darkMode 
        ? 'text-blue-300 bg-blue-900/20 border-blue-500/30' 
        : 'text-blue-700 bg-blue-50 border-blue-200';
    default:
      return darkMode 
        ? 'text-gray-300 bg-gray-800 border-gray-600' 
        : 'text-gray-700 bg-gray-50 border-gray-200';
  }
}

/**
 * Get the appropriate icon for an alert severity
 * 
 * @param severity - Alert severity level
 * @returns Emoji icon representing the severity
 */
export function getSeverityIcon(severity: string): string {
  switch (severity) {
    case 'critical':
      return '🔴';
    case 'error':
      return '❌';
    case 'warning':
      return '⚠️';
    case 'info':
      return 'ℹ️';
    default:
      return '•';
  }
}

/**
 * Format a timestamp as a relative time string
 * 
 * @param timestamp - ISO timestamp string or Date object
 * @returns Formatted relative time string
 */
export function formatTimestamp(timestamp: string | Date): string {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);

  if (diffHours < 1) {
    return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
  } else if (diffHours < 24) {
    return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
  } else {
    return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
  }
}


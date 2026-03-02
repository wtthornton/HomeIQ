/**
 * Alert Constants
 *
 * Runtime enum values for alert severity and status.
 * The canonical Alert interface lives in types/alerts.ts.
 */

export enum AlertSeverity {
  INFO = 'info',
  WARNING = 'warning',
  CRITICAL = 'critical'
}

export enum AlertStatus {
  ACTIVE = 'active',
  RESOLVED = 'resolved',
  ACKNOWLEDGED = 'acknowledged'
}

// Re-export the canonical Alert type for backward compatibility
export type { Alert } from '../types/alerts';

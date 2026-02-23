/**
 * Alert Constants
 * 
 * Shared constants for alert system
 * Extracted from AlertBanner to fix fast-refresh warnings
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

export interface Alert {
  id: string;
  name: string;
  severity: AlertSeverity;
  status: AlertStatus;
  message: string;
  service: string;
  metric?: string;
  current_value?: number;
  threshold_value?: number;
  created_at?: string;
  resolved_at?: string;
  acknowledged_at?: string;
  metadata?: Record<string, unknown>;
}


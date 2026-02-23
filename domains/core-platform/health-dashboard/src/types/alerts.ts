/**
 * Alert Types and Interfaces
 * Story 21.5: Alerts Tab Implementation
 */

// Alert severity levels
export type AlertSeverity = 'critical' | 'warning' | 'info';

// Alert status
export type AlertStatus = 'active' | 'acknowledged' | 'resolved';

// Main Alert interface matching API response
export interface Alert {
  id: string;
  name: string;
  severity: AlertSeverity;
  status: AlertStatus;
  message: string;
  service: string;
  metric?: string | null;
  current_value?: number | null;
  threshold_value?: number | null;
  created_at?: string | null;
  resolved_at?: string | null;
  acknowledged_at?: string | null;
  metadata?: Record<string, any> | null;
}

// Alert filters for API queries
export interface AlertFilters {
  severity?: AlertSeverity;
  service?: string;
  status?: AlertStatus;
}

// Alert summary for dashboard cards
export interface AlertSummary {
  total_active: number;
  critical: number;
  warning: number;
  info: number;
  total_alerts: number;
  alert_history_count: number;
}

// Alert API response
export interface AlertsResponse {
  alerts: Alert[];
  count: number;
}

// Alert action response
export interface AlertActionResponse {
  success: boolean;
  message: string;
  alert?: Alert;
}


/**
 * Health monitoring types for HA Setup Service
 * 
 * Context7 Pattern: TypeScript types matching backend Pydantic schemas
 */

export enum HealthStatus {
  HEALTHY = 'healthy',
  WARNING = 'warning',
  CRITICAL = 'critical',
  UNKNOWN = 'unknown'
}

export enum IntegrationStatus {
  HEALTHY = 'healthy',
  WARNING = 'warning',
  ERROR = 'error',
  NOT_CONFIGURED = 'not_configured'
}

export interface PerformanceMetrics {
  response_time_ms: number;
  cpu_usage_percent?: number;
  memory_usage_mb?: number;
  uptime_seconds?: number;
}

export interface IntegrationHealthDetail {
  name: string;
  type: string;
  status: IntegrationStatus;
  is_configured: boolean;
  is_connected: boolean;
  error_message?: string;
  last_check?: string;
  check_details?: Record<string, any>;
}

export interface EnvironmentHealth {
  health_score: number;
  ha_status: HealthStatus;
  ha_version?: string;
  integrations: IntegrationHealthDetail[];
  performance: PerformanceMetrics;
  issues_detected: string[];
  timestamp: string;
}

export interface IntegrationHealthResponse {
  timestamp: string;
  total_integrations: number;
  healthy_count: number;
  warning_count: number;
  error_count: number;
  not_configured_count: number;
  integrations: IntegrationHealthDetail[];
}

// Enhanced health types for dashboard
export interface DependencyHealth {
  name: string;
  type: string;
  status: 'healthy' | 'unhealthy' | 'degraded' | 'unknown';
  response_time_ms?: number;
  last_check?: string;
  error_message?: string;
  details?: Record<string, any>;
}

export interface ServiceHealthStatus {
  name?: string;
  status: 'healthy' | 'unhealthy' | 'degraded' | 'unknown' | 'pass' | 'error';
  last_check?: string;
  response_time_ms?: number;
  error_message?: string | null;
}

export type ServicesHealthResponse = Record<string, ServiceHealthStatus>;

export interface ServiceHealthResponse {
  status: 'healthy' | 'unhealthy' | 'degraded' | 'unknown';
  service: string;
  timestamp: string;
  uptime_seconds?: number;
  uptime_human?: string;
  uptime_percentage?: number;
  dependencies?: DependencyHealth[];
  metrics?: {
    uptime_human?: string;
    uptime_percentage?: number;
    total_requests?: number;
    error_rate?: number;
  };
}

// Helper functions for status display
export const getStatusColor = (status: string, darkMode: boolean = false) => {
  const colors = {
    healthy: darkMode ? 'text-green-200' : 'text-green-800',
    unhealthy: darkMode ? 'text-red-200' : 'text-red-800',
    degraded: darkMode ? 'text-yellow-200' : 'text-yellow-800',
    unknown: darkMode ? 'text-gray-200' : 'text-gray-800'
  };
  return colors[status as keyof typeof colors] || colors.unknown;
};

export const getStatusIcon = (status: string) => {
  const icons = {
    healthy: '✅',
    unhealthy: '❌',
    degraded: '⚠️',
    unknown: '❓'
  };
  return icons[status as keyof typeof icons] || icons.unknown;
};

export const getDependencyTypeIcon = (type: string) => {
  const icons = {
    database: '🗄️',
    api: '🌐',
    websocket: '🔌',
    service: '⚙️',
    default: '📡'
  };
  return icons[type.toLowerCase() as keyof typeof icons] || icons.default;
};

export const formatResponseTime = (ms?: number) => {
  if (!ms) return 'N/A';
  return `${ms.toFixed(1)}ms`;
};

export const formatUptime = (uptime?: string | number) => {
  if (!uptime) return 'N/A';
  if (typeof uptime === 'string') return uptime;
  // Convert seconds to human readable format
  const hours = Math.floor(uptime / 3600);
  const minutes = Math.floor((uptime % 3600) / 60);
  const seconds = Math.floor(uptime % 60);
  return `${hours}h ${minutes}m ${seconds}s`;
};
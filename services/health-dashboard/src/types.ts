export interface HealthStatus {
  service: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  uptime_seconds: number;
  version: string;
  dependencies: Array<{
    name: string;
    type: string;
    status: 'healthy' | 'degraded' | 'unhealthy';
    response_time_ms: number;
    message: string;
    details: any;
  }>;
  metrics: {
    uptime_seconds: number;
    uptime_human: string;
    start_time: string;
    current_time: string;
  };
}

export interface DataSourceHealth {
  status: 'healthy' | 'degraded' | 'error' | 'unknown';
  status_detail?: string;  // 'operational' | 'credentials_missing' | 'degraded' | 'starting'
  service: string;
  uptime_seconds: number;
  last_successful_fetch: string | null;
  total_fetches: number;
  failed_fetches: number;
  success_rate: number;
  timestamp: string;
  oauth_valid?: boolean;
  credentials_configured?: boolean;  // For services requiring external API credentials
  api_usage?: {
    calls_today: number;
    quota_limit?: number;
    quota_percentage?: number;
  };
}

export interface DataSourcesHealthMap {
  weather: DataSourceHealth | null;
  carbonIntensity: DataSourceHealth | null;
  electricityPricing: DataSourceHealth | null;
  airQuality: DataSourceHealth | null;
  calendar: DataSourceHealth | null;
  smartMeter: DataSourceHealth | null;
}

export interface DataSourceMetrics {
  carbon_intensity?: {
    current: number;
    renewable_pct: number;
    forecast_1h: number;
  };
  electricity_pricing?: {
    current_price: number;
    currency: string;
    cheapest_hours: number[];
  };
  air_quality?: {
    aqi: number;
    category: string;
    pm25: number;
    pm10: number;
    ozone: number;
    co?: number;
    no2?: number;
    so2?: number;
  };
  occupancy?: {
    currently_home: boolean;
    wfh_today: boolean;
    confidence: number;
  };
  smart_meter?: {
    total_power_w: number;
    daily_kwh: number;
  };
}

export interface Statistics {
  timestamp: string;
  period: string;
  metrics: {
    'websocket-ingestion': {
      events_per_minute: number;
      error_rate: number;
      response_time_ms: number;
      connection_attempts: number;
      total_events_received: number;
    };
    'enrichment-pipeline': {
      events_per_minute: number;
      error_rate: number;
      response_time_ms: number;
      connection_attempts: number;
      total_events_received: number;
    };
  };
  trends: {
    [key: string]: any;
  };
  alerts: Array<{
    type: string;
    message: string;
    severity: 'info' | 'warning' | 'error';
  }>;
  source: string;
}

// Service Management Types (Phase 1, 2, 3)
export interface ServiceStatus {
  service: string;
  running: boolean;
  status: 'running' | 'stopped' | 'error' | 'degraded';
  timestamp?: string;
  error?: string;
  port?: number;
  uptime?: string;
  metrics?: ServiceMetrics;
}

export interface ServiceMetrics {
  requests_per_minute?: number;
  error_rate?: number;
  cpu_usage?: number;
  memory_usage?: number;
  total_requests?: number;
}

export interface ServiceGroup {
  title: string;
  description: string;
  services: ServiceStatus[];
}

export type ServiceType = 'core' | 'external' | 'storage' | 'ui';

export interface ServiceDefinition {
  id: string;
  name: string;
  icon: string;
  type: ServiceType;
  port?: number;
  description: string;
}

export interface ServiceDetails {
  service: string;
  status: 'running' | 'stopped' | 'error' | 'degraded';
  uptime: string;
  container_id?: string;
  image?: string;
  last_restart?: string;
  port_mappings?: string[];
  environment?: Record<string, string>;
}

export interface ServiceLog {
  timestamp: string;
  level: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG';
  message: string;
}

export interface ServiceMetricPoint {
  timestamp: string;
  requests: number;
  errors: number;
  response_time?: number;
}

export interface ServiceHealthCheck {
  timestamp: string;
  status: 'healthy' | 'unhealthy';
  response_time?: number;
  error?: string;
}

export interface ServiceResourceUsage {
  cpu_percent: number;
  memory_used_mb: number;
  memory_limit_mb: number;
  memory_percent: number;
}

export interface ServiceDependency {
  from: string;
  to: string;
  type: 'data_flow' | 'api_call' | 'storage';
  description?: string;
}

export interface ServiceNode {
  id: string;
  name: string;
  icon: string;
  type: ServiceType;
  layer: number;
  position: number;
}
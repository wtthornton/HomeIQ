import { HealthStatus, Statistics, DataSourceHealth, DataSourceMetrics, DataSourcesHealthMap } from '../types';
import { ServiceHealthResponse, ServicesHealthResponse } from '../types/health';

export interface HygieneIssue {
  issue_key: string;
  issue_type: string;
  severity: string;
  status: string;
  device_id?: string;
  entity_id?: string;
  name?: string;
  summary?: string;
  suggested_action?: string;
  suggested_value?: string;
  metadata: Record<string, unknown>;
  detected_at?: string;
  updated_at?: string;
  resolved_at?: string | null;
}

export interface HygieneIssueListResponse {
  issues: HygieneIssue[];
  count: number;
  total: number;
}

export type HygieneStatus = 'open' | 'ignored' | 'resolved';

const createEmptyDataSources = (): DataSourcesHealthMap => ({
  weather: null,
  carbonIntensity: null,
  electricityPricing: null,
  airQuality: null,
  calendar: null,
  smartMeter: null,
});

// Docker management types
export interface ContainerInfo {
  name: string;
  service_name: string;
  status: string;
  image: string;
  created: string;
  ports: Record<string, string>;
  is_project_container: boolean;
}

export interface ContainerOperationResponse {
  success: boolean;
  message: string;
  timestamp: string;
}

export interface ContainerStats {
  cpu_percent?: number;
  memory_usage?: number;
  memory_limit?: number;
  memory_percent?: number;
  timestamp: string;
}

export interface APIKeyInfo {
  service: string;
  key_name: string;
  status: string;
  masked_key: string;
  is_required: boolean;
  description: string;
}

export interface APIKeyUpdateRequest {
  api_key: string;
}

export interface APIKeyTestResponse {
  success: boolean;
  message: string;
  timestamp: string;
}

// Epic 13 Story 13.2: Separated API clients for admin vs data APIs
const ADMIN_API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8003';
const DATA_API_BASE_URL = import.meta.env.VITE_DATA_API_URL || '';  // Will use nginx routing

/**
 * Base API client with error handling
 */
class BaseApiClient {
  constructor(protected baseUrl: string) {}

  protected async fetchWithErrorHandling<T>(url: string, options?: RequestInit): Promise<T> {
    try {
      const response = await fetch(url, options);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`API Error for ${url}:`, error);
      throw error;
    }
  }
}

/**
 * Admin API Client - System Monitoring & Control
 * Routes to admin-api service (port 8003/8004)
 */
class AdminApiClient extends BaseApiClient {
  constructor() {
    super(ADMIN_API_BASE_URL);
  }

  async getHealth(): Promise<HealthStatus> {
    return this.fetchWithErrorHandling<HealthStatus>(`${this.baseUrl}/api/health`);
  }

  async getEnhancedHealth(): Promise<ServiceHealthResponse> {
    return this.fetchWithErrorHandling<ServiceHealthResponse>(`${this.baseUrl}/api/v1/health`);
  }

  async getStatistics(period: string = '1h'): Promise<Statistics> {
    return this.fetchWithErrorHandling<Statistics>(`${this.baseUrl}/api/v1/stats?period=${period}`);
  }

  async getServicesHealth(): Promise<ServicesHealthResponse> {
    return this.fetchWithErrorHandling<ServicesHealthResponse>(`${this.baseUrl}/api/v1/health/services`);
  }

  // New data source health endpoints
  async getDataSourceHealth(port: number): Promise<DataSourceHealth> {
    try {
      return await fetch(`http://localhost:${port}/health`).then(r => r.json());
    } catch (error) {
      console.error(`Error fetching health from port ${port}:`, error);
      throw error;
    }
  }

  async getAllDataSources(): Promise<DataSourcesHealthMap> {
    try {
      const servicesData = await this.getServicesHealth();

      // Map backend service names to frontend expected names
      const serviceMapping: Record<string, keyof DataSourcesHealthMap> = {
        'carbon-intensity-service': 'carbonIntensity',
        'electricity-pricing-service': 'electricityPricing',
        'air-quality-service': 'airQuality',
        'calendar-service': 'calendar',
        'smart-meter-service': 'smartMeter',
        'weather-api': 'weather'
      };

      const result: DataSourcesHealthMap = createEmptyDataSources();

      // Map the services data to our expected format
      for (const [backendName, frontendName] of Object.entries(serviceMapping)) {
        const serviceData = servicesData[backendName];
        if (!serviceData) continue;

        const normalizedStatus: DataSourceHealth['status'] =
          serviceData.status === 'healthy' || serviceData.status === 'pass'
            ? 'healthy'
            : serviceData.status === 'degraded'
              ? 'degraded'
              : serviceData.status === 'unhealthy' || serviceData.status === 'error'
                ? 'error'
                : 'unknown';

        result[frontendName] = {
          status: normalizedStatus,
          service: serviceData.name || backendName,
          uptime_seconds: 0, // Not provided by admin-api health check
          last_successful_fetch: null, // Not provided by admin-api health check
          total_fetches: 0, // Not provided by admin-api health check
          failed_fetches: 0, // Not provided by admin-api health check
          success_rate: 1.0, // Not provided by admin-api health check
          timestamp: serviceData.last_check || new Date().toISOString(),
          error_message: serviceData.error_message || null,
        };
      }

      return result;
    } catch (error) {
      console.error('Failed to fetch data sources:', error);
      return createEmptyDataSources();
    }
  }

  // Docker Management API methods (System Admin)
  async getContainers(): Promise<ContainerInfo[]> {
    return this.fetchWithErrorHandling<ContainerInfo[]>(`${this.baseUrl}/api/v1/docker/containers`);
  }

  async startContainer(serviceName: string): Promise<ContainerOperationResponse> {
    return this.fetchWithErrorHandling<ContainerOperationResponse>(
      `${this.baseUrl}/api/v1/docker/containers/${serviceName}/start`,
      { method: 'POST' }
    );
  }

  async stopContainer(serviceName: string): Promise<ContainerOperationResponse> {
    return this.fetchWithErrorHandling<ContainerOperationResponse>(
      `${this.baseUrl}/api/v1/docker/containers/${serviceName}/stop`,
      { method: 'POST' }
    );
  }

  async restartContainer(serviceName: string): Promise<ContainerOperationResponse> {
    return this.fetchWithErrorHandling<ContainerOperationResponse>(
      `${this.baseUrl}/api/v1/docker/containers/${serviceName}/restart`,
      { method: 'POST' }
    );
  }

  async getContainerLogs(serviceName: string, tail: number = 100): Promise<{ logs: string }> {
    return this.fetchWithErrorHandling<{ logs: string }>(
      `${this.baseUrl}/api/v1/docker/containers/${serviceName}/logs?tail=${tail}`
    );
  }

  async getContainerStats(serviceName: string): Promise<ContainerStats> {
    return this.fetchWithErrorHandling<ContainerStats>(
      `${this.baseUrl}/api/v1/docker/containers/${serviceName}/stats`
    );
  }

  // API Key Management methods (System Admin)
  async getAPIKeys(): Promise<APIKeyInfo[]> {
    return this.fetchWithErrorHandling<APIKeyInfo[]>(`${this.baseUrl}/api/v1/docker/api-keys`);
  }

  async updateAPIKey(service: string, apiKey: string): Promise<ContainerOperationResponse> {
    return this.fetchWithErrorHandling<ContainerOperationResponse>(
      `${this.baseUrl}/api/v1/docker/api-keys/${service}`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey })
      }
    );
  }

  async testAPIKey(service: string, apiKey: string): Promise<APIKeyTestResponse> {
    return this.fetchWithErrorHandling<APIKeyTestResponse>(
      `${this.baseUrl}/api/v1/docker/api-keys/${service}/test`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey })
      }
    );
  }

  // Real-time metrics endpoint (Story 23.2 + Epic 34.1)
  async getRealTimeMetrics(): Promise<any> {
    return this.fetchWithErrorHandling<any>(`/api/v1/real-time-metrics`);
  }
}

/**
 * Data API Client - Feature Data Hub
 * Routes to data-api service (port 8006) - this is the correct service for devices/entities
 * Epic 13 Story 13.2: Events, Devices, Sports, Analytics, HA Automation
 */
class DataApiClient extends BaseApiClient {
  constructor() {
    // Use empty base URL for relative requests through nginx proxy
    // Dashboard nginx subsets (lines 44-60, none of whose URLs contain /api/v1) proxy /api/devices, /api/entities to data-api
    const DATA_API_URL = import.meta.env.VITE_DATA_API_URL || '';
    super(DATA_API_URL);
  }

  // Events endpoints (Story 13.2)
  async getEvents(params: {
    limit?: number;
    offset?: number;
    entity_id?: string;
    event_type?: string;
    start_time?: string;
    end_time?: string;
  } = {}): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (params.limit) queryParams.append('limit', params.limit.toString());
    if (params.offset) queryParams.append('offset', params.offset.toString());
    if (params.entity_id) queryParams.append('entity_id', params.entity_id);
    if (params.event_type) queryParams.append('event_type', params.event_type);
    if (params.start_time) queryParams.append('start_time', params.start_time);
    if (params.end_time) queryParams.append('end_time', params.end_time);

    const url = `/api/v1/events${queryParams.toString() ? `?${  queryParams.toString()}` : ''}`;
    return this.fetchWithErrorHandling<any[]>(url);
  }

  async getEventById(eventId: string): Promise<any> {
    return this.fetchWithErrorHandling<any>(`/api/v1/events/${eventId}`);
  }

  async searchEvents(query: string, fields: string[] = ['entity_id', 'event_type'], limit: number = 100): Promise<any[]> {
    return this.fetchWithErrorHandling<any[]>(
      `/api/v1/events/search`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, fields, limit })
      }
    );
  }

  async getEventsStats(period: string = '1h'): Promise<any> {
    return this.fetchWithErrorHandling<any>(`/api/v1/events/stats?period=${period}`);
  }

  // Energy Correlation endpoints (Phase 4)
  async getEnergyStatistics(hours: number = 24): Promise<any> {
    return this.fetchWithErrorHandling<any>(`/api/v1/energy/statistics?hours=${hours}`);
  }

  async getEnergyCorrelations(
    hours: number = 24,
    entity_id?: string,
    domain?: string,
    min_delta: number = 50,
    limit: number = 100
  ): Promise<any[]> {
    const params = new URLSearchParams({ hours: hours.toString(), min_delta: min_delta.toString(), limit: limit.toString() });
    if (entity_id) params.append('entity_id', entity_id);
    if (domain) params.append('domain', domain);
    return this.fetchWithErrorHandling<any[]>(`/api/v1/energy/correlations?${params.toString()}`);
  }

  async getCurrentPower(): Promise<any> {
    return this.fetchWithErrorHandling<any>(`/api/v1/energy/current`);
  }

  async getCircuitPower(hours: number = 1): Promise<any[]> {
    return this.fetchWithErrorHandling<any[]>(`/api/v1/energy/circuits?hours=${hours}`);
  }

  async getDeviceEnergyImpact(entity_id: string, days: number = 7): Promise<any> {
    return this.fetchWithErrorHandling<any>(`/api/v1/energy/device-impact/${entity_id}?days=${days}`);
  }

  async getTopEnergyConsumers(days: number = 7, limit: number = 10): Promise<any[]> {
    return this.fetchWithErrorHandling<any[]>(`/api/v1/energy/top-consumers?days=${days}&limit=${limit}`);
  }

  // Devices & Entities endpoints (Story 13.2)
  async getDevices(params: {
    limit?: number;
    manufacturer?: string;
    model?: string;
    area_id?: string;
  } = {}): Promise<any> {
    const queryParams = new URLSearchParams();
    if (params.limit) queryParams.append('limit', params.limit.toString());
    if (params.manufacturer) queryParams.append('manufacturer', params.manufacturer);
    if (params.model) queryParams.append('model', params.model);
    if (params.area_id) queryParams.append('area_id', params.area_id);

    const url = `/api/devices${queryParams.toString() ? `?${  queryParams.toString()}` : ''}`;
    return this.fetchWithErrorHandling<any>(url);
  }

  async getDeviceById(deviceId: string): Promise<any> {
    return this.fetchWithErrorHandling<any>(`/api/devices/${deviceId}`);
  }

  async getEntities(params: {
    limit?: number;
    domain?: string;
    platform?: string;
    device_id?: string;
  } = {}): Promise<any> {
    const queryParams = new URLSearchParams();
    if (params.limit) queryParams.append('limit', params.limit.toString());
    if (params.domain) queryParams.append('domain', params.domain);
    if (params.platform) queryParams.append('platform', params.platform);
    if (params.device_id) queryParams.append('device_id', params.device_id);

    const url = `/api/entities${queryParams.toString() ? `?${  queryParams.toString()}` : ''}`;
    return this.fetchWithErrorHandling<any>(url);
  }

  async getEntityById(entityId: string): Promise<any> {
    return this.fetchWithErrorHandling<any>(`/api/entities/${entityId}`);
  }

  async getIntegrations(limit: number = 100): Promise<any> {
    return this.fetchWithErrorHandling<any>(`/api/integrations?limit=${limit}`);
  }

  async getHygieneIssues(params: {
    status?: string;
    severity?: string;
    issue_type?: string;
    device_id?: string;
    limit?: number;
  } = {}): Promise<HygieneIssueListResponse> {
    const queryParams = new URLSearchParams();
    if (params.status) queryParams.append('status', params.status);
    if (params.severity) queryParams.append('severity', params.severity);
    if (params.issue_type) queryParams.append('issue_type', params.issue_type);
    if (params.device_id) queryParams.append('device_id', params.device_id);
    if (params.limit) queryParams.append('limit', params.limit.toString());

    const url = `/api/v1/hygiene/issues${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    return this.fetchWithErrorHandling<HygieneIssueListResponse>(url);
  }

  async updateHygieneIssueStatus(issueKey: string, status: HygieneStatus): Promise<HygieneIssue> {
    return this.fetchWithErrorHandling<HygieneIssue>(
      `/api/v1/hygiene/issues/${issueKey}/status`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      }
    );
  }

  async applyHygieneIssueAction(issueKey: string, action: string, value?: string): Promise<HygieneIssue> {
    return this.fetchWithErrorHandling<HygieneIssue>(
      `/api/v1/hygiene/issues/${issueKey}/actions/apply`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, value }),
      }
    );
  }

  // Sports endpoints (Story 13.4 - Coming soon)
  async getLiveGames(teamIds?: string, league?: string): Promise<any> {
    const queryParams = new URLSearchParams();
    if (teamIds) queryParams.append('team_ids', teamIds);
    if (league) queryParams.append('league', league);
    
    const url = `/api/v1/sports/games/live${queryParams.toString() ? `?${  queryParams.toString()}` : ''}`;
    return this.fetchWithErrorHandling<any>(url);
  }

  async getSportsHistory(team: string, season?: number): Promise<any> {
    const queryParams = new URLSearchParams();
    queryParams.append('team', team);
    if (season) queryParams.append('season', season.toString());

    const url = `/api/v1/sports/games/history?${queryParams.toString()}`;
    return this.fetchWithErrorHandling<any>(url);
  }
}

/**
 * AI Automation API Client
 * Epic AI1 Story 13: AI-powered automation suggestion system
 */
class AIAutomationApiClient {
  private baseUrl: string;

  constructor() {
    // AI Automation service runs on port 8018
    this.baseUrl = import.meta.env.VITE_AI_API_URL || 'http://localhost:8018/api';
  }

  private async fetchWithErrorHandling<T>(url: string, options?: RequestInit): Promise<T> {
    try {
      const response = await fetch(url, options);
      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`API request failed: ${url}`, error);
      throw error;
    }
  }

  // Analysis endpoints
  async triggerAnalysis(params?: {
    days?: number;
    max_suggestions?: number;
    min_confidence?: number;
  }): Promise<any> {
    const body = {
      days: params?.days || 30,
      max_suggestions: params?.max_suggestions || 10,
      min_confidence: params?.min_confidence || 0.7,
      time_of_day_enabled: true,
      co_occurrence_enabled: true
    };
    
    return this.fetchWithErrorHandling(`${this.baseUrl}/analysis/analyze-and-suggest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
  }

  async getAnalysisStatus(): Promise<any> {
    return this.fetchWithErrorHandling(`${this.baseUrl}/analysis/status`);
  }

  async triggerManualJob(): Promise<any> {
    return this.fetchWithErrorHandling(`${this.baseUrl}/analysis/trigger`, {
      method: 'POST'
    });
  }

  async getScheduleInfo(): Promise<any> {
    return this.fetchWithErrorHandling(`${this.baseUrl}/analysis/schedule`);
  }

  // Suggestion endpoints
  async listSuggestions(status?: string, limit?: number): Promise<any> {
    const queryParams = new URLSearchParams();
    if (status) queryParams.append('status', status);
    if (limit) queryParams.append('limit', limit.toString());
    
    const url = `${this.baseUrl}/suggestions/list${queryParams.toString() ? `?${  queryParams.toString()}` : ''}`;
    return this.fetchWithErrorHandling(url);
  }

  async generateSuggestions(params?: {
    pattern_type?: string;
    min_confidence?: number;
    max_suggestions?: number;
  }): Promise<any> {
    const queryParams = new URLSearchParams();
    if (params?.pattern_type) queryParams.append('pattern_type', params.pattern_type);
    if (params?.min_confidence) queryParams.append('min_confidence', params.min_confidence.toString());
    if (params?.max_suggestions) queryParams.append('max_suggestions', params.max_suggestions.toString());
    
    const url = `${this.baseUrl}/suggestions/generate${queryParams.toString() ? `?${  queryParams.toString()}` : ''}`;
    return this.fetchWithErrorHandling(url, { method: 'POST' });
  }

  async getUsageStats(): Promise<any> {
    return this.fetchWithErrorHandling(`${this.baseUrl}/suggestions/usage-stats`);
  }

  async resetUsageStats(): Promise<any> {
    return this.fetchWithErrorHandling(`${this.baseUrl}/suggestions/usage-stats/reset`, {
      method: 'POST'
    });
  }

  // Pattern endpoints
  async listPatterns(params?: {
    pattern_type?: string;
    device_id?: string;
    min_confidence?: number;
    limit?: number;
  }): Promise<any> {
    const queryParams = new URLSearchParams();
    if (params?.pattern_type) queryParams.append('pattern_type', params.pattern_type);
    if (params?.device_id) queryParams.append('device_id', params.device_id);
    if (params?.min_confidence) queryParams.append('min_confidence', params.min_confidence.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    
    const url = `${this.baseUrl}/patterns/list${queryParams.toString() ? `?${  queryParams.toString()}` : ''}`;
    return this.fetchWithErrorHandling(url);
  }

  async getPatternStats(): Promise<any> {
    return this.fetchWithErrorHandling(`${this.baseUrl}/patterns/stats`);
  }

  async detectTimeOfDayPatterns(params?: {
    days?: number;
    min_occurrences?: number;
    min_confidence?: number;
  }): Promise<any> {
    const queryParams = new URLSearchParams();
    if (params?.days) queryParams.append('days', params.days.toString());
    if (params?.min_occurrences) queryParams.append('min_occurrences', params.min_occurrences.toString());
    if (params?.min_confidence) queryParams.append('min_confidence', params.min_confidence.toString());
    
    const url = `${this.baseUrl}/patterns/detect/time-of-day${queryParams.toString() ? `?${  queryParams.toString()}` : ''}`;
    return this.fetchWithErrorHandling(url, { method: 'POST' });
  }

  async detectCoOccurrencePatterns(params?: {
    days?: number;
    window_minutes?: number;
    min_support?: number;
    min_confidence?: number;
  }): Promise<any> {
    const queryParams = new URLSearchParams();
    if (params?.days) queryParams.append('days', params.days.toString());
    if (params?.window_minutes) queryParams.append('window_minutes', params.window_minutes.toString());
    if (params?.min_support) queryParams.append('min_support', params.min_support.toString());
    if (params?.min_confidence) queryParams.append('min_confidence', params.min_confidence.toString());
    
    const url = `${this.baseUrl}/patterns/detect/co-occurrence${queryParams.toString() ? `?${  queryParams.toString()}` : ''}`;
    return this.fetchWithErrorHandling(url, { method: 'POST' });
  }
}

// Export API client instances
export const adminApi = new AdminApiClient();  // System monitoring
export const dataApi = new DataApiClient();    // Feature data
export const aiApi = new AIAutomationApiClient();  // AI Automation

// Legacy export for backward compatibility (uses admin API)
export const apiService = adminApi;

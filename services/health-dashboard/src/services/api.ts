import { HealthStatus, Statistics, DataSourceHealth, DataSourceMetrics, DataSourcesHealthMap } from '../types';
import { ServiceHealthResponse, ServicesHealthResponse } from '../types/health';
import type { Alert } from '../constants/alerts';
import { withCsrfHeader } from '../utils/security';

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
  sports: null,
  carbonIntensity: null,
  electricityPricing: null,
  airQuality: null,
  blueprintIndex: null,
  ruleRecommendation: null,
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
const ADMIN_API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
const DATA_API_BASE_URL = import.meta.env.VITE_DATA_API_URL || '';  // Will use nginx routing

/**
 * Get API key from environment variable
 * Security: No hardcoded fallback - API key must be configured via environment
 */
function getApiKey(): string {
  const apiKey = import.meta.env.VITE_API_KEY;
  
  if (!apiKey) {
    if (import.meta.env.MODE === 'production') {
      throw new Error('VITE_API_KEY environment variable is required in production mode');
    }
    // Development mode: warn but allow requests without API key
    console.warn('⚠️ VITE_API_KEY not set. API requests may fail authentication.');
    return '';
  }
  
  return apiKey;
}

const API_KEY = getApiKey();

/**
 * Add authentication headers to request options
 */
function withAuthHeaders(headers: HeadersInit = {}): HeadersInit {
  const authHeaders: Record<string, string> = {
    'Authorization': `Bearer ${API_KEY}`,
  };

  if (headers instanceof Headers) {
    Object.entries(authHeaders).forEach(([key, value]) => {
      headers.set(key, value);
    });
    return headers;
  }

  if (Array.isArray(headers)) {
    // Filter out existing auth headers and add new ones
    const filtered = headers.filter(([key]) => 
      key.toLowerCase() !== 'authorization'
    );
    return [...filtered, ...Object.entries(authHeaders)];
  }

  return {
    ...headers,
    ...authHeaders,
  };
}

/**
 * Base API client with error handling
 */
class BaseApiClient {
  constructor(protected baseUrl: string) {}

  protected async fetchWithErrorHandling<T>(url: string, options: RequestInit = {}): Promise<T> {
    const method = (options.method || 'GET').toUpperCase();
    const requestOptions = { ...options };

    // Add authentication headers for all requests
    requestOptions.headers = withAuthHeaders(requestOptions.headers);

    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
      requestOptions.headers = withCsrfHeader(requestOptions.headers);
    }

    try {
      const response = await fetch(url, requestOptions);
      if (!response.ok) {
        // Handle authentication errors specifically
        if (response.status === 401) {
          const errorMessage = 'Authentication failed. Please check API key configuration.';
          console.error(`API Authentication Error for ${url}:`, errorMessage);
          throw new Error(errorMessage);
        }
        
        // Try to extract detailed error message from response body
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const errorData = await response.json();
          if (errorData.detail) {
            errorMessage = errorData.detail;
          } else if (errorData.message) {
            errorMessage = errorData.message;
          } else if (typeof errorData === 'string') {
            errorMessage = errorData;
          }
        } catch {
          // If response is not JSON, use status text
        }
        throw new Error(errorMessage);
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
    // In production (nginx), use empty string for relative paths
    // In development (Vite dev server), use configured base URL or empty for proxy
    super(ADMIN_API_BASE_URL || '');
  }

  /**
   * Helper method to construct API URLs correctly
   * Handles empty baseUrl for relative paths (production/nginx)
   */
  private buildUrl(path: string): string {
    if (this.baseUrl) {
      // Remove leading slash from path if baseUrl already ends with slash
      const cleanPath = path.startsWith('/') ? path : `/${path}`;
      return `${this.baseUrl}${cleanPath}`;
    }
    // Empty baseUrl - use relative path
    return path.startsWith('/') ? path : `/${path}`;
  }

  async getHealth(): Promise<HealthStatus> {
    return this.fetchWithErrorHandling<HealthStatus>(this.buildUrl('/api/health'));
  }

  async getEnhancedHealth(): Promise<ServiceHealthResponse> {
    return this.fetchWithErrorHandling<ServiceHealthResponse>(this.buildUrl('/api/v1/health'));
  }

  async getStatistics(period: string = '1h'): Promise<Statistics> {
    return this.fetchWithErrorHandling<Statistics>(this.buildUrl(`/api/v1/stats?period=${period}`));
  }

  async getServicesHealth(): Promise<ServicesHealthResponse> {
    return this.fetchWithErrorHandling<ServicesHealthResponse>(this.buildUrl('/api/v1/health/services'));
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
        'weather-api': 'weather',
        'sports-api': 'sports',
        'blueprint-index': 'blueprintIndex',
        'rule-recommendation-ml': 'ruleRecommendation',
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

  async getActiveAlerts(): Promise<Alert[]> {
    return this.fetchWithErrorHandling<Alert[]>(this.buildUrl('/api/v1/alerts/active'));
  }

  async acknowledgeAlert(alertId: string): Promise<void> {
    await this.fetchWithErrorHandling(this.buildUrl(`/api/v1/alerts/${alertId}/acknowledge`), {
      method: 'POST',
    });
  }

  async resolveAlert(alertId: string): Promise<void> {
    await this.fetchWithErrorHandling(this.buildUrl(`/api/v1/alerts/${alertId}/resolve`), {
      method: 'POST',
    });
  }

  // Docker Management API methods (System Admin)
  async getContainers(): Promise<ContainerInfo[]> {
    return this.fetchWithErrorHandling<ContainerInfo[]>(this.buildUrl('/api/v1/docker/containers'));
  }

  async startContainer(serviceName: string): Promise<ContainerOperationResponse> {
    return this.fetchWithErrorHandling<ContainerOperationResponse>(
      this.buildUrl(`/api/v1/docker/containers/${serviceName}/start`),
      { method: 'POST' }
    );
  }

  async stopContainer(serviceName: string): Promise<ContainerOperationResponse> {
    return this.fetchWithErrorHandling<ContainerOperationResponse>(
      this.buildUrl(`/api/v1/docker/containers/${serviceName}/stop`),
      { method: 'POST' }
    );
  }

  async restartContainer(serviceName: string): Promise<ContainerOperationResponse> {
    return this.fetchWithErrorHandling<ContainerOperationResponse>(
      this.buildUrl(`/api/v1/docker/containers/${serviceName}/restart`),
      { method: 'POST' }
    );
  }

  async testServiceHealth(serviceName: string, port: number): Promise<{ success: boolean; message: string; data?: any }> {
    try {
      // Create abort controller for timeout (compatible with older browsers)
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(`http://localhost:${port}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorText = '';
        try {
          errorText = await response.text();
        } catch {
          errorText = `HTTP ${response.status}`;
        }
        return {
          success: false,
          message: `${serviceName} returned status ${response.status}${errorText ? `: ${errorText.substring(0, 100)}` : ''}`,
        };
      }

      let data: any = {};
      try {
        data = await response.json();
      } catch {
        // If response is not JSON, that's okay - service responded
        data = { status: 'ok' };
      }

      // Extract status from response if available
      const status = data.status || data.health || 'healthy';
      const statusMessage = status === 'healthy' || status === 'ok' || status === 'pass'
        ? `${serviceName} is healthy`
        : `${serviceName} status: ${status}`;

      return {
        success: true,
        message: statusMessage,
        data,
      };
    } catch (error: any) {
      if (error.name === 'AbortError' || error.name === 'TimeoutError') {
        return {
          success: false,
          message: `${serviceName} did not respond within 5 seconds. It may be starting up or not running.`,
        };
      }
      if (error.message?.includes('Failed to fetch') || 
          error.message?.includes('NetworkError') ||
          error.message?.includes('CORS') ||
          error.message?.includes('ERR_CONNECTION_REFUSED')) {
        return {
          success: false,
          message: `${serviceName} is not reachable on port ${port}. It may not be running or the port may be incorrect.`,
        };
      }
      return {
        success: false,
        message: `${serviceName} test failed: ${error.message || 'Unknown error occurred'}`,
      };
    }
  }

  async getContainerLogs(serviceName: string, tail: number = 100): Promise<{ logs: string }> {
    return this.fetchWithErrorHandling<{ logs: string }>(
      this.buildUrl(`/api/v1/docker/containers/${serviceName}/logs?tail=${tail}`)
    );
  }

  async getContainerStats(serviceName: string): Promise<ContainerStats> {
    return this.fetchWithErrorHandling<ContainerStats>(
      this.buildUrl(`/api/v1/docker/containers/${serviceName}/stats`)
    );
  }

  // API Key Management methods (System Admin)
  async getAPIKeys(): Promise<APIKeyInfo[]> {
    return this.fetchWithErrorHandling<APIKeyInfo[]>(this.buildUrl('/api/v1/docker/api-keys'));
  }

  async updateAPIKey(service: string, apiKey: string): Promise<ContainerOperationResponse> {
    return this.fetchWithErrorHandling<ContainerOperationResponse>(
      this.buildUrl(`/api/v1/docker/api-keys/${service}`),
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey })
      }
    );
  }

  async testAPIKey(service: string, apiKey: string): Promise<APIKeyTestResponse> {
    return this.fetchWithErrorHandling<APIKeyTestResponse>(
      this.buildUrl(`/api/v1/docker/api-keys/${service}/test`),
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey })
      }
    );
  }

  // Real-time metrics endpoint (Story 23.2 + Epic 34.1)
  async getRealTimeMetrics(): Promise<any> {
    return this.fetchWithErrorHandling<any>(this.buildUrl('/api/v1/real-time-metrics'));
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
      '/api/v1/events/search',
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
    return this.fetchWithErrorHandling<any>('/api/v1/energy/current');
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

  async getHaGameContext(team: string): Promise<any> {
    const encodedTeam = encodeURIComponent(team);
    return this.fetchWithErrorHandling<any>(`/api/v1/ha/game-context/${encodedTeam}`);
  }

  async getHaGameStatus(team: string): Promise<any> {
    const encodedTeam = encodeURIComponent(team);
    return this.fetchWithErrorHandling<any>(`/api/v1/ha/game-status/${encodedTeam}`);
  }

  async getGameTimeline(gameId: string, league?: string): Promise<any> {
    const queryParams = new URLSearchParams();
    if (league) queryParams.append('league', league);
    
    const url = `/api/v1/sports/games/timeline/${gameId}${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
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
    // Base URL should be /ai-automation (nginx proxies to ai-automation-service:8018)
    this.baseUrl = import.meta.env.VITE_AI_API_URL || '/ai-automation';
  }

  private async fetchWithErrorHandling<T>(url: string, options: RequestInit = {}): Promise<T> {
    const method = (options.method || 'GET').toUpperCase();
    const requestOptions = { ...options };

    // Add authentication headers for all requests
    requestOptions.headers = withAuthHeaders(requestOptions.headers);

    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
      requestOptions.headers = withCsrfHeader(requestOptions.headers);
    }

    try {
      const response = await fetch(url, requestOptions);
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

  async getStats(): Promise<any> {
    return this.fetchWithErrorHandling(`${this.baseUrl}/stats`);
  }

  async getModelComparison(): Promise<any> {
    return this.fetchWithErrorHandling(`${this.baseUrl}/api/suggestions/models/compare`);
  }

  async generateNaturalLanguageAutomation(requestText: string, userId: string = 'default'): Promise<any> {
    return this.fetchWithErrorHandling(`${this.baseUrl}/api/nl/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        request_text: requestText,
        user_id: userId,
      }),
    });
  }
}

/**
 * RAG Service Client - Retrieval-Augmented Generation Metrics
 * Routes to rag-service (port 8027) via /rag-service proxy
 */
class RAGServiceClient extends BaseApiClient {
  constructor() {
    super('/rag-service');  // Proxied through nginx
  }

  /**
   * Get RAG service metrics
   * Returns operational metrics including call counts, latencies, and error rates
   */
  async getMetrics(): Promise<{
    total_calls: number;
    store_calls: number;
    retrieve_calls: number;
    search_calls: number;
    cache_hits: number;
    cache_misses: number;
    cache_hit_rate: number;
    avg_latency_ms: number;
    min_latency_ms: number;
    max_latency_ms: number;
    errors: number;
    embedding_errors: number;
    storage_errors: number;
    error_rate: number;
    avg_success_score: number;
  }> {
    return this.fetchWithErrorHandling(`${this.baseUrl}/api/v1/metrics`);
  }

  /**
   * Reset RAG service metrics
   */
  async resetMetrics(): Promise<{ message: string }> {
    return this.fetchWithErrorHandling(`${this.baseUrl}/api/v1/metrics/reset`, {
      method: 'POST',
    });
  }
}

/**
 * HA Setup Service Client - Validation & Configuration
 * Routes to ha-setup-service (port 8020) via /setup-service proxy
 */
class SetupServiceClient extends BaseApiClient {
  constructor() {
    super('/setup-service');  // Proxied through nginx
  }

  // Validation API (Epic 32)
  async getValidationResults(params?: {
    category?: string;
    min_confidence?: number;
  }): Promise<{
    summary: {
      total_issues: number;
      by_category: Record<string, number>;
      scan_timestamp: string;
      ha_version: string | null;
    };
    issues: Array<{
      entity_id: string;
      category: string;
      current_area: string | null;
      suggestions: Array<{
        area_id: string;
        area_name: string;
        confidence: number;
        reasoning: string;
      }>;
      device_id: string | null;
      entity_name: string | null;
      confidence: number;
    }>;
  }> {
    const queryParams = new URLSearchParams();
    if (params?.category) queryParams.append('category', params.category);
    if (params?.min_confidence !== undefined) queryParams.append('min_confidence', params.min_confidence.toString());
    
    const url = `${this.baseUrl}/api/v1/validation/ha-config${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    return this.fetchWithErrorHandling(url);
  }

  async applyValidationFix(entityId: string, areaId: string): Promise<{
    success: boolean;
    entity_id: string;
    area_id: string;
    applied_at: string;
    result?: any;
  }> {
    return this.fetchWithErrorHandling(`${this.baseUrl}/api/v1/validation/apply-fix`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        entity_id: entityId,
        area_id: areaId,
      }),
    });
  }

  async applyBulkFixes(fixes: Array<{ entity_id: string; area_id: string }>): Promise<{
    success: boolean;
    applied: number;
    failed: number;
    results: Array<{
      entity_id: string;
      success: boolean;
      error?: string;
    }>;
  }> {
    return this.fetchWithErrorHandling(`${this.baseUrl}/api/v1/validation/apply-bulk-fixes`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ fixes }),
    });
  }
}

// Export API client instances
export const adminApi = new AdminApiClient();  // System monitoring
export const dataApi = new DataApiClient();    // Feature data
export const aiApi = new AIAutomationApiClient();  // AI Automation
export const ragApi = new RAGServiceClient();  // RAG Service metrics
export const setupApi = new SetupServiceClient();  // HA Setup & Validation

// Legacy export for backward compatibility (uses admin API)
export const apiService = adminApi;

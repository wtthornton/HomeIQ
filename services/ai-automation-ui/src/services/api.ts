/**
 * API Service for AI Automation Backend
 * Connects to ai-automation-service on port 8018
 */

import type { Suggestion, Pattern, ScheduleInfo, AnalysisStatus, UsageStats, SynergyOpportunity, ClarificationResponse, ClarificationAnswer } from '../types';

// Use relative path - nginx will proxy to ai-automation-service
// In production (Docker), nginx proxies /api to http://ai-automation-service:8018/api
// In development (standalone), use direct connection to localhost:8024 (mapped from 8018)
// When running via Docker (port 3001), nginx handles the proxy, so use relative /api
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

// SECURITY: Never hardcode API keys. Always use environment variables.
// In production, VITE_API_KEY must be set via environment variables.
// If not set, throw an error to prevent insecure fallback.
const API_KEY = import.meta.env.VITE_API_KEY;
if (!API_KEY) {
  console.error('VITE_API_KEY environment variable is not set. API requests will fail.');
  // In development, we can allow requests without key for local testing
  // but log a warning. In production, this should be enforced.
  if (import.meta.env.MODE === 'production') {
    throw new Error('VITE_API_KEY is required in production mode. Please set the environment variable.');
  }
}

export class APIError extends Error {
  public response?: {
    data?: {
      detail?: string | { error?: string; message?: string; retry_after?: number };
    };
  };
  
  constructor(public status: number, message: string, errorBody?: any) {
    super(message);
    this.name = 'APIError';
    // Preserve error body structure for frontend error handling
    if (errorBody) {
      this.response = {
        data: {
          detail: errorBody.detail || errorBody
        }
      };
    }
  }
}

/**
 * Add authentication headers to request options
 */
function withAuthHeaders(headers: HeadersInit = {}): HeadersInit {
  // Only add auth headers if API_KEY is available
  const authHeaders: Record<string, string> = {};
  if (API_KEY) {
    authHeaders['Authorization'] = `Bearer ${API_KEY}`;
    authHeaders['X-HomeIQ-API-Key'] = API_KEY;
  }

  if (headers instanceof Headers) {
    Object.entries(authHeaders).forEach(([key, value]) => {
      headers.set(key, value);
    });
    return headers;
  }

  if (Array.isArray(headers)) {
    // Filter out existing auth headers and add new ones
    const filtered = headers.filter(([key]) =>
      key.toLowerCase() !== 'authorization' && key.toLowerCase() !== 'x-homeiq-api-key'
    );
    return [...filtered, ...Object.entries(authHeaders)];
  }

  return {
    ...headers,
    ...authHeaders,
  };
}

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  try {
    // Add authentication headers to all requests
    const headers = withAuthHeaders({
      'Content-Type': 'application/json',
      ...options?.headers,
    });

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      // Try to parse error response body for better error messages
      let errorMessage = response.statusText;
      let errorBody: any = null;
      try {
        errorBody = await response.json();
        if (errorBody.detail) {
          // Extract message from detail if it's an object
          if (typeof errorBody.detail === 'object' && errorBody.detail.message) {
            errorMessage = errorBody.detail.message;
          } else if (typeof errorBody.detail === 'string') {
            errorMessage = errorBody.detail;
          } else {
            errorMessage = JSON.stringify(errorBody.detail);
          }
        } else if (errorBody.message) {
          errorMessage = errorBody.message;
        }
      } catch {
        // If JSON parsing fails, use statusText
      }
      throw new APIError(response.status, errorMessage, errorBody);
    }

    return await response.json();
  } catch (error) {
    // Enhanced error logging with more context
    if (error instanceof TypeError && error.message === 'Failed to fetch') {
      console.error(`API request failed (network error): ${url}`, {
        error: error.message,
        url,
        message: 'This usually indicates a network connectivity issue, CORS problem, or the server is unreachable.'
      });
      // Wrap in a more descriptive error
      const networkError = new Error(`Network error: Unable to connect to ${url}. Please check your connection and ensure the server is running.`);
      (networkError as any).originalError = error;
      throw networkError;
    }
    console.error(`API request failed: ${url}`, error);
    throw error;
  }
}

export const api = {
  // Suggestions
  async getSuggestions(_status?: string, _limit = 50): Promise<{ data: { suggestions: Suggestion[], count: number } }> {
    const params = new URLSearchParams();
    if (_status) params.append('status', _status);
    params.append('limit', _limit.toString());
    
    // API returns { suggestions: [...], total: N, limit: N, offset: N }
    // Frontend expects { data: { suggestions: [...], count: N } }
    const response = await fetchJSON<{ suggestions: Suggestion[], total: number }>(`${API_BASE_URL}/suggestions/list?${params}`);
    return { data: { suggestions: response.suggestions || [], count: response.total || 0 } };
  },

  async getSuggestionByAutomationId(automationId: string): Promise<any> {
    return fetchJSON(`${API_BASE_URL}/v1/suggestions/by-automation/${automationId}`);
  },

  async getRefreshStatus(): Promise<{ allowed: boolean; last_trigger_at: string | null; next_allowed_at: string | null }> {
    return fetchJSON(`${API_BASE_URL}/suggestions/refresh/status`);
  },

  async refreshSuggestions(): Promise<{ success: boolean; message: string; next_allowed_at: string | null }> {
    return fetchJSON(`${API_BASE_URL}/suggestions/refresh`, {
      method: 'POST',
    });
  },

  async redeploySuggestion(id: number, finalDescription?: string): Promise<{
    suggestion_id: string;
    status: string;
    automation_yaml: string;
    automation_id?: string;
    category?: string;
    priority?: string;
    yaml_validation: { syntax_valid: boolean; safety_score: number; issues: any[] };
    ready_to_deploy: boolean;
  }> {
    // Re-deploy uses the same approve endpoint - it regenerates YAML and deploys
    return fetchJSON(`${API_BASE_URL}/v1/suggestions/suggestion-${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ final_description: finalDescription || null }),
    });
  },

  async redeployAutomationById(automationId: string): Promise<{
    success: boolean;
    message: string;
    data: {
      automation_id: string;
      yaml_source: string;
      similarity: number;
      regeneration_used: boolean;
      validation: {
        valid: boolean;
        errors: string[];
        warnings: string[];
      };
    };
  }> {
    // Re-deploy automation by automation_id (works for automations without suggestion records)
    return fetchJSON(`${API_BASE_URL}/deploy/automations/${automationId}/redeploy`, {
      method: 'POST',
    });
  },

  // Story AI1.23: Generate new suggestions
  async generateSuggestion(patternId: number | undefined, patternType: string, deviceId: string, metadata: any): Promise<{
    suggestion_id: string;
    description: string;
    trigger_summary: string;
    action_summary: string;
    devices_involved: any[];
    confidence: number;
    status: string;
    created_at: string;
  }> {
    return fetchJSON(`${API_BASE_URL}/v1/suggestions/generate`, {
      method: 'POST',
      body: JSON.stringify({
        pattern_id: patternId ?? null,  // Send null if undefined
        pattern_type: patternType,
        device_id: deviceId,
        metadata: metadata
      }),
    });
  },

  async approveSuggestion(id: number): Promise<any> {
    return fetchJSON(`${API_BASE_URL}/suggestions/${id}/approve`, {
      method: 'PATCH',
    });
  },

  async rejectSuggestion(id: number, reason?: string): Promise<any> {
    const body = reason ? { action: 'rejected', feedback_text: reason } : undefined;
    return fetchJSON(`${API_BASE_URL}/suggestions/${id}/reject`, {
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  async updateSuggestion(id: number, updates: any): Promise<any> {
    return fetchJSON(`${API_BASE_URL}/suggestions/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  },

  async deleteSuggestion(id: number): Promise<any> {
    return fetchJSON(`${API_BASE_URL}/suggestions/${id}`, {
      method: 'DELETE',
    });
  },

  // Story AI1.23: Conversational Refinement
  async refineSuggestion(id: number, userInput: string): Promise<{
    suggestion_id: string;
    updated_description: string;
    changes_detected: string[];
    validation: { ok: boolean; messages: string[]; warnings: string[]; alternatives: string[] };
    refinement_count: number;
    status: string;
  }> {
    return fetchJSON(`${API_BASE_URL}/v1/suggestions/suggestion-${id}/refine`, {
      method: 'POST',
      body: JSON.stringify({ user_input: userInput, conversation_context: true }),
    });
  },

  async approveAndGenerateYAML(id: number, finalDescription?: string): Promise<{
    suggestion_id: string;
    status: string;
    automation_yaml: string;
    automation_id?: string;
    yaml_validation: { syntax_valid: boolean; safety_score: number; issues: any[] };
    ready_to_deploy: boolean;
  }> {
    return fetchJSON(`${API_BASE_URL}/v1/suggestions/suggestion-${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ final_description: finalDescription || null }),
    });
  },

  async getDeviceCapabilities(entityId: string): Promise<{
    entity_id: string;
    friendly_name: string;
    domain: string;
    area: string;
    supported_features: Record<string, any>;
    friendly_capabilities: string[];
    common_use_cases: string[];
  }> {
    return fetchJSON(`${API_BASE_URL}/v1/suggestions/devices/${entityId}/capabilities`);
  },

  async batchApproveSuggestions(suggestionIds: number[]): Promise<any> {
    return fetchJSON(`${API_BASE_URL}/suggestions/batch/approve`, {
      method: 'POST',
      body: JSON.stringify(suggestionIds),
    });
  },

  async batchRejectSuggestions(suggestionIds: number[]): Promise<any> {
    return fetchJSON(`${API_BASE_URL}/suggestions/batch/reject`, {
      method: 'POST',
      body: JSON.stringify(suggestionIds),
    });
  },

  // Analysis
  async triggerAnalysis(params?: {
    days?: number;
    max_suggestions?: number;
    min_confidence?: number;
  }): Promise<any> {
    return fetchJSON(`${API_BASE_URL}/analysis/analyze-and-suggest`, {
      method: 'POST',
      body: JSON.stringify({
        days: params?.days || 30,
        max_suggestions: params?.max_suggestions || 10,
        min_confidence: params?.min_confidence || 0.7,
        time_of_day_enabled: true,
        co_occurrence_enabled: true,
      }),
    });
  },

  async triggerManualJob(): Promise<any> {
    return fetchJSON(`${API_BASE_URL}/analysis/trigger`, {
      method: 'POST',
    });
  },

  async getAnalysisStatus(): Promise<AnalysisStatus> {
    return fetchJSON(`${API_BASE_URL}/analysis/status`);
  },

  async getScheduleInfo(): Promise<ScheduleInfo> {
    return fetchJSON(`${API_BASE_URL}/analysis/schedule`);
  },

  // Patterns
  async getPatterns(type?: string, minConfidence?: number): Promise<{ data: { patterns: Pattern[], count: number } }> {
    const params = new URLSearchParams();
    if (type) params.append('pattern_type', type);
    if (minConfidence) params.append('min_confidence', minConfidence.toString());
    params.append('limit', '100');
    
    const response = await fetchJSON<any>(`${API_BASE_URL}/patterns/list?${params}`);
    
    // Handle API response structure: { success: true, data: {...}, message: "..." }
    if (response.success !== undefined && response.data) {
      return { data: response.data };
    }
    // Fallback for direct data structure
    if (response.data) {
      return response;
    }
    // Last resort: wrap the response
    return { data: response };
  },

  async getPatternStats(): Promise<any> {
    const response = await fetchJSON<any>(`${API_BASE_URL}/patterns/stats`);
    
    // Handle API response structure: { success: true, data: {...}, message: "..." }
    // Also handle corruption errors: { success: false, data: {...}, error: "...", repair_available: true }
    if (response.success !== undefined) {
      // If corruption detected, throw error with repair flag
      if (!response.success && response.error) {
        const error = new Error(response.error || response.message || 'Database error');
        (error as any).repair_available = response.repair_available || false;
        (error as any).isCorruption = response.error.toLowerCase().includes('corrupt') || 
                                      response.error.toLowerCase().includes('malformed');
        throw error;
      }
      return response.data || {};
    }
    // Fallback for direct data structure
    return response.data || response;
  },

  async repairDatabase(): Promise<any> {
    const response = await fetchJSON<any>(`${API_BASE_URL}/patterns/repair`, {
      method: 'POST',
    });
    return response;
  },

  // Usage & Cost
  async getUsageStats(): Promise<{ data: UsageStats }> {
    return fetchJSON(`${API_BASE_URL}/suggestions/usage-stats`);
  },

  async resetUsageStats(): Promise<any> {
    return fetchJSON(`${API_BASE_URL}/suggestions/usage-stats/reset`, {
      method: 'POST',
    });
  },

  // Deployment (Story AI1.11)
  async deploySuggestion(suggestionId: number): Promise<any> {
    return fetchJSON(`${API_BASE_URL}/deploy/${suggestionId}`, {
      method: 'POST',
    });
  },

  async batchDeploySuggestions(suggestionIds: number[]): Promise<any> {
    return fetchJSON(`${API_BASE_URL}/deploy/batch`, {
      method: 'POST',
      body: JSON.stringify(suggestionIds),
    });
  },

  async listDeployedAutomations(): Promise<any> {
    return fetchJSON(`${API_BASE_URL}/deploy/automations`);
  },

  async getAutomationStatus(automationId: string): Promise<any> {
    return fetchJSON(`${API_BASE_URL}/deploy/automations/${automationId}`);
  },

  async enableAutomation(automationId: string): Promise<any> {
    return fetchJSON(`${API_BASE_URL}/deploy/automations/${automationId}/enable`, {
      method: 'POST',
    });
  },

  async disableAutomation(automationId: string): Promise<any> {
    return fetchJSON(`${API_BASE_URL}/deploy/automations/${automationId}/disable`, {
      method: 'POST',
    });
  },

  async triggerAutomation(automationId: string): Promise<any> {
    return fetchJSON(`${API_BASE_URL}/deploy/automations/${automationId}/trigger`, {
      method: 'POST',
    });
  },

  async testHAConnection(): Promise<any> {
    return fetchJSON(`${API_BASE_URL}/deploy/test-connection`);
  },

  // Device name resolution
  async getDeviceName(deviceId: string): Promise<string> {
    try {
      // Handle compound entity IDs (e.g., "hash1+hash2")
      if (deviceId.includes('+')) {
        const parts = deviceId.split('+');
        if (parts.length === 2) {
          // This is a co-occurrence pattern with two entity hashes
          // Try to get more meaningful names by looking up patterns
          const patternInfo = await this.getPatternInfo(deviceId);
          if (patternInfo) {
            return patternInfo;
          }
          
          // Fallback to descriptive name
          return `Co-occurrence Pattern (${parts[0].substring(0, 8)}... + ${parts[1].substring(0, 8)}...)`;
        }
      }
      
      // Skip data API call for now since it's failing
      // TODO: Fix data API device resolution
      console.warn(`Skipping device name resolution for ${deviceId} - data API unavailable`);
      
    } catch (error) {
      console.warn(`Failed to resolve device name for ${deviceId}:`, error);
    }
    
    // Fallback: try to extract readable name from device ID
    // Some device IDs might have readable parts after splitting
    const parts = deviceId.split('.');
    if (parts.length > 1) {
      return parts[1] || deviceId;
    }
    
    // Last resort: return truncated device ID
    return deviceId.length > 20 ? `${deviceId.substring(0, 20)}...` : deviceId;
  },

  // Get pattern information for better naming
  async getPatternInfo(deviceId: string): Promise<string | null> {
    try {
      // Use fetchJSON to ensure authentication headers are included
      const data = await fetchJSON<{ data?: { patterns?: any[] } }>(`${API_BASE_URL}/patterns/list?device_id=${encodeURIComponent(deviceId)}&limit=1`);
      const patterns = data.data?.patterns || [];
      if (patterns.length > 0) {
        const pattern = patterns[0];
        // Create a more meaningful name based on pattern type and metadata
        if (pattern.pattern_type === 'co_occurrence') {
          const occurrences = pattern.occurrences || 0;
          const confidence = Math.round((pattern.confidence || 0) * 100);
          return `Co-occurrence Pattern (${occurrences} occurrences, ${confidence}% confidence)`;
        } else if (pattern.pattern_type === 'time_of_day') {
          const metadata = pattern.metadata || {};
          const timeRange = metadata.time_range || 'Unknown time';
          const occurrences = pattern.occurrences || 0;
          const confidence = Math.round((pattern.confidence || 0) * 100);
          return `Time Pattern (${timeRange}, ${occurrences} occurrences, ${confidence}% confidence)`;
        }
      }
    } catch (error) {
      console.warn(`Failed to get pattern info for ${deviceId}:`, error);
    }
    return null;
  },

  async getDeviceNames(deviceIds: string[]): Promise<Record<string, string>> {
    // Import cache utility (dynamic import to avoid circular dependencies)
    const { deviceNameCache } = await import('../utils/deviceNameCache');
    
    // Use cache for batch processing
    return deviceNameCache.batchGet(deviceIds, async (deviceId) => {
      return this.getDeviceName(deviceId);
    });
  },

  // Synergies (Epic AI-3, Story AI3.8)
  async getSynergies(synergyType?: string | null, minConfidence = 0.7, validatedByPatterns?: boolean | null): Promise<{ data: { synergies: SynergyOpportunity[]; count?: number } }> {
    const params = new URLSearchParams();
    if (synergyType) params.append('synergy_type', synergyType);
    params.append('min_confidence', minConfidence.toString());
    if (validatedByPatterns !== null && validatedByPatterns !== undefined) {
      params.append('validated_by_patterns', validatedByPatterns.toString());
    }
    
    try {
      const response = await fetchJSON<{ success: boolean; data: { synergies: SynergyOpportunity[]; count: number } }>(`${API_BASE_URL}/synergies?${params}`);
      // Unwrap the response to match the expected return type
      if (response.success && response.data) {
        return { data: response.data };
      }
      // Handle case where response doesn't have success wrapper
      if (response.data) {
        return { data: response.data };
      }
      // Fallback: return empty data
      return { data: { synergies: [], count: 0 } };
    } catch (error: any) {
      console.error('Failed to fetch synergies:', error);
      // Re-throw with more context
      if (error.status === 404) {
        throw new APIError(404, 'Synergies API endpoint not found. The synergies service may not be available.', error.response?.data);
      } else if (error.status === 502 || error.status === 503) {
        throw new APIError(error.status, 'Synergies service unavailable. The service is temporarily down.', error.response?.data);
      } else if (error.status === 504) {
        throw new APIError(504, 'Synergies service timeout. The request took too long.', error.response?.data);
      }
      throw error;
    }
  },

  async getSynergyStats(): Promise<{ data: { total_synergies: number; by_type: Record<string, number>; by_complexity: Record<string, number>; avg_impact_score: number } }> {
    try {
      const response = await fetchJSON<{ success: boolean; data: any }>(`${API_BASE_URL}/synergies/stats`);  // Proxies to /statistics in pattern service
      // Unwrap the response to match the expected return type
      if (response.success && response.data) {
        return { data: response.data };
      }
      // Handle case where response doesn't have success wrapper
      if (response.data) {
        return { data: response.data };
      }
      // Fallback: return empty stats
      return {
        data: {
          total_synergies: 0,
          by_type: {},
          by_complexity: {},
          avg_impact_score: 0
        }
      };
    } catch (error: any) {
      console.error('Failed to fetch synergy stats:', error);
      // Return empty stats on error instead of throwing
      return {
        data: {
          total_synergies: 0,
          by_type: {},
          by_complexity: {},
          avg_impact_score: 0
        }
      };
    }
  },

  async getSynergy(synergyId: string): Promise<{ data: { synergy: SynergyOpportunity } }> {
    try {
      const response = await fetchJSON<{ success: boolean; data: { synergy: SynergyOpportunity } | SynergyOpportunity }>(`${API_BASE_URL}/synergies/${synergyId}`);
      // Handle both response formats: { success: true, data: { synergy: ... } } or { success: true, data: ... }
      if (response.success && response.data) {
        if ('synergy' in response.data) {
          return { data: response.data };
        } else {
          // Data is the synergy object directly
          return { data: { synergy: response.data as SynergyOpportunity } };
        }
      }
      // Handle case where response doesn't have success wrapper
      if (response.data) {
        if ('synergy' in response.data) {
          return { data: response.data };
        } else {
          return { data: { synergy: response.data as SynergyOpportunity } };
        }
      }
      throw new APIError(404, `Synergy ${synergyId} not found`);
    } catch (error: any) {
      console.error(`Failed to fetch synergy ${synergyId}:`, error);
      if (error.status === 404) {
        throw new APIError(404, `Synergy ${synergyId} not found`, error.response?.data);
      }
      throw error;
    }
  },

  /**
   * Generate and deploy Home Assistant automation from synergy.
   * Implements Recommendation 1.1: Complete Automation Generation Pipeline
   * 
   * @param synergyId - Unique synergy identifier
   * @returns Automation generation result with automation_id, yaml, and deployment status
   */
  async generateAutomationFromSynergy(synergyId: string): Promise<{
    success: boolean;
    data: {
      automation_id: string;
      automation_yaml: string;
      blueprint_id: string | null;
      deployment_status: string;
      estimated_impact: number;
    };
    message: string;
  }> {
    try {
      // Call the generate-automation endpoint
      // Note: The endpoint expects synergy_id as path parameter, not in body
      const response = await fetchJSON<{
        success: boolean;
        data: {
          automation_id: string;
          automation_yaml: string;
          blueprint_id: string | null;
          deployment_status: string;
          estimated_impact: number;
        };
        message: string;
      }>(`${API_BASE_URL}/synergies/${synergyId}/generate-automation`, {
        method: 'POST',
      });
      return response;
    } catch (error: any) {
      console.error(`Failed to generate automation from synergy ${synergyId}:`, error);
      throw error;
    }
  },

  // Ask AI - Natural Language Query Interface
  async clarifyAnswers(sessionId: string, answers: ClarificationAnswer[]): Promise<ClarificationResponse> {
    // Create abort controller for timeout
    // Frontend timeout: 180s (3 minutes) to allow for complex processing:
    // - Entity extraction: 30s
    // - Entity re-enrichment: 45s
    // - Suggestion generation: 60s
    // - RAG operations: variable
    // Total can exceed 2 minutes for complex queries
    const FRONTEND_TIMEOUT_MS = 180000; // 3 minutes
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), FRONTEND_TIMEOUT_MS);
    
    try {
      return await fetchJSON(`${API_BASE_URL}/v1/ask-ai/clarify`, {
        method: 'POST',
        body: JSON.stringify({
          session_id: sessionId,
          answers
        }),
        signal: controller.signal
      });
    } catch (error: any) {
      if (error.name === 'AbortError') {
        throw new Error('Request timed out after 3 minutes. The AI is processing a very complex request. Please try again with a simpler query or wait a moment.');
      }
      throw error;
    } finally {
      clearTimeout(timeoutId);
    }
  },

  async askAIQuery(query: string, options?: {
    conversation_context?: any;
    conversation_history?: any[];
    userId?: string;
  }): Promise<any> {
    const requestBody: any = {
      query,
      user_id: options?.userId || 'anonymous'
    };
    
    // Add context and history if provided
    if (options?.conversation_context) {
      requestBody.context = options.conversation_context;
    }
    
    if (options?.conversation_history) {
      requestBody.conversation_history = options.conversation_history;
    }
    
    return fetchJSON(`${API_BASE_URL}/v1/ask-ai/query`, {
      method: 'POST',
      body: JSON.stringify(requestBody),
    });
  },

  async refineAskAIQuery(queryId: string, refinement: string): Promise<any> {
    return fetchJSON(`${API_BASE_URL}/v1/ask-ai/query/${queryId}/refine`, {
      method: 'POST',
      body: JSON.stringify({
        refinement,
        include_context: true
      }),
    });
  },

  async getAskAIQuerySuggestions(queryId: string): Promise<any> {
    return fetchJSON(`${API_BASE_URL}/v1/ask-ai/query/${queryId}/suggestions`);
  },

  async approveAskAISuggestion(
    queryId: string, 
    suggestionId: string, 
    selectedEntityIds?: string[],
    customEntityMapping?: Record<string, string>
  ): Promise<any> {
    const body: any = {};
    if (selectedEntityIds && selectedEntityIds.length > 0) {
      body.selected_entity_ids = selectedEntityIds;
    }
    if (customEntityMapping && Object.keys(customEntityMapping).length > 0) {
      body.custom_entity_mapping = customEntityMapping;
    }
    return fetchJSON(`${API_BASE_URL}/v1/ask-ai/query/${queryId}/suggestions/${suggestionId}/approve`, {
      method: 'POST',
      body: Object.keys(body).length > 0 ? JSON.stringify(body) : undefined,
    });
  },

  async searchEntities(params: {
    domain?: string;
    search_term?: string;
    limit?: number;
  }): Promise<Array<{
    entity_id: string;
    friendly_name: string;
    domain: string;
    state?: string;
    capabilities?: string[];
    device_id?: string;
    area_id?: string;
  }>> {
    const queryParams = new URLSearchParams();
    if (params.domain) queryParams.append('domain', params.domain);
    if (params.search_term) queryParams.append('search_term', params.search_term);
    if (params.limit) queryParams.append('limit', params.limit.toString());
    
    return fetchJSON(`${API_BASE_URL}/v1/ask-ai/entities/search?${queryParams}`);
  },

  async validateYAML(data: {
    yaml: string;
    validate_entities?: boolean;
    validate_safety?: boolean;
    context?: any;
  }): Promise<any> {
    return fetchJSON(`${API_BASE_URL}/v1/yaml/validate`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async reverseEngineerYAML(data: {
    yaml: string;
    original_prompt: string;
    context?: any;
  }): Promise<any> {
    return fetchJSON(`${API_BASE_URL}/v1/ask-ai/reverse-engineer-yaml`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Name Enhancement (Device Intelligence Service)
  async getNameSuggestions(deviceId: string): Promise<{
    device_id: string;
    current_name: string;
    suggestions: Array<{
      name: string;
      confidence: number;
      source: string;
      reasoning: string | null;
    }>;
  }> {
    // Device Intelligence Service API (port 8019)
    const DEVICE_INTELLIGENCE_API = import.meta.env.VITE_DEVICE_INTELLIGENCE_API || 'http://localhost:8019';
    return fetchJSON(`${DEVICE_INTELLIGENCE_API}/api/name-enhancement/devices/${deviceId}/suggestions`);
  },

  async acceptNameSuggestion(deviceId: string, suggestedName: string, syncToHA: boolean = false): Promise<{
    success: boolean;
    device_id: string;
    old_name: string;
    new_name: string;
  }> {
    const DEVICE_INTELLIGENCE_API = import.meta.env.VITE_DEVICE_INTELLIGENCE_API || 'http://localhost:8019';
    return fetchJSON(`${DEVICE_INTELLIGENCE_API}/api/name-enhancement/devices/${deviceId}/accept`, {
      method: 'POST',
      body: JSON.stringify({ suggested_name: suggestedName, sync_to_ha: syncToHA }),
    });
  },

  async rejectNameSuggestion(deviceId: string, suggestedName: string, reason?: string): Promise<{
    success: boolean;
    message: string;
  }> {
    const DEVICE_INTELLIGENCE_API = import.meta.env.VITE_DEVICE_INTELLIGENCE_API || 'http://localhost:8019';
    const params = new URLSearchParams({ suggested_name: suggestedName });
    if (reason) params.append('reason', reason);
    return fetchJSON(`${DEVICE_INTELLIGENCE_API}/api/name-enhancement/devices/${deviceId}/reject?${params}`, {
      method: 'POST',
    });
  },

  async batchEnhanceNames(deviceIds: string[] | null = null, useAI: boolean = false, autoAccept: boolean = false): Promise<{
    success: boolean;
    job_id: string;
    status: string;
    estimated_duration: string;
  }> {
    const DEVICE_INTELLIGENCE_API = import.meta.env.VITE_DEVICE_INTELLIGENCE_API || 'http://localhost:8019';
    return fetchJSON(`${DEVICE_INTELLIGENCE_API}/api/name-enhancement/batch-enhance`, {
      method: 'POST',
      body: JSON.stringify({
        device_ids: deviceIds,
        use_ai: useAI,
        auto_accept_high_confidence: autoAccept
      }),
    });
  },

  async getEnhancementStatus(): Promise<{
    total_suggestions: number;
    by_status: Record<string, number>;
    by_confidence: {
      high: number;
      medium: number;
      low: number;
    };
  }> {
    const DEVICE_INTELLIGENCE_API = import.meta.env.VITE_DEVICE_INTELLIGENCE_API || 'http://localhost:8019';
    return fetchJSON(`${DEVICE_INTELLIGENCE_API}/api/name-enhancement/status`);
  },
  };

export default api;


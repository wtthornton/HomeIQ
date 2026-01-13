/**
 * Blueprint Suggestions Service API Client
 * 
 * Connects to blueprint-suggestion-service on port 8032
 */

import { API_CONFIG } from '../config/api';

const BASE_URL = API_CONFIG.BLUEPRINT_SUGGESTIONS;

const API_KEY = import.meta.env.VITE_API_KEY;
if (!API_KEY) {
  console.error('VITE_API_KEY environment variable is not set. API requests will fail.');
  if (import.meta.env.MODE === 'production') {
    throw new Error('VITE_API_KEY is required in production mode.');
  }
}

export interface DeviceMatch {
  entity_id: string;
  domain: string;
  device_class?: string;
  area_id?: string;
  area_name?: string;
  device_id?: string;
  friendly_name?: string;
}

export interface BlueprintSuggestion {
  id: string;
  blueprint_id: string;
  blueprint_name: string;
  blueprint_description?: string;
  suggestion_score: number;
  matched_devices: DeviceMatch[];
  use_case?: string;
  status: string;
  created_at: string;
  updated_at: string;
  accepted_at?: string;
  declined_at?: string;
  conversation_id?: string;
}

export interface BlueprintSuggestionListResponse {
  suggestions: BlueprintSuggestion[];
  total: number;
  limit: number;
  offset: number;
}

export interface AcceptSuggestionResponse {
  id: string;
  status: string;
  blueprint_id: string;
  blueprint_yaml?: string;
  blueprint_inputs: Record<string, any>;
  matched_devices: DeviceMatch[];
  suggestion_score: number;
  conversation_id?: string;
}

export interface SuggestionStats {
  total_suggestions: number;
  pending_count: number;
  accepted_count: number;
  declined_count: number;
  average_score: number;
  min_score: number;
  max_score: number;
}

export class BlueprintSuggestionsAPIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'BlueprintSuggestionsAPIError';
  }
}

function withAuthHeaders(headers: HeadersInit = {}): HeadersInit {
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
  const headers = withAuthHeaders({
    'Content-Type': 'application/json',
    ...options?.headers,
  });

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail: string | undefined;
    try {
      const text = await response.text();
      if (text && text.trim()) {
        try {
          const errorBody = JSON.parse(text);
          errorDetail = errorBody.detail || errorBody.message || response.statusText;
        } catch {
          errorDetail = text || response.statusText;
        }
      } else {
        errorDetail = response.statusText;
      }
    } catch (error) {
      errorDetail = response.statusText || 'Unknown error';
    }

    throw new BlueprintSuggestionsAPIError(response.status, `API Error: ${errorDetail}`);
  }

  const contentLength = response.headers.get('content-length');
  if (contentLength === '0') {
    return undefined as T;
  }

  try {
    return await response.json();
  } catch (error) {
    console.error(`Failed to parse JSON response from ${url}:`, error);
    throw error;
  }
}

/**
 * Get blueprint suggestions with filters
 */
export async function getSuggestions(params?: {
  min_score?: number;
  use_case?: string;
  status?: string;
  blueprint_id?: string;
  limit?: number;
  offset?: number;
}): Promise<BlueprintSuggestionListResponse> {
  const queryParams = new URLSearchParams();
  if (params?.min_score !== undefined) queryParams.append('min_score', params.min_score.toString());
  if (params?.use_case) queryParams.append('use_case', params.use_case);
  if (params?.status) queryParams.append('status', params.status);
  if (params?.blueprint_id) queryParams.append('blueprint_id', params.blueprint_id);
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  if (params?.offset) queryParams.append('offset', params.offset.toString());

  const url = `${BASE_URL}/suggestions${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
  return fetchJSON<BlueprintSuggestionListResponse>(url);
}

/**
 * Accept a blueprint suggestion
 */
export async function acceptSuggestion(
  suggestionId: string,
  conversationId?: string
): Promise<AcceptSuggestionResponse> {
  const queryParams = new URLSearchParams();
  if (conversationId) queryParams.append('conversation_id', conversationId);

  const url = `${BASE_URL}/${suggestionId}/accept${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
  return fetchJSON<AcceptSuggestionResponse>(url, {
    method: 'POST',
  });
}

/**
 * Decline a blueprint suggestion
 */
export async function declineSuggestion(suggestionId: string): Promise<{ id: string; status: string }> {
  return fetchJSON<{ id: string; status: string }>(`${BASE_URL}/${suggestionId}/decline`, {
    method: 'POST',
  });
}

/**
 * Get suggestion statistics
 */
export async function getStats(): Promise<SuggestionStats> {
  return fetchJSON<SuggestionStats>(`${BASE_URL}/stats`);
}

/**
 * Generate suggestions (admin/trigger endpoint)
 */
export async function generateSuggestions(params?: {
  min_score?: number;
  max_per_blueprint?: number;
}): Promise<{ generated: number; status: string }> {
  const queryParams = new URLSearchParams();
  if (params?.min_score !== undefined) queryParams.append('min_score', params.min_score.toString());
  if (params?.max_per_blueprint) queryParams.append('max_per_blueprint', params.max_per_blueprint.toString());

  const url = `${BASE_URL}/generate${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
  return fetchJSON<{ generated: number; status: string }>(url, {
    method: 'POST',
  });
}

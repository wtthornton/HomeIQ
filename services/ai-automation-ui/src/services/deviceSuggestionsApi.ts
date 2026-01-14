/**
 * Device Suggestions API Service
 * Phase 2: Device-Based Automation Suggestions Feature
 * 
 * Connects to ha-ai-agent-service on port 8030 for device suggestion generation
 */

import { API_CONFIG } from '../config/api';
import type { DeviceSuggestion } from '../components/ha-agent/DeviceSuggestions';

const BASE_URL = API_CONFIG.HA_AI_AGENT;

const API_KEY = import.meta.env.VITE_API_KEY;
if (!API_KEY) {
  console.error('VITE_API_KEY environment variable is not set. API requests will fail.');
  if (import.meta.env.MODE === 'production') {
    throw new Error('VITE_API_KEY is required in production mode.');
  }
}

/**
 * Device suggestion context configuration
 */
export interface DeviceSuggestionContext {
  include_synergies?: boolean;
  include_blueprints?: boolean;
  include_sports?: boolean;
  include_weather?: boolean;
}

/**
 * Device suggestions request
 */
export interface DeviceSuggestionsRequest {
  device_id: string;
  conversation_id?: string | null;
  context?: DeviceSuggestionContext;
}

/**
 * Device context information
 */
export interface DeviceContext {
  device_id: string;
  capabilities: Array<Record<string, any>>;
  related_synergies: Array<Record<string, any>>;
  compatible_blueprints: Array<Record<string, any>>;
  home_assistant_entities: Array<Record<string, any>>;
  home_assistant_services: Array<Record<string, any>>;
}

/**
 * Device suggestions response
 */
export interface DeviceSuggestionsResponse {
  suggestions: DeviceSuggestion[];
  device_context: DeviceContext;
}

/**
 * Device Suggestions API error class
 */
export class DeviceSuggestionsAPIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'DeviceSuggestionsAPIError';
  }
}

/**
 * Add authentication headers to requests
 */
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

/**
 * Fetch JSON with error handling
 */
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

    throw new DeviceSuggestionsAPIError(response.status, `API Error: ${errorDetail}`);
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
 * Generate device suggestions
 */
export async function generateDeviceSuggestions(
  request: DeviceSuggestionsRequest
): Promise<DeviceSuggestionsResponse> {
  return fetchJSON<DeviceSuggestionsResponse>(`${BASE_URL}/api/v1/chat/device-suggestions`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Device Suggestions API Service
 * Phase 2: Device-Based Automation Suggestions Feature
 *
 * Connects to ha-ai-agent-service on port 8030 for device suggestion generation
 */

import { fetchJSON, API_CONFIG } from '../lib/api-client';
import type { DeviceSuggestion } from '../components/ha-agent/DeviceSuggestions';

const BASE_URL = API_CONFIG.HA_AI_AGENT;

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

/** @deprecated Use APIError from lib/api-client instead */
export { APIError as DeviceSuggestionsAPIError } from '../lib/api-client';

/**
 * Generate device suggestions
 */
export async function generateDeviceSuggestions(
  request: DeviceSuggestionsRequest
): Promise<DeviceSuggestionsResponse> {
  return fetchJSON<DeviceSuggestionsResponse>(`${BASE_URL}/v1/chat/device-suggestions`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

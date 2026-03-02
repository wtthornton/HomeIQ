/**
 * Blueprint Suggestions Service API Client
 *
 * Connects to blueprint-suggestion-service on port 8032
 */

import { fetchJSON, API_CONFIG } from '../lib/api-client';

const BASE_URL = API_CONFIG.BLUEPRINT_SUGGESTIONS;

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

/** @deprecated Use APIError from lib/api-client instead */
export { APIError as BlueprintSuggestionsAPIError } from '../lib/api-client';

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

export interface GenerateSuggestionsRequest {
  device_ids?: string[];
  complexity?: 'simple' | 'medium' | 'high';
  use_case?: 'convenience' | 'security' | 'energy' | 'comfort';
  min_score?: number;
  max_suggestions?: number;
  min_quality_score?: number;
  domain?: string;
}

export interface GenerateSuggestionsResponse {
  generated: number;
  status: string;
  message?: string;
}

/**
 * Delete all blueprint suggestions
 */
export async function deleteAllSuggestions(): Promise<{ deleted: number; status: string }> {
  return fetchJSON<{ deleted: number; status: string }>(`${BASE_URL}/delete-all`, {
    method: 'DELETE',
  });
}

/**
 * Generate suggestions with user-defined parameters
 */
export async function generateSuggestions(
  request: GenerateSuggestionsRequest
): Promise<GenerateSuggestionsResponse> {
  return fetchJSON<GenerateSuggestionsResponse>(`${BASE_URL}/generate`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

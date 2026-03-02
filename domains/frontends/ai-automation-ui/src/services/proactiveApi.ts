/**
 * Proactive Agent Service API Client
 * Epic AI-21: Context-aware automation suggestions
 *
 * Endpoints:
 * - GET  /api/proactive/suggestions          - List suggestions
 * - GET  /api/proactive/suggestions/{id}     - Get by ID
 * - PATCH /api/proactive/suggestions/{id}    - Update status
 * - DELETE /api/proactive/suggestions/{id}   - Delete
 * - GET  /api/proactive/suggestions/stats/summary - Stats
 * - POST /api/proactive/suggestions/trigger  - Manual trigger
 */

import type {
  ProactiveSuggestion,
  ProactiveSuggestionFilters,
  ProactiveSuggestionListResponse,
  ProactiveSuggestionStats,
  ProactiveSuggestionStatus,
  ProactiveTriggerResponse,
} from '../types/proactive';
import { fetchJSON } from '../lib/api-client';

const PROACTIVE_API_BASE = '/api/proactive/suggestions';

/** @deprecated Use APIError from lib/api-client instead */
export { APIError as ProactiveAPIError } from '../lib/api-client';

export const proactiveApi = {
  /**
   * List proactive suggestions with optional filters
   */
  async getSuggestions(
    filters?: ProactiveSuggestionFilters
  ): Promise<ProactiveSuggestionListResponse> {
    const params = new URLSearchParams();

    if (filters?.status) {
      params.append('status', filters.status);
    }
    if (filters?.context_type) {
      params.append('context_type', filters.context_type);
    }
    if (filters?.limit !== undefined) {
      params.append('limit', filters.limit.toString());
    }
    if (filters?.offset !== undefined) {
      params.append('offset', filters.offset.toString());
    }

    const queryString = params.toString();
    const url = queryString ? `${PROACTIVE_API_BASE}?${queryString}` : PROACTIVE_API_BASE;

    return fetchJSON<ProactiveSuggestionListResponse>(url);
  },

  /**
   * Get a single suggestion by ID
   */
  async getSuggestion(id: string): Promise<ProactiveSuggestion> {
    return fetchJSON<ProactiveSuggestion>(`${PROACTIVE_API_BASE}/${id}`);
  },

  /**
   * Update suggestion status (approve/reject)
   */
  async updateSuggestionStatus(
    id: string,
    status: ProactiveSuggestionStatus
  ): Promise<ProactiveSuggestion> {
    return fetchJSON<ProactiveSuggestion>(`${PROACTIVE_API_BASE}/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  },

  /**
   * Delete a suggestion
   */
  async deleteSuggestion(id: string): Promise<{ success: boolean; message: string }> {
    return fetchJSON<{ success: boolean; message: string }>(`${PROACTIVE_API_BASE}/${id}`, {
      method: 'DELETE',
    });
  },

  /**
   * Get suggestion statistics
   */
  async getStats(): Promise<ProactiveSuggestionStats> {
    return fetchJSON<ProactiveSuggestionStats>(`${PROACTIVE_API_BASE}/stats/summary`);
  },

  /**
   * Manually trigger suggestion generation
   */
  async triggerGeneration(): Promise<ProactiveTriggerResponse> {
    return fetchJSON<ProactiveTriggerResponse>(`${PROACTIVE_API_BASE}/trigger`, {
      method: 'POST',
    });
  },

  /**
   * Send a suggestion to the HA AI Agent Service
   */
  async sendToAgent(id: string): Promise<ProactiveSuggestion> {
    return fetchJSON<ProactiveSuggestion>(`${PROACTIVE_API_BASE}/${id}/send`, {
      method: 'POST',
    });
  },

  /**
   * Health check for proactive-agent-service
   */
  async healthCheck(): Promise<{ status: string }> {
    // Note: health endpoint is at root, not under /suggestions
    return fetchJSON<{ status: string }>('/api/proactive/../health');
  },
};

export default proactiveApi;

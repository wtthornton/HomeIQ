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

const PROACTIVE_API_BASE = '/api/proactive/suggestions';

// Get API key from environment (same as main api.ts)
const API_KEY = import.meta.env.VITE_API_KEY;

export class ProactiveAPIError extends Error {
  constructor(
    public status: number,
    message: string,
    public details?: unknown
  ) {
    super(message);
    this.name = 'ProactiveAPIError';
  }
}

/**
 * Add authentication headers to request
 */
function getHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (API_KEY) {
    headers['Authorization'] = `Bearer ${API_KEY}`;
    headers['X-HomeIQ-API-Key'] = API_KEY;
  }

  return headers;
}

/**
 * Generic fetch wrapper with error handling
 */
async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  try {
    const response = await fetch(url, {
      ...options,
      headers: getHeaders(),
    });

    if (!response.ok) {
      let errorMessage = response.statusText;
      let errorDetails: unknown = null;

      try {
        const errorBody = await response.json();
        errorMessage = errorBody.detail || errorBody.message || errorMessage;
        errorDetails = errorBody;
      } catch {
        // Ignore JSON parse errors
      }

      throw new ProactiveAPIError(response.status, errorMessage, errorDetails);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ProactiveAPIError) {
      throw error;
    }

    // Network error or other fetch failure
    if (error instanceof TypeError && error.message === 'Failed to fetch') {
      throw new ProactiveAPIError(
        0,
        'Unable to connect to Proactive Agent Service. Please check if the service is running.',
        { originalError: error.message }
      );
    }

    throw new ProactiveAPIError(
      500,
      error instanceof Error ? error.message : 'Unknown error',
      error
    );
  }
}

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
   * Health check for proactive-agent-service
   */
  async healthCheck(): Promise<{ status: string }> {
    // Note: health endpoint is at root, not under /suggestions
    return fetchJSON<{ status: string }>('/api/proactive/../health');
  },
};

export default proactiveApi;

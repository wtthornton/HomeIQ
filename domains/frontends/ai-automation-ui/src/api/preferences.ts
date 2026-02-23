/**
 * Preferences API Client
 * 
 * API functions for managing suggestion preferences:
 * - max_suggestions (5-50)
 * - creativity_level (conservative/balanced/creative)
 * - blueprint_preference (low/medium/high)
 * 
 * Epic AI-6 Story AI6.12: Frontend Preference Settings UI
 */

export interface Preferences {
  max_suggestions: number;
  creativity_level: 'conservative' | 'balanced' | 'creative';
  blueprint_preference: 'low' | 'medium' | 'high';
}

export interface PreferenceUpdateRequest {
  max_suggestions?: number;
  creativity_level?: 'conservative' | 'balanced' | 'creative';
  blueprint_preference?: 'low' | 'medium' | 'high';
}

export const defaultPreferences: Preferences = {
  max_suggestions: 10,
  creativity_level: 'balanced',
  blueprint_preference: 'medium',
};

const API_BASE = '/api/v1';
const API_KEY = import.meta.env.VITE_API_KEY || 'hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR';

/**
 * Add authentication headers to request options
 */
function withAuthHeaders(headers: HeadersInit = {}): HeadersInit {
  const authHeaders: Record<string, string> = {
    'Authorization': `Bearer ${API_KEY}`,
    'X-HomeIQ-API-Key': API_KEY,
  };

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

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    return response.json() as Promise<T>;
  }

  const message = await response.text();
  throw new Error(message || `Request failed with status ${response.status}`);
}

/**
 * Get current user preferences
 * Returns default preferences if not found (404)
 */
export async function getPreferences(userId: string = 'default'): Promise<Preferences> {
  try {
    const headers = withAuthHeaders({
      Accept: 'application/json',
    });

    const response = await fetch(`${API_BASE}/preferences?user_id=${encodeURIComponent(userId)}`, {
      method: 'GET',
      headers,
      credentials: 'include',
    });

    // Handle 404 gracefully - return default preferences if not found
    if (response.status === 404) {
      console.log('Preferences not found, using defaults');
      return defaultPreferences;
    }

    // Check if response is OK before processing
    if (!response.ok) {
      // For non-404 errors, try to get error message but don't throw
      const errorText = await response.text().catch(() => 'Unknown error');
      console.warn(`Failed to load preferences (status ${response.status}):`, errorText);
      // Return defaults for any error (network, 500, etc.)
      return defaultPreferences;
    }

    return handleResponse<Preferences>(response);
  } catch (error) {
    // Network errors, fetch failures, etc. - return defaults
    console.warn('Error loading preferences, using defaults:', error);
    return defaultPreferences;
  }
}

/**
 * Update user preferences
 */
export async function updatePreferences(
  preferences: PreferenceUpdateRequest,
  userId: string = 'default'
): Promise<Preferences> {
  const headers = withAuthHeaders({
    'Content-Type': 'application/json',
    Accept: 'application/json',
  });

  const response = await fetch(`${API_BASE}/preferences?user_id=${encodeURIComponent(userId)}`, {
    method: 'PUT',
    headers,
    credentials: 'include',
    body: JSON.stringify(preferences),
  });

  return handleResponse<Preferences>(response);
}

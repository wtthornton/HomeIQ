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
 */
export async function getPreferences(userId: string = 'default'): Promise<Preferences> {
  const headers = withAuthHeaders({
    Accept: 'application/json',
  });

  const response = await fetch(`${API_BASE}/preferences?user_id=${encodeURIComponent(userId)}`, {
    method: 'GET',
    headers,
    credentials: 'include',
  });

  return handleResponse<Preferences>(response);
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

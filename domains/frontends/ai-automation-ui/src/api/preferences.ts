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

import { fetchJSON } from '../lib/api-client';

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

/**
 * Get current user preferences
 * Returns default preferences if not found (404)
 */
export async function getPreferences(userId: string = 'default'): Promise<Preferences> {
  try {
    return await fetchJSON<Preferences>(`${API_BASE}/preferences?user_id=${encodeURIComponent(userId)}`);
  } catch (error: unknown) {
    const err = error as { status?: number };
    if (err.status === 404) {
      return defaultPreferences;
    }
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
  return fetchJSON<Preferences>(`${API_BASE}/preferences?user_id=${encodeURIComponent(userId)}`, {
    method: 'PUT',
    body: JSON.stringify(preferences),
  });
}

import { Page } from '@playwright/test';

/**
 * Authentication Helpers
 * Helper functions for handling authentication in tests
 */

const DEFAULT_API_KEY = 'hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR';

/**
 * Set API key for health-dashboard (sessionStorage.api_key per api.ts getAuthHeaders)
 */
export async function setApiKey(page: Page, apiKey: string = DEFAULT_API_KEY): Promise<void> {
  await page.addInitScript((key) => {
    sessionStorage.setItem('api_key', key);
    localStorage.setItem('apiKey', key); // backward compat
  }, apiKey);
}

/**
 * Set authentication token
 */
export async function setAuthToken(page: Page, token: string): Promise<void> {
  await page.addInitScript((authToken) => {
    localStorage.setItem('authToken', authToken);
  }, token);
}

/**
 * Clear authentication data
 */
export async function clearAuth(page: Page): Promise<void> {
  await page.addInitScript(() => {
    localStorage.removeItem('apiKey');
    localStorage.removeItem('authToken');
  });
}

/**
 * Set authorization header for API requests
 */
export async function setAuthHeader(
  page: Page,
  apiKey: string = DEFAULT_API_KEY
): Promise<void> {
  await page.setExtraHTTPHeaders({
    'Authorization': `Bearer ${apiKey}`,
    'X-HomeIQ-API-Key': apiKey,
  });
}

/**
 * Setup authenticated session
 */
export async function setupAuthenticatedSession(
  page: Page,
  apiKey: string = DEFAULT_API_KEY
): Promise<void> {
  await setApiKey(page, apiKey);
  await setAuthHeader(page, apiKey);
}

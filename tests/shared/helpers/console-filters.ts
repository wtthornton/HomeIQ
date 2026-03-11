/**
 * Console error filters for E2E tests.
 * Used to ignore known non-critical errors (env, backend not ready, network) so
 * "no console errors" tests pass when running against Docker or partial backends.
 */

/**
 * Returns true if the console error message is ignorable in E2E (not a real app bug).
 */
export function isIgnorableConsoleError(message: string): boolean {
  const m = message;
  if (!m || typeof m !== 'string') return true;
  // DevTools / tooling
  if (m.includes('favicon') || m.includes('sourcemap') || m.includes('DevTools') || m.includes('deprecated')) return true;
  // Env / build (no API key in E2E is expected)
  if (m.includes('VITE_API_KEY is not set') || m.includes('API requests may fail with 401')) return true;
  // HTTP status from backend not ready or auth
  if (m.includes('Failed to load resource:') && (
    m.includes('503') || m.includes('502') || m.includes('501') ||
    m.includes('401') || m.includes('404 (Not Found)') || m.includes('500 (Internal Server Error)')
  )) return true;
  // Backend service not ready
  if (m.includes('Service not ready') || m.includes('APIError: Service not ready')) return true;
  if (m.includes('Failed to load conversations') || m.includes('Chat error: APIError')) return true;
  // Patterns / DB (e.g. relation "patterns" does not exist in test env)
  if (m.includes('Failed to load patterns') || m.includes('relation "patterns" does not exist')) return true;
  if (m.includes('Failed to load analysis status') || m.includes('Unable to connect to /api/')) return true;
  // Discovery / recommendations
  if (m.includes('Error fetching recommendations') || m.includes('Failed to fetch recommendations')) return true;
  if (m.includes('Error fetching devices') || m.includes('Failed to fetch entities')) return true;
  return false;
}

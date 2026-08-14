/**
 * taskApi production BASE path tests (bug-hunt c4, BUG-HomeIQ-4-3).
 *
 * taskApi.ts computes its production BASE from `import.meta.env.MODE` at
 * module-load time, so the buggy doubled-/v1/ path only reproduces when the
 * module is (re-)imported under MODE=production — not under the dev-time
 * default that vitest runs with, which is exactly how the bug stayed masked
 * locally.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const mockFetchJSON = vi.fn();
vi.mock('../../lib/api-client', () => ({
  fetchJSON: (...args: unknown[]) => mockFetchJSON(...args),
}));

describe('taskApi production BASE', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it('does not double /v1/ under production mode', async () => {
    vi.stubEnv('MODE', 'production');
    vi.resetModules();
    mockFetchJSON.mockResolvedValue({ tasks: [], total: 0 });

    const { taskApi } = await import('../taskApi');
    await taskApi.listTasks();

    const url = mockFetchJSON.mock.calls[0][0] as string;
    expect(url).not.toContain('/v1/v1/');
    expect(url).toBe('/api/proactive/tasks');
  });
});

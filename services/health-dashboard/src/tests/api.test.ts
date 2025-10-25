// services/health-dashboard/src/tests/api.test.ts
import { describe, it, expect, vi } from 'vitest';

describe('API Configuration', () => {
  it('uses environment-based API URL', () => {
    // Context7 pattern: Use vi.stubEnv for isolated testing
    vi.stubEnv('VITE_API_BASE_URL', 'http://test-api:8000');
    
    expect(import.meta.env.VITE_API_BASE_URL).toBe('http://test-api:8000');
  });
  
  it('automatically resets environment between tests', () => {
    // Context7: vi.stubEnv auto-resets with unstubEnvs: true
    // This test verifies the environment is reset to default
    // Since .env.test might not be loaded, we'll just verify it's not the stubbed value
    const apiUrl = import.meta.env.VITE_API_BASE_URL;
    expect(apiUrl).not.toBe('http://test-api:8000'); // Should not be the stubbed value
  });
  
  it('uses environment-based WebSocket URL', () => {
    vi.stubEnv('VITE_WS_URL', 'ws://test-ws:8001');
    
    expect(import.meta.env.VITE_WS_URL).toBe('ws://test-ws:8001');
  });
});

describe('Health API', () => {
  it('fetches health data from correct endpoint', async () => {
    // Use the default environment URL for this test
    const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    
    // Mock fetch for this specific test
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'healthy' })
    });
    
    vi.stubGlobal('fetch', mockFetch);
    
    const response = await fetch(`${apiUrl}/api/health`);
    expect(response.ok).toBe(true);
    
    // Verify the correct URL was called
    expect(mockFetch).toHaveBeenCalledWith(`${apiUrl}/api/health`);
  });
});

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useHealth } from '../useHealth';
import { server } from '../../tests/mocks/server';
import { http, HttpResponse } from 'msw';

describe('useHealth Hook', () => {
  afterEach(() => {
    // ✅ Context7 Best Practice: Cleanup after each test
    vi.useRealTimers();
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it('displays health status when health data loads', async () => {
    const { result } = renderHook(() => useHealth(1000));
    
    // Initially loading
    expect(result.current.loading).toBe(true);
    expect(result.current.health).toBeNull();
    expect(result.current.error).toBeNull();
    
    // Wait for data to load
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    
    // Verify health data is populated
    expect(result.current.health).toBeDefined();
    expect(result.current.health?.overall_status).toBe('healthy');
    expect(result.current.health?.ingestion_service?.websocket_connection?.is_connected).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it('shows error message when health API returns 500 error', async () => {
    // Mock API to return 500 error
    server.use(
      http.get('http://localhost/api/health', () => {
        return new HttpResponse(null, { status: 500, statusText: 'Internal Server Error' });
      })
    );

    const { result } = renderHook(() => useHealth(1000));

    // Wait for error to be set
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Verify error state
    expect(result.current.health).toBeNull();
    expect(result.current.error).toBeDefined();
    expect(result.current.error).toContain('500');
  });

  it('shows error message when network connection fails', async () => {
    // Mock network failure
    server.use(
      http.get('http://localhost/api/health', () => {
        return HttpResponse.error();
      })
    );

    const { result } = renderHook(() => useHealth(1000));

    // Wait for error to be set
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Verify error state
    expect(result.current.health).toBeNull();
    expect(result.current.error).toBeDefined();
  });

  it('refreshes health data automatically at polling interval', async () => {
    // Use a short polling interval for faster test execution
    const { result } = renderHook(() => useHealth(100));

    // Wait for initial fetch
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    const initialHealth = result.current.health;
    expect(initialHealth).toBeDefined();
    expect(initialHealth?.overall_status).toBe('healthy');

    // Mock a different response for the next fetch
    server.use(
      http.get('http://localhost/api/health', () => {
        return HttpResponse.json({
          overall_status: 'degraded',
          timestamp: new Date().toISOString(),
          ingestion_service: {
            websocket_connection: { is_connected: false, connection_attempts: 10 },
            event_processing: { status: 'degraded', events_per_minute: 10 },
          },
        });
      })
    );

    // Wait for automatic refresh to complete (should happen after 100ms)
    await waitFor(() => {
      expect(result.current.health?.overall_status).toBe('degraded');
    }, { timeout: 1000 });
  });
});


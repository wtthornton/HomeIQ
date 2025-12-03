import { describe, it, expect, afterEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useStatistics } from '../useStatistics';
import { server } from '../../tests/mocks/server';
import { http, HttpResponse } from 'msw';

describe('useStatistics Hook', () => {
  afterEach(() => {
    // ✅ Context7 Best Practice: Cleanup after each test
    server.resetHandlers();
    vi.useRealTimers();
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it('displays statistics data when API responds successfully', async () => {
    const { result } = renderHook(() => useStatistics('1h', 1000));

    // Initially loading
    expect(result.current.loading).toBe(true);
    expect(result.current.statistics).toBeNull();
    expect(result.current.error).toBeNull();

    // Wait for data to load
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Verify statistics data is populated
    expect(result.current.statistics).toBeDefined();
    expect(result.current.statistics?.total_events).toBe(12345);
    expect(result.current.statistics?.events_per_minute).toBe(42);
    expect(result.current.error).toBeNull();
  });

  it('shows error message when statistics API returns error', async () => {
    // Mock API to return 500 error
    server.use(
      http.get('http://localhost/api/v1/stats', () => {
        return new HttpResponse(null, { status: 500, statusText: 'Internal Server Error' });
      })
    );

    const { result } = renderHook(() => useStatistics('1h', 1000));

    // Wait for error to be set
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Verify error state
    expect(result.current.statistics).toBeNull();
    expect(result.current.error).toBeDefined();
    expect(result.current.error).toContain('500');
  });

  it('passes correct period parameter to API request', async () => {
    let requestedPeriod = '';

    server.use(
      http.get('http://localhost/api/v1/stats', ({ request }) => {
        const url = new URL(request.url);
        requestedPeriod = url.searchParams.get('period') || '';
        return HttpResponse.json({
          total_events: 999,
          events_per_minute: 10,
          error_rate: 1.0,
        });
      })
    );

    const { result } = renderHook(() => useStatistics('24h', 1000));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Verify period parameter was passed correctly
    expect(requestedPeriod).toBe('24h');
  });
});


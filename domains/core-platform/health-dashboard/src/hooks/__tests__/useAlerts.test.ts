import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from '../../tests/mocks/server';
import { useAlerts } from '../useAlerts';

const mockAlerts = [
  {
    id: 'alert-1',
    name: 'High CPU',
    severity: 'critical',
    status: 'active',
    message: 'CPU usage above 90%',
    service: 'data-api',
    created_at: '2025-01-01T00:00:00Z',
  },
  {
    id: 'alert-2',
    name: 'Disk Space',
    severity: 'warning',
    status: 'active',
    message: 'Disk usage above 80%',
    service: 'websocket-ingestion',
    created_at: '2025-01-01T00:00:00Z',
  },
];

const mockSummary = {
  total_active: 2,
  critical: 1,
  warning: 1,
  info: 0,
  total_alerts: 2,
  alert_history_count: 5,
};

function setupHandlers(options?: { alertsError?: boolean; httpStatus?: number }) {
  server.use(
    http.get('/api/v1/alerts/summary', () => {
      return HttpResponse.json(mockSummary);
    }),
    http.get('/api/v1/alerts', () => {
      if (options?.alertsError) {
        return new HttpResponse(null, { status: options.httpStatus || 500, statusText: 'Internal Server Error' });
      }
      return HttpResponse.json(mockAlerts);
    }),
  );
}

describe('useAlerts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    setupHandlers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('starts in loading state', () => {
    const { result } = renderHook(() => useAlerts({ autoRefresh: false }));
    expect(result.current.loading).toBe(true);
  });

  it('fetches alerts successfully', async () => {
    const { result } = renderHook(() => useAlerts({ autoRefresh: false }));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.alerts).toEqual(mockAlerts);
    expect(result.current.error).toBeNull();
  });

  it('fetches summary alongside alerts', async () => {
    const { result } = renderHook(() => useAlerts({ autoRefresh: false }));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.summary).toEqual(mockSummary);
  });

  it('handles HTTP error responses', async () => {
    setupHandlers({ alertsError: true, httpStatus: 500 });

    const { result } = renderHook(() => useAlerts({ autoRefresh: false }));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toContain('500');
  });

  it('sets lastUpdate on successful fetch', async () => {
    const { result } = renderHook(() => useAlerts({ autoRefresh: false }));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.lastUpdate).toBeInstanceOf(Date);
  });

  it('provides refresh, acknowledgeAlert, and resolveAlert functions', async () => {
    const { result } = renderHook(() => useAlerts({ autoRefresh: false }));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(typeof result.current.refresh).toBe('function');
    expect(typeof result.current.acknowledgeAlert).toBe('function');
    expect(typeof result.current.resolveAlert).toBe('function');
  });

  it('returns empty alerts initially', () => {
    const { result } = renderHook(() => useAlerts({ autoRefresh: false }));
    expect(result.current.alerts).toEqual([]);
    expect(result.current.summary).toBeNull();
  });

  it('handles network error gracefully', async () => {
    server.use(
      http.get('/api/v1/alerts', () => {
        return HttpResponse.error();
      }),
    );

    const { result } = renderHook(() => useAlerts({ autoRefresh: false }));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBeTruthy();
  });
});

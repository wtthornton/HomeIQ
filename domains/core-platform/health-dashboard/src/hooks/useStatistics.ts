import { useState, useEffect, useRef, useCallback } from 'react';
import { Statistics } from '../types';
import { apiService } from '../services/api';

const FETCH_TIMEOUT_MS = 10000;

function fetchWithTimeout<T>(fetchFn: () => Promise<T>, timeoutMs: number): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timeoutId = setTimeout(() => {
      reject(new Error('Request timed out'));
    }, timeoutMs);

    fetchFn()
      .then((result) => {
        clearTimeout(timeoutId);
        resolve(result);
      })
      .catch((err) => {
        clearTimeout(timeoutId);
        reject(err);
      });
  });
}

export const useStatistics = (period: string = '1h', refreshInterval: number = 60000) => {
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const mountedRef = useRef(true);

  const fetchStatistics = useCallback(async () => {
    try {
      const statsData = await fetchWithTimeout(
        () => apiService.getStatistics(period),
        FETCH_TIMEOUT_MS
      );
      if (mountedRef.current) {
        setStatistics(statsData);
        setError(null);
        setLastUpdated(new Date());
      }
    } catch (err) {
      if (mountedRef.current) {
        const message = err instanceof Error ? err.message : 'Failed to fetch statistics';
        setError(message);
        // Don't clear existing statistics — keep stale value visible
        console.error('Statistics fetch error:', err);
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [period]);

  useEffect(() => {
    mountedRef.current = true;
    let interval: ReturnType<typeof setInterval> | null = null;

    const startPolling = () => {
      fetchStatistics();
      interval = setInterval(fetchStatistics, refreshInterval);
    };

    const stopPolling = () => {
      if (interval) {
        clearInterval(interval);
        interval = null;
      }
    };

    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopPolling();
      } else {
        startPolling();
      }
    };

    startPolling();
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      mountedRef.current = false;
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [period, refreshInterval, fetchStatistics]);

  const refresh = useCallback(async () => {
    if (!mountedRef.current) return;
    setLoading(true);
    await fetchStatistics();
  }, [fetchStatistics]);

  return { statistics, loading, error, lastUpdated, refresh };
};

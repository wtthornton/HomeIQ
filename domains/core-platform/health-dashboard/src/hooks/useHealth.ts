import { useState, useEffect, useRef, useCallback } from 'react';
import { HealthStatus } from '../types';
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

export const useHealth = (refreshInterval: number = 30000) => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const mountedRef = useRef(true);

  const fetchHealth = useCallback(async () => {
    try {
      const healthData = await fetchWithTimeout(
        () => apiService.getHealth(),
        FETCH_TIMEOUT_MS
      );
      if (mountedRef.current) {
        setHealth(healthData);
        setError(null);
        setLastUpdated(new Date());
      }
    } catch (err) {
      if (mountedRef.current) {
        const message = err instanceof Error ? err.message : 'Failed to fetch health data';
        setError(message);
        // Don't clear existing health data — keep stale value visible
        console.error('Health fetch error:', err);
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    let interval: ReturnType<typeof setInterval> | null = null;

    const startPolling = () => {
      fetchHealth();
      interval = setInterval(fetchHealth, refreshInterval);
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
  }, [refreshInterval, fetchHealth]);

  const refresh = useCallback(async () => {
    setLoading(true);
    await fetchHealth();
  }, [fetchHealth]);

  return { health, loading, error, lastUpdated, refresh };
};

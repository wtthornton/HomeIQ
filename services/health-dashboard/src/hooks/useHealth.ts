import { useState, useEffect } from 'react';
import { HealthStatus } from '../types';
import { apiService } from '../services/api';

export const useHealth = (refreshInterval: number = 30000) => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    const controller = new AbortController();
    let interval: ReturnType<typeof setInterval> | null = null;

    const fetchHealth = async () => {
      try {
        setError(null);
        const healthData = await apiService.getHealth();
        if (mounted) {
          setHealth(healthData);
        }
      } catch (err) {
        if (mounted && !controller.signal.aborted) {
          setError(err instanceof Error ? err.message : 'Failed to fetch health data');
          console.error('Health fetch error:', err);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

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
      mounted = false;
      controller.abort();
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [refreshInterval]);

  const refresh = async () => {
    try {
      setError(null);
      const healthData = await apiService.getHealth();
      setHealth(healthData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch health data');
      console.error('Health fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  return { health, loading, error, refresh };
};

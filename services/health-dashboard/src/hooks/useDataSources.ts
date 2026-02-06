import { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import { DataSourcesHealthMap } from '../types';

export const useDataSources = (refreshInterval: number = 30000) => {
  const [dataSources, setDataSources] = useState<DataSourcesHealthMap | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    const controller = new AbortController();
    let interval: ReturnType<typeof setInterval> | null = null;

    const fetchDataSources = async () => {
      try {
        const data = await apiService.getAllDataSources();
        if (mounted) {
          setDataSources(data);
          setError(null);
        }
      } catch (err) {
        if (mounted && !controller.signal.aborted) {
          setError(err instanceof Error ? err.message : 'Failed to fetch data sources');
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    const startPolling = () => {
      fetchDataSources();
      interval = setInterval(fetchDataSources, refreshInterval);
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

  const refetch = async () => {
    try {
      const data = await apiService.getAllDataSources();
      setDataSources(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data sources');
    } finally {
      setLoading(false);
    }
  };

  return { dataSources, loading, error, refetch };
};


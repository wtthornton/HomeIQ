import { useState, useEffect } from 'react';
import { Statistics } from '../types';
import { apiService } from '../services/api';

export const useStatistics = (period: string = '1h', refreshInterval: number = 60000) => {
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    const controller = new AbortController();

    const fetchStatistics = async () => {
      try {
        setError(null);
        const statsData = await apiService.getStatistics(period);
        if (mounted) {
          setStatistics(statsData);
        }
      } catch (err) {
        if (mounted && !controller.signal.aborted) {
          setError(err instanceof Error ? err.message : 'Failed to fetch statistics');
          console.error('Statistics fetch error:', err);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    // Initial fetch
    fetchStatistics();

    // Set up polling
    const interval = setInterval(fetchStatistics, refreshInterval);

    return () => {
      mounted = false;
      controller.abort();
      clearInterval(interval);
    };
  }, [period, refreshInterval]);

  const refresh = async () => {
    try {
      setError(null);
      const statsData = await apiService.getStatistics(period);
      setStatistics(statsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch statistics');
      console.error('Statistics fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  return { statistics, loading, error, refresh };
};

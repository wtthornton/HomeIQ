/**
 * Custom hook for real-time metrics polling
 * Story 23.3: Enhanced Dependencies UI
 */

import { useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/api';

export interface RealTimeMetrics {
  events_per_hour: number;
  api_calls_active: number;
  data_sources_active: string[];
  api_metrics: ApiMetric[];
  inactive_apis: number;
  error_apis: number;
  total_apis: number;
  health_summary: {
    healthy: number;
    unhealthy: number;
    total: number;
    health_percentage: number;
  };
  timestamp: string;
  error?: string;
}

export interface ApiMetric {
  service: string;
  events_per_hour: number;
  uptime_seconds: number;
  status: 'active' | 'inactive' | 'error' | 'timeout' | 'not_configured';
  response_time_ms?: number;
  last_success?: string;
  error_message?: string;
  is_fallback?: boolean;
}

export const useRealTimeMetrics = (pollInterval: number = 5000) => {
  const [metrics, setMetrics] = useState<RealTimeMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = useCallback(async () => {
    try {
      setError(null);
      const data = await apiService.getRealTimeMetrics();
      setMetrics(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch metrics';
      setError(errorMessage);
      console.error('Error fetching real-time metrics:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | null = null;

    const startPolling = () => {
      fetchMetrics();
      interval = setInterval(fetchMetrics, pollInterval);
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
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [fetchMetrics, pollInterval]);

  return {
    metrics,
    loading,
    error,
    refetch: fetchMetrics
  };
};
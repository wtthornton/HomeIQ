/**
 * useAnalyticsData Hook
 * 
 * Custom hook for fetching and managing analytics data
 * Extracted from AnalyticsPanel to reduce complexity
 */

import { useState, useEffect, useCallback } from 'react';
import type { AnalyticsData } from '../mocks/analyticsMock';

export type TimeRange = '1h' | '6h' | '24h' | '7d';

interface UseAnalyticsDataReturn {
  data: AnalyticsData | null;
  loading: boolean;
  error: string | null;
  lastUpdate: Date;
  refetch: () => Promise<void>;
}

/**
 * Fetch and manage analytics data from the data-api service
 * 
 * @param timeRange - Time range for analytics (1h, 6h, 24h, 7d)
 * @param options - Optional configuration
 * @returns Analytics data, loading state, error state, and refetch function
 * 
 * @example
 * ```tsx
 * const { data, loading, error, refetch } = useAnalyticsData('1h');
 * 
 * if (loading) return <LoadingState />;
 * if (error) return <ErrorState message={error} />;
 * if (!data) return null;
 * 
 * return <AnalyticsDisplay data={data} onRefresh={refetch} />;
 * ```
 */
export function useAnalyticsData(
  timeRange: TimeRange,
  options: { autoRefresh?: boolean; refreshInterval?: number } = {}
): UseAnalyticsDataReturn {
  const { autoRefresh = true, refreshInterval = 60000 } = options;

  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  /**
   * Fetch analytics data from the API
   */
  const fetchAnalytics = useCallback(async (): Promise<void> => {
    try {
      // Fetch real analytics data from data-api
      const response = await fetch(`/api/v1/analytics?range=${timeRange}`, {
        headers: {
          'Content-Type': 'application/json',
          ...(sessionStorage.getItem('api_key') ? { 'X-API-Key': sessionStorage.getItem('api_key')! } : {}),
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const responseData = await response.json();
      
      setData(responseData);
      setError(null);
      setLastUpdate(new Date());
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch analytics');
      setLoading(false);
      console.error('Error fetching analytics:', err);
    }
  }, [timeRange]);

  // Initial fetch and auto-refresh
  useEffect(() => {
    fetchAnalytics();
    
    if (autoRefresh) {
      const interval = setInterval(fetchAnalytics, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [fetchAnalytics, autoRefresh, refreshInterval]);

  return {
    data,
    loading,
    error,
    lastUpdate,
    refetch: fetchAnalytics
  };
}


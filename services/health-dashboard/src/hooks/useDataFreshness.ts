/**
 * Data Freshness Hook
 * 
 * Tracks when data was last successfully loaded and determines if it's stale.
 * Prevents showing false/default values until real data has loaded at least once.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';

export interface DataFreshnessState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  lastUpdate: Date | null;
  isStale: boolean;
  hasLoadedOnce: boolean; // Critical: tracks if we've ever received real data
  staleThresholdMs: number; // Default: 60 seconds
}

export interface UseDataFreshnessOptions {
  staleThresholdMs?: number; // Consider data stale after this many milliseconds
  initialData?: any; // Initial data value (null by default)
}

/**
 * Hook to track data freshness and prevent false data display
 * 
 * @param fetchFn - Function that fetches the data
 * @param refreshInterval - How often to refresh (ms), 0 = no auto-refresh
 * @param options - Additional options
 * 
 * @example
 * ```tsx
 * const { data, loading, error, isStale, hasLoadedOnce } = useDataFreshness(
 *   () => apiService.getHealth(),
 *   30000, // Refresh every 30s
 *   { staleThresholdMs: 60000 } // Consider stale after 60s
 * );
 * 
 * // Only show data if we've loaded it at least once
 * if (!hasLoadedOnce) {
 *   return <LoadingSpinner />;
 * }
 * 
 * // Show stale indicator if data is old
 * return (
 *   <div>
 *     {isStale && <StaleDataIndicator />}
 *     <DataDisplay data={data} />
 *   </div>
 * );
 * ```
 */
export function useDataFreshness<T>(
  fetchFn: () => Promise<T>,
  refreshInterval: number = 0,
  options: UseDataFreshnessOptions = {}
): DataFreshnessState<T> {
  const {
    staleThresholdMs = 60000, // Default: 60 seconds
    initialData = null
  } = options;

  const [data, setData] = useState<T | null>(initialData as T | null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [hasLoadedOnce, setHasLoadedOnce] = useState<boolean>(false);

  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const result = await fetchFn();
      
      // Only set data if we got a non-null result
      // This prevents overwriting real data with null/empty responses
      if (result !== null && result !== undefined) {
        setData(result);
        setLastUpdate(new Date());
        setHasLoadedOnce(true); // Mark that we've received real data at least once
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch data';
      setError(errorMessage);
      console.error('Data fetch error:', err);
      // Don't clear existing data on error - show stale data with error indicator
    } finally {
      setLoading(false);
    }
  }, [fetchFn]);

  // Initial fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-refresh if interval is set
  useEffect(() => {
    if (refreshInterval > 0) {
      const interval = setInterval(fetchData, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [fetchData, refreshInterval]);

  // Calculate if data is stale
  const isStale = useMemo(() => {
    if (!lastUpdate) return true; // No data = stale
    const age = Date.now() - lastUpdate.getTime();
    return age > staleThresholdMs;
  }, [lastUpdate, staleThresholdMs]);

  return {
    data,
    loading,
    error,
    lastUpdate,
    isStale,
    hasLoadedOnce,
    staleThresholdMs
  };
}


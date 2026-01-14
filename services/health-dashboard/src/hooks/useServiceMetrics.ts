/**
 * useServiceMetrics Hook
 * 
 * React hook for managing service metrics state and updates
 * 
 * Prototype: Basic implementation with manual refresh
 */

import { useState, useEffect, useCallback } from 'react';
import { serviceMetricsClient } from '../services/serviceMetricsClient';
import type { ServiceMetrics } from '../types/serviceMetrics';

export interface UseServiceMetricsResult {
  metrics: ServiceMetrics | null;
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
  refresh: () => Promise<void>;
  clearCache: () => void;
}

export interface UseServiceMetricsOptions {
  serviceId: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
  enabled?: boolean;
}

export function useServiceMetrics(
  options: UseServiceMetricsOptions
): UseServiceMetricsResult {
  const { serviceId, autoRefresh = false, refreshInterval = 5000, enabled = true } = options;

  const [metrics, setMetrics] = useState<ServiceMetrics | null>(null);
  const [loading, setLoading] = useState(true); // Start with loading true for initial fetch
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchMetrics = useCallback(async () => {
    if (!enabled || !serviceId) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const fetchedMetrics = await serviceMetricsClient.fetchMetrics(serviceId);
      if (fetchedMetrics) {
        setMetrics(fetchedMetrics);
        setLastUpdated(new Date());
      } else {
        setError('Failed to fetch metrics');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      console.error('Error fetching service metrics:', err);
    } finally {
      setLoading(false);
    }
  }, [serviceId, enabled]);

  const refresh = useCallback(async () => {
    serviceMetricsClient.clearCache(serviceId);
    await fetchMetrics();
  }, [serviceId, fetchMetrics]);

  const clearCache = useCallback(() => {
    serviceMetricsClient.clearCache(serviceId);
  }, [serviceId]);

  // Initial fetch
  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  // Auto-refresh (prototype: disabled, will be enabled in full implementation)
  useEffect(() => {
    if (!autoRefresh || !enabled) {
      return;
    }

    const interval = setInterval(() => {
      fetchMetrics();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, enabled, fetchMetrics]);

  return {
    metrics,
    loading,
    error,
    lastUpdated,
    refresh,
    clearCache,
  };
}

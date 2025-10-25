/**
 * useAlerts Hook
 * Story 21.5: Alerts Tab Implementation
 * 
 * Fetches and manages alert data with filtering and actions
 */

import { useState, useEffect, useCallback } from 'react';
import type { Alert, AlertFilters, AlertSummary } from '../types/alerts';

interface UseAlertsProps {
  filters?: AlertFilters;
  pollInterval?: number;
  autoRefresh?: boolean;
}

interface UseAlertsReturn {
  alerts: Alert[];
  summary: AlertSummary | null;
  loading: boolean;
  error: string | null;
  lastUpdate: Date | null;
  refresh: () => Promise<void>;
  acknowledgeAlert: (alertId: string) => Promise<boolean>;
  resolveAlert: (alertId: string) => Promise<boolean>;
}

export const useAlerts = ({
  filters = {},
  pollInterval = 120000, // Increased from 60s to 120s (2 minutes)
  autoRefresh = true
}: UseAlertsProps = {}): UseAlertsReturn => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [summary, setSummary] = useState<AlertSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  // Fetch alerts from API
  const fetchAlerts = useCallback(async () => {
    try {
      setError(null);
      
      // Build query parameters
      const params = new URLSearchParams();
      if (filters.severity) params.append('severity', filters.severity);
      if (filters.service) params.append('service', filters.service);
      if (filters.status) params.append('status', filters.status);
      
      // Fetch alerts
      const alertsResponse = await fetch(`/api/v1/alerts?${params.toString()}`);
      if (!alertsResponse.ok) {
        throw new Error(`HTTP ${alertsResponse.status}: ${alertsResponse.statusText}`);
      }
      
      const alertsData: Alert[] = await alertsResponse.json();
      setAlerts(alertsData);
      
      // Fetch summary
      const summaryResponse = await fetch('/api/v1/alerts/summary');
      if (summaryResponse.ok) {
        const summaryData: AlertSummary = await summaryResponse.json();
        setSummary(summaryData);
      }
      
      setLastUpdate(new Date());
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch alerts');
      setLoading(false);
      console.error('Error fetching alerts:', err);
    }
  }, [filters]);

  // Acknowledge an alert
  const acknowledgeAlert = useCallback(async (alertId: string): Promise<boolean> => {
    try {
      const response = await fetch(`/api/v1/alerts/${alertId}/acknowledge`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      // Update local state optimistically
      setAlerts(prev => prev.map(alert => 
        alert.id === alertId 
          ? { ...alert, status: 'acknowledged', acknowledged_at: new Date().toISOString() }
          : alert
      ));

      // Refresh to get updated data
      await fetchAlerts();
      
      return true;
    } catch (err) {
      console.error('Error acknowledging alert:', err);
      setError(err instanceof Error ? err.message : 'Failed to acknowledge alert');
      return false;
    }
  }, [fetchAlerts]);

  // Resolve an alert
  const resolveAlert = useCallback(async (alertId: string): Promise<boolean> => {
    try {
      const response = await fetch(`/api/v1/alerts/${alertId}/resolve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      // Update local state optimistically
      setAlerts(prev => prev.map(alert => 
        alert.id === alertId 
          ? { ...alert, status: 'resolved', resolved_at: new Date().toISOString() }
          : alert
      ));

      // Refresh to get updated data
      await fetchAlerts();
      
      return true;
    } catch (err) {
      console.error('Error resolving alert:', err);
      setError(err instanceof Error ? err.message : 'Failed to resolve alert');
      return false;
    }
  }, [fetchAlerts]);

  // Initial fetch and auto-refresh setup
  useEffect(() => {
    fetchAlerts();

    if (autoRefresh) {
      const interval = setInterval(fetchAlerts, pollInterval);
      return () => clearInterval(interval);
    }
  }, [fetchAlerts, pollInterval, autoRefresh]);

  return {
    alerts,
    summary,
    loading,
    error,
    lastUpdate,
    refresh: fetchAlerts,
    acknowledgeAlert,
    resolveAlert,
  };
};


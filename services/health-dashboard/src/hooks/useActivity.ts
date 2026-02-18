/**
 * useActivity - Fetches current household activity from data-api
 * Story 2.3: Epic Activity Recognition Integration
 */

import { useState, useEffect, useCallback } from 'react';
import { dataApi } from '../services/api';

const STALE_MINUTES = 10;
const POLL_INTERVAL_MS = 60000; // 1 min

export interface ActivityData {
  activity: string;
  activity_id: number;
  confidence: number;
  timestamp: string;
}

export function useActivity(pollIntervalMs: number = POLL_INTERVAL_MS) {
  const [activity, setActivity] = useState<ActivityData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchActivity = useCallback(async () => {
    try {
      setError(null);
      const data = await dataApi.getCurrentActivity();
      setActivity(data);
      return data;
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Activity unavailable';
      setError(msg);
      setActivity(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchActivity();
    const id = setInterval(fetchActivity, pollIntervalMs);
    return () => clearInterval(id);
  }, [fetchActivity, pollIntervalMs]);

  const isStale = activity?.timestamp
    ? (Date.now() - new Date(activity.timestamp).getTime()) > STALE_MINUTES * 60 * 1000
    : false;

  return {
    activity,
    loading,
    error,
    isStale,
    refresh: fetchActivity,
  };
}

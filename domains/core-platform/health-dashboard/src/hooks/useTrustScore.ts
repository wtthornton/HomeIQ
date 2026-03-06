import { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = '/api/v1';
const FETCH_TIMEOUT_MS = 10000;

export interface TrustScore {
  domain: string;
  trust_score: number;
  approvals: number;
  rejections: number;
  overrides: number;
  total_interactions: number;
}

export interface TrustScoresResponse {
  scores: TrustScore[];
  updated_at?: string;
}

export interface TrustLevel {
  min: number;
  label: string;
  color: string;
  textColor: string;
}

export const TRUST_LEVELS: Record<string, TrustLevel> = {
  high: { min: 0.8, label: 'High Trust', color: 'bg-green-500', textColor: 'text-green-500' },
  medium: { min: 0.4, label: 'Medium Trust', color: 'bg-yellow-500', textColor: 'text-yellow-500' },
  low: { min: 0.0, label: 'Low Trust', color: 'bg-red-500', textColor: 'text-red-500' },
};

export function getTrustLevel(score: number): TrustLevel {
  if (score >= 0.8) return TRUST_LEVELS.high;
  if (score >= 0.4) return TRUST_LEVELS.medium;
  return TRUST_LEVELS.low;
}

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

export const useTrustScores = (refreshInterval: number = 30000) => {
  const [scores, setScores] = useState<TrustScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const mountedRef = useRef(true);

  const fetchScores = useCallback(async () => {
    try {
      const response = await fetchWithTimeout(
        async () => {
          const res = await fetch(`${API_BASE}/memories/trust`);
          if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
          }
          return res.json() as Promise<TrustScoresResponse>;
        },
        FETCH_TIMEOUT_MS
      );
      
      if (mountedRef.current) {
        setScores(response.scores || []);
        setError(null);
        setLastUpdated(new Date());
      }
    } catch (err) {
      if (mountedRef.current) {
        const message = err instanceof Error ? err.message : 'Failed to fetch trust scores';
        setError(message);
        console.error('Trust scores fetch error:', err);
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
      fetchScores();
      interval = setInterval(fetchScores, refreshInterval);
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
  }, [refreshInterval, fetchScores]);

  const refresh = useCallback(async () => {
    setLoading(true);
    await fetchScores();
  }, [fetchScores]);

  return { scores, loading, error, lastUpdated, refresh };
};

export const useTrustScore = (domain: string, refreshInterval: number = 30000) => {
  const { scores, loading, error, lastUpdated, refresh } = useTrustScores(refreshInterval);
  
  const score = scores.find(s => s.domain === domain) ?? null;
  const trustLevel = score ? getTrustLevel(score.trust_score) : null;
  
  return { score, trustLevel, loading, error, lastUpdated, refresh };
};

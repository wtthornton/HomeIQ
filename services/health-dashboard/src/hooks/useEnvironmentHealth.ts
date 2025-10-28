/**
 * Custom React hook for environment health monitoring
 * 
 * Context7 Pattern: useState/useEffect for real-time updates with 30-second polling
 * 
 * Updated: Fixed port configuration from 8020 to 8027 to match docker-compose mapping
 */
import { useState, useEffect, useCallback } from 'react';
import { EnvironmentHealth } from '../types/health';

const SETUP_SERVICE_URL = 'http://localhost:8027';  // Port 8027 (container internal port is 8020, external is 8027)
const POLL_INTERVAL = 30000; // 30 seconds

interface UseEnvironmentHealthReturn {
  health: EnvironmentHealth | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useEnvironmentHealth(): UseEnvironmentHealthReturn {
  const [health, setHealth] = useState<EnvironmentHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = useCallback(async () => {
    try {
      setError(null);
      const response = await fetch(`${SETUP_SERVICE_URL}/api/health/environment`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      setHealth(data);
      setLoading(false);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch health data';
      setError(errorMessage);
      setLoading(false);
      console.error('Error fetching environment health:', err);
    }
  }, []);

  // Initial fetch on mount
  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  // Set up 30-second polling (Context7 best practice)
  useEffect(() => {
    const interval = setInterval(() => {
      fetchHealth();
    }, POLL_INTERVAL);

    // Cleanup on unmount (Context7 requirement)
    return () => clearInterval(interval);
  }, [fetchHealth]);

  return {
    health,
    loading,
    error,
    refetch: fetchHealth
  };
}


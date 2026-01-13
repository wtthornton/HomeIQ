/**
 * Custom React hook for environment health monitoring
 * 
 * Context7 Pattern: useState/useEffect for real-time updates with 30-second polling
 * 
 * Updated: Fixed port configuration from 8020 to 8027 to match docker-compose mapping
 */
import { useState, useEffect, useCallback } from 'react';
import { EnvironmentHealth } from '../types/health';

const SETUP_SERVICE_URL = '/setup-service';  // Proxied through nginx to ha-setup-service
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
      setLoading(true);
      const response = await fetch(`${SETUP_SERVICE_URL}/api/health/environment`);

      const bodyText = await response.text();

      if (!response.ok) {
        // Provide user-friendly error messages based on status code
        let errorMessage: string;
        
        if (response.status === 502) {
          errorMessage = 'The setup service is not available. It may be starting up, not running, or experiencing issues. Please check that the ha-setup-service is running and accessible.';
        } else if (response.status === 503) {
          errorMessage = 'The setup service is temporarily unavailable. Please try again in a few moments.';
        } else if (response.status === 404) {
          errorMessage = 'The health endpoint was not found. This may indicate a configuration issue.';
        } else if (response.status === 500) {
          errorMessage = 'The setup service encountered an internal error.';
        } else {
          // For other status codes, try to extract a clean error message
          let detail = response.statusText;
          
          if (bodyText) {
            try {
              const parsed = JSON.parse(bodyText);
              detail = parsed?.detail || parsed?.message || detail;
            } catch (parseError) {
              // If it's not JSON, check if it's HTML and strip it
              if (bodyText.trim().startsWith('<')) {
                // HTML response (e.g., from nginx error page) - use status text
                detail = response.statusText;
              } else {
                // Plain text - use it but truncate if too long
                detail = bodyText.length > 200 ? bodyText.substring(0, 200) + '...' : bodyText;
              }
            }
          }
          
          errorMessage = `Setup service error ${response.status}: ${detail}`;
        }
        
        throw new Error(errorMessage);
      }

      let parsed: unknown;
      try {
        parsed = bodyText ? JSON.parse(bodyText) : null;
      } catch (parseError) {
        throw new Error('Received malformed health payload from setup service');
      }

      if (!parsed || typeof parsed !== 'object') {
        throw new Error('Setup service returned empty health payload');
      }

      // Ensure required fields have defaults to prevent crashes
      const healthData = parsed as any;
      const normalizedHealth: EnvironmentHealth = {
        health_score: healthData.health_score ?? 0,
        ha_status: healthData.ha_status ?? 'unknown',
        ha_version: healthData.ha_version,
        integrations: Array.isArray(healthData.integrations) ? healthData.integrations : [],
        performance: healthData.performance ?? {
          response_time_ms: 0
        },
        issues_detected: Array.isArray(healthData.issues_detected) ? healthData.issues_detected : [],
        timestamp: healthData.timestamp ?? new Date().toISOString()
      };

      setHealth(normalizedHealth);
      setLoading(false);
    } catch (err) {
      let errorMessage: string;
      
      if (err instanceof TypeError && err.message.includes('fetch')) {
        // Network error - fetch failed completely
        errorMessage = 'Unable to connect to the setup service. Please check your network connection and ensure the service is running.';
      } else if (err instanceof Error) {
        errorMessage = err.message;
      } else {
        errorMessage = 'Failed to fetch health data. Please try again.';
      }
      
      setError(errorMessage);
      setHealth(null);
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


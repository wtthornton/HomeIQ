/**
 * ServiceMetricsClient
 * 
 * Centralized client for fetching service-specific metrics.
 * Handles caching, error handling, and fallback logic.
 * 
 * Features:
 * - In-memory caching with TTL
 * - Automatic cache invalidation
 * - Error handling and logging
 * - Service-specific fetcher registry
 * 
 * Prototype: Basic implementation for websocket-ingestion service
 */

import type { ServiceMetrics } from '../types/serviceMetrics';
import { getServiceMetricsConfig } from '../config/serviceMetricsConfig';

/**
 * Cached metrics structure
 */
interface CachedMetrics {
  data: ServiceMetrics;
  timestamp: number; // Unix timestamp in milliseconds
  ttl: number; // Time to live in milliseconds
}

/**
 * ServiceMetricsClient
 * 
 * Singleton client for fetching and caching service metrics.
 * Provides efficient caching to reduce API calls and improve performance.
 */
class ServiceMetricsClient {
  private readonly cache: Map<string, CachedMetrics> = new Map();
  private readonly defaultTTL = 3000; // 3 seconds
  private readonly defaultTimeout = 5000; // 5 seconds

  /**
   * Fetch metrics for a service
   * 
   * @param serviceId - The service identifier (e.g., 'websocket-ingestion')
   * @returns Promise resolving to ServiceMetrics or null if unavailable
   * 
   * @example
   * ```typescript
   * const metrics = await serviceMetricsClient.fetchMetrics('websocket-ingestion');
   * if (metrics) {
   *   console.log('Events per minute:', metrics.performance.eventsPerMinute);
   * }
   * ```
   */
  async fetchMetrics(serviceId: string): Promise<ServiceMetrics | null> {
    if (!serviceId || typeof serviceId !== 'string') {
      console.warn('Invalid serviceId provided to fetchMetrics:', serviceId);
      return null;
    }

    // Check cache first
    const cached = this.getCachedMetrics(serviceId);
    if (cached) {
      return cached;
    }

    // Fetch from service
    try {
      const metrics = await this.fetchFromService(serviceId);
      if (metrics) {
        this.setCache(serviceId, metrics);
        return metrics;
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error(`Failed to fetch metrics for ${serviceId}:`, errorMessage, error);
    }

    return null;
  }

  /**
   * Get cached metrics if available and fresh
   * 
   * @param serviceId - The service identifier
   * @returns Cached metrics if available and not expired, null otherwise
   */
  getCachedMetrics(serviceId: string): ServiceMetrics | null {
    if (!serviceId) {
      return null;
    }

    const cached = this.cache.get(serviceId);
    if (!cached) {
      return null;
    }

    const now = Date.now();
    const age = now - cached.timestamp;
    
    if (age > cached.ttl) {
      // Cache expired, remove it
      this.cache.delete(serviceId);
      return null;
    }

    return cached.data;
  }

  /**
   * Set cache for a service
   * 
   * @param serviceId - The service identifier
   * @param metrics - The metrics data to cache
   * @param ttl - Optional TTL override (default: 3000ms)
   */
  private setCache(serviceId: string, metrics: ServiceMetrics, ttl?: number): void {
    if (!serviceId || !metrics) {
      return;
    }

    this.cache.set(serviceId, {
      data: metrics,
      timestamp: Date.now(),
      ttl: ttl ?? this.defaultTTL,
    });
  }

  /**
   * Clear cache for a service or all services
   * 
   * @param serviceId - Optional service identifier. If provided, clears only that service's cache.
   *                    If omitted, clears all cached metrics.
   * 
   * @example
   * ```typescript
   * // Clear cache for specific service
   * serviceMetricsClient.clearCache('websocket-ingestion');
   * 
   * // Clear all caches
   * serviceMetricsClient.clearCache();
   * ```
   */
  clearCache(serviceId?: string): void {
    if (serviceId) {
      this.cache.delete(serviceId);
    } else {
      this.cache.clear();
    }
  }

  /**
   * Check if cached metrics are expired
   * 
   * @param serviceId - The service identifier
   * @returns true if cache is expired or doesn't exist, false if fresh
   */
  isExpired(serviceId: string): boolean {
    if (!serviceId) {
      return true;
    }

    const cached = this.cache.get(serviceId);
    if (!cached) {
      return true;
    }

    const now = Date.now();
    return now - cached.timestamp > cached.ttl;
  }

  /**
   * Fetch metrics from service endpoint using configured fetcher
   * 
   * @param serviceId - The service identifier
   * @returns Promise resolving to ServiceMetrics or null on error
   * @private
   */
  private async fetchFromService(serviceId: string): Promise<ServiceMetrics | null> {
    const config = getServiceMetricsConfig(serviceId);
    if (!config?.fetcher) {
      console.warn(`No metrics fetcher configured for service: ${serviceId}`);
      return null;
    }

    try {
      const metrics = await config.fetcher(serviceId);
      if (!metrics) {
        console.warn(`Fetcher returned null for service: ${serviceId}`);
        return null;
      }
      return metrics;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error(`Error in fetcher for ${serviceId}:`, errorMessage, error);
      return null;
    }
  }

  /**
   * Get cache statistics (for debugging/monitoring)
   * 
   * @returns Object with cache size and service IDs
   */
  getCacheStats(): { size: number; services: string[] } {
    return {
      size: this.cache.size,
      services: Array.from(this.cache.keys()),
    };
  }
}

// Singleton instance
export const serviceMetricsClient = new ServiceMetricsClient();

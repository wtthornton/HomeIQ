/**
 * ServiceMetricsClient
 * 
 * Centralized client for fetching service-specific metrics.
 * Handles caching, error handling, and fallback logic.
 * 
 * Prototype: Basic implementation for websocket-ingestion service
 */

import type { ServiceMetrics } from '../types/serviceMetrics';
import { getServiceMetricsConfig } from '../config/serviceMetricsConfig';

interface CachedMetrics {
  data: ServiceMetrics;
  timestamp: number;
  ttl: number;
}

class ServiceMetricsClient {
  private cache: Map<string, CachedMetrics> = new Map();
  private defaultTTL = 3000; // 3 seconds
  private defaultTimeout = 5000; // 5 seconds

  /**
   * Fetch metrics for a service
   */
  async fetchMetrics(serviceId: string): Promise<ServiceMetrics | null> {
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
      console.error(`Failed to fetch metrics for ${serviceId}:`, error);
    }

    return null;
  }

  /**
   * Get cached metrics if available and fresh
   */
  getCachedMetrics(serviceId: string): ServiceMetrics | null {
    const cached = this.cache.get(serviceId);
    if (!cached) {
      return null;
    }

    const now = Date.now();
    if (now - cached.timestamp > cached.ttl) {
      this.cache.delete(serviceId);
      return null;
    }

    return cached.data;
  }

  /**
   * Set cache for a service
   */
  private setCache(serviceId: string, metrics: ServiceMetrics, ttl?: number): void {
    this.cache.set(serviceId, {
      data: metrics,
      timestamp: Date.now(),
      ttl: ttl || this.defaultTTL,
    });
  }

  /**
   * Clear cache for a service or all services
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
   */
  isExpired(serviceId: string): boolean {
    const cached = this.cache.get(serviceId);
    if (!cached) {
      return true;
    }

    const now = Date.now();
    return now - cached.timestamp > cached.ttl;
  }

  /**
   * Fetch metrics from service endpoint
   */
  private async fetchFromService(serviceId: string): Promise<ServiceMetrics | null> {
    const config = getServiceMetricsConfig(serviceId);
    if (!config || !config.fetcher) {
      console.warn(`No metrics fetcher configured for service: ${serviceId}`);
      return null;
    }

    try {
      return await config.fetcher(serviceId);
    } catch (error) {
      console.error(`Error in fetcher for ${serviceId}:`, error);
      return null;
    }
  }
}

// Singleton instance
export const serviceMetricsClient = new ServiceMetricsClient();

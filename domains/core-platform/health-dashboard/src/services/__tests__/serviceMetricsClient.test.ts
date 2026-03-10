/**
 * ServiceMetricsClient Tests
 *
 * Unit tests for caching, fetching, and error handling.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { serviceMetricsClient } from '../serviceMetricsClient';
import type { ServiceMetrics } from '../../types/serviceMetrics';

// Mock the config module
vi.mock('../../config/serviceMetricsConfig', () => ({
  getServiceMetricsConfig: vi.fn(),
}));

import { getServiceMetricsConfig } from '../../config/serviceMetricsConfig';

const mockGetConfig = vi.mocked(getServiceMetricsConfig);

const mockMetrics: ServiceMetrics = {
  serviceId: 'websocket-ingestion',
  timestamp: new Date().toISOString(),
  operational: { status: 'healthy', uptime: 3600 },
  performance: { eventsPerMinute: 42, totalRequests: 12345 },
  errors: { errorRate: 0.5, totalErrors: 3 },
  resources: { memoryMB: 128, cpuPercent: 15 },
};

describe('ServiceMetricsClient', () => {
  beforeEach(() => {
    serviceMetricsClient.clearCache();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should fetch metrics for a service', async () => {
    const mockFetcher = vi.fn().mockResolvedValue(mockMetrics);
    mockGetConfig.mockReturnValue({
      serviceId: 'websocket-ingestion',
      fetcher: mockFetcher,
      groups: [],
    });

    const result = await serviceMetricsClient.fetchMetrics('websocket-ingestion');

    expect(mockFetcher).toHaveBeenCalledWith('websocket-ingestion');
    expect(result).toEqual(mockMetrics);
  });

  it('should cache metrics with TTL', async () => {
    const mockFetcher = vi.fn().mockResolvedValue(mockMetrics);
    mockGetConfig.mockReturnValue({
      serviceId: 'websocket-ingestion',
      fetcher: mockFetcher,
      groups: [],
    });

    await serviceMetricsClient.fetchMetrics('websocket-ingestion');

    // Second call should use cache — fetcher only called once
    const cached = await serviceMetricsClient.fetchMetrics('websocket-ingestion');
    expect(cached).toEqual(mockMetrics);
    expect(mockFetcher).toHaveBeenCalledTimes(1);
  });

  it('should return cached metrics if available and fresh', async () => {
    const mockFetcher = vi.fn().mockResolvedValue(mockMetrics);
    mockGetConfig.mockReturnValue({
      serviceId: 'test-service',
      fetcher: mockFetcher,
      groups: [],
    });

    await serviceMetricsClient.fetchMetrics('test-service');

    const cached = serviceMetricsClient.getCachedMetrics('test-service');
    expect(cached).toEqual(mockMetrics);
  });

  it('should return null if cache expired', async () => {
    const mockFetcher = vi.fn().mockResolvedValue(mockMetrics);
    mockGetConfig.mockReturnValue({
      serviceId: 'test-service',
      fetcher: mockFetcher,
      groups: [],
    });

    await serviceMetricsClient.fetchMetrics('test-service');

    // Advance time past the default TTL (3000ms)
    vi.spyOn(Date, 'now').mockReturnValue(Date.now() + 5000);

    const cached = serviceMetricsClient.getCachedMetrics('test-service');
    expect(cached).toBeNull();
  });

  it('should clear cache for specific service', async () => {
    const mockFetcher = vi.fn().mockResolvedValue(mockMetrics);
    mockGetConfig.mockReturnValue({
      serviceId: 'websocket-ingestion',
      fetcher: mockFetcher,
      groups: [],
    });

    await serviceMetricsClient.fetchMetrics('websocket-ingestion');
    expect(serviceMetricsClient.getCachedMetrics('websocket-ingestion')).not.toBeNull();

    serviceMetricsClient.clearCache('websocket-ingestion');
    expect(serviceMetricsClient.getCachedMetrics('websocket-ingestion')).toBeNull();
  });

  it('should clear all cache', async () => {
    const mockFetcher = vi.fn().mockResolvedValue(mockMetrics);
    mockGetConfig.mockReturnValue({
      serviceId: 'websocket-ingestion',
      fetcher: mockFetcher,
      groups: [],
    });

    await serviceMetricsClient.fetchMetrics('websocket-ingestion');
    expect(serviceMetricsClient.getCacheStats().size).toBe(1);

    serviceMetricsClient.clearCache();
    expect(serviceMetricsClient.getCacheStats().size).toBe(0);
  });

  it('should handle fetch errors gracefully', async () => {
    const mockFetcher = vi.fn().mockRejectedValue(new Error('Network error'));
    mockGetConfig.mockReturnValue({
      serviceId: 'failing-service',
      fetcher: mockFetcher,
      groups: [],
    });

    const result = await serviceMetricsClient.fetchMetrics('failing-service');
    expect(result).toBeNull();
  });
});

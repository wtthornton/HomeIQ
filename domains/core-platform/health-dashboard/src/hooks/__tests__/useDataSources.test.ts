import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useDataSources } from '../useDataSources';

vi.mock('../../services/api', () => ({
  apiService: {
    getAllDataSources: vi.fn(),
  },
}));

import { apiService } from '../../services/api';

const mockApiService = vi.mocked(apiService);

const mockDataSources = {
  weather: { status: 'healthy', last_update: '2025-01-01T00:00:00Z' },
  sports: { status: 'healthy', last_update: '2025-01-01T00:00:00Z' },
  carbonIntensity: null,
  electricityPricing: null,
  airQuality: null,
  blueprintIndex: null,
  ruleRecommendation: null,
  calendar: null,
  smartMeter: null,
};

describe('useDataSources', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockApiService.getAllDataSources.mockResolvedValue(mockDataSources as any);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('starts in loading state', () => {
    const { result } = renderHook(() => useDataSources(60000));
    expect(result.current.loading).toBe(true);
  });

  it('fetches data sources successfully', async () => {
    const { result } = renderHook(() => useDataSources(60000));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.dataSources).toEqual(mockDataSources);
    expect(result.current.error).toBeNull();
  });

  it('handles fetch error', async () => {
    mockApiService.getAllDataSources.mockRejectedValue(new Error('API unavailable'));

    const { result } = renderHook(() => useDataSources(60000));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe('API unavailable');
  });

  it('handles non-Error rejection', async () => {
    mockApiService.getAllDataSources.mockRejectedValue('string error');

    const { result } = renderHook(() => useDataSources(60000));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe('Failed to fetch data sources');
  });

  it('provides a refetch function', async () => {
    const { result } = renderHook(() => useDataSources(60000));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(typeof result.current.refetch).toBe('function');
  });

  it('returns null dataSources initially before fetch completes', () => {
    // Create a never-resolving promise to keep loading state
    mockApiService.getAllDataSources.mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useDataSources(60000));

    expect(result.current.dataSources).toBeNull();
    expect(result.current.loading).toBe(true);
  });

  it('clears error on successful refetch', async () => {
    mockApiService.getAllDataSources.mockRejectedValueOnce(new Error('fail'));

    const { result } = renderHook(() => useDataSources(60000));

    await waitFor(() => {
      expect(result.current.error).toBe('fail');
    });

    // Now make it succeed
    mockApiService.getAllDataSources.mockResolvedValue(mockDataSources as any);

    await result.current.refetch();

    await waitFor(() => {
      expect(result.current.error).toBeNull();
    });

    expect(result.current.dataSources).toEqual(mockDataSources);
  });
});

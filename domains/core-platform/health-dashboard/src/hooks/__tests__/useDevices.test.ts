import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useDevices } from '../useDevices';

// Mock the dataApi module
vi.mock('../../services/api', () => ({
  dataApi: {
    getDevices: vi.fn(),
    getEntities: vi.fn(),
    getIntegrations: vi.fn(),
  },
}));

import { dataApi } from '../../services/api';

const mockDataApi = vi.mocked(dataApi);

const mockDevices = [
  {
    device_id: 'dev-1',
    name: 'Living Room Light',
    manufacturer: 'Philips',
    model: 'Hue Bulb',
    entity_count: 3,
    timestamp: '2025-01-01T00:00:00Z',
    status: 'active',
  },
  {
    device_id: 'dev-2',
    name: 'Thermostat',
    manufacturer: 'Nest',
    model: 'Learning',
    entity_count: 5,
    timestamp: '2025-01-01T00:00:00Z',
    status: 'active',
  },
];

const mockEntities = [
  {
    entity_id: 'light.living_room',
    device_id: 'dev-1',
    domain: 'light',
    platform: 'hue',
    disabled: false,
    timestamp: '2025-01-01T00:00:00Z',
  },
];

const mockIntegrations = [
  {
    entry_id: 'int-1',
    domain: 'hue',
    title: 'Philips Hue',
    state: 'loaded',
    version: 1,
    timestamp: '2025-01-01T00:00:00Z',
  },
];

describe('useDevices', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockDataApi.getDevices.mockResolvedValue({ devices: mockDevices });
    mockDataApi.getEntities.mockResolvedValue({ entities: mockEntities });
    mockDataApi.getIntegrations.mockResolvedValue({ integrations: mockIntegrations });
  });

  it('starts in loading state', () => {
    const { result } = renderHook(() => useDevices());
    expect(result.current.loading).toBe(true);
  });

  it('fetches devices successfully', async () => {
    const { result } = renderHook(() => useDevices());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.devices).toEqual(mockDevices);
    expect(result.current.error).toBeNull();
  });

  it('fetches entities successfully', async () => {
    const { result } = renderHook(() => useDevices());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.entities).toEqual(mockEntities);
  });

  it('fetches integrations successfully', async () => {
    const { result } = renderHook(() => useDevices());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.integrations).toEqual(mockIntegrations);
  });

  it('handles device fetch error', async () => {
    mockDataApi.getDevices.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useDevices());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe('Network error');
  });

  it('handles non-Error rejection in device fetch', async () => {
    mockDataApi.getDevices.mockRejectedValue('string error');

    const { result } = renderHook(() => useDevices());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe('Failed to fetch devices');
  });

  it('handles entity fetch error without clearing device error', async () => {
    mockDataApi.getEntities.mockRejectedValue(new Error('Entity fetch failed'));

    const { result } = renderHook(() => useDevices());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Entities error should not override device data
    expect(result.current.devices).toEqual(mockDevices);
  });

  it('handles integrations fetch error gracefully', async () => {
    mockDataApi.getIntegrations.mockRejectedValue(new Error('Integrations failed'));

    const { result } = renderHook(() => useDevices());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Integrations should be empty on error
    expect(result.current.integrations).toEqual([]);
  });

  it('provides a refresh function that re-fetches all data', async () => {
    const { result } = renderHook(() => useDevices());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Clear to check re-fetch
    vi.clearAllMocks();
    mockDataApi.getDevices.mockResolvedValue({ devices: [] });
    mockDataApi.getEntities.mockResolvedValue({ entities: [] });
    mockDataApi.getIntegrations.mockResolvedValue({ integrations: [] });

    await act(async () => {
      await result.current.refresh();
    });

    expect(mockDataApi.getDevices).toHaveBeenCalled();
    expect(mockDataApi.getEntities).toHaveBeenCalled();
    expect(mockDataApi.getIntegrations).toHaveBeenCalled();
  });

  it('handles empty response gracefully', async () => {
    mockDataApi.getDevices.mockResolvedValue({ devices: undefined });
    mockDataApi.getEntities.mockResolvedValue({ entities: undefined });
    mockDataApi.getIntegrations.mockResolvedValue({ integrations: undefined });

    const { result } = renderHook(() => useDevices());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.devices).toEqual([]);
    expect(result.current.entities).toEqual([]);
    expect(result.current.integrations).toEqual([]);
  });
});

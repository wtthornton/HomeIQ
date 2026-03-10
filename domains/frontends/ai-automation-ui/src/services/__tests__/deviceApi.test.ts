/**
 * Device API Tests
 * Story 44.8: Device API client coverage.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockFetchJSON = vi.fn();
vi.mock('../../lib/api-client', () => ({
  fetchJSON: (...args: unknown[]) => mockFetchJSON(...args),
  API_CONFIG: {
    DATA: 'http://localhost:8006/api',
    AI_AUTOMATION: 'http://localhost:8018/api',
    HA_AI_AGENT: 'http://localhost:8030/api',
    BLUEPRINT_SUGGESTIONS: 'http://localhost:8039/api/blueprint-suggestions',
  },
  APIError: class APIError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.name = 'APIError';
      this.status = status;
    }
  },
}));

import {
  listDevices,
  getDevice,
  getDeviceCapabilities,
  listEntities,
  getEntity,
} from '../deviceApi';

describe('deviceApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('listDevices', () => {
    it('fetches devices without params', async () => {
      mockFetchJSON.mockResolvedValue({ devices: [], count: 0, limit: 100 });

      await listDevices();

      expect(mockFetchJSON).toHaveBeenCalledWith('http://localhost:8006/api/devices');
    });

    it('appends filter params', async () => {
      mockFetchJSON.mockResolvedValue({ devices: [], count: 0, limit: 50 });

      await listDevices({ limit: 50, manufacturer: 'Philips', area_id: 'kitchen' });

      const url = mockFetchJSON.mock.calls[0][0];
      expect(url).toContain('limit=50');
      expect(url).toContain('manufacturer=Philips');
      expect(url).toContain('area_id=kitchen');
    });

    it('includes device_type and device_category params', async () => {
      mockFetchJSON.mockResolvedValue({ devices: [], count: 0, limit: 100 });

      await listDevices({ device_type: 'light', device_category: 'smart' });

      const url = mockFetchJSON.mock.calls[0][0];
      expect(url).toContain('device_type=light');
      expect(url).toContain('device_category=smart');
    });

    it('returns device list', async () => {
      const devices = [{ device_id: 'd1', name: 'Kitchen Light' }];
      mockFetchJSON.mockResolvedValue({ devices, count: 1, limit: 100 });

      const result = await listDevices();

      expect(result.devices).toHaveLength(1);
      expect(result.devices[0].name).toBe('Kitchen Light');
    });
  });

  describe('getDevice', () => {
    it('fetches device by ID', async () => {
      mockFetchJSON.mockResolvedValue({ device_id: 'd1', name: 'Office Light' });

      const result = await getDevice('d1');

      expect(mockFetchJSON).toHaveBeenCalledWith('http://localhost:8006/api/devices/d1');
      expect(result.name).toBe('Office Light');
    });

    it('propagates errors', async () => {
      mockFetchJSON.mockRejectedValue(new Error('Not found'));

      await expect(getDevice('bad-id')).rejects.toThrow('Not found');
    });
  });

  describe('getDeviceCapabilities', () => {
    it('fetches capabilities for a device', async () => {
      mockFetchJSON.mockResolvedValue({
        device_id: 'd1',
        capabilities: [{ capability_name: 'brightness', capability_type: 'number', exposed: true, configured: true, source: 'ha', last_updated: '2026-01-01' }],
      });

      const result = await getDeviceCapabilities('d1');

      expect(mockFetchJSON).toHaveBeenCalledWith('http://localhost:8006/api/devices/d1/capabilities');
      expect(result.capabilities).toHaveLength(1);
    });
  });

  describe('listEntities', () => {
    it('fetches entities without params', async () => {
      mockFetchJSON.mockResolvedValue({ entities: [], count: 0, limit: 100 });

      await listEntities();

      expect(mockFetchJSON).toHaveBeenCalledWith('http://localhost:8006/api/entities');
    });

    it('appends filter params', async () => {
      mockFetchJSON.mockResolvedValue({ entities: [], count: 0, limit: 50 });

      await listEntities({ domain: 'light', device_id: 'd1', limit: 50 });

      const url = mockFetchJSON.mock.calls[0][0];
      expect(url).toContain('domain=light');
      expect(url).toContain('device_id=d1');
      expect(url).toContain('limit=50');
    });
  });

  describe('getEntity', () => {
    it('fetches entity by ID', async () => {
      mockFetchJSON.mockResolvedValue({ entity_id: 'light.office', domain: 'light' });

      const result = await getEntity('light.office');

      expect(mockFetchJSON).toHaveBeenCalledWith('http://localhost:8006/api/entities/light.office');
      expect(result.domain).toBe('light');
    });
  });
});

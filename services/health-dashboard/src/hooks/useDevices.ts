import { useState, useEffect, useCallback } from 'react';
import { dataApi } from '../services/api';  // Epic 13 Story 13.2: Use data-api for devices/entities

export interface Device {
  device_id: string;
  name: string;
  manufacturer: string;
  model: string;
  sw_version?: string;
  area_id?: string;
  integration?: string;  // HA integration/platform name
  entity_count: number;
  timestamp: string;
}

export interface Entity {
  entity_id: string;
  device_id?: string;
  domain: string;
  platform: string;
  unique_id?: string;
  area_id?: string;
  disabled: boolean;
  timestamp: string;
}

export interface Integration {
  entry_id: string;
  domain: string;
  title: string;
  state: string;
  version: number;
  timestamp: string;
}

export function useDevices() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDevices = useCallback(async (filters?: Record<string, string>) => {
    try {
      setLoading(true);
      setError(null);
      
      // Epic 13 Story 13.2: Use dataApi.getDevices()
      // Increased limit to ensure we fetch all devices (currently 99)
      const response = await dataApi.getDevices({
        limit: 1000,
        manufacturer: filters?.manufacturer,
        model: filters?.model,
        area_id: filters?.area_id
      });
      
      setDevices(response.devices || []);
    } catch (err: any) {
      console.error('Error fetching devices:', err);
      const errorMessage = err.message || 'Failed to fetch devices';
      setError(errorMessage);
      // Keep existing devices on error - don't clear them
      // This allows UI to show cached data even if refresh fails
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchEntities = useCallback(async (filters?: Record<string, string>) => {
    try {
      // Epic 13 Story 13.2: Use dataApi.getEntities()
      // Increased limit from 100 to 10000 to accommodate all entities
      // (99 devices × avg 10-15 entities = ~1000-1500 entities needed)
      const response = await dataApi.getEntities({
        limit: 10000,
        domain: filters?.domain,
        platform: filters?.platform,
        device_id: filters?.device_id
      });
      
      setEntities(response.entities || []);
    } catch (err: any) {
      console.error('Error fetching entities:', err);
      // Keep existing entities on error - don't clear them
      // This allows UI to show cached data even if refresh fails
      // Only set error if we don't already have one from devices fetch
      setError(prev => prev || err.message || 'Failed to fetch entities');
    }
  }, []);

  const fetchIntegrations = useCallback(async () => {
    try {
      // Epic 13 Story 13.2: Use dataApi.getIntegrations()
      const response = await dataApi.getIntegrations(100);
      setIntegrations(response.integrations || []);
    } catch (err: any) {
      console.error('Error fetching integrations:', err);
      setIntegrations([]);
    }
  }, []);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      await Promise.all([
        fetchDevices(),
        fetchEntities(),
        fetchIntegrations()
      ]);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  }, [fetchDevices, fetchEntities, fetchIntegrations]);

  // Initial fetch
  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  return {
    devices,
    entities,
    integrations,
    loading,
    error,
    fetchDevices,
    fetchEntities,
    fetchIntegrations,
    refresh: fetchAll
  };
}


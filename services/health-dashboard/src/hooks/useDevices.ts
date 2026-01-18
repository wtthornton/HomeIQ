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
  status?: string;  // Device status: 'active' or 'inactive'
  // Priority 1 & 2: Additional device attributes
  device_type?: string;  // Device classification: 'light', 'sensor', 'thermostat', etc.
  device_category?: string;  // Category: 'lighting', 'security', 'climate', etc.
  labels?: string[];  // Device labels for organization
  via_device?: string;  // Parent device ID
  configuration_url?: string;  // Device configuration URL
  // Additional device attributes from API
  config_entry_id?: string;  // Config entry ID (source tracking)
  serial_number?: string;  // Optional serial number
  model_id?: string;  // Optional model ID (manufacturer identifier)
  // Device intelligence fields (Phase 1.1)
  power_consumption_idle_w?: number;  // Standby power consumption (W)
  power_consumption_active_w?: number;  // Active power consumption (W)
  power_consumption_max_w?: number;  // Peak power consumption (W)
  setup_instructions_url?: string;  // Link to setup guide
  troubleshooting_notes?: string;  // Common issues and solutions
  device_features_json?: string;  // Structured capabilities (JSON string)
  community_rating?: number;  // Rating from Device Database
  last_capability_sync?: string;  // When capabilities were last updated
}

export interface Entity {
  entity_id: string;
  device_id?: string;
  domain: string;
  platform: string;
  unique_id?: string;
  area_id?: string;
  disabled: boolean;
  config_entry_id?: string;
  timestamp: string;
  // Entity Registry Name Fields (2025 HA API)
  friendly_name?: string;  // User-friendly entity name (computed: name_by_user > name > original_name)
  name?: string;  // Entity Registry name (source of truth)
  name_by_user?: string;  // User-customized name (highest priority)
  original_name?: string;  // Original name from integration
  // Entity Capabilities
  supported_features?: number;  // Bitmask of supported features
  capabilities?: string[];  // Parsed capabilities list: ['brightness', 'color', 'effect', etc.]
  available_services?: string[];  // List of available service calls: ['light.turn_on', 'light.turn_off', 'light.toggle']
  // Entity Attributes
  icon?: string;  // Current icon (may be user-customized)
  original_icon?: string;  // Original icon from integration/platform
  device_class?: string;  // Device class: 'temperature', 'motion', 'door', etc.
  unit_of_measurement?: string;  // Unit for sensors: '°C', '%', 'W', etc.
  // Entity Registry 2025 Attributes
  aliases?: string[];  // Array of alternative names for entity resolution
  labels?: string[];  // Entity labels for organization
  options?: Record<string, any>;  // Entity-specific options/config (e.g., default brightness)
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


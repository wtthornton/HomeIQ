/**
 * Device API Service
 *
 * Connects to data-api on port 8006 for device and entity data
 * Phase 1: Device-Based Automation Suggestions Feature
 */

import { fetchJSON, API_CONFIG } from '../lib/api-client';

const BASE_URL = API_CONFIG.DATA;

/**
 * Device response interface matching data-api DeviceResponse model
 */
export interface Device {
  device_id: string;
  name: string;
  manufacturer: string;
  model: string;
  integration?: string | null;
  sw_version?: string | null;
  area_id?: string | null;
  config_entry_id?: string | null;
  via_device?: string | null;
  device_type?: string | null;
  device_category?: string | null;
  power_consumption_idle_w?: number | null;
  power_consumption_active_w?: number | null;
  power_consumption_max_w?: number | null;
  setup_instructions_url?: string | null;
  troubleshooting_notes?: string | null;
  device_features_json?: string | null;
  community_rating?: number | null;
  last_capability_sync?: string | null;
  entity_count: number;
  timestamp: string;
  labels?: string[] | null;
  serial_number?: string | null;
  model_id?: string | null;
  status: 'active' | 'inactive';
}

/**
 * Entity response interface matching data-api EntityResponse model
 */
export interface Entity {
  entity_id: string;
  device_id?: string | null;
  domain: string;
  platform: string;
  unique_id?: string | null;
  area_id?: string | null;
  disabled: boolean;
  config_entry_id?: string | null;
  timestamp: string;
  name?: string | null;
  name_by_user?: string | null;
  original_name?: string | null;
  friendly_name?: string | null;
  supported_features?: number | null;
  capabilities?: string[] | null;
  available_services?: string[] | null;
  icon?: string | null;
  original_icon?: string | null;
  device_class?: string | null;
  unit_of_measurement?: string | null;
  aliases?: string[] | null;
  labels?: string[] | null;
  options?: Record<string, any> | null;
}

/**
 * Device capabilities response
 */
export interface DeviceCapability {
  capability_name: string;
  capability_type: string;
  properties?: Record<string, any> | null;
  exposed: boolean;
  configured: boolean;
  source: string;
  last_updated: string;
}

export interface DeviceCapabilitiesResponse {
  device_id: string;
  capabilities: DeviceCapability[];
  features?: Record<string, any> | null;
}

/**
 * Devices list response
 */
export interface DevicesListResponse {
  devices: Device[];
  count: number;
  limit: number;
}

/**
 * Entities list response
 */
export interface EntitiesListResponse {
  entities: Entity[];
  count: number;
  limit: number;
}

/** @deprecated Use APIError from lib/api-client instead */
export { APIError as DeviceAPIError } from '../lib/api-client';

/**
 * List devices with optional filters
 */
export async function listDevices(params?: {
  limit?: number;
  manufacturer?: string;
  model?: string;
  area_id?: string;
  platform?: string;
  device_type?: string;
  device_category?: string;
}): Promise<DevicesListResponse> {
  const queryParams = new URLSearchParams();
  if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
  if (params?.manufacturer) queryParams.append('manufacturer', params.manufacturer);
  if (params?.model) queryParams.append('model', params.model);
  if (params?.area_id) queryParams.append('area_id', params.area_id);
  if (params?.platform) queryParams.append('platform', params.platform);
  if (params?.device_type) queryParams.append('device_type', params.device_type);
  if (params?.device_category) queryParams.append('device_category', params.device_category);

  const url = `${BASE_URL}/devices${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
  return fetchJSON<DevicesListResponse>(url);
}

/**
 * Get device by ID
 */
export async function getDevice(device_id: string): Promise<Device> {
  const url = `${BASE_URL}/devices/${device_id}`;
  return fetchJSON<Device>(url);
}

/**
 * Get device capabilities
 */
export async function getDeviceCapabilities(device_id: string): Promise<DeviceCapabilitiesResponse> {
  const url = `${BASE_URL}/devices/${device_id}/capabilities`;
  return fetchJSON<DeviceCapabilitiesResponse>(url);
}

/**
 * List entities with optional filters
 */
export async function listEntities(params?: {
  limit?: number;
  domain?: string;
  platform?: string;
  device_id?: string;
  area_id?: string;
}): Promise<EntitiesListResponse> {
  const queryParams = new URLSearchParams();
  if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
  if (params?.domain) queryParams.append('domain', params.domain);
  if (params?.platform) queryParams.append('platform', params.platform);
  if (params?.device_id) queryParams.append('device_id', params.device_id);
  if (params?.area_id) queryParams.append('area_id', params.area_id);

  const url = `${BASE_URL}/entities${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
  return fetchJSON<EntitiesListResponse>(url);
}

/**
 * Get entity by ID
 */
export async function getEntity(entity_id: string): Promise<Entity> {
  const url = `${BASE_URL}/entities/${entity_id}`;
  return fetchJSON<Entity>(url);
}

/**
 * TypeScript types for house status data from websocket-ingestion.
 * Mirrors the Pydantic models in house_status/models.py.
 */

export interface ClimateStatus {
  entity_id: string;
  friendly_name: string;
  current_temperature: number | null;
  target_temperature: number | null;
  hvac_mode: string;
  unit: string;
}

export interface PresenceStatus {
  name: string;
  state: string; // "home" | "not_home" | "unknown"
}

export interface AreaLightStatus {
  area: string;
  on_count: number;
  off_count: number;
}

export interface SensorStatus {
  name: string;
  state: string; // human-readable: "open"/"closed", "detected"/"clear"
  device_class: string;
}

export interface HouseStatus {
  climate: ClimateStatus[];
  presence: PresenceStatus[];
  lights_by_area: AreaLightStatus[];
  sensors: Record<string, SensorStatus[]>;
  switches_on: string[];
  active_automations: string[];
  timestamp: string;
}

/** Delta update pushed over WebSocket. */
export interface HouseStatusDelta {
  type: 'delta';
  section: string;
  data: unknown;
}

/** Full snapshot sent on initial WebSocket connect. */
export interface HouseStatusSnapshot {
  type: 'snapshot';
  climate: ClimateStatus[];
  presence: PresenceStatus[];
  lights_by_area: AreaLightStatus[];
  sensors: Record<string, SensorStatus[]>;
  switches_on: string[];
  active_automations: string[];
  timestamp: string;
}

/** Keepalive ping from server. */
export interface HouseStatusPing {
  type: 'ping';
}

export type HouseStatusMessage =
  | HouseStatusDelta
  | HouseStatusSnapshot
  | HouseStatusPing;

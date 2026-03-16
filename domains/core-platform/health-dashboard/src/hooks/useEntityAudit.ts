import { useState, useEffect, useCallback, useRef } from 'react';
import { dataApi, adminApi } from '../services/api';

// --- Types ---

export interface EntityRecord {
  entity_id: string;
  device_id?: string;
  domain: string;
  platform: string;
  area_id?: string;
  disabled: boolean;
  friendly_name?: string;
  name?: string;
  name_by_user?: string;
  original_name?: string;
  device_class?: string;
  unit_of_measurement?: string;
  icon?: string;
  labels?: string[];
  aliases?: string[];
  capabilities?: string[];
  available_services?: string[];
  supported_features?: number;
}

export interface AreaInfo {
  area_id: string;
  display_name: string;
  entity_count: number;
  domains: string[];
}

export interface LabelInfo {
  label: string;
  entity_count: number;
  prefix: string;
}

export interface AuditScore {
  entity_id: string;
  total: number;
  hasArea: boolean;
  hasLabels: boolean;
  hasAiLabel: boolean;
  hasAliases: boolean;
  nameFollowsConvention: boolean;
  hasDeviceClass: boolean;
  issues: string[];
}

// Known manufacturer/model strings to detect in friendly names
const BRAND_PATTERNS = [
  /philips/i, /hue/i, /aqara/i, /ikea/i, /tradfri/i, /sonoff/i,
  /shelly/i, /zigbee/i, /z-wave/i, /zwave/i, /tuya/i, /xiaomi/i,
  /tp-link/i, /tapo/i, /meross/i, /wemo/i, /broadlink/i,
];

const AI_INTENT_LABELS = ['ai:automatable', 'ai:monitor-only', 'ai:ignore', 'ai:critical'];
const SENSOR_ROLE_LABELS = ['sensor:primary', 'sensor:trigger', 'sensor:condition', 'sensor:diagnostic'];

function isTitleCase(name: string): boolean {
  return name.split(/\s+/).every(w => w.length === 0 || w[0] === w[0].toUpperCase());
}

function hasBrandInName(name: string): boolean {
  return BRAND_PATTERNS.some(p => p.test(name));
}

export function scoreEntity(entity: EntityRecord, areaNames: string[]): AuditScore {
  const issues: string[] = [];
  let total = 0;

  // Has area? (+20)
  const hasArea = !!entity.area_id;
  if (hasArea) total += 20;
  else issues.push('No area assigned');

  // Has labels? (+20, +10 if AI intent)
  const labels = entity.labels || [];
  const hasLabels = labels.length > 0;
  const hasAiLabel = labels.some(l => AI_INTENT_LABELS.includes(l));
  if (hasLabels) {
    total += 20;
    if (hasAiLabel) total += 10;
  } else {
    issues.push('No labels');
  }

  // Has aliases? (+20)
  const aliases = entity.aliases || [];
  const hasAliases = aliases.length > 0;
  if (hasAliases) total += 20;
  else issues.push('No aliases');

  // Friendly name follows convention? (+20)
  const fname = entity.friendly_name || entity.name || entity.original_name || '';
  let nameFollowsConvention = true;
  if (fname) {
    let nameScore = 0;
    // Starts with area name (+8)
    const areaId = entity.area_id || '';
    const areaDisplay = areaId.replace(/_/g, ' ');
    const startsWithArea = areaNames.some(a =>
      fname.toLowerCase().startsWith(a.toLowerCase())
    ) || (areaDisplay && fname.toLowerCase().startsWith(areaDisplay.toLowerCase()));
    if (startsWithArea) nameScore += 8;
    else if (entity.area_id) issues.push('Name doesn\'t start with area');

    // Title Case (+4)
    if (isTitleCase(fname)) nameScore += 4;
    else issues.push('Name not Title Case');

    // No brand (+4)
    if (!hasBrandInName(fname)) nameScore += 4;
    else issues.push('Name contains brand/model');

    // No integration prefix (+4)
    const integrationPrefixes = ['zigbee', 'z-wave', 'mqtt', 'esphome', 'tasmota'];
    const hasIntegrationPrefix = integrationPrefixes.some(p =>
      fname.toLowerCase().startsWith(p)
    );
    if (!hasIntegrationPrefix) nameScore += 4;
    else issues.push('Name has integration prefix');

    total += nameScore;
    nameFollowsConvention = nameScore >= 16;
  } else {
    nameFollowsConvention = false;
    issues.push('No friendly name');
  }

  // Device class set? (+10 for sensors/binary_sensors)
  const needsDeviceClass = entity.domain === 'sensor' || entity.domain === 'binary_sensor';
  const hasDeviceClass = !!entity.device_class;
  if (needsDeviceClass) {
    if (hasDeviceClass) total += 10;
    else issues.push('No device_class set');
  }

  return {
    entity_id: entity.entity_id,
    total: Math.min(total, 100),
    hasArea,
    hasLabels,
    hasAiLabel,
    hasAliases,
    nameFollowsConvention,
    hasDeviceClass,
    issues,
  };
}

// --- Standard label taxonomy ---
export const LABEL_TAXONOMY: Record<string, string[]> = {
  'AI Intent': AI_INTENT_LABELS,
  'Sensor Role': SENSOR_ROLE_LABELS,
  'Grouping': ['group:all-lights', 'group:night-lights', 'group:media', 'group:security', 'group:climate'],
  'Energy': ['energy:producer', 'energy:consumer', 'energy:meter', 'energy:tariff'],
};

// --- Label suggestion rules ---
export function suggestLabels(entity: EntityRecord): string[] {
  const suggestions: string[] = [];
  const labels = entity.labels || [];

  if (entity.domain === 'light' || entity.domain === 'switch' || entity.domain === 'cover' || entity.domain === 'fan') {
    if (!labels.includes('ai:automatable')) suggestions.push('ai:automatable');
  }
  if (entity.domain === 'light' && !labels.includes('group:all-lights')) {
    suggestions.push('group:all-lights');
  }
  if (entity.domain === 'sensor' && !labels.includes('ai:monitor-only')) {
    suggestions.push('ai:monitor-only');
  }
  if (entity.device_class === 'motion' && !labels.includes('sensor:trigger')) {
    suggestions.push('sensor:trigger');
  }
  if (entity.device_class === 'temperature' && !labels.includes('sensor:primary')) {
    suggestions.push('sensor:primary');
  }
  if (entity.device_class === 'battery' && !labels.includes('sensor:diagnostic')) {
    suggestions.push('sensor:diagnostic');
  }
  if ((entity.domain === 'lock' || entity.domain === 'alarm_control_panel') && !labels.includes('ai:critical')) {
    suggestions.push('ai:critical');
  }
  if (entity.device_class === 'battery' && !labels.includes('ai:ignore')) {
    suggestions.push('ai:ignore');
  }
  if (['climate', 'humidifier', 'fan'].includes(entity.domain) && !labels.includes('group:climate')) {
    suggestions.push('group:climate');
  }
  if (entity.domain === 'media_player' && !labels.includes('group:media')) {
    suggestions.push('group:media');
  }

  return suggestions.filter(s => !labels.includes(s));
}

// --- Alias suggestion rules ---
export function suggestAliases(entity: EntityRecord): string[] {
  const fname = entity.friendly_name || entity.name || '';
  if (!fname) return [];

  const existing = (entity.aliases || []).map(a => a.toLowerCase());
  const suggestions: string[] = [];

  // Singular/plural of friendly name
  const lower = fname.toLowerCase();
  if (!existing.includes(lower)) suggestions.push(lower);
  if (!lower.endsWith('s') && !existing.includes(lower + 's')) {
    suggestions.push(lower + 's');
  }

  // Without area prefix
  if (entity.area_id) {
    const areaDisplay = entity.area_id.replace(/_/g, ' ');
    if (lower.startsWith(areaDisplay.toLowerCase() + ' ')) {
      const withoutArea = fname.substring(areaDisplay.length + 1);
      if (withoutArea && !existing.includes(withoutArea.toLowerCase())) {
        suggestions.push(withoutArea.toLowerCase());
      }
    }
  }

  // Common abbreviations
  const abbreviations: Record<string, string> = {
    'television': 'TV', 'air conditioner': 'AC', 'air conditioning': 'AC',
    'thermostat': 'heating',
  };
  for (const [full, abbr] of Object.entries(abbreviations)) {
    if (lower.includes(full) && !existing.includes(abbr.toLowerCase())) {
      suggestions.push(abbr.toLowerCase());
    }
  }

  return suggestions.filter(s => !existing.includes(s));
}

// --- Exclusion pattern matching ---
const DEFAULT_EXCLUSION_PATTERNS = [
  'sensor.*_battery',
  'sensor.*_signal_strength',
  'sensor.*_linkquality',
  'update.*',
  'button.*_identify',
  'number.*_calibration_*',
  'sensor.hacs*',
  'persistent_notification.*',
];

export function matchesGlobPattern(entityId: string, pattern: string): boolean {
  const regex = new RegExp(
    '^' + pattern.replace(/\./g, '\\.').replace(/\*/g, '.*') + '$'
  );
  return regex.test(entityId);
}

export function getDefaultExclusionPatterns(): string[] {
  return [...DEFAULT_EXCLUSION_PATTERNS];
}

// --- Hook ---

export type SubView = 'audit' | 'labels' | 'aliases' | 'exclusions';

export function useEntityAudit() {
  const [entities, setEntities] = useState<EntityRecord[]>([]);
  const [areas, setAreas] = useState<AreaInfo[]>([]);
  const [labelsList, setLabelsList] = useState<LabelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [subView, setSubView] = useState<SubView>('audit');
  const mounted = useRef(true);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [entitiesRes, areasRes, labelsRes] = await Promise.all([
        dataApi.getEntities({ limit: 10000 }),
        dataApi.getAreas(),
        dataApi.getLabels(),
      ]);
      if (!mounted.current) return;
      setEntities(entitiesRes.entities || []);
      setAreas(areasRes.areas || []);
      setLabelsList(labelsRes.labels || []);
    } catch (err) {
      if (!mounted.current) return;
      setError(err instanceof Error ? err.message : 'Failed to load entity data');
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    fetchData();
    return () => { mounted.current = false; };
  }, [fetchData]);

  const areaNames = areas.map(a => a.display_name);

  const scores = entities.map(e => scoreEntity(e, areaNames));

  const updateEntityLabels = useCallback(async (entityId: string, labels: string[]) => {
    await adminApi.setEntityLabels(entityId, labels);
    setEntities(prev => prev.map(e =>
      e.entity_id === entityId ? { ...e, labels } : e
    ));
  }, []);

  const updateEntityAliases = useCallback(async (entityId: string, aliases: string[]) => {
    await adminApi.setEntityAliases(entityId, aliases);
    setEntities(prev => prev.map(e =>
      e.entity_id === entityId ? { ...e, aliases } : e
    ));
  }, []);

  const updateEntityName = useCallback(async (entityId: string, nameByUser: string) => {
    await adminApi.setEntityName(entityId, nameByUser);
    setEntities(prev => prev.map(e =>
      e.entity_id === entityId ? { ...e, name_by_user: nameByUser, friendly_name: nameByUser } : e
    ));
  }, []);

  const bulkAddLabels = useCallback(async (entityIds: string[], addLabels: string[], removeLabels: string[] = []) => {
    await adminApi.bulkLabel(entityIds, addLabels, removeLabels);
    setEntities(prev => prev.map(e => {
      if (!entityIds.includes(e.entity_id)) return e;
      const current = new Set(e.labels || []);
      addLabels.forEach(l => current.add(l));
      removeLabels.forEach(l => current.delete(l));
      return { ...e, labels: Array.from(current) };
    }));
  }, []);

  return {
    entities, areas, labelsList, loading, error, scores,
    subView, setSubView,
    refresh: fetchData,
    updateEntityLabels, updateEntityAliases, updateEntityName, bulkAddLabels,
  };
}

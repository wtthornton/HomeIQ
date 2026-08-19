import { useState, useEffect, useCallback, useRef } from 'react';
import { dataApi, adminApi } from '../services/api';
import { scoreEntities, type ServerEntityScore } from '../services/namingApi';

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
  /** Points awarded by the backend rubric. Never computed here. */
  total: number;
  /** The rubric's maximum, so the UI never has to hardcode 100. */
  max: number;
  hasArea: boolean;
  hasLabels: boolean;
  hasAliases: boolean;
  nameFollowsConvention: boolean;
  hasDeviceClass: boolean;
  issues: string[];
}

const AI_INTENT_LABELS = ['ai:automatable', 'ai:monitor-only', 'ai:ignore', 'ai:critical'];
const SENSOR_ROLE_LABELS = ['sensor:primary', 'sensor:trigger', 'sensor:condition', 'sensor:diagnostic'];

/**
 * Rule names emitted by the backend rubric (convention_rules.ALL_RULES). The
 * dashboard reads these; it does not decide them.
 */
const RULE_AREA = 'area_id';
const RULE_LABELS = 'labels';
const RULE_ALIASES = 'aliases';
const RULE_FRIENDLY_NAME = 'friendly_name';
const RULE_DEVICE_CLASS = 'device_class';

/**
 * Translate one server score into the shape the audit components render.
 *
 * Every field here is derived from the server's verdict. The dashboard
 * deliberately owns no scoring logic of its own — it used to, and the two
 * rubrics silently disagreed on six separate axes (TAP-6230).
 */
export function toAuditScore(score: ServerEntityScore): AuditScore {
  const earned = new Map(score.rules.map(r => [r.rule, r]));
  const satisfied = (rule: string): boolean => (earned.get(rule)?.earned ?? 0) > 0;
  const friendlyName = earned.get(RULE_FRIENDLY_NAME);

  return {
    entity_id: score.entity_id,
    total: score.total_score,
    max: score.max_score,
    hasArea: satisfied(RULE_AREA),
    hasLabels: satisfied(RULE_LABELS),
    hasAliases: satisfied(RULE_ALIASES),
    hasDeviceClass: satisfied(RULE_DEVICE_CLASS),
    nameFollowsConvention: friendlyName ? friendlyName.earned === friendlyName.max : false,
    issues: score.issues,
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
  const [scores, setScores] = useState<AuditScore[]>([]);
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
      const loadedEntities = entitiesRes.entities || [];
      setEntities(loadedEntities);
      setAreas(areasRes.areas || []);
      setLabelsList(labelsRes.labels || []);

      // Scored by the backend rubric, for exactly the entities on screen.
      const serverScores = await scoreEntities(loadedEntities);
      if (!mounted.current) return;
      setScores(serverScores.map(toAuditScore));
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

  /**
   * Re-score entities the user just edited. The write has not necessarily
   * reached the service's registry yet, so the entity is sent along rather
   * than looked up — otherwise the row would show a stale score until sync.
   */
  const rescore = useCallback(async (updated: EntityRecord[]) => {
    const fresh = await scoreEntities(updated);
    if (!mounted.current) return;
    const byId = new Map(fresh.map(s => [s.entity_id, toAuditScore(s)]));
    setScores(prev => prev.map(score => byId.get(score.entity_id) ?? score));
  }, []);

  /** Apply a change to one entity locally, then re-score it on the backend. */
  const applyEntityPatch = useCallback(
    async (entityId: string, patch: Partial<EntityRecord>) => {
      let updated: EntityRecord | undefined;
      setEntities(prev =>
        prev.map(e => {
          if (e.entity_id !== entityId) return e;
          updated = { ...e, ...patch };
          return updated;
        })
      );
      if (updated) await rescore([updated]);
    },
    [rescore]
  );

  const updateEntityLabels = useCallback(async (entityId: string, labels: string[]) => {
    await adminApi.setEntityLabels(entityId, labels);
    await applyEntityPatch(entityId, { labels });
  }, [applyEntityPatch]);

  const updateEntityAliases = useCallback(async (entityId: string, aliases: string[]) => {
    await adminApi.setEntityAliases(entityId, aliases);
    await applyEntityPatch(entityId, { aliases });
  }, [applyEntityPatch]);

  const updateEntityName = useCallback(async (entityId: string, nameByUser: string) => {
    await adminApi.setEntityName(entityId, nameByUser);
    await applyEntityPatch(entityId, { name_by_user: nameByUser, friendly_name: nameByUser });
  }, [applyEntityPatch]);

  const bulkAddLabels = useCallback(async (entityIds: string[], addLabels: string[], removeLabels: string[] = []) => {
    await adminApi.bulkLabel(entityIds, addLabels, removeLabels);
    const touched: EntityRecord[] = [];
    setEntities(prev => prev.map(e => {
      if (!entityIds.includes(e.entity_id)) return e;
      const current = new Set(e.labels || []);
      addLabels.forEach(l => current.add(l));
      removeLabels.forEach(l => current.delete(l));
      const updated = { ...e, labels: Array.from(current) };
      touched.push(updated);
      return updated;
    }));
    await rescore(touched);
  }, [rescore]);

  return {
    entities, areas, labelsList, loading, error, scores,
    subView, setSubView,
    refresh: fetchData,
    updateEntityLabels, updateEntityAliases, updateEntityName, bulkAddLabels,
  };
}

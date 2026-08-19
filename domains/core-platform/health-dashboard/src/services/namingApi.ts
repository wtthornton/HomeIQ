/**
 * Naming convention API (TAP-6230).
 *
 * The device-intelligence service owns the only naming/area scoring rubric in
 * HomeIQ. The dashboard used to carry a second copy in TypeScript, and the two
 * had drifted far enough that the Overview and HA Setup tabs showed different
 * numbers for the same entity. Scoring now happens in exactly one place and the
 * dashboard renders what it is told.
 *
 * Reached through the nginx prefix in nginx.conf, which proxies
 * /device-intelligence/ to the service on port 8019.
 */

const NAMING_BASE = '/device-intelligence/api/naming';

/** Per-rule breakdown, as emitted by score_engine.EntityScore.to_dict. */
export interface ServerRuleScore {
  rule: string;
  earned: number;
  max: number;
  issues: string[];
  suggestions: string[];
}

export interface ServerEntityScore {
  entity_id: string;
  total_score: number;
  max_score: number;
  pct: number;
  rules: ServerRuleScore[];
  issues: string[];
  suggestions: string[];
}

export interface NamingAuditResponse {
  total_entities: number;
  average_score: number;
  compliance_pct: number;
  top_issues: Array<{ issue: string; count: number }>;
  score_distribution: Record<string, number>;
  entities: ServerEntityScore[];
}

/** The entity fields the rubric reads. Anything else is ignored by the server. */
export interface ScorableEntity {
  entity_id: string;
  domain?: string;
  area_id?: string;
  friendly_name?: string;
  device_class?: string;
  aliases?: string[];
  labels?: string[];
}

/** The server caps a scoring batch at 500 entities (ScoreBatchRequest). */
const MAX_SCORE_BATCH = 500;

async function getJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    throw new Error(`${url} responded ${response.status}`);
  }
  return response.json() as Promise<T>;
}

/** Full audit, scored from the service's own registry snapshot. */
export async function fetchNamingAudit(limit = 2000): Promise<NamingAuditResponse> {
  return getJson<NamingAuditResponse>(`${NAMING_BASE}/audit?limit=${limit}`);
}

/**
 * Score entities exactly as supplied, without the server consulting its
 * registry. This is what makes an edit rescore immediately: the dashboard's
 * copy of an entity is newer than the synced one right after a write.
 */
export async function scoreEntities(
  entities: ScorableEntity[]
): Promise<ServerEntityScore[]> {
  if (entities.length === 0) return [];

  const batches: ScorableEntity[][] = [];
  for (let i = 0; i < entities.length; i += MAX_SCORE_BATCH) {
    batches.push(entities.slice(i, i + MAX_SCORE_BATCH));
  }

  const results = await Promise.all(
    batches.map(batch =>
      getJson<{ entities: ServerEntityScore[] }>(`${NAMING_BASE}/score`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entities: batch.map(toScorable) }),
      })
    )
  );
  return results.flatMap(r => r.entities);
}

/** Narrow an entity to the rubric's inputs, defaulting like the server does. */
function toScorable(entity: ScorableEntity): Required<ScorableEntity> {
  return {
    entity_id: entity.entity_id,
    domain: entity.domain ?? '',
    area_id: entity.area_id ?? '',
    friendly_name: entity.friendly_name ?? '',
    device_class: entity.device_class ?? '',
    aliases: entity.aliases ?? [],
    labels: entity.labels ?? [],
  };
}

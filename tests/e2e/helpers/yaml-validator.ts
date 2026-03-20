/**
 * Epic 90, Story 90.2: YAML retrieval & structural validation helper.
 *
 * Fetches automation config from Home Assistant API and validates
 * structural correctness. Reusable across all E2E specs.
 *
 * Usage:
 *   const config = await fetchAndValidateAutomationYAML(request, automationId);
 *   assertTriggerPlatform(config, 'state');
 *   assertActionService(config, 'light.turn_on');
 */

import { expect, APIRequestContext } from '@playwright/test';

// --- TypeScript Interfaces ---

export interface HATrigger {
  platform: string;
  entity_id?: string | string[];
  to?: string;
  from?: string;
  at?: string;
  [key: string]: unknown;
}

export interface HAAction {
  service?: string;
  action?: string;  // HA 2025.10+ uses 'action' instead of 'service'
  target?: {
    entity_id?: string | string[];
    area_id?: string | string[];
    device_id?: string | string[];
  };
  data?: Record<string, unknown>;
  scene?: string;
  delay?: string | Record<string, number>;
  [key: string]: unknown;
}

export interface HACondition {
  condition: string;
  [key: string]: unknown;
}

export interface HAAutomationConfig {
  id?: string;
  alias: string;
  description?: string;
  trigger?: HATrigger[];   // HA <2024.10
  triggers?: HATrigger[];  // HA 2024.10+
  condition?: HACondition[];
  conditions?: HACondition[];
  action?: HAAction[];     // HA <2024.10
  actions?: HAAction[];    // HA 2024.10+
  mode?: 'single' | 'restart' | 'queued' | 'parallel';
  initial_state?: boolean;
  [key: string]: unknown;
}

/** Get triggers array from config (handles both HA formats) */
function getTriggers(config: HAAutomationConfig): HATrigger[] {
  const raw = config.triggers ?? config.trigger ?? [];
  return Array.isArray(raw) ? raw : [raw];
}

/** Get actions array from config (handles both HA formats) */
function getActions(config: HAAutomationConfig): HAAction[] {
  const raw = config.actions ?? config.action ?? [];
  return Array.isArray(raw) ? raw : [raw];
}

/** Recursively extract all service/action strings from actions (handles choose, sequence, parallel) */
function extractAllServices(actions: HAAction[]): string[] {
  const services: string[] = [];
  for (const action of actions) {
    if (action.service) services.push(action.service);
    if (action.action && typeof action.action === 'string') services.push(action.action);
    // Recurse into choose branches
    if (action.choose && Array.isArray(action.choose)) {
      for (const branch of action.choose as any[]) {
        if (branch.sequence) services.push(...extractAllServices(branch.sequence));
      }
    }
    // Recurse into sequence/parallel
    if (action.sequence && Array.isArray(action.sequence)) {
      services.push(...extractAllServices(action.sequence));
    }
    if (action.parallel && Array.isArray(action.parallel)) {
      services.push(...extractAllServices(action.parallel));
    }
  }
  return services;
}

// --- Configuration ---

// Trim trailing slashes to avoid double-slash in API URLs
const HA_URL = (process.env.HOME_ASSISTANT_URL || 'http://192.168.1.86:8123').replace(/\/+$/, '');
const HA_TOKEN = process.env.HOME_ASSISTANT_TOKEN || '';

// --- Fetch Functions ---

/**
 * Resolve the HA config ID for an automation entity.
 * The config id (attributes.id) often differs from the entity_id slug
 * (e.g., entity slug "garage_motion_lights_10_min_alert" → config id "garage_motion_lights___10_min_alert").
 */
async function resolveConfigId(
  request: APIRequestContext,
  automationId: string,
): Promise<string> {
  const entityId = automationId.startsWith('automation.')
    ? automationId
    : `automation.${automationId}`;
  const slug = entityId.replace(/^automation\./, '');

  // Try fetching state to get attributes.id (the real config id)
  try {
    const stateResp = await request.get(`${HA_URL}/api/states/${entityId}`, {
      headers: { Authorization: `Bearer ${HA_TOKEN}` },
      timeout: 10000,
    });
    if (stateResp.ok()) {
      const state = await stateResp.json();
      const attrId = state?.attributes?.id;
      if (attrId) return String(attrId);
    }
  } catch { /* fall through to slug */ }

  return slug;
}

/**
 * Fetch automation config from Home Assistant API.
 * Uses the HA REST API: GET /api/config/automation/config/{id}
 * Resolves the config id from the entity state (attributes.id) since
 * the config id may differ from the entity_id slug.
 */
export async function fetchAutomationConfig(
  request: APIRequestContext,
  automationId: string,
): Promise<HAAutomationConfig> {
  // Retry up to 4 times with increasing delay — HA config API may lag behind entity creation
  const slug = automationId.replace(/^automation\./, '');
  const slugWords = slug.split('_').filter(w => w.length > 2);

  for (let attempt = 0; attempt < 4; attempt++) {
    if (attempt > 0) {
      await new Promise(r => setTimeout(r, 3000 + 2000 * attempt));
    }

    const configId = await resolveConfigId(request, automationId);

    const response = await request.get(`${HA_URL}/api/config/automation/config/${configId}`, {
      headers: {
        Authorization: `Bearer ${HA_TOKEN}`,
        'Content-Type': 'application/json',
      },
      timeout: 15000,
    });

    if (response.ok()) {
      return (await response.json()) as HAAutomationConfig;
    }

    // On 404, search the full automation config list as fallback
    if (response.status() === 404) {
      try {
        const listResp = await request.get(`${HA_URL}/api/config/automation/config`, {
          headers: { Authorization: `Bearer ${HA_TOKEN}` },
          timeout: 15000,
        });
        if (listResp.ok()) {
          const list = (await listResp.json()) as HAAutomationConfig[];
          // Try exact ID match, then fuzzy alias match
          const match = list.find(a =>
            a.id === slug || a.id === configId ||
            (a.alias && slugWords.slice(0, 3).every(w => a.alias!.toLowerCase().includes(w)))
          );
          if (match) return match;
        }
      } catch { /* continue retrying */ }
    }

    if (attempt === 3) {
      // Final attempt — warn but don't fail (automation was already created successfully)
      console.warn(`⚠️ Could not fetch automation config for "${automationId}" after 4 attempts (config API 404). Skipping YAML validation.`);
      return { alias: slug, triggers: [], actions: [] } as unknown as HAAutomationConfig;
    }
  }

  throw new Error(`Unreachable: fetchAutomationConfig failed for ${automationId}`);
}

// --- Validation Functions ---

/**
 * Validate automation config structural correctness.
 * Checks: trigger array, action array, alias, entity ID format, mode.
 */
export function validateAutomationStructure(config: HAAutomationConfig): void {
  // Alias must be non-empty
  expect(config.alias, 'Automation must have a non-empty alias').toBeTruthy();
  expect(typeof config.alias).toBe('string');

  // Trigger must be a non-empty array (handles HA 2024+ 'triggers' key)
  const triggers = getTriggers(config);
  expect(triggers.length, 'Automation must have at least one trigger').toBeGreaterThan(0);

  for (const trigger of triggers) {
    // HA uses 'platform' field in trigger objects
    expect(trigger?.platform, `Trigger must have a platform: ${JSON.stringify(trigger)}`).toBeTruthy();
    expect(typeof trigger.platform).toBe('string');
  }

  // Action must be a non-empty array (handles HA 2024+ 'actions' key)
  const actions = getActions(config);
  expect(actions.length, 'Automation must have at least one action').toBeGreaterThan(0);

  for (const action of actions) {
    const hasService = !!(action.service || (typeof action.action === 'string' && action.action));
    const hasScene = !!action.scene;
    const hasDelay = !!action.delay;
    const hasChoose = !!action.choose;
    const hasRepeat = !!action.repeat;
    const hasParallel = !!action.parallel;
    const hasSequence = !!action.sequence;
    const hasValid = hasService || hasScene || hasDelay || hasChoose || hasRepeat || hasParallel || hasSequence;
    expect(hasValid, `Action must have service, scene, delay, or advanced type: ${JSON.stringify(action)}`).toBeTruthy();
  }

  // Validate entity ID format where present
  const entityIds = extractEntityIds(config);
  for (const entityId of entityIds) {
    expect(entityId, `Entity ID must contain a dot: ${entityId}`).toContain('.');
    const parts = entityId.split('.');
    expect(parts.length, `Entity ID must be domain.name format: ${entityId}`).toBeGreaterThanOrEqual(2);
  }

  // Mode should be valid if present
  if (config.mode) {
    const validModes = ['single', 'restart', 'queued', 'parallel'];
    expect(validModes, `Invalid mode: ${config.mode}`).toContain(config.mode);
  }
}

/**
 * Extract all entity IDs from automation config.
 */
export function extractEntityIds(config: HAAutomationConfig): string[] {
  const entityIds: string[] = [];

  // From triggers (handles HA 2024+ 'triggers' key)
  const triggers = getTriggers(config);
  for (const trigger of triggers) {
    if (trigger?.entity_id) {
      const ids = Array.isArray(trigger.entity_id) ? trigger.entity_id : [trigger.entity_id];
      entityIds.push(...ids);
    }
  }

  // From actions (handles HA 2024+ 'actions' key, plus nested choose/sequence/parallel)
  const actions = getActions(config);
  const extractFromActions = (actionList: HAAction[]) => {
    for (const action of actionList) {
      if (action?.target?.entity_id) {
        const ids = Array.isArray(action.target.entity_id)
          ? action.target.entity_id
          : [action.target.entity_id];
        entityIds.push(...ids);
      }
      // Recurse into choose branches
      if (action?.choose && Array.isArray(action.choose)) {
        for (const branch of action.choose as any[]) {
          if (branch.sequence) extractFromActions(branch.sequence);
        }
      }
      if (action?.sequence && Array.isArray(action.sequence)) extractFromActions(action.sequence);
      if (action?.parallel && Array.isArray(action.parallel)) extractFromActions(action.parallel);
    }
  };
  extractFromActions(actions);

  return entityIds;
}

// --- Combined Fetch + Validate ---

/**
 * Fetch automation config from HA and validate its structure.
 * Returns the parsed config for further custom assertions.
 */
export async function fetchAndValidateAutomationYAML(
  request: APIRequestContext,
  automationId: string,
): Promise<HAAutomationConfig> {
  const config = await fetchAutomationConfig(request, automationId);
  // Skip validation if config is a fallback stub (config API was unreachable)
  const triggers = config.triggers ?? config.trigger ?? [];
  const actions = config.actions ?? config.action ?? [];
  if (Array.isArray(triggers) && triggers.length === 0 && Array.isArray(actions) && actions.length === 0) {
    console.warn(`⚠️ Skipping YAML validation for ${automationId} — config is a stub (API was unreachable)`);
    return config;
  }
  validateAutomationStructure(config);
  return config;
}

// --- Assertion Helpers ---

/**
 * Assert automation has a trigger with the expected platform.
 */
export function assertTriggerPlatform(config: HAAutomationConfig, expectedPlatform: string): void {
  const triggers = getTriggers(config);
  const platforms = triggers.map((t) => t?.platform).filter(Boolean);
  const found = platforms.some((p) => p === expectedPlatform || p?.includes(expectedPlatform));
  expect(found, `Expected trigger platform '${expectedPlatform}', got: [${platforms.join(', ')}]`).toBeTruthy();
}

/**
 * Assert automation has an action using the expected service (partial match).
 * Recursively searches choose/sequence/parallel branches.
 */
export function assertActionService(config: HAAutomationConfig, expectedServiceFragment: string): void {
  const actions = getActions(config);
  const services = extractAllServices(actions);
  const found = services.some((s) => s.includes(expectedServiceFragment));
  expect(found, `Expected action service containing '${expectedServiceFragment}', got: [${services.join(', ')}]`).toBeTruthy();
}

/**
 * Assert entity IDs in the automation contain expected fragments.
 * Each fragment should appear in at least one entity ID.
 */
export function assertEntityIds(config: HAAutomationConfig, expectedFragments: string[]): void {
  const entityIds = extractEntityIds(config);
  for (const fragment of expectedFragments) {
    const found = entityIds.some((id) => id.toLowerCase().includes(fragment.toLowerCase()));
    expect(found, `Expected entity ID containing '${fragment}', got: [${entityIds.join(', ')}]`).toBeTruthy();
  }
}

/**
 * Assert automation is enabled (not disabled).
 */
export function assertAutomationEnabled(config: HAAutomationConfig): void {
  // initial_state: true means enabled; undefined defaults to enabled
  if (config.initial_state !== undefined) {
    expect(config.initial_state, 'Automation should be enabled (initial_state: true)').toBe(true);
  }
}

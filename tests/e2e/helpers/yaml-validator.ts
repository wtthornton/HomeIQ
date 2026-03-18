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
  trigger: HATrigger[];
  condition?: HACondition[];
  action: HAAction[];
  mode?: 'single' | 'restart' | 'queued' | 'parallel';
  initial_state?: boolean;
  [key: string]: unknown;
}

// --- Configuration ---

const HA_URL = process.env.HOME_ASSISTANT_URL || 'http://192.168.1.86:8123';
const HA_TOKEN = process.env.HOME_ASSISTANT_TOKEN || '';

// --- Fetch Functions ---

/**
 * Fetch automation config from Home Assistant API.
 * Uses the HA REST API: GET /api/config/automation/config/{id}
 */
export async function fetchAutomationConfig(
  request: APIRequestContext,
  automationId: string,
): Promise<HAAutomationConfig> {
  // Strip "automation." prefix if present (HA API expects just the numeric ID)
  const configId = automationId.replace(/^automation\./, '');

  const response = await request.get(`${HA_URL}/api/config/automation/config/${configId}`, {
    headers: {
      Authorization: `Bearer ${HA_TOKEN}`,
      'Content-Type': 'application/json',
    },
    timeout: 15000,
  });

  expect(response.ok(), `Failed to fetch automation ${configId}: ${response.status()}`).toBeTruthy();
  const config = (await response.json()) as HAAutomationConfig;
  return config;
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

  // Trigger must be a non-empty array
  const triggers = Array.isArray(config.trigger) ? config.trigger : [config.trigger];
  expect(triggers.length, 'Automation must have at least one trigger').toBeGreaterThan(0);

  for (const trigger of triggers) {
    expect(trigger.platform, `Trigger must have a platform: ${JSON.stringify(trigger)}`).toBeTruthy();
    expect(typeof trigger.platform).toBe('string');
  }

  // Action must be a non-empty array
  const actions = Array.isArray(config.action) ? config.action : [config.action];
  expect(actions.length, 'Automation must have at least one action').toBeGreaterThan(0);

  for (const action of actions) {
    const hasService = !!(action.service || action.action);
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

  // From triggers
  const triggers = Array.isArray(config.trigger) ? config.trigger : [config.trigger];
  for (const trigger of triggers) {
    if (trigger.entity_id) {
      const ids = Array.isArray(trigger.entity_id) ? trigger.entity_id : [trigger.entity_id];
      entityIds.push(...ids);
    }
  }

  // From actions
  const actions = Array.isArray(config.action) ? config.action : [config.action];
  for (const action of actions) {
    if (action.target?.entity_id) {
      const ids = Array.isArray(action.target.entity_id)
        ? action.target.entity_id
        : [action.target.entity_id];
      entityIds.push(...ids);
    }
  }

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
  validateAutomationStructure(config);
  return config;
}

// --- Assertion Helpers ---

/**
 * Assert automation has a trigger with the expected platform.
 */
export function assertTriggerPlatform(config: HAAutomationConfig, expectedPlatform: string): void {
  const triggers = Array.isArray(config.trigger) ? config.trigger : [config.trigger];
  const platforms = triggers.map((t) => t.platform);
  const found = platforms.some((p) => p === expectedPlatform || p?.includes(expectedPlatform));
  expect(found, `Expected trigger platform '${expectedPlatform}', got: [${platforms.join(', ')}]`).toBeTruthy();
}

/**
 * Assert automation has an action using the expected service (partial match).
 */
export function assertActionService(config: HAAutomationConfig, expectedServiceFragment: string): void {
  const actions = Array.isArray(config.action) ? config.action : [config.action];
  const services = actions.map((a) => a.service || a.action || '').filter(Boolean);
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

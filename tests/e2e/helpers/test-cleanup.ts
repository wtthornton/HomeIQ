/**
 * Epic 90, Story 90.5: Test isolation & cleanup harness.
 *
 * Provides automation tracking and cleanup for E2E tests.
 * - Tracks automation IDs created during tests
 * - Deletes tracked automations via HA API in afterEach
 * - Health-gate: skips suite if services are unreachable
 *
 * Usage:
 *   import { AutomationTracker, healthGate } from './helpers/test-cleanup';
 *
 *   test.beforeAll(async ({ request }) => {
 *     await healthGate(request);
 *   });
 *
 *   test.beforeEach(async () => {
 *     tracker = new AutomationTracker();
 *   });
 *
 *   test.afterEach(async ({ request }) => {
 *     await tracker.cleanup(request);
 *   });
 */

import { expect, APIRequestContext } from '@playwright/test';

// --- Configuration ---

const HA_URL = (process.env.HOME_ASSISTANT_URL || 'http://192.168.1.86:8123').replace(/\/+$/, '');
const HA_TOKEN = process.env.HOME_ASSISTANT_TOKEN || '';
const HA_AGENT_URL = process.env.HA_AGENT_URL || 'http://localhost:8030';
const DEPLOY_URL = process.env.DEPLOY_SERVICE_URL || 'http://localhost:8018';

// --- Automation Tracker ---

/**
 * Tracks automation IDs created during a test and deletes them in cleanup.
 * Each test should create a new AutomationTracker instance.
 */
export class AutomationTracker {
  private createdIds: Set<string> = new Set();

  /**
   * Register an automation ID for cleanup.
   * Call this whenever a test creates an automation.
   */
  track(automationId: string): void {
    if (automationId) {
      this.createdIds.add(automationId);
    }
  }

  /**
   * Get all tracked automation IDs.
   */
  getTrackedIds(): string[] {
    return [...this.createdIds];
  }

  /**
   * Delete all tracked automations via HA API.
   * Silently ignores errors for already-deleted automations (idempotent).
   */
  async cleanup(request: APIRequestContext): Promise<void> {
    if (this.createdIds.size === 0) return;

    const errors: string[] = [];

    for (const automationId of this.createdIds) {
      try {
        await deleteAutomation(request, automationId);
      } catch (err) {
        // Log but don't fail — automation may already be deleted
        errors.push(`Failed to delete ${automationId}: ${err}`);
      }
    }

    // Clear tracked IDs regardless of errors
    this.createdIds.clear();

    if (errors.length > 0) {
      console.warn(`[AutomationTracker] Cleanup warnings:\n${errors.join('\n')}`);
    }
  }
}

// --- HA API Operations ---

/**
 * Delete an automation from Home Assistant.
 * Uses DELETE /api/config/automation/config/{id}
 * Idempotent: does not throw if automation doesn't exist (404).
 */
async function deleteAutomation(
  request: APIRequestContext,
  automationId: string,
): Promise<boolean> {
  // Strip "automation." prefix if present
  const configId = automationId.replace(/^automation\./, '');

  const response = await request.delete(
    `${HA_URL}/api/config/automation/config/${configId}`,
    {
      headers: {
        Authorization: `Bearer ${HA_TOKEN}`,
        'Content-Type': 'application/json',
      },
      timeout: 10000,
    },
  );

  // 200 = deleted, 404 = already gone (both are fine)
  if (response.status() === 200 || response.status() === 404) {
    return true;
  }

  console.warn(
    `[test-cleanup] Unexpected status ${response.status()} deleting automation ${configId}`,
  );
  return false;
}

// --- Health Gate ---

/**
 * Health gate: checks that required services are reachable.
 * Call in beforeAll — skips entire suite with clear message if services are down.
 *
 * Checks:
 * 1. ha-ai-agent-service health endpoint
 * 2. Home Assistant API reachability
 */
export async function healthGate(request: APIRequestContext): Promise<void> {
  // Check ha-ai-agent-service
  try {
    const agentResponse = await request.get(`${HA_AGENT_URL}/health`, {
      timeout: 10000,
    });
    if (!agentResponse.ok()) {
      throw new Error(
        `ha-ai-agent-service unhealthy: ${agentResponse.status()}`,
      );
    }
  } catch (err) {
    const msg = `[HEALTH GATE] ha-ai-agent-service unreachable at ${HA_AGENT_URL}/health — skipping Ask AI test suite. Error: ${err}`;
    console.error(msg);
    // Use test.skip pattern — throw with skip marker
    throw new Error(msg);
  }

  // Check Home Assistant API
  try {
    const haResponse = await request.get(`${HA_URL}/api/`, {
      headers: {
        Authorization: `Bearer ${HA_TOKEN}`,
      },
      timeout: 10000,
    });
    if (!haResponse.ok()) {
      throw new Error(`Home Assistant API returned ${haResponse.status()}`);
    }
  } catch (err) {
    const msg = `[HEALTH GATE] Home Assistant unreachable at ${HA_URL}/api/ — skipping Ask AI test suite. Error: ${err}`;
    console.error(msg);
    throw new Error(msg);
  }
}

/**
 * Snapshot current automation IDs from the deploy service.
 * Useful for before/after comparison.
 */
export async function snapshotAutomationIds(
  request: APIRequestContext,
): Promise<Set<string>> {
  try {
    const response = await request.get(
      `${DEPLOY_URL}/api/deploy/automations`,
      { timeout: 15000 },
    );

    if (!response.ok()) {
      return new Set();
    }

    const data = await response.json();
    const automations = data.automations || data || [];
    const ids = new Set<string>();

    for (const auto of automations) {
      const id = auto.automation_id || auto.entity_id || auto.id;
      if (id) ids.add(id);
    }

    return ids;
  } catch {
    return new Set();
  }
}

/**
 * Verify that no test automations leaked by comparing before/after snapshots.
 * Call in afterAll to ensure test isolation.
 */
export async function verifyNoLeakedAutomations(
  request: APIRequestContext,
  beforeIds: Set<string>,
): Promise<void> {
  const afterIds = await snapshotAutomationIds(request);
  const leaked = [...afterIds].filter((id) => !beforeIds.has(id));

  if (leaked.length > 0) {
    console.warn(
      `[test-cleanup] ${leaked.length} automation(s) leaked after test suite: ${leaked.join(', ')}`,
    );
    // Attempt cleanup of leaked automations
    for (const id of leaked) {
      try {
        await deleteAutomation(request, id);
      } catch {
        // Best effort
      }
    }
  }
}

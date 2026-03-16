/**
 * Ask AI → HA Automation Creation — Full E2E Verification
 *
 * Verifies the complete pipeline from natural language query to a real
 * automation existing in Home Assistant:
 *
 *   1. User submits an automation request (NOT a command) on the Ask AI page
 *   2. OpenAI generates automation suggestions
 *   3. User clicks Test (or Approve) on a suggestion
 *   4. Backend creates the automation in HA
 *   5. Test verifies via deploy API that the automation exists
 *   6. Test navigates to /automations and confirms it appears in the UI
 *
 * Prompts are based on REAL devices in the HA instance:
 *   - Presence: Office FP300, Bar PF300, outdoor Hue motion sensors
 *   - Lights: office, bar, kitchen strip, living room, patio, porch, garage, WLED
 *   - Switches: nightlights, office fan, Roborock DND, front door chime
 *   - Media: Frame TV, Denon AVR, Office Samsung TV, Family Room TV
 *   - Sensors: garage door, outdoor motion, sun state
 *   - Person: Bill Thornton (home/away tracking)
 *
 * Prerequisites: Docker stack running (ai-automation-ui :3001,
 *   ha-ai-agent-service :8018, ai-automation-service-new :8036, HA instance).
 *   Requires OPENAI_API_KEY in the backend environment.
 */

import { test, expect } from '@playwright/test';
import { AskAIPage } from './page-objects/AskAIPage';
import { DeployedPage } from './page-objects/DeployedPage';

// Backend deploy service (proxied through ha-ai-agent-service)
const DEPLOY_API = 'http://localhost:8018/api/deploy/automations';

/**
 * Helper: snapshot current automation IDs from the deploy API
 */
async function snapshotAutomationIds(request: any): Promise<Set<string>> {
  const response = await request.get(DEPLOY_API);
  expect(response.ok(), 'Deploy API should be reachable').toBeTruthy();
  const data = await response.json();
  return new Set(
    (data.automations ?? []).map((a: any) => a.entity_id ?? a.automation_id ?? a.id)
  );
}

/**
 * Helper: verify automation exists in deploy API after creation
 */
async function verifyAutomationInAPI(
  request: any,
  automationId: string,
  beforeIds: Set<string>,
  page: any
): Promise<void> {
  // Give HA a moment to register the new automation
  await page.waitForTimeout(2000);

  const afterResponse = await request.get(DEPLOY_API);
  expect(afterResponse.ok()).toBeTruthy();
  const afterData = await afterResponse.json();
  const afterIds = new Set(
    (afterData.automations ?? []).map((a: any) => a.entity_id ?? a.automation_id ?? a.id)
  );

  const newIds = [...afterIds].filter((id) => !beforeIds.has(id));
  console.log(`New automations since test started: ${JSON.stringify(newIds)}`);
  expect(
    afterIds.has(automationId) ||
      newIds.some(
        (id: string) => automationId.includes(id) || id.includes(automationId)
      ),
    `Automation ${automationId} should appear in GET /api/deploy/automations`
  ).toBeTruthy();
}

/**
 * Helper: verify automation is visible on the /automations UI page
 */
async function verifyAutomationInUI(
  page: any,
  automationId: string
): Promise<void> {
  const deployed = new DeployedPage(page);
  await deployed.goto();

  const automationLocator = page.locator(
    `[data-testid="deployed-automation"]:has-text("${automationId}"), ` +
      `[data-testid="deployed-automation-${automationId}"], ` +
      `text=${automationId}`
  );
  const visibleOnPage = await automationLocator
    .first()
    .isVisible({ timeout: 10_000 })
    .catch(() => false);
  expect(
    visibleOnPage,
    `Automation ${automationId} should be visible on /automations page`
  ).toBeTruthy();
}

// ─────────────────────────────────────────────────────────────────────────────
// Presence-triggered automations (using real FP300/PF300 occupancy sensors)
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Ask AI → HA Automation (Presence-Based)', () => {
  test.setTimeout(120_000);

  test('Office presence → lights + fan automation', async ({ page, request }) => {
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    await askAI.submitQuery(
      'When the Office FP300 presence sensor detects someone in the office, turn on the office lights and the office fan. When the office is unoccupied for 10 minutes, turn them off.'
    );
    await askAI.waitForResponse(60_000);
    await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45_000);

    const suggestionCount = await askAI.getSuggestionCount();
    expect(suggestionCount).toBeGreaterThan(0);

    const testResponsePromise = page.waitForResponse(
      (resp) =>
        resp.url().includes('/api/v1/ask-ai/query/') &&
        resp.url().includes('/test') &&
        resp.request().method() === 'POST',
      { timeout: 90_000 }
    );

    await askAI.testSuggestion(0);

    const testResponse = await testResponsePromise;
    expect(testResponse.ok(), 'Test endpoint should return 200').toBeTruthy();

    const testResult = await testResponse.json();
    const automationId: string =
      testResult.automation_id ?? testResult.automationId ?? '';
    expect(automationId).toBeTruthy();
    expect(automationId).toContain('automation.');
    console.log(`✅ Presence automation created: ${automationId}`);

    await verifyAutomationInAPI(request, automationId, beforeIds, page);
    await verifyAutomationInUI(page, automationId);
  });

  test('Bar presence → bar lights automation', async ({ page, request }) => {
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    await askAI.submitQuery(
      'Create an automation that turns on the bar lights when the Bar PF300 sensor detects occupancy, and turns them off after 5 minutes of no presence.'
    );
    await askAI.waitForResponse(60_000);
    await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45_000);

    expect(await askAI.getSuggestionCount()).toBeGreaterThan(0);

    const testResponsePromise = page.waitForResponse(
      (resp) =>
        resp.url().includes('/api/v1/ask-ai/query/') &&
        resp.url().includes('/test') &&
        resp.request().method() === 'POST',
      { timeout: 90_000 }
    );

    await askAI.testSuggestion(0);

    const testResponse = await testResponsePromise;
    expect(testResponse.ok()).toBeTruthy();

    const testResult = await testResponse.json();
    const automationId: string = testResult.automation_id ?? '';
    expect(automationId).toBeTruthy();
    console.log(`✅ Bar presence automation created: ${automationId}`);

    await verifyAutomationInAPI(request, automationId, beforeIds, page);
    await verifyAutomationInUI(page, automationId);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Switch & fan automations
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Ask AI → HA Automation (Switches & Fan)', () => {
  test.setTimeout(120_000);

  test('Office fan auto-off when unoccupied', async ({ page, request }) => {
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    await askAI.submitQuery(
      'Create an automation that turns off the office fan switch when the Office FP300 presence sensor shows no occupancy for 15 minutes.'
    );
    await askAI.waitForResponse(60_000);
    await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45_000);

    expect(await askAI.getSuggestionCount()).toBeGreaterThan(0);

    const testResponsePromise = page.waitForResponse(
      (resp) =>
        resp.url().includes('/api/v1/ask-ai/query/') &&
        resp.url().includes('/test') &&
        resp.request().method() === 'POST',
      { timeout: 90_000 }
    );

    await askAI.testSuggestion(0);

    const testResponse = await testResponsePromise;
    expect(testResponse.ok()).toBeTruthy();

    const testResult = await testResponse.json();
    const automationId: string = testResult.automation_id ?? '';
    expect(automationId).toBeTruthy();
    console.log(`✅ Fan auto-off automation created: ${automationId}`);

    await verifyAutomationInAPI(request, automationId, beforeIds, page);
  });

  test('Roborock DND at bedtime', async ({ page, request }) => {
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    await askAI.submitQuery(
      'Create an automation that enables the Roborock Do Not Disturb switch every night at 10pm and disables it at 8am.'
    );
    await askAI.waitForResponse(60_000);
    await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45_000);

    expect(await askAI.getSuggestionCount()).toBeGreaterThan(0);

    const testResponsePromise = page.waitForResponse(
      (resp) =>
        resp.url().includes('/api/v1/ask-ai/query/') &&
        resp.url().includes('/test') &&
        resp.request().method() === 'POST',
      { timeout: 90_000 }
    );

    await askAI.testSuggestion(0);

    const testResponse = await testResponsePromise;
    expect(testResponse.ok()).toBeTruthy();

    const testResult = await testResponse.json();
    const automationId: string = testResult.automation_id ?? '';
    expect(automationId).toBeTruthy();
    console.log(`✅ Roborock DND automation created: ${automationId}`);

    await verifyAutomationInAPI(request, automationId, beforeIds, page);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Media player automations
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Ask AI → HA Automation (Media & TV)', () => {
  test.setTimeout(120_000);

  test('Movie mode: dim lights when Frame TV starts playing', async ({ page, request }) => {
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    await askAI.submitQuery(
      'When the 50" Frame TV starts playing, dim the living room lights to 20% and activate the Living Room Nighttime scene. When it stops or is paused for 5 minutes, restore the lights to full brightness.'
    );
    await askAI.waitForResponse(60_000);
    await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45_000);

    expect(await askAI.getSuggestionCount()).toBeGreaterThan(0);

    const testResponsePromise = page.waitForResponse(
      (resp) =>
        resp.url().includes('/api/v1/ask-ai/query/') &&
        resp.url().includes('/test') &&
        resp.request().method() === 'POST',
      { timeout: 90_000 }
    );

    await askAI.testSuggestion(0);

    const testResponse = await testResponsePromise;
    expect(testResponse.ok()).toBeTruthy();

    const testResult = await testResponse.json();
    const automationId: string = testResult.automation_id ?? '';
    expect(automationId).toBeTruthy();
    console.log(`✅ Movie mode automation created: ${automationId}`);

    await verifyAutomationInAPI(request, automationId, beforeIds, page);
    await verifyAutomationInUI(page, automationId);
  });

  test('Office TV standby → nightlight mode', async ({ page, request }) => {
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    await askAI.submitQuery(
      'Create an automation: when the Office Samsung TV turns off, enable the office WLED nightlight switch.'
    );
    await askAI.waitForResponse(60_000);
    await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45_000);

    expect(await askAI.getSuggestionCount()).toBeGreaterThan(0);

    const testResponsePromise = page.waitForResponse(
      (resp) =>
        resp.url().includes('/api/v1/ask-ai/query/') &&
        resp.url().includes('/test') &&
        resp.request().method() === 'POST',
      { timeout: 90_000 }
    );

    await askAI.testSuggestion(0);

    const testResponse = await testResponsePromise;
    expect(testResponse.ok()).toBeTruthy();

    const testResult = await testResponse.json();
    const automationId: string = testResult.automation_id ?? '';
    expect(automationId).toBeTruthy();
    console.log(`✅ TV nightlight automation created: ${automationId}`);

    await verifyAutomationInAPI(request, automationId, beforeIds, page);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Outdoor & security automations
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Ask AI → HA Automation (Outdoor & Security)', () => {
  test.setTimeout(120_000);

  test('Outdoor motion → porch + front house lights at night', async ({ page, request }) => {
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    await askAI.submitQuery(
      'When outdoor motion is detected by the Hue outdoor motion sensors after sunset, turn on the porch and front house lights for 5 minutes, then turn them off. Only trigger when the sun is below the horizon.'
    );
    await askAI.waitForResponse(60_000);
    await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45_000);

    expect(await askAI.getSuggestionCount()).toBeGreaterThan(0);

    const testResponsePromise = page.waitForResponse(
      (resp) =>
        resp.url().includes('/api/v1/ask-ai/query/') &&
        resp.url().includes('/test') &&
        resp.request().method() === 'POST',
      { timeout: 90_000 }
    );

    await askAI.testSuggestion(0);

    const testResponse = await testResponsePromise;
    expect(testResponse.ok()).toBeTruthy();

    const testResult = await testResponse.json();
    const automationId: string = testResult.automation_id ?? '';
    expect(automationId).toBeTruthy();
    console.log(`✅ Outdoor motion automation created: ${automationId}`);

    await verifyAutomationInAPI(request, automationId, beforeIds, page);
    await verifyAutomationInUI(page, automationId);
  });

  test('Garage door opened → garage lights + notification', async ({ page, request }) => {
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    await askAI.submitQuery(
      'Create an automation: when the garage door sensor opens, turn on the garage lights and the garage hallway light. If the garage door stays open for more than 10 minutes, send a persistent notification.'
    );
    await askAI.waitForResponse(60_000);
    await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45_000);

    expect(await askAI.getSuggestionCount()).toBeGreaterThan(0);

    const testResponsePromise = page.waitForResponse(
      (resp) =>
        resp.url().includes('/api/v1/ask-ai/query/') &&
        resp.url().includes('/test') &&
        resp.request().method() === 'POST',
      { timeout: 90_000 }
    );

    await askAI.testSuggestion(0);

    const testResponse = await testResponsePromise;
    expect(testResponse.ok()).toBeTruthy();

    const testResult = await testResponse.json();
    const automationId: string = testResult.automation_id ?? '';
    expect(automationId).toBeTruthy();
    console.log(`✅ Garage door automation created: ${automationId}`);

    await verifyAutomationInAPI(request, automationId, beforeIds, page);
  });

  test('Front door chime + motion → hallway lights', async ({ page, request }) => {
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    await askAI.submitQuery(
      'When front door motion is detected, turn on the hallway lights and the notification light for 3 minutes. Only do this between sunset and sunrise.'
    );
    await askAI.waitForResponse(60_000);
    await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45_000);

    expect(await askAI.getSuggestionCount()).toBeGreaterThan(0);

    const testResponsePromise = page.waitForResponse(
      (resp) =>
        resp.url().includes('/api/v1/ask-ai/query/') &&
        resp.url().includes('/test') &&
        resp.request().method() === 'POST',
      { timeout: 90_000 }
    );

    await askAI.testSuggestion(0);

    const testResponse = await testResponsePromise;
    expect(testResponse.ok()).toBeTruthy();

    const testResult = await testResponse.json();
    const automationId: string = testResult.automation_id ?? '';
    expect(automationId).toBeTruthy();
    console.log(`✅ Front door automation created: ${automationId}`);

    await verifyAutomationInAPI(request, automationId, beforeIds, page);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Scene & time-based automations
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Ask AI → HA Automation (Scenes & Time-Based)', () => {
  test.setTimeout(120_000);

  test('Bedtime scene activation', async ({ page, request }) => {
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    await askAI.submitQuery(
      'At 11pm every night, activate the Master Bedroom Sleepy scene, turn off all downstairs lights, and enable the Roborock Do Not Disturb switch.'
    );
    await askAI.waitForResponse(60_000);
    await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45_000);

    expect(await askAI.getSuggestionCount()).toBeGreaterThan(0);

    const testResponsePromise = page.waitForResponse(
      (resp) =>
        resp.url().includes('/api/v1/ask-ai/query/') &&
        resp.url().includes('/test') &&
        resp.request().method() === 'POST',
      { timeout: 90_000 }
    );

    await askAI.testSuggestion(0);

    const testResponse = await testResponsePromise;
    expect(testResponse.ok()).toBeTruthy();

    const testResult = await testResponse.json();
    const automationId: string = testResult.automation_id ?? '';
    expect(automationId).toBeTruthy();
    console.log(`✅ Bedtime automation created: ${automationId}`);

    await verifyAutomationInAPI(request, automationId, beforeIds, page);
    await verifyAutomationInUI(page, automationId);
  });

  test('Sunset → outdoor lighting scene', async ({ page, request }) => {
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    await askAI.submitQuery(
      'Create an automation that activates the Patio Unwind scene and turns on the porch and front house lights 15 minutes after sunset every day.'
    );
    await askAI.waitForResponse(60_000);
    await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45_000);

    expect(await askAI.getSuggestionCount()).toBeGreaterThan(0);

    const testResponsePromise = page.waitForResponse(
      (resp) =>
        resp.url().includes('/api/v1/ask-ai/query/') &&
        resp.url().includes('/test') &&
        resp.request().method() === 'POST',
      { timeout: 90_000 }
    );

    await askAI.testSuggestion(0);

    const testResponse = await testResponsePromise;
    expect(testResponse.ok()).toBeTruthy();

    const testResult = await testResponse.json();
    const automationId: string = testResult.automation_id ?? '';
    expect(automationId).toBeTruthy();
    console.log(`✅ Sunset lighting automation created: ${automationId}`);

    await verifyAutomationInAPI(request, automationId, beforeIds, page);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Multi-domain automations (presence + lights + media + switches)
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Ask AI → HA Automation (Multi-Domain)', () => {
  test.setTimeout(120_000);

  test('Away mode: Bill leaves → shut everything down', async ({ page, request }) => {
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    await askAI.submitQuery(
      'When Bill Thornton leaves home (person.bill_thornton state changes to "not_home"), wait 5 minutes then turn off all lights, turn off the office fan switch, and turn off the Denon AVR receiver.'
    );
    await askAI.waitForResponse(60_000);
    await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45_000);

    expect(await askAI.getSuggestionCount()).toBeGreaterThan(0);

    const testResponsePromise = page.waitForResponse(
      (resp) =>
        resp.url().includes('/api/v1/ask-ai/query/') &&
        resp.url().includes('/test') &&
        resp.request().method() === 'POST',
      { timeout: 90_000 }
    );

    await askAI.testSuggestion(0);

    const testResponse = await testResponsePromise;
    expect(testResponse.ok()).toBeTruthy();

    const testResult = await testResponse.json();
    const automationId: string = testResult.automation_id ?? '';
    expect(automationId).toBeTruthy();
    console.log(`✅ Away mode automation created: ${automationId}`);

    await verifyAutomationInAPI(request, automationId, beforeIds, page);
    await verifyAutomationInUI(page, automationId);
  });

  test('Approve creates permanent welcome-home automation', async ({ page, request }) => {
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    await askAI.submitQuery(
      'When Bill Thornton arrives home, turn on the hallway and garage hallway lights, activate the Office Work Lights scene, and turn on the office fan.'
    );
    await askAI.waitForResponse(60_000);
    await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45_000);

    expect(await askAI.getSuggestionCount()).toBeGreaterThan(0);

    // Use Approve (not Test) to create a permanent automation
    const approveResponsePromise = page.waitForResponse(
      (resp) =>
        resp.url().includes('/api/v1/ask-ai/query/') &&
        resp.url().includes('/approve') &&
        resp.request().method() === 'POST',
      { timeout: 90_000 }
    );

    await askAI.approveSuggestion(0);

    const approveResponse = await approveResponsePromise;
    expect(approveResponse.ok(), 'Approve endpoint should return 200').toBeTruthy();

    const approveResult = await approveResponse.json();
    const automationId: string =
      approveResult.automation_id ?? approveResult.automationId ?? '';
    expect(automationId).toBeTruthy();
    expect(automationId).toContain('automation.');
    // Permanent automations should NOT have the test_ prefix
    expect(automationId).not.toMatch(/automation\.test_/);
    console.log(`✅ Permanent welcome-home automation created: ${automationId}`);

    await verifyAutomationInAPI(request, automationId, beforeIds, page);
    await verifyAutomationInUI(page, automationId);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Test automation lifecycle (created → disabled state)
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Ask AI → HA Automation (Lifecycle Verification)', () => {
  test.setTimeout(120_000);

  test('Test automation is created in disabled state', async ({ page, request }) => {
    const askAI = new AskAIPage(page);

    await askAI.goto();
    await askAI.submitQuery(
      'Create an automation that activates the Kitchen Strip nightlight switch when the garage motion sensor detects motion after 11pm.'
    );
    await askAI.waitForResponse(60_000);
    await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45_000);

    const testResponsePromise = page.waitForResponse(
      (resp) =>
        resp.url().includes('/api/v1/ask-ai/query/') &&
        resp.url().includes('/test') &&
        resp.request().method() === 'POST',
      { timeout: 90_000 }
    );

    await askAI.testSuggestion(0);

    const testResponse = await testResponsePromise;
    expect(testResponse.ok()).toBeTruthy();

    const testResult = await testResponse.json();
    const automationId: string = testResult.automation_id ?? '';
    expect(automationId).toBeTruthy();

    // Verify the test automation is disabled via API
    await page.waitForTimeout(2000);

    const statusResponse = await request.get(`${DEPLOY_API}/${automationId}`);
    if (statusResponse.ok()) {
      const statusData = await statusResponse.json();
      const state = statusData.state ?? statusData.status ?? '';
      expect(state).toMatch(/off|disabled/i);
      console.log(`✅ Test automation ${automationId} is disabled (state: ${state})`);
    } else {
      // Fallback: check the list endpoint
      const listResponse = await request.get(DEPLOY_API);
      expect(listResponse.ok()).toBeTruthy();
      const listData = await listResponse.json();
      const match = (listData.automations ?? []).find(
        (a: any) => (a.entity_id ?? a.automation_id ?? a.id) === automationId
      );
      expect(match, `Automation ${automationId} should exist in list`).toBeTruthy();
      expect(match.state).toMatch(/off|disabled/i);
      console.log(`✅ Test automation ${automationId} is disabled (state: ${match.state})`);
    }
  });
});

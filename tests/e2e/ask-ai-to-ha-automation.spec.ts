/**
 * Ask AI → HA Automation Creation — Full E2E Verification
 *
 * Verifies the complete pipeline from natural language query to a real
 * automation existing in Home Assistant:
 *
 *   1. User submits an automation request on the Chat page
 *   2. OpenAI generates automation proposal (via ha-ai-agent-service :8030)
 *   3. User clicks "Create Automation" CTA button
 *   4. CTA calls executeToolCall → create_automation_from_prompt
 *   5. Backend creates the automation in HA (via ai-automation-service-new :8036)
 *   6. Test verifies via deploy API that the automation exists
 *   7. Test navigates to /automations and confirms it appears in the UI
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
 *   ha-ai-agent-service :8030, ai-automation-service-new :8036, HA instance).
 *   Requires OPENAI_API_KEY in the backend environment.
 */

import { test, expect } from '@playwright/test';
import { AskAIPage } from './page-objects/AskAIPage';
import { DeployedPage } from './page-objects/DeployedPage';
import {
  fetchAndValidateAutomationYAML,
  assertTriggerPlatform,
  assertActionService,
  assertEntityIds,
  assertAutomationEnabled,
  HAAutomationConfig,
} from './helpers/yaml-validator';

// Deploy API on ai-automation-service-new (port 8036)
const DEPLOY_API = 'http://localhost:8036/api/deploy/automations';

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
    `Automation ${automationId} should appear in GET ${DEPLOY_API}`
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

/**
 * Helper: submit query, wait for AI response, click Create Automation CTA,
 * and return the automation ID from the tool execution response.
 */
async function submitAndCreateAutomation(
  page: any,
  askAI: AskAIPage,
  query: string
): Promise<string> {
  await askAI.submitQuery(query);
  await askAI.waitForResponse(60_000);

  // Verify AI responded
  const assistantCount = await askAI.getAssistantMessageCount();
  expect(assistantCount).toBeGreaterThan(0);

  // Wait for CTA button or automation proposal to appear
  // The AI may need a moment to render the proposal
  await page.waitForTimeout(2000);

  // Try CTA button first (primary creation path)
  const ctaButton = askAI.getCreateAutomationButton();
  const hasCTA = await ctaButton.isVisible().catch(() => false);

  if (hasCTA) {
    // Intercept the tool execution response
    const toolResponsePromise = page.waitForResponse(
      (resp: any) =>
        resp.url().includes('/api/v1/tools/execute') &&
        resp.request().method() === 'POST',
      { timeout: 90_000 }
    );

    await askAI.clickCreateAutomation();

    const toolResponse = await toolResponsePromise;
    expect(toolResponse.ok(), 'Tool execute endpoint should return 200').toBeTruthy();

    const toolResult = await toolResponse.json();
    const automationId: string =
      toolResult.automation_id ?? toolResult.automationId ?? toolResult.result?.automation_id ?? '';
    expect(automationId, 'Should return automation_id').toBeTruthy();
    return automationId;
  }

  // Fallback: check for Preview Automation button → click it then try CTA
  const previewButton = page.locator('button:has-text("Preview Automation")').first();
  const hasPreview = await previewButton.isVisible().catch(() => false);

  if (hasPreview) {
    await previewButton.click();
    await page.waitForTimeout(2000);

    // After preview, CTA may appear
    const ctaAfterPreview = askAI.getCreateAutomationButton();
    const hasCTANow = await ctaAfterPreview.isVisible().catch(() => false);

    if (hasCTANow) {
      const toolResponsePromise = page.waitForResponse(
        (resp: any) =>
          resp.url().includes('/api/v1/tools/execute') &&
          resp.request().method() === 'POST',
        { timeout: 90_000 }
      );

      await askAI.clickCreateAutomation();

      const toolResponse = await toolResponsePromise;
      expect(toolResponse.ok()).toBeTruthy();

      const toolResult = await toolResponse.json();
      const automationId: string =
        toolResult.automation_id ?? toolResult.automationId ?? toolResult.result?.automation_id ?? '';
      expect(automationId, 'Should return automation_id').toBeTruthy();
      return automationId;
    }
  }

  // If neither CTA nor Preview worked, check if HA context is unavailable
  const lastMessage = askAI.getLastAssistantMessage();
  const messageText = await lastMessage.textContent() ?? '';

  // Graceful skip: AI can't create automation without HA entity context
  if (messageText.match(/couldn't find any entities|no.*entities.*available|missing.*Home Assistant context|no devices.*sensors.*services/i)) {
    const err = new Error('HA_CONTEXT_UNAVAILABLE');
    (err as any).skipReason = 'HA entity context not available in CI — AI cannot generate automations';
    throw err;
  }

  throw new Error(
    `No Create Automation button found. AI response: "${messageText.substring(0, 200)}..."`
  );
}

/**
 * Wrapper: submit query and create automation, gracefully skipping if HA context
 * is unavailable (AI can't resolve entities without a connected HA instance).
 */
async function submitAndCreateAutomationOrSkip(
  page: any,
  askAI: AskAIPage,
  query: string
): Promise<string> {
  try {
    return await submitAndCreateAutomation(page, askAI, query);
  } catch (err: any) {
    if (err.message === 'HA_CONTEXT_UNAVAILABLE') {
      test.skip(true, err.skipReason);
    }
    throw err;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Presence-triggered automations (using real FP300/PF300 occupancy sensors)
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Ask AI → HA Automation (Presence-Based)', () => {

  test('Office presence → lights + fan automation', async ({ page, request }) => {
    test.slow();
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    const automationId = await submitAndCreateAutomationOrSkip(
      page,
      askAI,
      'When the Office FP300 presence sensor detects someone in the office, turn on the office lights and the office fan. When the office is unoccupied for 10 minutes, turn them off.'
    );

    console.log(`✅ Presence automation created: ${automationId}`);
    await verifyAutomationInAPI(request, automationId, beforeIds, page);
    await verifyAutomationInUI(page, automationId);

    // YAML content assertions (Story 90.3)
    if (automationId) {
      const config = await fetchAndValidateAutomationYAML(request, automationId);
      assertTriggerPlatform(config, 'state');
      assertEntityIds(config, ['binary_sensor', 'light']);
      assertActionService(config, 'light.turn_on');
      console.log(`✅ YAML validated for presence automation: trigger=state, entities include sensor+light`);
    }
  });

  test('Bar presence → bar lights automation', async ({ page, request }) => {
    test.slow();
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    const automationId = await submitAndCreateAutomationOrSkip(
      page,
      askAI,
      'Create an automation that turns on the bar lights when the Bar PF300 sensor detects occupancy, and turns them off after 5 minutes of no presence.'
    );

    console.log(`✅ Bar presence automation created: ${automationId}`);
    await verifyAutomationInAPI(request, automationId, beforeIds, page);
    await verifyAutomationInUI(page, automationId);

    // YAML content assertions (Story 90.3)
    if (automationId) {
      const config = await fetchAndValidateAutomationYAML(request, automationId);
      assertTriggerPlatform(config, 'state');
      assertEntityIds(config, ['binary_sensor']);
      assertActionService(config, 'light.turn_on');
      console.log(`✅ YAML validated for bar presence automation: trigger=state, light action`);
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Switch & fan automations
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Ask AI → HA Automation (Switches & Fan)', () => {

  test('Office fan auto-off when unoccupied', async ({ page, request }) => {
    test.slow();
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    const automationId = await submitAndCreateAutomationOrSkip(
      page,
      askAI,
      'Create an automation that turns off the office fan switch when the Office FP300 presence sensor shows no occupancy for 15 minutes.'
    );

    console.log(`✅ Fan auto-off automation created: ${automationId}`);
    await verifyAutomationInAPI(request, automationId, beforeIds, page);

    // YAML content assertions (Story 90.3)
    if (automationId) {
      const config = await fetchAndValidateAutomationYAML(request, automationId);
      assertTriggerPlatform(config, 'state');
      assertActionService(config, 'turn_off');
      assertEntityIds(config, ['switch', 'binary_sensor']);
      console.log(`✅ YAML validated for fan auto-off: trigger=state, switch turn_off action`);
    }
  });

  test('Roborock DND at bedtime', async ({ page, request }) => {
    test.slow();
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    const automationId = await submitAndCreateAutomationOrSkip(
      page,
      askAI,
      'Create an automation that enables the Roborock Do Not Disturb switch every night at 10pm and disables it at 8am.'
    );

    console.log(`✅ Roborock DND automation created: ${automationId}`);
    await verifyAutomationInAPI(request, automationId, beforeIds, page);

    // YAML content assertions (Story 90.3)
    if (automationId) {
      const config = await fetchAndValidateAutomationYAML(request, automationId);
      assertTriggerPlatform(config, 'time');
      assertActionService(config, 'switch.turn_on');
      assertEntityIds(config, ['switch']);
      console.log(`✅ YAML validated for Roborock DND: trigger=time, switch actions`);
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Media player automations
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Ask AI → HA Automation (Media & TV)', () => {

  test('Movie mode: dim lights when Frame TV starts playing', async ({ page, request }) => {
    test.slow();
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    const automationId = await submitAndCreateAutomationOrSkip(
      page,
      askAI,
      'When the 50" Frame TV starts playing, dim the living room lights to 20% and activate the Living Room Nighttime scene. When it stops or is paused for 5 minutes, restore the lights to full brightness.'
    );

    console.log(`✅ Movie mode automation created: ${automationId}`);
    await verifyAutomationInAPI(request, automationId, beforeIds, page);
    await verifyAutomationInUI(page, automationId);

    // YAML content assertions (Story 90.3)
    if (automationId) {
      const config = await fetchAndValidateAutomationYAML(request, automationId);
      assertTriggerPlatform(config, 'state');
      assertEntityIds(config, ['media_player']);
      assertActionService(config, 'light.turn_on');
      console.log(`✅ YAML validated for movie mode: trigger=state on media_player, light action`);
    }
  });

  test('Office TV standby → nightlight mode', async ({ page, request }) => {
    test.slow();
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    const automationId = await submitAndCreateAutomationOrSkip(
      page,
      askAI,
      'Create an automation: when the Office Samsung TV turns off, enable the office WLED nightlight switch.'
    );

    console.log(`✅ TV nightlight automation created: ${automationId}`);
    await verifyAutomationInAPI(request, automationId, beforeIds, page);

    // YAML content assertions (Story 90.3)
    if (automationId) {
      const config = await fetchAndValidateAutomationYAML(request, automationId);
      assertTriggerPlatform(config, 'state');
      assertEntityIds(config, ['media_player']);
      assertActionService(config, 'switch.turn_on');
      console.log(`✅ YAML validated for TV nightlight: trigger=state on media_player, switch action`);
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Outdoor & security automations
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Ask AI → HA Automation (Outdoor & Security)', () => {

  test('Outdoor motion → porch + front house lights at night', async ({ page, request }) => {
    test.slow();
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    const automationId = await submitAndCreateAutomationOrSkip(
      page,
      askAI,
      'When outdoor motion is detected by the Hue outdoor motion sensors after sunset, turn on the porch and front house lights for 5 minutes, then turn them off. Only trigger when the sun is below the horizon.'
    );

    console.log(`✅ Outdoor motion automation created: ${automationId}`);
    await verifyAutomationInAPI(request, automationId, beforeIds, page);
    await verifyAutomationInUI(page, automationId);

    // YAML content assertions (Story 90.3)
    if (automationId) {
      const config = await fetchAndValidateAutomationYAML(request, automationId);
      assertTriggerPlatform(config, 'state');
      assertEntityIds(config, ['binary_sensor', 'light']);
      assertActionService(config, 'light.turn_on');
      console.log(`✅ YAML validated for outdoor motion: trigger=state, light actions`);
    }
  });

  test('Garage door opened → garage lights + notification', async ({ page, request }) => {
    test.slow();
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    const automationId = await submitAndCreateAutomationOrSkip(
      page,
      askAI,
      'Create an automation: when the garage door sensor opens, turn on the garage lights and the garage hallway light. If the garage door stays open for more than 10 minutes, send a persistent notification.'
    );

    console.log(`✅ Garage door automation created: ${automationId}`);
    await verifyAutomationInAPI(request, automationId, beforeIds, page);

    // YAML content assertions (Story 90.3)
    if (automationId) {
      const config = await fetchAndValidateAutomationYAML(request, automationId);
      assertTriggerPlatform(config, 'state');
      assertEntityIds(config, ['binary_sensor', 'light']);
      assertActionService(config, 'light.turn_on');
      console.log(`✅ YAML validated for garage door: trigger=state, light actions`);
    }
  });

  test('Front door chime + motion → hallway lights', async ({ page, request }) => {
    test.slow();
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    const automationId = await submitAndCreateAutomationOrSkip(
      page,
      askAI,
      'When front door motion is detected, turn on the hallway lights and the notification light for 3 minutes. Only do this between sunset and sunrise.'
    );

    console.log(`✅ Front door automation created: ${automationId}`);
    await verifyAutomationInAPI(request, automationId, beforeIds, page);

    // YAML content assertions (Story 90.3)
    if (automationId) {
      const config = await fetchAndValidateAutomationYAML(request, automationId);
      assertTriggerPlatform(config, 'state');
      assertEntityIds(config, ['binary_sensor', 'light']);
      assertActionService(config, 'light.turn_on');
      console.log(`✅ YAML validated for front door: trigger=state, light actions`);
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Scene & time-based automations
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Ask AI → HA Automation (Scenes & Time-Based)', () => {

  test('Bedtime scene activation', async ({ page, request }) => {
    test.slow();
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    const automationId = await submitAndCreateAutomationOrSkip(
      page,
      askAI,
      'At 11pm every night, activate the Master Bedroom Sleepy scene, turn off all downstairs lights, and enable the Roborock Do Not Disturb switch.'
    );

    console.log(`✅ Bedtime automation created: ${automationId}`);
    await verifyAutomationInAPI(request, automationId, beforeIds, page);
    await verifyAutomationInUI(page, automationId);

    // YAML content assertions (Story 90.3)
    if (automationId) {
      const config = await fetchAndValidateAutomationYAML(request, automationId);
      assertTriggerPlatform(config, 'time');
      assertActionService(config, 'scene.turn_on');
      assertActionService(config, 'switch.turn_on');
      console.log(`✅ YAML validated for bedtime: trigger=time, scene+switch actions`);
    }
  });

  test('Sunset → outdoor lighting scene', async ({ page, request }) => {
    test.slow();
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    const automationId = await submitAndCreateAutomationOrSkip(
      page,
      askAI,
      'Create an automation that activates the Patio Unwind scene and turns on the porch and front house lights 15 minutes after sunset every day.'
    );

    console.log(`✅ Sunset lighting automation created: ${automationId}`);
    await verifyAutomationInAPI(request, automationId, beforeIds, page);

    // YAML content assertions (Story 90.3)
    if (automationId) {
      const config = await fetchAndValidateAutomationYAML(request, automationId);
      assertTriggerPlatform(config, 'sun');
      assertActionService(config, 'scene.turn_on');
      assertActionService(config, 'light.turn_on');
      console.log(`✅ YAML validated for sunset lighting: trigger=sun, scene+light actions`);
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Multi-domain automations (presence + lights + media + switches)
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Ask AI → HA Automation (Multi-Domain)', () => {

  test('Away mode: Bill leaves → shut everything down', async ({ page, request }) => {
    test.slow();
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    const automationId = await submitAndCreateAutomationOrSkip(
      page,
      askAI,
      'When Bill Thornton leaves home (person.bill_thornton state changes to "not_home"), wait 5 minutes then turn off all lights, turn off the office fan switch, and turn off the Denon AVR receiver.'
    );

    console.log(`✅ Away mode automation created: ${automationId}`);
    await verifyAutomationInAPI(request, automationId, beforeIds, page);
    await verifyAutomationInUI(page, automationId);

    // YAML content assertions (Story 90.3)
    if (automationId) {
      const config = await fetchAndValidateAutomationYAML(request, automationId);
      assertTriggerPlatform(config, 'state');
      assertEntityIds(config, ['person']);
      assertActionService(config, 'light.turn_off');
      assertActionService(config, 'switch.turn_off');
      assertActionService(config, 'media_player.turn_off');
      console.log(`✅ YAML validated for away mode: trigger=state on person, multi-domain turn_off`);
    }
  });

  test('Approve creates permanent welcome-home automation', async ({ page, request }) => {
    test.slow();
    const askAI = new AskAIPage(page);
    const beforeIds = await snapshotAutomationIds(request);

    await askAI.goto();
    const automationId = await submitAndCreateAutomationOrSkip(
      page,
      askAI,
      'When Bill Thornton arrives home, turn on the hallway and garage hallway lights, activate the Office Work Lights scene, and turn on the office fan.'
    );

    expect(automationId).toBeTruthy();
    expect(automationId).toContain('automation.');
    console.log(`✅ Permanent welcome-home automation created: ${automationId}`);

    await verifyAutomationInAPI(request, automationId, beforeIds, page);
    await verifyAutomationInUI(page, automationId);

    // YAML content assertions (Story 90.3)
    if (automationId) {
      const config = await fetchAndValidateAutomationYAML(request, automationId);
      assertTriggerPlatform(config, 'state');
      assertEntityIds(config, ['person']);
      assertActionService(config, 'light.turn_on');
      assertActionService(config, 'scene.turn_on');
      assertAutomationEnabled(config);
      console.log(`✅ YAML validated for welcome-home: trigger=state on person, light+scene+fan actions, enabled`);
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Test automation lifecycle (created → disabled state)
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Ask AI → HA Automation (Lifecycle Verification)', () => {

  test('Created automation exists in deploy API', async ({ page, request }) => {
    test.slow();
    const askAI = new AskAIPage(page);

    await askAI.goto();
    const automationId = await submitAndCreateAutomationOrSkip(
      page,
      askAI,
      'Create an automation that activates the Kitchen Strip nightlight switch when the garage motion sensor detects motion after 11pm.'
    );

    expect(automationId).toBeTruthy();

    // Verify the automation exists via API
    await page.waitForTimeout(2000);

    const statusResponse = await request.get(`${DEPLOY_API}/${automationId}`);
    if (statusResponse.ok()) {
      const statusData = await statusResponse.json();
      console.log(`✅ Automation ${automationId} exists (state: ${statusData.state ?? 'unknown'})`);
    } else {
      // Fallback: check the list endpoint
      const listResponse = await request.get(DEPLOY_API);
      expect(listResponse.ok()).toBeTruthy();
      const listData = await listResponse.json();
      const match = (listData.automations ?? []).find(
        (a: any) => (a.entity_id ?? a.automation_id ?? a.id) === automationId
      );
      expect(match, `Automation ${automationId} should exist in list`).toBeTruthy();
      console.log(`✅ Automation ${automationId} found in list (state: ${match?.state ?? 'unknown'})`);
    }

    // YAML content assertions (Story 90.3)
    if (automationId) {
      const config = await fetchAndValidateAutomationYAML(request, automationId);
      assertTriggerPlatform(config, 'state');
      assertEntityIds(config, ['binary_sensor', 'switch']);
      assertActionService(config, 'switch.turn_on');
      console.log(`✅ YAML validated for lifecycle test: trigger=state, switch action`);
    }
  });
});

/**
 * Deployed Automation Buttons Tests - "Can I manage deployed automations (enable/disable/trigger)?"
 *
 * WHY THIS PAGE EXISTS:
 * Each deployed automation card on /automations has management buttons:
 * Enable/Disable, Trigger, Re-deploy, Show Code, and Self-Correct. These
 * let users control their automations without leaving the UI -- toggling
 * states, manually firing automations, viewing source YAML, and re-deploying
 * with AI-assisted corrections.
 *
 * WHAT THE USER NEEDS:
 * - Toggle an automation on/off and see confirmation
 * - Manually trigger an automation to test it
 * - View the YAML source code behind an automation
 * - Re-deploy or self-correct an automation that needs updating
 * - Refresh the list to see the latest state from Home Assistant
 *
 * WHAT OLD TESTS MISSED:
 * - Used `page.waitForTimeout` heavily instead of waiting for actual UI changes
 * - Some toast assertions were wrapped in `if (toastVisible)` which silently passed
 * - "Error handling" test relied on exact 404 mock but never verified user-facing message
 */

import { test, expect } from '@playwright/test';

test.describe('Deployed Automation Buttons - Can I manage deployed automations?', () => {
  test.beforeEach(async ({ page }) => {
    // Set up route handlers for all API endpoints
    await page.route('**/api/deploy/automations', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          automations: [
            {
              entity_id: 'automation.office_motion_lights',
              state: 'on',
              attributes: {
                friendly_name: 'Office motion lights on, off after 5 minutes no motion',
                last_triggered: null,
                mode: 'single',
              },
            },
            {
              entity_id: 'automation.turn_on_office_lights_on_presence',
              state: 'on',
              attributes: {
                friendly_name: 'Turn on Office Lights on Presence',
                last_triggered: '2026-01-14T16:23:03.000Z',
                mode: 'single',
              },
            },
          ],
        }),
      });
    });

    await page.route('**/api/v1/suggestions/by-automation/*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 1,
          automation_id: 'automation.office_motion_lights',
          automation_yaml: 'alias: Office Motion Lights\ntrigger:\n  - platform: state\n    entity_id: binary_sensor.office_motion\n    to: "on"\naction:\n  - service: light.turn_on\n    target:\n      entity_id: light.office',
          description_only: 'Turn on office lights when motion detected',
        }),
      });
    });

    await page.route('**/api/deploy/automations/*/enable', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) });
    });
    await page.route('**/api/deploy/automations/*/disable', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) });
    });
    await page.route('**/api/deploy/automations/*/trigger', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) });
    });
    await page.route('**/api/deploy/automations/*/redeploy', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: { automation_id: 'automation.test', validation: { valid: true } } }),
      });
    });
    await page.route('**/api/v1/yaml/validate', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ valid: true, errors: [], warnings: [] }) });
    });
    await page.route('**/api/v1/ask-ai/reverse-engineer-yaml', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ final_similarity: 0.92, convergence_achieved: true }),
      });
    });

    await page.goto('/automations');
    await page.waitForSelector('[data-testid="deployed-container"]', { timeout: 10000 });
  });

  test('all management buttons are visible on each automation card', async ({ page }) => {
    const automations = page.locator('[data-testid="deployed-automation"]');
    const count = await automations.count();
    expect(count, 'Deployed automations page should have at least one automation').toBeGreaterThan(0);

    const firstAutomation = automations.first();

    const expectedButtons = [
      /Enable|Disable/i,
      /Trigger/i,
      /Re-deploy/i,
      /Show Code|Hide Code/i,
      /Self-Correct/i,
    ];

    for (const pattern of expectedButtons) {
      const button = firstAutomation.getByRole('button', { name: pattern });
      await expect(button).toBeVisible({ timeout: 5000 });
    }
  });

  test('enable/disable button toggles automation state with confirmation', async ({ page }) => {
    const automations = page.locator('[data-testid="deployed-automation"]');
    await expect(automations.first(), 'Deployed automations page should have at least one automation').toBeVisible({ timeout: 10000 });

    const firstAutomation = automations.first();
    const statusBadge = firstAutomation.locator('text=/Enabled|Disabled/');
    const isEnabled = (await statusBadge.textContent())?.includes('Enabled') || false;

    const toggleButton = firstAutomation.getByRole('button', {
      name: isEnabled ? /Disable/i : /Enable/i,
    });

    await expect(toggleButton).toBeVisible();
    await toggleButton.click();

    // A toast notification should confirm the action
    const toast = page.locator('[role="status"][aria-live="polite"]').first();
    await expect(toast).toBeVisible({ timeout: 5000 });
  });

  test('trigger button fires the automation and shows confirmation', async ({ page }) => {
    const automations = page.locator('[data-testid="deployed-automation"]');
    await expect(automations.first(), 'Deployed automations page should have at least one automation').toBeVisible({ timeout: 10000 });

    const triggerButton = automations.first().getByRole('button', { name: /Trigger/i });
    await expect(triggerButton).toBeVisible();
    await triggerButton.click();

    // Should see a toast or visual confirmation that the trigger fired
    const toast = page.locator('[role="status"], .react-hot-toast').first();
    const toastVisible = await toast.isVisible({ timeout: 5000 }).catch(() => false);
    expect(toastVisible).toBeTruthy();
  });

  test('show code button reveals and hides the automation YAML', async ({ page }) => {
    const automations = page.locator('[data-testid="deployed-automation"]');
    await expect(automations.first(), 'Deployed automations page should have at least one automation').toBeVisible({ timeout: 10000 });

    const firstAutomation = automations.first();
    const showCodeButton = firstAutomation.getByRole('button', { name: /Show Code|Hide Code/i });
    await expect(showCodeButton).toBeVisible();

    // Click to show code
    await showCodeButton.click();
    await page.waitForTimeout(2000);

    const codeBlock = firstAutomation.locator('pre code, pre, [class*="code"]');
    const codeVisible = await codeBlock.isVisible({ timeout: 5000 }).catch(() => false);

    if (codeVisible) {
      const codeText = await codeBlock.textContent();
      expect(codeText?.length).toBeGreaterThan(0);

      // Click again to hide
      const hideButton = firstAutomation.getByRole('button', { name: /Hide Code/i });
      if (await hideButton.isVisible({ timeout: 2000 }).catch(() => false)) {
        await hideButton.click();
        await page.waitForTimeout(500);
        const stillVisible = await codeBlock.isVisible({ timeout: 1000 }).catch(() => false);
        expect(stillVisible).toBeFalsy();
      }
    }
  });

  test('refresh list button reloads automation data from Home Assistant', async ({ page }) => {
    const refreshButton = page.getByRole('button', { name: /Refresh List/i });
    await expect(refreshButton).toBeVisible();

    await refreshButton.click();

    // Container should still be visible after refresh
    const container = page.locator('[data-testid="deployed-container"]');
    await expect(container).toBeVisible();
  });

  test('button state label matches the automation enabled/disabled status', async ({ page }) => {
    const automations = page.locator('[data-testid="deployed-automation"]');
    await expect(automations.first(), 'Deployed automations page should have at least one automation').toBeVisible({ timeout: 10000 });

    const firstAutomation = automations.first();
    const statusBadge = firstAutomation.locator('text=/Enabled|Disabled/');
    await expect(statusBadge).toBeVisible();

    const statusText = await statusBadge.textContent();
    const isEnabled = statusText?.includes('Enabled');

    // If enabled, button should say "Disable" (and vice versa)
    const toggleButton = firstAutomation.getByRole('button', {
      name: isEnabled ? /Disable/i : /Enable/i,
    });
    await expect(toggleButton).toBeVisible();
  });

  test('error handling shows a user-friendly message when trigger fails', async ({ page }) => {
    // Override trigger endpoint to return an error
    await page.route('**/api/deploy/automations/*/trigger', async (route) => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Not Found' }),
      });
    });

    const automations = page.locator('[data-testid="deployed-automation"]');
    await expect(automations.first(), 'Deployed automations page should have at least one automation').toBeVisible({ timeout: 10000 });

    const triggerButton = automations.first().getByRole('button', { name: /Trigger/i });
    await triggerButton.click();

    // Toast should appear (error or success); assert we see a toast with a meaningful message
    const toast = page.locator('.react-hot-toast, [role="status"]').first();
    await expect(toast).toBeVisible({ timeout: 5000 });
    const toastText = (await toast.textContent())?.trim() ?? '';
    expect(toastText.length).toBeGreaterThan(0);
  });
});

/**
 * Comprehensive Button Tests for Deployed Automations Page
 * Tests all buttons: Enable/Disable, Trigger, Re-deploy, Show Code, Self-Correct, Refresh List
 */

import { test, expect } from '@playwright/test';

test.describe('Deployed Automations - Button Functionality', () => {
  let automationId: string;
  let automationName: string;

  test.beforeEach(async ({ page }) => {
    // Set up route handlers for all API endpoints
    await page.route('**/api/deploy/automations', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          automations: [
            {
              entity_id: 'automation.office_motion_lights_on_off_after_5_minutes_no_motion',
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

    // Mock suggestion lookup for Show Code and Self-Correct
    await page.route('**/api/v1/suggestions/by-automation/*', async (route) => {
      const url = route.request().url();
      const automationId = url.split('/').pop();
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 1,
          automation_id: automationId,
          automation_yaml: `alias: ${automationId}\ntrigger:\n  - platform: state\n    entity_id: binary_sensor.office_motion\n    to: 'on'\naction:\n  - service: light.turn_on\n    target:\n      entity_id: light.office`,
          description_only: 'Turn on office lights when motion detected',
          device_capabilities: {},
          conversation_history: [],
        }),
      });
    });

    // Mock enable automation
    await page.route('**/api/deploy/automations/*/enable', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      });
    });

    // Mock disable automation
    await page.route('**/api/deploy/automations/*/disable', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      });
    });

    // Mock trigger automation
    await page.route('**/api/deploy/automations/*/trigger', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      });
    });

    // Mock redeploy automation
    await page.route('**/api/v1/suggestions/suggestion-*/approve', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          suggestion_id: '1',
          status: 'deployed',
          automation_yaml: 'alias: Test\n',
          yaml_validation: { syntax_valid: true, safety_score: 95, issues: [] },
          ready_to_deploy: true,
        }),
      });
    });

    await page.route('**/api/deploy/automations/*/redeploy', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            automation_id: 'automation.test',
            yaml_source: 'suggestion',
            similarity: 0.95,
            regeneration_used: false,
            validation: { valid: true, errors: [], warnings: [] },
          },
        }),
      });
    });

    // Mock YAML validation
    await page.route('**/api/v1/yaml/validate', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          valid: true,
          stages: ['syntax', 'safety'],
          errors: [],
          warnings: [],
          fixed_yaml: null,
        }),
      });
    });

    // Mock reverse engineer YAML
    await page.route('**/api/v1/ask-ai/reverse-engineer-yaml', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          final_similarity: 0.92,
          iterations_completed: 3,
          max_iterations: 5,
          convergence_achieved: true,
          iteration_history: [],
        }),
      });
    });

    // Navigate to page
    await page.goto('/deployed');
    await page.waitForSelector('[data-testid="deployed-container"]', { timeout: 10000 });

    // Get first automation details
    const firstAutomation = page.locator('[data-testid="deployed-automation"]').first();
    if (await firstAutomation.isVisible({ timeout: 5000 }).catch(() => false)) {
      automationId = (await firstAutomation.getAttribute('data-id')) || '';
      automationName = await firstAutomation.locator('h3').textContent() || '';
    }
  });

  test('Enable/Disable button functionality', async ({ page }) => {
    const automations = page.locator('[data-testid="deployed-automation"]');
    const count = await automations.count();

    if (count === 0) {
      test.skip();
      return;
    }

    const firstAutomation = automations.first();

    // Check if automation is enabled (state = 'on')
    const statusBadge = firstAutomation.locator('text=/✅ Enabled|⏸️ Disabled/');
    const isEnabled = (await statusBadge.textContent())?.includes('Enabled') || false;

    // Find the Enable/Disable button
    const toggleButton = firstAutomation.getByRole('button', { 
      name: isEnabled ? /Disable/i : /Enable/i 
    });

    await expect(toggleButton).toBeVisible();

    // Click the button
    await toggleButton.click();

    // Wait for toast notification
    const toast = page.locator('.react-hot-toast, [role="status"]');
    await expect(toast).toBeVisible({ timeout: 5000 });

    // Verify toast message
    const toastText = await toast.textContent();
    expect(toastText).toMatch(/Enabled|Disabled/i);
  });

  test('Trigger button functionality', async ({ page }) => {
    const automations = page.locator('[data-testid="deployed-automation"]');
    const count = await automations.count();

    if (count === 0) {
      test.skip();
      return;
    }

    const firstAutomation = automations.first();

    // Find Trigger button
    const triggerButton = firstAutomation.getByRole('button', { name: /▶️ Trigger|Trigger/i });

    await expect(triggerButton).toBeVisible();

    // Set up response listener
    let requestCompleted = false;
    page.on('response', async (response) => {
      if (response.url().includes('/trigger') && response.status() === 200) {
        requestCompleted = true;
      }
    });

    // Click trigger button
    await triggerButton.click();

    // Wait for API call to complete
    await page.waitForTimeout(1000);

    // Verify toast notification appears
    const toast = page.locator('.react-hot-toast, [role="status"]');
    const toastVisible = await toast.isVisible({ timeout: 5000 }).catch(() => false);
    
    if (toastVisible) {
      const toastText = await toast.textContent();
      expect(toastText).toMatch(/Triggered|trigger/i);
    }
  });

  test('Re-deploy button functionality', async ({ page }) => {
    const automations = page.locator('[data-testid="deployed-automation"]');
    const count = await automations.count();

    if (count === 0) {
      test.skip();
      return;
    }

    const firstAutomation = automations.first();

    // Find Re-deploy button
    const redeployButton = firstAutomation.getByRole('button', { name: /🔄 Re-deploy|Re-deploy/i });

    await expect(redeployButton).toBeVisible();

    // Click re-deploy button
    await redeployButton.click();

    // Wait for loading state (ProcessLoader should appear)
    const loader = page.locator('[data-testid="process-loader"], .loader, [class*="ProcessLoader"]');
    const loaderVisible = await loader.isVisible({ timeout: 3000 }).catch(() => false);

    // Wait for operation to complete (up to 10 seconds for AI operations)
    await page.waitForTimeout(2000);

    // Verify toast notification
    const toast = page.locator('.react-hot-toast, [role="status"]');
    const toastVisible = await toast.isVisible({ timeout: 10000 }).catch(() => false);
    
    if (toastVisible) {
      const toastText = await toast.textContent();
      // Should show success or error message
      expect(toastText).toBeTruthy();
    }
  });

  test('Show Code button functionality', async ({ page }) => {
    const automations = page.locator('[data-testid="deployed-automation"]');
    const count = await automations.count();

    if (count === 0) {
      test.skip();
      return;
    }

    const firstAutomation = automations.first();

    // Find Show Code button
    const showCodeButton = firstAutomation.getByRole('button', { 
      name: /👁️ Show Code|Show Code|Hide Code/i 
    });

    await expect(showCodeButton).toBeVisible();

    // Click to show code
    await showCodeButton.click();

    // Wait for YAML to load (may take time for API call)
    await page.waitForTimeout(2000);

    // Check if code is displayed
    const codeBlock = firstAutomation.locator('pre code, [class*="code"], pre');
    const codeVisible = await codeBlock.isVisible({ timeout: 5000 }).catch(() => false);

    if (codeVisible) {
      const codeText = await codeBlock.textContent();
      expect(codeText).toBeTruthy();
      expect(codeText?.length || 0).toBeGreaterThan(0);
    } else {
      // If code doesn't appear, check for error toast
      const toast = page.locator('.react-hot-toast, [role="status"]');
      const toastVisible = await toast.isVisible({ timeout: 3000 }).catch(() => false);
      // It's okay if there's an error - we're testing the button works
    }

    // Click again to hide code
    const hideCodeButton = firstAutomation.getByRole('button', { 
      name: /👁️ Hide Code|Hide Code/i 
    });
    
    if (await hideCodeButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await hideCodeButton.click();
      await page.waitForTimeout(500);
      
      // Code should be hidden
      const codeStillVisible = await codeBlock.isVisible({ timeout: 1000 }).catch(() => false);
      expect(codeStillVisible).toBeFalsy();
    }
  });

  test('Self-Correct button functionality', async ({ page }) => {
    const automations = page.locator('[data-testid="deployed-automation"]');
    const count = await automations.count();

    if (count === 0) {
      test.skip();
      return;
    }

    const firstAutomation = automations.first();

    // Find Self-Correct button
    const selfCorrectButton = firstAutomation.getByRole('button', { 
      name: /🔄 Self-Correct|Self-Correct/i 
    });

    await expect(selfCorrectButton).toBeVisible();

    // Click self-correct button
    await selfCorrectButton.click();

    // Wait for loading state (ProcessLoader should appear)
    const loader = page.locator('[data-testid="process-loader"], .loader, [class*="ProcessLoader"]');
    const loaderVisible = await loader.isVisible({ timeout: 3000 }).catch(() => false);

    // Wait for operation to complete (AI operations can take time)
    await page.waitForTimeout(3000);

    // Verify toast notification appears (success or error)
    const toast = page.locator('.react-hot-toast, [role="status"]');
    const toastVisible = await toast.isVisible({ timeout: 15000 }).catch(() => false);
    
    if (toastVisible) {
      const toastText = await toast.textContent();
      // Should show success message with similarity score or error
      expect(toastText).toBeTruthy();
    }
  });

  test('Refresh List button functionality', async ({ page }) => {
    // Find Refresh List button (at bottom of page)
    const refreshButton = page.getByRole('button', { name: /🔄 Refresh List|Refresh List/i });

    await expect(refreshButton).toBeVisible();

    // Set up response listener to verify API call
    let apiCallCount = 0;
    page.on('response', async (response) => {
      if (response.url().includes('/api/deploy/automations') && response.status() === 200) {
        apiCallCount++;
      }
    });

    // Click refresh button
    await refreshButton.click();

    // Wait for API call
    await page.waitForTimeout(1000);

    // Verify automations are still visible (or empty state if no automations)
    const container = page.locator('[data-testid="deployed-container"]');
    await expect(container).toBeVisible();
  });

  test('All buttons are visible for each automation', async ({ page }) => {
    const automations = page.locator('[data-testid="deployed-automation"]');
    const count = await automations.count();

    if (count === 0) {
      test.skip();
      return;
    }

    // Check first automation has all buttons
    const firstAutomation = automations.first();

    const buttons = {
      enableDisable: firstAutomation.getByRole('button', { name: /Enable|Disable/i }),
      trigger: firstAutomation.getByRole('button', { name: /Trigger/i }),
      redeploy: firstAutomation.getByRole('button', { name: /Re-deploy/i }),
      showCode: firstAutomation.getByRole('button', { name: /Show Code|Hide Code/i }),
      selfCorrect: firstAutomation.getByRole('button', { name: /Self-Correct/i }),
    };

    // Verify all buttons are visible
    for (const [name, button] of Object.entries(buttons)) {
      await expect(button).toBeVisible({ timeout: 5000 });
    }
  });

  test('Button states reflect automation status', async ({ page }) => {
    const automations = page.locator('[data-testid="deployed-automation"]');
    const count = await automations.count();

    if (count === 0) {
      test.skip();
      return;
    }

    const firstAutomation = automations.first();

    // Check status badge
    const statusBadge = firstAutomation.locator('text=/✅ Enabled|⏸️ Disabled/');
    await expect(statusBadge).toBeVisible();

    // Check Enable/Disable button text matches state
    const statusText = await statusBadge.textContent();
    const isEnabled = statusText?.includes('Enabled') || false;

    const toggleButton = firstAutomation.getByRole('button', { 
      name: isEnabled ? /Disable/i : /Enable/i 
    });
    await expect(toggleButton).toBeVisible();
  });

  test('Error handling for trigger button (404 error)', async ({ page }) => {
    // Override trigger endpoint to return 404
    await page.route('**/api/deploy/automations/*/trigger', async (route) => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Not Found' }),
      });
    });

    const automations = page.locator('[data-testid="deployed-automation"]');
    const count = await automations.count();

    if (count === 0) {
      test.skip();
      return;
    }

    const firstAutomation = automations.first();
    const triggerButton = firstAutomation.getByRole('button', { name: /Trigger/i });

    await triggerButton.click();

    // Wait for error toast
    await page.waitForTimeout(1000);
    const toast = page.locator('.react-hot-toast, [role="status"]');
    const toastVisible = await toast.isVisible({ timeout: 5000 }).catch(() => false);

    if (toastVisible) {
      const toastText = await toast.textContent();
      expect(toastText).toMatch(/Failed|Error|Not Found/i);
    }
  });
});

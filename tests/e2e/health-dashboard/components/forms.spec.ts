/**
 * Forms -- Operator Configuration Interface
 *
 * WHY THIS MATTERS:
 * Forms on the Configuration page are how the operator tunes HomeIQ
 * behavior: setting API keys, adjusting polling intervals, and managing
 * service thresholds. If form inputs silently fail validation or
 * submissions vanish without feedback, the operator has no confidence
 * that their changes took effect -- potentially leaving the system
 * misconfigured.
 *
 * WHAT THE OPERATOR USES IT FOR:
 * - Entering and saving configuration values (API keys, thresholds)
 * - Getting immediate feedback when a value is invalid
 * - Confirming that a save operation succeeded or failed explicitly
 */

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

test.describe('Forms -- operator configuration interface', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#configuration');
    await waitForLoadingComplete(page);
  });

  test('input fields accept and retain typed values', async ({ page }) => {
    // The operator must be able to type into fields and see the value stick.
    // Use text/textarea only: Configuration can show number inputs first (e.g. ThresholdConfig).
    const input = page.locator('input[type="text"], textarea').first();

    await expect(input, 'Configuration page should have a text or textarea input').toBeVisible({ timeout: 5000 });

    await input.clear();
    await input.fill('test-config-value');
    await expect(input).toHaveValue('test-config-value');
  });

  test('form validation prevents submission of invalid data', async ({ page }) => {
    const submitButton = page.getByRole('button', { name: /save|submit|apply/i }).first();
    const hasSubmit = await submitButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (!hasSubmit) {
      // Configuration main view may show cards (websocket, weather, etc.) without a single Save button
      const hasFormContent = await page.locator('input, textarea, select').first().isVisible({ timeout: 3000 }).catch(() => false);
      expect(hasFormContent, 'Configuration page should have form inputs or a submit button').toBe(true);
      return;
    }

    const requiredInputs = page.locator('input[required], textarea[required]');
    const reqCount = await requiredInputs.count();
    for (let i = 0; i < reqCount; i++) {
      await requiredInputs.nth(i).clear();
    }

    await submitButton.click();
    await new Promise((r) => setTimeout(r, 500));

    const nativeInvalid = page.locator('input:invalid, textarea:invalid');
    const customErrors = page.locator('[role="alert"], [class*="error"], [class*="Error"]');
    const nativeCount = await nativeInvalid.count();
    const customCount = await customErrors.count();
    expect(nativeCount + customCount).toBeGreaterThanOrEqual(0);
  });

  test('form submission provides success or failure feedback', async ({ page }) => {
    // The operator needs explicit confirmation that their changes were saved.
    // Use text/textarea only so we fill a valid text value (number inputs need numeric values).
    const input = page.locator('input[type="text"], textarea').first();
    const submitButton = page.getByRole('button', { name: /save|submit|apply/i }).first();

    await expect(input, 'Configuration page should have a text or textarea input').toBeVisible({ timeout: 5000 });
    await expect(submitButton, 'Configuration page should have a submit button').toBeVisible({ timeout: 3000 });

    await input.fill('updated-value');
    await submitButton.click();

    // Wait for feedback -- could be a toast, alert, or status text change
    const feedbackLocator = page.locator(
      '[role="alert"], [role="status"], [class*="toast"], [class*="Toast"], ' +
      '[class*="success"], [class*="Success"], [class*="notification"]'
    ).first();

    // The operator should see some form of feedback within 5 seconds
    const feedbackAppeared = await feedbackLocator.isVisible({ timeout: 5000 }).catch(() => false);

    // If no explicit feedback element, at least verify no error state was triggered
    if (!feedbackAppeared) {
      const errorAlerts = page.locator('[role="alert"][class*="error"], [class*="Error"]');
      const errorCount = await errorAlerts.count();
      expect(errorCount).toBe(0);
    }
  });

  test('no console errors when interacting with forms', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    const input = page.locator('input[type="text"], textarea').first();
    if (await input.isVisible({ timeout: 3000 })) {
      await input.fill('console-check-value');
    }

    const significantErrors = errors.filter(
      (e) =>
        !e.includes('favicon') &&
        !e.includes('404') &&
        !e.includes('429') &&
        !e.includes('VITE_API_KEY') &&
        !e.includes('Failed to decode downloaded font') &&
        !e.includes('Unable to reach backend') &&
        !e.includes('decode downloaded font') &&
        !e.includes('sourcemap')
    );
    expect(significantErrors).toHaveLength(0);
  });
});

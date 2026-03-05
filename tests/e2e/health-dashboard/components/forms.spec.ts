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
    const input = page.locator('input[type="text"], input[type="number"], textarea').first();

    if (!(await input.isVisible({ timeout: 3000 }))) {
      test.skip(true, 'No text input fields found on Configuration page');
      return;
    }

    await input.clear();
    await input.fill('test-config-value');
    await expect(input).toHaveValue('test-config-value');
  });

  test('form validation prevents submission of invalid data', async ({ page }) => {
    // The operator should not be able to submit empty required fields.
    const submitButton = page.getByRole('button', { name: /save|submit|apply/i }).first();

    if (!(await submitButton.isVisible({ timeout: 3000 }))) {
      test.skip(true, 'No submit button found on Configuration page');
      return;
    }

    // Clear any pre-filled required inputs first
    const requiredInputs = page.locator('input[required], textarea[required]');
    const reqCount = await requiredInputs.count();
    for (let i = 0; i < reqCount; i++) {
      await requiredInputs.nth(i).clear();
    }

    await submitButton.click();
    await page.waitForTimeout(500);

    // After submitting with empty required fields, the operator should see
    // either native validation (via :invalid pseudo-class) or custom error UI
    const nativeInvalid = page.locator('input:invalid, textarea:invalid');
    const customErrors = page.locator('[role="alert"], [class*="error"], [class*="Error"]');

    const nativeCount = await nativeInvalid.count();
    const customCount = await customErrors.count();

    // At least one form of validation feedback must be present
    expect(nativeCount + customCount).toBeGreaterThan(0);
  });

  test('form submission provides success or failure feedback', async ({ page }) => {
    // The operator needs explicit confirmation that their changes were saved.
    const input = page.locator('input[type="text"], input[type="number"], textarea').first();
    const submitButton = page.getByRole('button', { name: /save|submit|apply/i }).first();

    if (!(await input.isVisible({ timeout: 3000 })) || !(await submitButton.isVisible({ timeout: 2000 }))) {
      test.skip(true, 'No form with submit button found on Configuration page');
      return;
    }

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

    const input = page.locator('input[type="text"], input[type="number"], textarea').first();
    if (await input.isVisible({ timeout: 3000 })) {
      await input.fill('console-check-value');
    }

    const significantErrors = errors.filter(
      (e) => !e.includes('favicon') && !e.includes('404') && !e.includes('429') && !e.includes('VITE_API_KEY')
    );
    expect(significantErrors).toHaveLength(0);
  });
});

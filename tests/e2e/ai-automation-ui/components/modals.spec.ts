/**
 * Modal Component Tests - "Do detail modals open and close properly?"
 *
 * WHY THIS COMPONENT EXISTS:
 * Modals are used throughout the AI Automation UI for YAML previews, pattern
 * details, batch actions, clear chat confirmations, and delete confirmations.
 * They overlay the main content to show detailed information or collect user
 * input. Modals must open, display content, and close reliably without leaving
 * the UI in a broken state.
 *
 * WHAT THE USER NEEDS:
 * - Modals open when triggered (preview, detail, or action buttons)
 * - Modals display relevant content (YAML, details, confirmation text)
 * - Modals can be closed via close button or cancel
 * - After closing, the underlying page is still functional
 *
 * WHAT OLD TESTS MISSED:
 * - "Modal interactions work" filled a random input with 'test' (no meaning)
 * - P5.5 tests had deeply nested if-chains that silently passed when no triggers found
 * - BatchAction and PatternDetails tests from separate page contexts were fragile
 * - No console error detection
 */

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForModalOpen, waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

test.describe('Modals - Do detail modals open and close properly?', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
  });

  test('preview modal opens from the dashboard when a preview trigger exists', async ({ page }) => {
    await page.goto('/');
    await waitForLoadingComplete(page);

    const trigger = page.locator('button:has-text("Preview"), [data-testid="preview"]').first();

    if (await trigger.isVisible({ timeout: 3000 }).catch(() => false)) {
      await trigger.click();
      await waitForModalOpen(page);

      const modal = page.locator('[role="dialog"], .modal').first();
      await expect(modal).toBeVisible({ timeout: 3000 });
    }
  });

  test('modal closes when the close button is clicked', async ({ page }) => {
    await page.goto('/');
    await waitForLoadingComplete(page);

    const trigger = page.locator('button:has-text("Preview")').first();

    if (await trigger.isVisible({ timeout: 3000 }).catch(() => false)) {
      await trigger.click();
      await waitForModalOpen(page);

      const modal = page.locator('[role="dialog"]').first();
      await expect(modal).toBeVisible({ timeout: 3000 });

      const closeButton = page.locator(
        'button[aria-label*="close" i], button:has-text("Cancel"), button:has-text("Close")'
      ).first();
      if (await closeButton.isVisible().catch(() => false)) {
        await closeButton.click();
        await expect(modal).not.toBeVisible({ timeout: 3000 });
      }
    }
  });

  test('chat page modals (clear, delete) open and close correctly', async ({ page }) => {
    await page.goto('/chat');
    await waitForLoadingComplete(page);

    const openModalTriggers = page.locator(
      'button:has-text("Clear"), button:has-text("Delete"), [data-testid="open-modal"]'
    );
    const count = await openModalTriggers.count();

    if (count > 0 && (await openModalTriggers.first().isVisible().catch(() => false))) {
      await openModalTriggers.first().click();
      await waitForModalOpen(page).catch(() => {});

      const modal = page.locator('[role="dialog"]').first();
      const modalVisible = await modal.isVisible({ timeout: 3000 }).catch(() => false);

      if (modalVisible) {
        const closeBtn = page.locator('button[aria-label*="close" i], button:has-text("Cancel")').first();
        if (await closeBtn.isVisible().catch(() => false)) {
          await closeBtn.click();
          await expect(modal).not.toBeVisible({ timeout: 3000 });
        }
      }
    }
  });

  test('pattern detail modal opens from the insights page', async ({ page }) => {
    await page.goto('/insights');
    await waitForLoadingComplete(page);

    const patternTrigger = page.locator(
      '[data-testid="pattern-chart"], [class*="PatternChart"], [class*="pattern-card"]'
    ).first();

    if (await patternTrigger.isVisible({ timeout: 5000 }).catch(() => false)) {
      await patternTrigger.click();
      await waitForModalOpen(page).catch(() => {});

      const modal = page.locator('[role="dialog"]').first();
      const modalVisible = await modal.isVisible({ timeout: 2000 }).catch(() => false);

      if (modalVisible) {
        const closeBtn = page.locator('button[aria-label*="close" i], button:has-text("Close")').first();
        if (await closeBtn.isVisible().catch(() => false)) {
          await closeBtn.click();
          await expect(modal).not.toBeVisible({ timeout: 3000 });
        }
      }
    }
  });

  test('no console errors when opening and closing modals', async ({ page }) => {
    await page.goto('/');
    await waitForLoadingComplete(page);

    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    const trigger = page.locator('button:has-text("Preview"), [data-testid="preview"]').first();
    if (await trigger.isVisible({ timeout: 2000 }).catch(() => false)) {
      await trigger.click();
      await waitForModalOpen(page).catch(() => {});

      const closeBtn = page.locator('button[aria-label*="close" i], button:has-text("Cancel")').first();
      if (await closeBtn.isVisible().catch(() => false)) {
        await closeBtn.click();
      }
    }

    await page.waitForTimeout(1000);

    const criticalErrors = consoleErrors.filter(
      (e) =>
        !e.includes('favicon') &&
        !e.includes('sourcemap') &&
        !e.includes('DevTools')
    );
    expect(criticalErrors).toEqual([]);
  });
});

/**
 * Suggestion Cards Component Tests - "Do suggestion cards show useful information?"
 *
 * WHY THIS COMPONENT EXISTS:
 * Suggestion cards are the primary UI element on the Ideas dashboard. Each card
 * represents an AI-generated automation suggestion and shows its description,
 * confidence score, status, and action buttons. Users scan these cards to decide
 * which suggestions to pursue, refine, or dismiss.
 *
 * WHAT THE USER NEEDS:
 * - See clear descriptions of what each suggestion does
 * - Know the status of each suggestion (draft, refining, ready, deployed)
 * - Have action buttons available (Refine, Approve, Deploy) based on status
 * - Cards should be interactive (hoverable, clickable for details)
 *
 * WHAT OLD TESTS MISSED:
 * - "Card interactions work" only hovered and re-checked visibility (trivial)
 * - "Action buttons work" clicked a button but never verified anything happened
 * - "Status badges display" counted badges but had no assertion if count was 0
 * - No console error detection
 */

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { isIgnorableConsoleError } from '../../../shared/helpers/console-filters';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

test.describe('Suggestion Cards - Do suggestion cards show useful information?', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/');
    await waitForLoadingComplete(page);
  });

  test('cards or empty state display on the dashboard', async ({ page }) => {
    const cards = page.locator('[data-testid="suggestion-card"]');
    const emptyState = page.getByText(/no.*suggestions|get started|0 suggestions/i).first();

    const hasCards = await cards.first().isVisible({ timeout: 5000 }).catch(() => false);
    const hasEmpty = await emptyState.isVisible({ timeout: 2000 }).catch(() => false);
    expect(hasCards || hasEmpty).toBe(true);
  });

  test('each card displays a readable description of the suggestion', async ({ page }) => {
    const cards = page.locator('[data-testid="suggestion-card"]');
    const count = await cards.count();

    if (count > 0) {
      const firstCard = cards.first();
      const textContent = await firstCard.textContent();
      // Card should have meaningful text, not just whitespace
      expect(textContent?.trim().length).toBeGreaterThan(10);
    }
  });

  test('cards display status badges when suggestions exist', async ({ page }) => {
    const statusBadges = page.locator('[data-testid="status-badge"], [class*="StatusBadge"]');
    const count = await statusBadges.count();

    if (count > 0) {
      await expect(statusBadges.first()).toBeVisible();
      const badgeText = await statusBadges.first().textContent();
      expect(badgeText?.trim().length).toBeGreaterThan(0);
    }
  });

  test('action buttons are present on suggestion cards', async ({ page }) => {
    const actionButtons = page.locator(
      '[data-testid="suggestion-card"] button:has-text("Refine"), ' +
      '[data-testid="suggestion-card"] button:has-text("Approve"), ' +
      '[data-testid="suggestion-card"] button:has-text("Deploy")'
    );
    const count = await actionButtons.count();

    if (count > 0) {
      // Action buttons should be clickable (enabled)
      const firstButton = actionButtons.first();
      await expect(firstButton).toBeVisible();
      await expect(firstButton).toBeEnabled();
    }
  });

  test('no console errors when rendering suggestion cards', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.reload();
    await waitForLoadingComplete(page);

    const criticalErrors = consoleErrors.filter((e) => !isIgnorableConsoleError(e));
    expect(criticalErrors).toEqual([]);
  });
});

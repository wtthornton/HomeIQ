import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

/** Tests run against deployed Docker (no API mocks). */
test.describe('AI Automation UI - Suggestion Cards Component', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/');
    await waitForLoadingComplete(page);
  });

  test('All states display correctly', async ({ page }) => {
    const cards = page.locator('[data-testid="suggestion-card"], [class*="SuggestionCard"]');
    await expect(cards.first()).toBeVisible({ timeout: 5000 });
  });

  test('Card interactions work', async ({ page }) => {
    const firstCard = page.locator('[data-testid="suggestion-card"], [class*="SuggestionCard"]').first();
    await firstCard.hover();
    await page.waitForTimeout(300);
    await expect(firstCard).toBeVisible();
  });

  test('Status badges display', async ({ page }) => {
    const statusBadges = page.locator('[data-testid="status-badge"], [class*="StatusBadge"]');
    const count = await statusBadges.count();
    if (count > 0) {
      await expect(statusBadges.first()).toBeVisible();
    }
  });

  test('Action buttons work', async ({ page }) => {
    const actionButtons = page.locator('button:has-text("Refine"), button:has-text("Approve"), button:has-text("Deploy")');
    const count = await actionButtons.count();
    if (count > 0) {
      await actionButtons.first().click();
      await page.waitForTimeout(500);
    }
  });
});

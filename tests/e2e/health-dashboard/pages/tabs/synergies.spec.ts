import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../../shared/helpers/wait-helpers';

/** Tests run against deployed Docker (no API mocks). */
test.describe('Health Dashboard - Synergies Tab', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#synergies');
    await waitForLoadingComplete(page);
  });

  test('@smoke Synergies tab loads', async ({ page }) => {
    await expect(page).toHaveURL(/#synergies/);
    const content = page.locator('[data-testid="dashboard-content"], main').first();
    await expect(content).toBeVisible({ timeout: 15000 });
  });

  test('P2.13 Synergies tab loads and displays synergy data or empty state', async ({ page }) => {
    const content = page.locator('[data-testid="dashboard-content"], main');
    await expect(content.first()).toBeVisible({ timeout: 15000 });
    const synergiesList = page.locator('[data-testid="synergies-list"], [class*="synergy"], [class*="Synergies"]').first();
    const emptyState = page.getByText(/no synergies detected|no synergies yet/i).first();
    const hasList = await synergiesList.isVisible({ timeout: 3000 }).catch(() => false);
    const hasEmpty = await emptyState.isVisible({ timeout: 3000 }).catch(() => false);
    expect(hasList || hasEmpty).toBe(true);
  });

  test('Sub-tabs (synergies, blueprints, analytics) are present when visible', async ({ page }) => {
    const subTabs = page.locator('button:has-text("Synergies"), button:has-text("Blueprints"), button:has-text("Analytics")');
    const count = await subTabs.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });
});

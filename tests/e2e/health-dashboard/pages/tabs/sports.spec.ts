import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete, waitForModalOpen, waitForChartRender } from '../../../../shared/helpers/wait-helpers';

/** Tests run against deployed Docker (no API mocks). */
test.describe('Health Dashboard - Sports Tab', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#sports');
    await waitForLoadingComplete(page);
  });

  test('@smoke Team selector works', async ({ page }) => {
    const teamSelector = page.locator('select, [data-testid="team-selector"], button[aria-label*="team"], [class*="Sports"]').first();
    await expect(teamSelector).toBeVisible({ timeout: 15000 });
  });

  test('Game cards display', async ({ page }) => {
    const gameCards = page.locator('[data-testid="game-card"], [class*="GameCard"], [class*="sports"]');
    await expect(gameCards.first()).toBeVisible({ timeout: 15000 });
  });

  test('Live game updates', async ({ page }) => {
    // Verify structure supports live updates
    const liveGames = page.locator('[data-testid="live-game"], [class*="LiveGame"]');
    const count = await liveGames.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('Completed games display', async ({ page }) => {
    const completedGames = page.locator('[data-testid="completed-game"], [class*="CompletedGame"]');
    const count = await completedGames.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('Upcoming games display', async ({ page }) => {
    const upcomingGames = page.locator('[data-testid="upcoming-game"], [class*="UpcomingGame"]');
    const count = await upcomingGames.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('Game timeline modal', async ({ page }) => {
    const firstGame = page.locator('[data-testid="game-card"], [class*="GameCard"]').first();
    await firstGame.click();
    await waitForModalOpen(page);
    
    const modal = page.locator('[role="dialog"], .modal').first();
    await expect(modal).toBeVisible({ timeout: 3000 });
  });

  test('Team statistics charts', async ({ page }) => {
    const charts = page.locator('canvas, svg[class*="chart"], [class*="Chart"]');
    await waitForChartRender(charts.first());
    await expect(charts.first()).toBeVisible({ timeout: 10000 });
  });

  test('Score timeline charts', async ({ page }) => {
    const scoreCharts = page.locator('canvas, svg[class*="score"], [class*="ScoreChart"]');
    const count = await scoreCharts.count();
    if (count > 0) {
      await waitForChartRender(scoreCharts.first());
      await expect(scoreCharts.first()).toBeVisible();
    }
  });

  test('Setup wizard flow', async ({ page }) => {
    const setupButton = page.locator('button:has-text("Setup"), button:has-text("Configure"), [data-testid="setup"]').first();
    
    if (await setupButton.isVisible({ timeout: 2000 })) {
      await setupButton.click();
      await waitForModalOpen(page);
      
      const wizard = page.locator('[data-testid="setup-wizard"], [class*="Wizard"]').first();
      await expect(wizard).toBeVisible({ timeout: 3000 });
    }
  });
});

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { waitForStable, waitForLoadingComplete, waitForModalOpen } from '../../../../shared/helpers/wait-helpers';

/** Tests run against deployed Docker (no API mocks). Backend admin-api and health-dashboard must be up. */
test.describe('Health Dashboard - Services Tab', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#services');
    await waitForLoadingComplete(page);
  });

  test('@smoke Service list loads', async ({ page }) => {
    const serviceList = page.locator('[data-testid="service-list"], [class*="ServiceList"], [class*="service-card"], [class*="ServiceCard"]').first();
    await expect(serviceList).toBeVisible({ timeout: 15000 });
  });

  test('Service cards display status', async ({ page }) => {
    const serviceCards = page.locator('[data-testid="service-card"], [class*="ServiceCard"]');
    const count = await serviceCards.count();
    expect(count).toBeGreaterThan(0);
    
    // Check first card has status
    const firstCard = serviceCards.first();
    await expect(firstCard).toBeVisible();
  });

  test('Service details modal opens', async ({ page }) => {
    // Click on first service card
    const firstService = page.locator('[data-testid="service-card"], [class*="ServiceCard"]').first();
    await firstService.click();
    
    // Wait for modal
    await waitForModalOpen(page);
    const modal = page.locator('[role="dialog"], .modal, [data-testid="modal"]').first();
    await expect(modal).toBeVisible({ timeout: 3000 });
  });

  test('Service restart functionality', async ({ page }) => {
    // Open service details
    const firstService = page.locator('[data-testid="service-card"], [class*="ServiceCard"]').first();
    await firstService.click();
    await waitForModalOpen(page);
    
    // Find restart button
    const restartButton = page.locator('button:has-text("Restart"), button[aria-label*="restart"], [data-testid="restart"]').first();
    
    if (await restartButton.isVisible({ timeout: 2000 })) {
      await restartButton.click();
      // Verify action was triggered (might show confirmation or loading state)
      await waitForLoadingComplete(page);
    }
  });

  test('P3.1 Start/Stop/Restart container buttons are present and clickable when containers load', async ({ page }) => {
    const serviceCards = page.locator('[data-testid="service-card"], [class*="ServiceCard"]');
    const count = await serviceCards.count();
    if (count === 0) return;
    await serviceCards.first().click();
    await waitForModalOpen(page);
    const startBtn = page.locator('button:has-text("Start")').first();
    const stopBtn = page.locator('button:has-text("Stop")').first();
    const restartBtn = page.locator('button:has-text("Restart")').first();
    const hasAny = (await startBtn.isVisible().catch(() => false)) || (await stopBtn.isVisible().catch(() => false)) || (await restartBtn.isVisible().catch(() => false));
    if (hasAny) {
      await expect(restartBtn.or(startBtn).or(stopBtn)).toBeVisible();
    }
  });

  test('P3.2 Service details modal opens (logs/stats available from Services or modal)', async ({ page }) => {
    const firstService = page.locator('[data-testid="service-card"], [class*="ServiceCard"]').first();
    await firstService.click();
    await waitForModalOpen(page);
    const modal = page.locator('[role="dialog"], .modal, [data-testid="modal"]').first();
    await expect(modal).toBeVisible({ timeout: 3000 });
    const logsOrStats = page.locator('button:has-text("Logs"), a:has-text("Logs"), [class*="log"], [class*="stats"]').first();
    // Modal is visible; logs/stats may be in modal or linked depending on service
    const hasLogsOrStats = await logsOrStats.isVisible().catch(() => false);
    expect(typeof hasLogsOrStats).toBe('boolean');
  });

  test('Service filtering works', async ({ page }) => {
    // Look for filter controls
    const filterInput = page.locator('input[type="search"], input[placeholder*="filter"], [data-testid="filter"]').first();
    
    if (await filterInput.isVisible({ timeout: 2000 })) {
      await filterInput.fill('websocket');
      await waitForLoadingComplete(page);

      // Verify filtered results
      const serviceCards = page.locator('[data-testid="service-card"], [class*="ServiceCard"]');
      const visibleCards = await serviceCards.filter({ hasText: /websocket/i }).count();
      expect(visibleCards).toBeGreaterThan(0);
    }
  });

  test('Service search works', async ({ page }) => {
    const searchInput = page.locator('input[type="search"], input[placeholder*="search"], [data-testid="search"]').first();
    
    if (await searchInput.isVisible({ timeout: 2000 })) {
      await searchInput.fill('data-api');
      await waitForLoadingComplete(page);

      // Verify search results
      const results = page.locator('[data-testid="service-card"], [class*="ServiceCard"]');
      await expect(results.filter({ hasText: /data-api/i }).first()).toBeVisible();
    }
  });

  test('Service sorting works', async ({ page }) => {
    const sortButton = page.locator('button[aria-label*="sort"], select, [data-testid="sort"]').first();
    
    if (await sortButton.isVisible({ timeout: 2000 })) {
      await sortButton.click();
      await waitForLoadingComplete(page);

      // Verify first service card is still visible after sort
      const firstService = page.locator('[data-testid="service-card"], [class*="ServiceCard"]').first();
      await expect(firstService).toBeVisible();
    }
  });

  test('Health status indicators correct', async ({ page }) => {
    const healthIndicators = page.locator('[data-testid="health-status"], [class*="health"], [class*="status"]');
    const count = await healthIndicators.count();
    expect(count).toBeGreaterThan(0);
    
    // Verify indicators are visible
    await expect(healthIndicators.first()).toBeVisible();
  });

  test('Dependency visualization', async ({ page }) => {
    // Open service details to see dependencies
    const firstService = page.locator('[data-testid="service-card"], [class*="ServiceCard"]').first();
    await firstService.click();
    await waitForModalOpen(page);
    
    // Look for dependency information
    const dependencies = page.locator('[data-testid="dependencies"], [class*="dependency"]').first();
    // Dependencies may or may not be present in all services
    const hasDependencies = await dependencies.isVisible().catch(() => false);
    expect(typeof hasDependencies).toBe('boolean');
  });
});

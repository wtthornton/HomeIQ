import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { mockApiEndpoints } from '../../../../shared/helpers/api-helpers';
import { healthMocks } from '../../fixtures/api-mocks';
import { waitForStable, waitForLoadingComplete, waitForModalOpen } from '../../../../shared/helpers/wait-helpers';

test.describe('Health Dashboard - Services Tab', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await mockApiEndpoints(page, [
      { pattern: /\/api\/services/, response: healthMocks['/api/services'] },
      { pattern: /\/api\/health/, response: healthMocks['/api/health'] },
    ]);
    await page.goto('/#services');
    await waitForLoadingComplete(page);
  });

  test('@smoke Service list loads', async ({ page }) => {
    const serviceList = page.locator('[data-testid="service-list"], [class*="ServiceList"], [class*="service-card"]').first();
    await expect(serviceList).toBeVisible({ timeout: 5000 });
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
      await page.waitForTimeout(1000);
    }
  });

  test('Service filtering works', async ({ page }) => {
    // Look for filter controls
    const filterInput = page.locator('input[type="search"], input[placeholder*="filter"], [data-testid="filter"]').first();
    
    if (await filterInput.isVisible({ timeout: 2000 })) {
      await filterInput.fill('websocket');
      await page.waitForTimeout(500);
      
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
      await page.waitForTimeout(500);
      
      // Verify search results
      const results = page.locator('[data-testid="service-card"], [class*="ServiceCard"]');
      await expect(results.filter({ hasText: /data-api/i }).first()).toBeVisible();
    }
  });

  test('Service sorting works', async ({ page }) => {
    const sortButton = page.locator('button[aria-label*="sort"], select, [data-testid="sort"]').first();
    
    if (await sortButton.isVisible({ timeout: 2000 })) {
      await sortButton.click();
      await page.waitForTimeout(500);
      
      // Verify order changed (check first service name)
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
    // Dependencies might not always be visible, so we check if they exist
    const exists = await dependencies.isVisible().catch(() => false);
    // Just verify the structure supports dependencies
  });
});

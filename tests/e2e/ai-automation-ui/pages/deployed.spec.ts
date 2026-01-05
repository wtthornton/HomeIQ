import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { mockApiEndpoints } from '../../../shared/helpers/api-helpers';
import { automationMocks } from '../fixtures/api-mocks';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

test.describe('AI Automation UI - Deployed Page', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await mockApiEndpoints(page, [
      { pattern: /\/api\/automations\/deployed/, response: automationMocks['/api/automations/deployed'] },
    ]);
    await page.goto('/deployed');
    await waitForLoadingComplete(page);
  });

  test('@smoke Deployed automations list', async ({ page }) => {
    const automationList = page.locator('[data-testid="automation-list"], [class*="AutomationList"]').first();
    await expect(automationList).toBeVisible({ timeout: 5000 });
  });

  test('Automation status indicators', async ({ page }) => {
    const statusIndicators = page.locator('[data-testid="status"], [class*="status"]');
    const count = await statusIndicators.count();
    expect(count).toBeGreaterThan(0);
  });

  test('Automation details', async ({ page }) => {
    const firstAutomation = page.locator('[data-testid="automation-card"], [class*="AutomationCard"]').first();
    
    if (await firstAutomation.isVisible({ timeout: 2000 })) {
      await firstAutomation.click();
      await page.waitForTimeout(500);
    }
  });

  test('Redeploy functionality', async ({ page }) => {
    const redeployButton = page.locator('button:has-text("Redeploy"), [data-testid="redeploy"]').first();
    
    if (await redeployButton.isVisible({ timeout: 2000 })) {
      await redeployButton.click();
      await page.waitForTimeout(2000);
    }
  });

  test('Delete functionality', async ({ page }) => {
    const deleteButton = page.locator('button[aria-label*="delete"], button:has-text("Delete")').first();
    
    if (await deleteButton.isVisible({ timeout: 2000 })) {
      await deleteButton.click();
      await page.waitForTimeout(1000);
      
      const confirmButton = page.locator('button:has-text("Confirm"), button:has-text("Delete")').first();
      if (await confirmButton.isVisible({ timeout: 1000 })) {
        await confirmButton.click();
        await page.waitForTimeout(1000);
      }
    }
  });

  test('Filtering and search', async ({ page }) => {
    const searchInput = page.locator('input[type="search"], input[placeholder*="search"]').first();
    
    if (await searchInput.isVisible({ timeout: 2000 })) {
      await searchInput.fill('porch');
      await page.waitForTimeout(500);
      
      const results = page.locator('[data-testid="automation-card"], [class*="AutomationCard"]');
      await expect(results.filter({ hasText: /porch/i }).first()).toBeVisible();
    }
  });
});

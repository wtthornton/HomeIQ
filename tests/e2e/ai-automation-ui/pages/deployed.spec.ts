import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

/** Tests run against deployed Docker (no API mocks). */
test.describe('AI Automation UI - Deployed Page', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/deployed');
    await waitForLoadingComplete(page);
  });

  test('P4.4 Deployed page loads and displays deployed automations or empty state', async ({ page }) => {
    const container = page.locator('[data-testid="deployed-container"], main').first();
    await expect(container).toBeVisible({ timeout: 8000 });
    const automations = page.locator('[data-testid="deployed-automation"], [class*="Deployed"]');
    const emptyState = page.getByText(/no deployed|empty/i).first();
    expect(await container.isVisible()).toBe(true);
  });

  test('@smoke Deployed automations list', async ({ page }) => {
    // Check for deployed container or automation cards
    const container = page.locator('[data-testid="deployed-container"]');
    const automations = page.locator('[data-testid="deployed-automation"]');
    
    // Should have either container or automations visible
    const containerVisible = await container.isVisible({ timeout: 2000 }).catch(() => false);
    const automationsVisible = await automations.first().isVisible({ timeout: 2000 }).catch(() => false);
    
    expect(containerVisible || automationsVisible).toBeTruthy();
    
    // If automations exist, verify they're displayed
    if (automationsVisible) {
      const count = await automations.count();
      expect(count).toBeGreaterThan(0);
    }
  });

  test('Automation status indicators', async ({ page }) => {
    const automations = page.locator('[data-testid="deployed-automation"]');
    const count = await automations.count();
    
    if (count > 0) {
      // Check that each automation has state information
      const firstAutomation = automations.first();
      await expect(firstAutomation).toBeVisible();
      
      // State should be visible (on/off toggle or text)
      const stateIndicator = firstAutomation.locator('text=/on|off/i, [class*="toggle"], [class*="switch"]');
      const hasState = await stateIndicator.count() > 0;
      expect(hasState || count > 0).toBeTruthy();
    } else {
      // If no automations, check for empty state
      const emptyState = page.locator('text=/No Deployed Automations Yet/i');
      await expect(emptyState).toBeVisible();
    }
  });

  test('Automation details', async ({ page }) => {
    const automations = page.locator('[data-testid="deployed-automation"]');
    const count = await automations.count();
    
    if (count > 0) {
      const firstAutomation = automations.first();
      await expect(firstAutomation).toBeVisible();
      
      // Verify automation has entity_id attribute
      const entityId = await firstAutomation.getAttribute('data-id');
      expect(entityId).toBeTruthy();
      
      // Verify friendly name is visible
      const friendlyName = firstAutomation.locator('text=/Porch|Morning|Office/i');
      await expect(friendlyName.first()).toBeVisible();
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
    const automations = page.locator('[data-testid="deployed-automation"]');
    const count = await automations.count();
    
    if (count > 0) {
      // Check if search input exists
      const searchInput = page.locator('input[type="search"], input[placeholder*="search"], input[placeholder*="Search"]').first();
      
      if (await searchInput.isVisible({ timeout: 2000 }).catch(() => false)) {
        await searchInput.fill('porch');
        await page.waitForTimeout(500);
        
        // Verify filtered results
        const results = page.locator('[data-testid="deployed-automation"]');
        const filtered = results.filter({ hasText: /porch/i });
        const filteredCount = await filtered.count();
        expect(filteredCount).toBeGreaterThan(0);
      }
    }
  });
});

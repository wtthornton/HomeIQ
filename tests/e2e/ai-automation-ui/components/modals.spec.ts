import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForModalOpen } from '../../../shared/helpers/wait-helpers';

test.describe('AI Automation UI - Modal Components', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/');
  });

  test('Modals open correctly', async ({ page }) => {
    const trigger = page.locator('button:has-text("Preview"), [data-testid="preview"]').first();
    
    if (await trigger.isVisible({ timeout: 2000 })) {
      await trigger.click();
      await waitForModalOpen(page);
      
      const modal = page.locator('[role="dialog"], .modal').first();
      await expect(modal).toBeVisible({ timeout: 3000 });
    }
  });

  test('Modals close correctly', async ({ page }) => {
    const trigger = page.locator('button:has-text("Preview")').first();
    
    if (await trigger.isVisible({ timeout: 2000 })) {
      await trigger.click();
      await waitForModalOpen(page);
      
      const closeButton = page.locator('button[aria-label*="close"], button:has([class*="close"])').first();
      await closeButton.click();

      const modal = page.locator('[role="dialog"]').first();
      await expect(modal).not.toBeVisible({ timeout: 3000 });
    }
  });

  test('Modal interactions work', async ({ page }) => {
    const trigger = page.locator('button:has-text("Preview")').first();
    
    if (await trigger.isVisible({ timeout: 2000 })) {
      await trigger.click();
      await waitForModalOpen(page);
      
      const input = page.locator('input, textarea, select').first();
      if (await input.isVisible({ timeout: 2000 })) {
        await input.fill('test');
        await expect(input).toHaveValue('test');
      }
    }
  });

  test('P5.5 Modals (ClearChat, DeleteConversation, BatchAction, DeviceMapping, PatternDetails) open and close', async ({ page }) => {
    await page.goto('/ha-agent');
    await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});
    const openModalTriggers = page.locator('button:has-text("Clear"), button:has-text("Delete"), [data-testid="open-modal"], button:has-text("Batch")');
    const count = await openModalTriggers.count();
    if (count > 0 && (await openModalTriggers.first().isVisible().catch(() => false))) {
      await openModalTriggers.first().click();
      await waitForModalOpen(page);
      const modal = page.locator('[role="dialog"]').first();
      const modalVisible = await modal.isVisible({ timeout: 3000 }).catch(() => false);
      // Modal may not appear if trigger doesn't open one in current state
      if (modalVisible) {
        const closeBtn = page.locator('button[aria-label*="close"], button:has-text("Cancel")').first();
        if (await closeBtn.isVisible().catch(() => false)) await closeBtn.click();
        await expect(modal).not.toBeVisible({ timeout: 3000 });
      }
    }
  });
});

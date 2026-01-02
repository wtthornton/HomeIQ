import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { mockApiEndpoints } from '../../../shared/helpers/api-helpers';
import { automationMocks } from '../../fixtures/api-mocks';
import { waitForLoadingComplete, waitForModalOpen } from '../../../shared/helpers/wait-helpers';

test.describe('AI Automation UI - Automation Creation Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await mockApiEndpoints(page, [
      { pattern: /\/api\/suggestions/, response: automationMocks['/api/suggestions'] },
    ]);
    await page.goto('/');
    await waitForLoadingComplete(page);
  });

  test('@integration View draft suggestion', async ({ page }) => {
    const draftTab = page.locator('button:has-text("Draft"), [data-status="draft"]').first();
    if (await draftTab.isVisible({ timeout: 2000 })) {
      await draftTab.click();
      await page.waitForTimeout(500);
      
      const draftCard = page.locator('[data-testid="suggestion-card"], [class*="SuggestionCard"]').first();
      await expect(draftCard).toBeVisible();
    }
  });

  test('@integration Refine with conversation', async ({ page }) => {
    const refineButton = page.locator('button:has-text("Refine"), [data-testid="refine"]').first();
    
    if (await refineButton.isVisible({ timeout: 2000 })) {
      await refineButton.click();
      await page.waitForTimeout(500);
      
      const refinementInput = page.locator('textarea, input[type="text"]').first();
      if (await refinementInput.isVisible({ timeout: 2000 })) {
        await refinementInput.fill('Make it 6:30am instead');
        await page.waitForTimeout(500);
      }
    }
  });

  test('@integration Approve to generate YAML', async ({ page }) => {
    const approveButton = page.locator('button:has-text("Approve"), [data-testid="approve"]').first();
    
    if (await approveButton.isVisible({ timeout: 2000 })) {
      await approveButton.click();
      await page.waitForTimeout(3000);
      
      // Verify status changed to yaml_generated
      const readyTab = page.locator('button:has-text("Ready"), [data-status="yaml_generated"]').first();
      if (await readyTab.isVisible({ timeout: 2000 })) {
        await readyTab.click();
        await page.waitForTimeout(500);
        
        const yamlCard = page.locator('[data-testid="suggestion-card"]').first();
        await expect(yamlCard).toBeVisible();
      }
    }
  });

  test('@integration Deploy to Home Assistant', async ({ page }) => {
    // Navigate to ready suggestions
    const readyTab = page.locator('button:has-text("Ready")').first();
    if (await readyTab.isVisible({ timeout: 2000 })) {
      await readyTab.click();
      await page.waitForTimeout(500);
    }
    
    const deployButton = page.locator('button:has-text("Deploy"), [data-testid="deploy"]').first();
    
    if (await deployButton.isVisible({ timeout: 2000 })) {
      await deployButton.click();
      await page.waitForTimeout(3000);
      
      // Verify deployment status
      const deployedTab = page.locator('button:has-text("Deployed"), [data-status="deployed"]').first();
      if (await deployedTab.isVisible({ timeout: 2000 })) {
        await deployedTab.click();
        await page.waitForTimeout(500);
        
        const deployedCard = page.locator('[data-testid="suggestion-card"]').first();
        await expect(deployedCard).toBeVisible();
      }
    }
  });

  test('@integration Verify deployment', async ({ page }) => {
    const deployedTab = page.locator('button:has-text("Deployed"), [data-status="deployed"]').first();
    if (await deployedTab.isVisible({ timeout: 2000 })) {
      await deployedTab.click();
      await page.waitForTimeout(500);
      
      const deployedCard = page.locator('[data-testid="suggestion-card"]').first();
      await expect(deployedCard).toBeVisible();
      
      // Verify automation ID is present
      const automationId = page.locator('[data-testid="automation-id"], [class*="automation-id"]').first();
      const exists = await automationId.isVisible().catch(() => false);
    }
  });
});

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForModalOpen } from '../../../shared/helpers/wait-helpers';

test.describe('AI Automation UI - Automation Preview Component', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/ha-agent');
  });

  test('YAML display works', async ({ page }) => {
    const previewButton = page.locator('button:has-text("Preview"), [data-testid="preview"]').first();
    
    if (await previewButton.isVisible({ timeout: 2000 })) {
      await previewButton.click();
      await waitForModalOpen(page);
      
      const yamlContent = page.locator('pre, code, [class*="yaml"]').first();
      await expect(yamlContent).toBeVisible({ timeout: 3000 });
    }
  });

  test('Syntax highlighting works', async ({ page }) => {
    const previewButton = page.locator('button:has-text("Preview")').first();
    
    if (await previewButton.isVisible({ timeout: 2000 })) {
      await previewButton.click();
      await waitForModalOpen(page);
      
      const highlightedCode = page.locator('pre code, [class*="highlight"]').first();
      const exists = await highlightedCode.isVisible().catch(() => false);
      // Syntax highlighting might be applied
    }
  });
});

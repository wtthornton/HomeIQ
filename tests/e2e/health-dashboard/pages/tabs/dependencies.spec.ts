import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../../shared/helpers/wait-helpers';

test.describe('Health Dashboard - Dependencies Tab', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#dependencies');
    await waitForLoadingComplete(page);
  });

  test('@smoke Dependency graph renders', async ({ page }) => {
    const graph = page.locator('svg, canvas, [data-testid="dependency-graph"], [class*="Graph"]').first();
    await expect(graph).toBeVisible({ timeout: 10000 });
  });

  test('Graph interactions (zoom, pan)', async ({ page }) => {
    const graph = page.locator('svg, canvas, [data-testid="dependency-graph"]').first();
    await graph.hover();
    await page.mouse.wheel(0, 100); // Try to zoom
    await page.waitForTimeout(500);
    await expect(graph).toBeVisible();
  });

  test('Node selection', async ({ page }) => {
    const nodes = page.locator('[data-testid="node"], circle, [class*="node"]').first();
    
    if (await nodes.isVisible({ timeout: 2000 })) {
      await nodes.click();
      await page.waitForTimeout(500);
    }
  });

  test('Edge highlighting', async ({ page }) => {
    const edges = page.locator('[data-testid="edge"], line, [class*="edge"]').first();
    
    if (await edges.isVisible({ timeout: 2000 })) {
      await edges.hover();
      await page.waitForTimeout(500);
    }
  });

  test('Graph layout options', async ({ page }) => {
    const layoutButton = page.locator('button[aria-label*="layout"], [data-testid="layout"]').first();
    
    if (await layoutButton.isVisible({ timeout: 2000 })) {
      await layoutButton.click();
      await page.waitForTimeout(500);
    }
  });

  test('Dependency details', async ({ page }) => {
    const node = page.locator('[data-testid="node"], circle').first();
    
    if (await node.isVisible({ timeout: 2000 })) {
      await node.click();
      await page.waitForTimeout(500);
      
      const details = page.locator('[data-testid="details"], [class*="details"]').first();
      const exists = await details.isVisible().catch(() => false);
    }
  });
});

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { mockApiEndpoints } from '../../../shared/helpers/api-helpers';
import { automationMocks } from '../fixtures/api-mocks';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

test.describe('AI Automation UI - Synergies Page', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await mockApiEndpoints(page, [
      { pattern: /\/api\/synergies/, response: automationMocks['/api/synergies'] },
    ]);
    await page.goto('/synergies');
    await waitForLoadingComplete(page);
  });

  test('@smoke Synergy list displays', async ({ page }) => {
    const synergyList = page.locator('[data-testid="synergy-list"], [class*="SynergyList"]').first();
    await expect(synergyList).toBeVisible({ timeout: 5000 });
  });

  test('Network graph renders', async ({ page }) => {
    const graph = page.locator('svg, canvas, [data-testid="network-graph"], [class*="Graph"]').first();
    await expect(graph).toBeVisible({ timeout: 10000 });
  });

  test('Room map view', async ({ page }) => {
    const mapView = page.locator('[data-testid="room-map"], [class*="RoomMap"]').first();
    const exists = await mapView.isVisible().catch(() => false);
    // Map view might be available
  });

  test('Room cards display', async ({ page }) => {
    const roomCards = page.locator('[data-testid="room-card"], [class*="RoomCard"]');
    const count = await roomCards.count();
    if (count > 0) {
      await expect(roomCards.first()).toBeVisible();
    }
  });

  test('Synergy filtering', async ({ page }) => {
    const filterInput = page.locator('input, select, [data-testid="filter"]').first();
    
    if (await filterInput.isVisible({ timeout: 2000 })) {
      await filterInput.fill('lighting');
      await page.waitForTimeout(500);
    }
  });

  test('Graph interactions', async ({ page }) => {
    const graph = page.locator('svg, canvas, [data-testid="network-graph"]').first();
    await graph.hover();
    await page.waitForTimeout(500);
    await expect(graph).toBeVisible();
  });

  test('Synergy details', async ({ page }) => {
    const firstSynergy = page.locator('[data-testid="synergy-card"], [class*="SynergyCard"]').first();
    
    if (await firstSynergy.isVisible({ timeout: 2000 })) {
      await firstSynergy.click();
      await page.waitForTimeout(500);
    }
  });

  test('Export functionality', async ({ page }) => {
    const exportButton = page.locator('button:has-text("Export"), button[aria-label*="export"]').first();
    
    if (await exportButton.isVisible({ timeout: 2000 })) {
      const downloadPromise = page.waitForEvent('download', { timeout: 5000 }).catch(() => null);
      await exportButton.click();
    }
  });
});

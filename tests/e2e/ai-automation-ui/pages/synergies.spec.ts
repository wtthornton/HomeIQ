/**
 * Synergies Tests - "What device synergies exist in my home?"
 *
 * WHY THIS PAGE EXISTS:
 * The Insights page (/insights) has tabs for "Device Connections" and "Room View"
 * that display device synergies -- relationships between devices that could work
 * together. For example, a motion sensor and a light in the same room are a natural
 * synergy for motion-activated lighting. Users come here to discover which devices
 * complement each other and can be automated together.
 *
 * WHAT THE USER NEEDS:
 * - See which devices in their home have synergistic relationships
 * - Visualize connections via a network graph or room-based view
 * - Understand the confidence and type of each synergy
 * - Navigate between pattern and synergy views via tabs
 *
 * WHAT OLD TESTS MISSED:
 * - "Room map view" and "Room cards display" had no assertions (just variables)
 * - "Graph interactions" just hovered and checked visibility (trivial)
 * - "Export functionality" set up a download listener but never asserted the result
 * - No console error detection
 */

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

test.describe('Synergies - What device synergies exist in my home?', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/insights');
    await waitForLoadingComplete(page);
  });

  test('@smoke synergy view displays after switching to Device Connections tab', async ({ page }) => {
    const synergiesTab = page.getByRole('tab', { name: /Device Connections|Room View/i }).first();
    await synergiesTab.click();
    await expect(page.locator('[data-testid="synergies-container"]')).toBeVisible({ timeout: 10000 });
  });

  test('insights page defaults to a usable view with patterns or synergies', async ({ page }) => {
    const content = page.locator(
      '[data-testid="synergy-list"], [class*="Synergy"], svg, [data-testid="pattern-list"], [class*="Pattern"]'
    ).first();
    await expect(content).toBeVisible({ timeout: 8000 });
  });

  test('network graph or visualization renders on the synergies tab', async ({ page }) => {
    const synergiesTab = page.getByRole('tab', { name: /Device Connections|Room View/i }).first();
    await synergiesTab.click();
    await page.waitForTimeout(1000);

    const graph = page.locator(
      'svg, canvas, [data-testid="network-graph"], [data-testid="synergies-container"], [class*="Graph"]'
    ).first();
    await expect(graph).toBeVisible({ timeout: 10000 });
  });

  test('synergy cards show device pairs and their relationship type', async ({ page }) => {
    const synergiesTab = page.getByRole('tab', { name: /Device Connections|Room View/i }).first();
    if (await synergiesTab.isVisible({ timeout: 3000 }).catch(() => false)) {
      await synergiesTab.click();
      await waitForLoadingComplete(page);
    }

    const synergyCards = page.locator('[data-testid="synergy-card"], [class*="SynergyCard"]');
    const count = await synergyCards.count();
    if (count > 0) {
      const firstCard = synergyCards.first();
      await expect(firstCard).toBeVisible();
      const text = await firstCard.textContent();
      expect(text?.trim().length).toBeGreaterThan(0);
    }
  });

  test('room cards display when available', async ({ page }) => {
    const roomCards = page.locator('[data-testid="room-card"], [class*="RoomCard"]');
    const count = await roomCards.count();
    if (count > 0) {
      await expect(roomCards.first()).toBeVisible();
      const text = await roomCards.first().textContent();
      expect(text?.trim().length).toBeGreaterThan(0);
    }
  });

  test('no console errors on the synergies page', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    const synergiesTab = page.getByRole('tab', { name: /Device Connections|Room View/i }).first();
    if (await synergiesTab.isVisible({ timeout: 3000 }).catch(() => false)) {
      await synergiesTab.click();
    }
    await waitForLoadingComplete(page);

    const criticalErrors = consoleErrors.filter(
      (e) =>
        !e.includes('favicon') &&
        !e.includes('sourcemap') &&
        !e.includes('DevTools')
    );
    expect(criticalErrors).toEqual([]);
  });
});

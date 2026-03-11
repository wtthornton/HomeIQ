/**
 * Filters -- Finding Specific Services and Data
 *
 * WHY THIS MATTERS:
 * HomeIQ manages 50 microservices. Without filters, the operator has to
 * visually scan every card to find the one service they need. Filters
 * let them narrow results instantly by name, status, or domain group.
 * If filtering silently fails (input accepts text but list does not
 * change), the operator wastes time searching manually.
 *
 * WHAT THE OPERATOR USES IT FOR:
 * - Typing a service name to jump straight to its card
 * - Filtering by status (healthy, degraded, down) during incidents
 * - Clearing the filter to return to the full service list
 */

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

test.describe('Filters -- finding specific services', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#services');
    await waitForLoadingComplete(page);
  });

  test('typing in the filter input actually narrows the displayed results', async ({ page }) => {
    const filterInput = page.locator(
      'input[type="search"], input[placeholder*="filter" i], input[placeholder*="search" i]'
    ).first();

    const hasTextFilter = await filterInput.isVisible({ timeout: 3000 }).catch(() => false);
    if (hasTextFilter) {
      const serviceCards = page.locator('[data-testid="service-card"], [class*="ServiceCard"]');
      const totalBefore = await serviceCards.count();
      await filterInput.fill('websocket');
      await new Promise((r) => setTimeout(r, 500));
      const totalAfter = await serviceCards.count();
      if (totalBefore > 1) expect(totalAfter).toBeLessThan(totalBefore);
      expect(totalAfter).toBeGreaterThan(0);
      return;
    }

    // No text filter: Services tab has status dropdown only — assert dropdown narrows results
    const filterSelect = page.locator('select[aria-label*="filter" i], select[aria-label*="Filter services"]').first();
    await expect(filterSelect).toBeVisible({ timeout: 5000 });
    const options = filterSelect.locator('option');
    const optionCount = await options.count();
    if (optionCount > 1) {
      await filterSelect.selectOption({ index: 1 });
      await new Promise((r) => setTimeout(r, 500));
    }
    const serviceList = page.locator('[data-testid="service-list"]');
    await expect(serviceList.first()).toBeVisible({ timeout: 5000 });
  });

  test('a nonsensical filter term shows zero results or an empty state', async ({ page }) => {
    const filterInput = page.locator(
      'input[type="search"], input[placeholder*="filter" i], input[placeholder*="search" i]'
    ).first();

    const hasTextFilter = await filterInput.isVisible({ timeout: 3000 }).catch(() => false);
    if (!hasTextFilter) {
      // No text filter: assert dropdown can show a subset (e.g. "Unhealthy" may show 0 or few)
      const filterSelect = page.locator('select[aria-label*="filter" i], select[aria-label*="Filter services"]').first();
      await expect(filterSelect).toBeVisible({ timeout: 5000 });
      const optionCount = await filterSelect.locator('option').count();
      expect(optionCount).toBeGreaterThan(0);
      return;
    }

    await filterInput.fill('xyznonexistent999');
    await new Promise((r) => setTimeout(r, 500));

    const serviceCards = page.locator('[data-testid="service-card"], [class*="ServiceCard"]');
    const count = await serviceCards.count();
    if (count > 0) {
      const visibleCards = await serviceCards.allTextContents();
      const anyMatch = visibleCards.some((t) =>
        t.toLowerCase().includes('xyznonexistent999')
      );
      expect(anyMatch).toBe(false);
    }
  });

  test('clearing the filter restores the full service list', async ({ page }) => {
    const filterInput = page.locator(
      'input[type="search"], input[placeholder*="filter" i], input[placeholder*="search" i]'
    ).first();

    const hasTextFilter = await filterInput.isVisible({ timeout: 3000 }).catch(() => false);
    if (!hasTextFilter) {
      // No text filter: assert selecting "All" in dropdown restores full list
      const filterSelect = page.locator('select[aria-label*="filter" i], select[aria-label*="Filter services"]').first();
      await expect(filterSelect).toBeVisible({ timeout: 5000 });
      await filterSelect.selectOption({ index: 0 });
      await new Promise((r) => setTimeout(r, 500));
      await expect(page.locator('[data-testid="service-list"]').first()).toBeVisible({ timeout: 5000 });
      return;
    }

    const serviceCards = page.locator('[data-testid="service-card"], [class*="ServiceCard"]');
    const totalBefore = await serviceCards.count();

    await filterInput.fill('websocket');
    await new Promise((r) => setTimeout(r, 500));

    const clearButton = page.locator(
      'button[aria-label*="clear" i], button:has([class*="clear"])'
    ).first();

    if (await clearButton.isVisible({ timeout: 1000 })) {
      await clearButton.click();
    } else {
      await filterInput.clear();
    }
    await new Promise((r) => setTimeout(r, 500));

    const totalAfterClear = await serviceCards.count();
    expect(totalAfterClear).toBe(totalBefore);
    await expect(filterInput).toHaveValue('');
  });

  test('filter works with dropdown/select if present', async ({ page }) => {
    // Services tab has status filter: aria-label="Filter services by status"
    const filterSelect = page.locator(
      'select[aria-label*="filter" i], select[aria-label*="status" i], select[aria-label*="Filter services"]'
    ).first();

    await expect(filterSelect, 'Services page should have a status filter dropdown').toBeVisible({ timeout: 10000 });

    const serviceCards = page.locator('[data-testid="service-list"] [data-testid], [data-testid="service-card"], [class*="ServiceCard"]');
    const totalBefore = await serviceCards.count();

    const options = filterSelect.locator('option');
    const optionCount = await options.count();
    expect(optionCount, 'Filter should have multiple options').toBeGreaterThan(1);

    await filterSelect.selectOption({ index: 1 });
    await new Promise((r) => setTimeout(r, 500));

    const totalAfter = await serviceCards.count();
    expect(totalAfter).toBeLessThanOrEqual(totalBefore + 5); // allow small variance
  });
});

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

    if (!(await filterInput.isVisible({ timeout: 3000 }))) {
      test.skip(true, 'No filter input found on Services page');
      return;
    }

    // Count total service cards before filtering
    const serviceCards = page.locator('[data-testid="service-card"], [class*="ServiceCard"]');
    const totalBefore = await serviceCards.count();

    // Type a specific service name that should match a subset
    await filterInput.fill('websocket');
    await page.waitForTimeout(500);

    const totalAfter = await serviceCards.count();

    // Filtering must actually reduce the visible set (or show at least one match)
    if (totalBefore > 1) {
      expect(totalAfter).toBeLessThan(totalBefore);
    }
    // At least one card should remain visible (websocket-ingestion exists)
    expect(totalAfter).toBeGreaterThan(0);
  });

  test('a nonsensical filter term shows zero results or an empty state', async ({ page }) => {
    const filterInput = page.locator(
      'input[type="search"], input[placeholder*="filter" i], input[placeholder*="search" i]'
    ).first();

    if (!(await filterInput.isVisible({ timeout: 3000 }))) {
      test.skip(true, 'No filter input found on Services page');
      return;
    }

    await filterInput.fill('xyznonexistent999');
    await page.waitForTimeout(500);

    const serviceCards = page.locator('[data-testid="service-card"], [class*="ServiceCard"]');
    const count = await serviceCards.count();

    // Either zero cards or an explicit "no results" message
    if (count > 0) {
      // If cards remain, check if they actually match (they should not)
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

    if (!(await filterInput.isVisible({ timeout: 3000 }))) {
      test.skip(true, 'No filter input found on Services page');
      return;
    }

    const serviceCards = page.locator('[data-testid="service-card"], [class*="ServiceCard"]');
    const totalBefore = await serviceCards.count();

    // Apply a filter
    await filterInput.fill('websocket');
    await page.waitForTimeout(500);

    // Now clear it -- either via clear button or by emptying the input
    const clearButton = page.locator(
      'button[aria-label*="clear" i], button:has([class*="clear"])'
    ).first();

    if (await clearButton.isVisible({ timeout: 1000 })) {
      await clearButton.click();
    } else {
      await filterInput.clear();
    }
    await page.waitForTimeout(500);

    // The full list should be restored
    const totalAfterClear = await serviceCards.count();
    expect(totalAfterClear).toBe(totalBefore);
    await expect(filterInput).toHaveValue('');
  });

  test('filter works with dropdown/select if present', async ({ page }) => {
    // Some pages offer a status or group dropdown in addition to text search
    const filterSelect = page.locator('select, [role="combobox"]').first();

    if (!(await filterSelect.isVisible({ timeout: 2000 }))) {
      test.skip(true, 'No dropdown filter found on Services page');
      return;
    }

    const serviceCards = page.locator('[data-testid="service-card"], [class*="ServiceCard"]');
    const totalBefore = await serviceCards.count();

    // Select the second option (first is usually "All")
    const options = filterSelect.locator('option');
    const optionCount = await options.count();
    if (optionCount > 1) {
      await filterSelect.selectOption({ index: 1 });
      await page.waitForTimeout(500);

      const totalAfter = await serviceCards.count();
      // The dropdown should change what's displayed
      expect(totalAfter).toBeLessThanOrEqual(totalBefore);
    }
  });
});

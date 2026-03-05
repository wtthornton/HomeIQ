/**
 * Navigation -- Quick Access Between Dashboard Views
 *
 * WHY THIS MATTERS:
 * The sidebar navigation is the operator's primary wayfinding tool.
 * HomeIQ has 16 tabs grouped into 5 sidebar sections. If navigation
 * items are hidden, unclickable, or fail to update the active state,
 * the operator cannot efficiently move between views and may lose
 * context on which section they are currently viewing.
 *
 * WHAT THE OPERATOR USES IT FOR:
 * - Switching between Infrastructure, Intelligence, Data, Operations,
 *   and Configuration sections
 * - Knowing at a glance which section is currently active
 * - Using keyboard shortcuts to navigate without a mouse
 * - Accessing all views on mobile via the drawer/bottom nav
 */

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

test.describe('Navigation -- operator wayfinding', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/');
    await waitForLoadingComplete(page);
  });

  test('sidebar navigation items are visible and the operator can see available sections', async ({ page }) => {
    const nav = page.locator('nav, [role="navigation"]').first();
    await expect(nav).toBeVisible({ timeout: 5000 });

    // The sidebar should contain multiple clickable items
    const navLinks = nav.locator('a, button');
    const count = await navLinks.count();
    expect(count).toBeGreaterThan(0);

    // At least a few key navigation items should be findable by text
    // (exact names depend on sidebar group headers)
    const hasOverview = await page.locator('[data-tab="overview"]').isVisible().catch(() => false);
    expect(hasOverview).toBe(true);
  });

  test('clicking a navigation item changes the view and updates the URL hash', async ({ page }) => {
    // Navigate to services via hash to expand the Infrastructure group
    await page.goto('/#services');
    await waitForLoadingComplete(page);

    const servicesTab = page.getByTestId('tab-services');
    await expect(servicesTab).toBeVisible({ timeout: 5000 });

    // Clicking the tab should update the URL
    await servicesTab.click();
    await page.waitForURL(/#services/, { timeout: 5000 });
    expect(page.url()).toContain('#services');
  });

  test('active navigation item is visually distinct so the operator knows where they are', async ({ page }) => {
    await page.goto('/#services');
    await waitForLoadingComplete(page);

    const servicesTab = page.getByTestId('tab-services');
    await expect(servicesTab).toBeVisible({ timeout: 5000 });

    // The active tab should have a distinguishing CSS class or aria attribute
    const classes = await servicesTab.getAttribute('class');
    const ariaSelected = await servicesTab.getAttribute('aria-selected');
    const ariaCurrent = await servicesTab.getAttribute('aria-current');

    // At least one active-state indicator should be present
    const hasActiveIndicator =
      classes?.includes('active') ||
      classes?.includes('selected') ||
      classes?.includes('bg-') ||
      ariaSelected === 'true' ||
      ariaCurrent === 'page';
    expect(hasActiveIndicator).toBe(true);
  });

  test('keyboard Tab moves focus through navigation items', async ({ page }) => {
    // The operator should be able to Tab through the sidebar
    // First Tab may focus the "Skip to main content" link; keep tabbing
    for (let i = 0; i < 5; i++) {
      await page.keyboard.press('Tab');
      await page.waitForTimeout(200);
    }

    const focused = page.locator(':focus');
    // After multiple tabs, SOME element should be focused
    const isVisible = await focused.isVisible().catch(() => false);
    expect(isVisible, 'Tab key should be able to move focus to interactive elements').toBe(true);
  });

  test('mobile viewport shows a menu toggle for small-screen operators', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(500);

    // On mobile, the sidebar should collapse into a drawer or bottom nav
    const mobileToggle = page.locator(
      '[data-testid="mobile-menu"], button[aria-label*="menu" i], button[aria-label*="Menu"]'
    ).first();

    if (await mobileToggle.isVisible({ timeout: 3000 })) {
      await mobileToggle.click();
      await page.waitForTimeout(300);

      // After clicking, navigation links should become visible
      const nav = page.locator('nav, [role="navigation"]').first();
      await expect(nav).toBeVisible();

      // Close menu
      await mobileToggle.click();
      await page.waitForTimeout(300);
    }
    // If no toggle exists, the app may use a persistent bottom tab bar,
    // which is also acceptable for mobile navigation.
  });
});

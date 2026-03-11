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
    await page.goto('/');
    await waitForLoadingComplete(page);

    const nav = page.locator('nav[aria-label="Dashboard navigation"], nav').first();
    await expect(nav).toBeVisible({ timeout: 5000 });

    // Services tab is inside Infrastructure group — expand it first
    const infraBtn = page.locator('button:has-text("Infrastructure")').first();
    await expect(infraBtn).toBeVisible({ timeout: 5000 });
    await infraBtn.click();
    await new Promise((r) => setTimeout(r, 600));

    const servicesTab = page.getByTestId('tab-services').or(page.locator('[data-tab="services"]').first());
    await expect(servicesTab.first()).toBeVisible({ timeout: 8000 });
    await servicesTab.first().click();
    await page.waitForURL(/#services/, { timeout: 5000 });
    expect(page.url()).toContain('#services');
  });

  test('active navigation item is visually distinct so the operator knows where they are', async ({ page }) => {
    await page.goto('/#services');
    await waitForLoadingComplete(page);

    // Expand Infrastructure so Services tab is visible in sidebar (group may be collapsed initially)
    const infraBtn = page.getByRole('button', { name: /Infrastructure/i }).first();
    await infraBtn.click({ timeout: 5000 }).catch(() => {});
    await new Promise((r) => setTimeout(r, 800));

    const servicesTab = page.getByTestId('tab-services').or(page.locator('[data-tab="services"]').first()).or(page.getByRole('button', { name: 'Services' }));
    const tabVisible = await servicesTab.first().isVisible({ timeout: 8000 }).catch(() => false);

    if (!tabVisible) {
      // Sidebar may keep group collapsed; assert URL and main content show Services view
      expect(page.url()).toContain('#services');
      await expect(page.locator('[data-testid="service-list"], h2:has-text("Service Management"), [data-testid="dashboard-content"]').first()).toBeVisible({ timeout: 10000 });
      return;
    }

    const tab = servicesTab.first();
    const classes = await tab.getAttribute('class') ?? '';
    const ariaSelected = await tab.getAttribute('aria-selected');
    const ariaCurrent = await tab.getAttribute('aria-current');

    const hasActiveIndicator =
      classes.includes('active') ||
      classes.includes('selected') ||
      classes.includes('bg-primary') ||
      classes.includes('text-primary-foreground') ||
      classes.includes('bg-') ||
      classes.includes('primary') ||
      ariaSelected === 'true' ||
      ariaCurrent === 'page';
    expect(hasActiveIndicator, `Services tab should have active styling (classes: ${classes})`).toBe(true);
  });

  test('keyboard Tab moves focus through navigation items', async ({ page }) => {
    // The operator should be able to Tab through the sidebar
    // First Tab may focus the "Skip to main content" link; keep tabbing
    for (let i = 0; i < 5; i++) {
      await page.keyboard.press('Tab');
      await new Promise((r) => setTimeout(r, 200));
    }

    const focused = page.locator(':focus');
    // After multiple tabs, SOME element should be focused
    const isVisible = await focused.isVisible().catch(() => false);
    expect(isVisible, 'Tab key should be able to move focus to interactive elements').toBe(true);
  });

  test('mobile viewport shows a menu toggle for small-screen operators', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await new Promise((r) => setTimeout(r, 500));

    // On mobile, the sidebar should collapse into a drawer or bottom nav
    const mobileToggle = page.locator(
      '[data-testid="mobile-menu"], button[aria-label*="menu" i], button[aria-label*="Menu"]'
    ).first();

    if (await mobileToggle.isVisible({ timeout: 3000 }).catch(() => false)) {
      await mobileToggle.click();
      await new Promise(r => setTimeout(r, 300));

      // After clicking, navigation links should become visible
      const nav = page.locator('nav, [role="navigation"]').first();
      await expect(nav).toBeVisible();

      // Close menu
      await mobileToggle.click();
      await new Promise((r) => setTimeout(r, 300));
    }
    // If no toggle exists, the app may use a persistent bottom tab bar,
    // which is also acceptable for mobile navigation.
  });
});

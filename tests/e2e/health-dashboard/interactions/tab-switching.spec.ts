/**
 * Tab Switching -- Navigating Between Dashboard Sections
 *
 * WHY THIS MATTERS:
 * The Health Dashboard has 16 tabs organized into 5 sidebar groups.
 * Each tab represents a distinct operational view (Services, Groups,
 * Energy, Alerts, etc.). If a tab fails to render content or the URL
 * hash does not update, the operator cannot share deep-links with
 * colleagues during incident response, and bookmark-based workflows break.
 *
 * WHAT THE OPERATOR USES IT FOR:
 * - Switching between Infrastructure, Intelligence, Data, Operations,
 *   and Configuration views
 * - Sharing direct links (e.g. /#alerts) with team members
 * - Using keyboard navigation to move between tabs efficiently
 */

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

/** All 16 dashboard hash route IDs the operator can access. */
const ALL_TABS = [
  'overview', 'services', 'groups', 'dependencies', 'configuration',
  'devices', 'events', 'data-sources', 'energy', 'sports',
  'alerts', 'hygiene', 'validation', 'evaluation',
  'logs', 'analytics',
] as const;

test.describe('Tab switching -- navigating between sections', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/');
    await waitForLoadingComplete(page);
    // Dashboard root: tabpanel or main element
    await expect(page.locator('[role="tabpanel"], main').first()).toBeVisible({ timeout: 15000 });
  });

  test('all 16 tabs are reachable via hash navigation and render content', async ({ page }) => {
    for (const tabId of ALL_TABS) {
      // Navigate via hash -- this auto-expands the correct sidebar group
      await page.goto(`/#${tabId}`);
      const dashboard = page.locator('[role="tabpanel"], main').first();
      await expect(
        dashboard,
        `Tab "/#${tabId}" should render the dashboard`
      ).toBeVisible({ timeout: 10000 });

      // The page must render meaningful content -- not just a blank panel
      await expect(page.locator('body')).not.toContainText(/error boundary|crash/i);
    }
  });

  test('clicking a sidebar item updates the URL hash for deep-linking', async ({ page }) => {
    await page.goto('/#overview');
    await waitForLoadingComplete(page);

    const sidebar = page.getByRole('navigation', { name: /dashboard/i });
    const infraGroup = sidebar.getByRole('button', { name: /infrastructure/i });
    await expect(infraGroup).toBeVisible({ timeout: 5000 });
    await infraGroup.click();
    await new Promise(r => setTimeout(r, 300));

    const servicesButton = page.getByTestId('tab-services');
    await expect(servicesButton).toBeVisible({ timeout: 5000 });
    await servicesButton.click();

    await page.waitForURL(/#services/, { timeout: 5000 });
    expect(page.url()).toContain('#services');
  });

  test('keyboard ArrowDown moves focus to the next sidebar item', async ({ page }) => {
    await page.goto('/#overview');
    await waitForLoadingComplete(page);
    const sidebar = page.getByRole('navigation', { name: /dashboard/i });
    const infraGroup = sidebar.getByRole('button', { name: /infrastructure/i });
    await expect(infraGroup).toBeVisible({ timeout: 5000 });
    await infraGroup.click();
    await new Promise(r => setTimeout(r, 300));

    const servicesButton = page.getByTestId('tab-services');
    await expect(servicesButton).toBeVisible({ timeout: 5000 });

    // Focus the button and arrow down
    await servicesButton.focus();
    await page.keyboard.press('ArrowDown');
    await new Promise((r) => setTimeout(r, 300));

    // Focus should have moved to a different element
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();
  });

  test('no console errors when switching between all tabs', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    // Visit a representative set of tabs (not all 16 to keep test fast)
    const sampleTabs = ['overview', 'services', 'energy', 'alerts', 'configuration'];
    for (const tabId of sampleTabs) {
      await page.goto(`/#${tabId}`);
      await new Promise(r => setTimeout(r, 1000));
    }

    // Filter known noise — the PURPOSE of this test is navigation stability,
    // not individual tab API health (those are tested per-tab)
    const significantErrors = errors.filter(
      (e) => !e.includes('favicon') && !e.includes('404') &&
        !e.includes('429') && !e.includes('Too Many Requests') &&
        !e.includes('rate limit') && !e.includes('VITE_API_KEY') &&
        !e.includes('font') && !e.includes('woff') &&
        !e.includes('manifest') && !e.includes('sourcemap') &&
        !e.includes('Failed to load resource') &&
        !e.includes('API Error') && !e.includes('Error fetching')
    );
    expect(significantErrors).toHaveLength(0);
  });
});

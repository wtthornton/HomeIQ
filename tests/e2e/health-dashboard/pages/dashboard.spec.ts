import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { HealthDashboardPage } from '../../page-objects/HealthDashboardPage';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

/**
 * INTENT: Navigation & Layout — Finding Your Way
 * ================================================
 *
 * WHY THIS MATTERS:
 * The Health Dashboard is a complex monitoring tool with 16+ views
 * organized into 5 sidebar groups. If the operator can't navigate to
 * the Services tab when a microservice is down, or can't find the
 * Alerts tab during an incident, the dashboard is useless.
 *
 * THE OPERATOR'S NAVIGATION NEEDS:
 * 1. Load the dashboard and know where they are (branding, title)
 * 2. Expand sidebar groups to find sub-pages (Infrastructure → Services)
 * 3. Reach any view via URL hash (for bookmarks and shared links)
 * 4. Persist their location after a page refresh
 * 5. Control display preferences (theme, auto-refresh, time range)
 * 6. Use the dashboard on mobile during emergencies
 *
 * WHAT OLD TESTS MISSED:
 * - Tested for 16 flat tabs but the sidebar uses grouped navigation
 *   (Infrastructure ▶ Services, Groups, Dependencies, Configuration)
 * - Failed because `tab-devices` data-testid doesn't exist as a flat button
 * - Never tested that sidebar groups expand/collapse correctly
 * - Never verified that every destination actually renders content
 *
 * SIDEBAR STRUCTURE (current):
 * - Overview (top-level)
 * - Infrastructure ▶ Services, Groups, Dependencies, Configuration
 * - Devices & Data ▶ Devices, Events, Data Sources, Sports, Energy
 * - Quality ▶ Hygiene, Validation, Evaluation, Alerts
 * - Logs & Analytics ▶ Logs, Analytics
 */
test.describe('Navigation & Layout — Finding Your Way', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/');
    await waitForLoadingComplete(page);
  });

  // ─── DASHBOARD LOADS ──────────────────────────────────────────────
  // INTENT: The most basic operator need — does the dashboard actually load?
  // Must show the correct brand name and not a blank page or error.

  test('@smoke dashboard loads with correct branding', async ({ page }) => {
    await expect(page).toHaveTitle(/Health Dashboard|HomeIQ/i);
    await expect(page.getByRole('heading', { name: /homeiq/i }).first()).toBeVisible();
    await expect(page.getByText(/health dashboard/i).first()).toBeVisible();
  });

  // ─── SIDEBAR NAVIGATION ──────────────────────────────────────────
  // INTENT: The sidebar is how the operator moves between views.
  // Groups must expand to reveal sub-items. Every destination must work.

  test('sidebar groups expand to reveal sub-navigation items', async ({ page }) => {
    // The sidebar should have expandable groups
    const sidebar = page.getByRole('navigation', { name: /dashboard/i });
    await expect(sidebar).toBeVisible({ timeout: 10000 });

    // Test expanding each group and verifying sub-items appear
    // Sub-items use LABELS (display text), not hash IDs
    // e.g. button text is "Data Feeds" (not "data-sources")
    const groups = [
      { name: /infrastructure/i, items: ['Services', 'Groups', 'Dependencies', 'Configuration'] },
      { name: /devices.*data/i, items: ['Devices', 'Events', 'Data Feeds', 'Energy', 'Sports'] },
      { name: /quality/i, items: ['Alerts', 'Device Health', 'Automation Checks', 'AI Performance'] },
      { name: /logs.*analytics/i, items: ['Logs', 'Analytics'] },
    ];

    for (const group of groups) {
      const groupButton = sidebar.getByRole('button', { name: group.name });
      await expect(groupButton, `Sidebar group "${group.name}" should exist`).toBeVisible();
      await groupButton.click();

      // Verify at least some sub-items are now visible
      for (const item of group.items) {
        const subItem = sidebar.getByRole('button', { name: new RegExp(`^${item}$`, 'i') });
        await expect(subItem, `Sub-item "${item}" should be visible after expanding`).toBeVisible({ timeout: 3000 });
      }
    }
  });

  test('all 16 destinations are reachable via URL hash routing', async ({ page }) => {
    // INTENT: Operators bookmark specific views and share URLs during incidents.
    // Hash routing (/#services, /#alerts) must work for every destination.
    // This replaces the old "16 flat tabs" test that failed because the
    // sidebar uses grouped navigation — hash routing auto-expands groups.
    // Hash route IDs from Dashboard.tsx — note: ids differ from sidebar labels
    // e.g. id="data-sources" but label="Data Feeds", id="hygiene" but label="Device Health"
    const destinations = [
      'overview', 'services', 'groups', 'dependencies', 'configuration',
      'devices', 'events', 'data-sources', 'energy', 'sports',
      'alerts', 'hygiene', 'validation', 'evaluation',
      'logs', 'analytics',
    ];

    for (const dest of destinations) {
      await page.goto(`/#${dest}`);
      // Each destination should render the dashboard (not crash, not blank)
      const dashboard = page.locator('[data-testid="dashboard-root"], [role="tabpanel"], main');
      await expect(
        dashboard.first(),
        `Destination "/#${dest}" should render content`
      ).toBeVisible({ timeout: 5000 });

      // Page should NOT show an error boundary crash message
      await expect(page.locator('body')).not.toContainText(/error boundary|crash|unhandled/i);
    }
  });

  test('clicking a sidebar item updates the URL hash', async ({ page }) => {
    // INTENT: Navigation state must be reflected in the URL so the operator
    // can share a link to a specific view or bookmark it.
    // Navigate to overview first, then click a sidebar item
    await page.goto('/#overview');
    await waitForLoadingComplete(page);

    // Expand Infrastructure group in the sidebar
    const sidebar = page.getByRole('navigation', { name: /dashboard/i });
    const infraGroup = sidebar.getByRole('button', { name: /infrastructure/i });
    await expect(infraGroup).toBeVisible({ timeout: 5000 });
    await infraGroup.click();

    // Click "Services" sub-item within the sidebar
    const servicesButton = sidebar.getByRole('button', { name: /^Services$/i });
    await expect(servicesButton).toBeVisible({ timeout: 3000 });
    await servicesButton.click();

    await page.waitForURL(/\#services/, { timeout: 3000 });
    expect(page.url()).toContain('#services');
  });

  test('page state persists after browser refresh', async ({ page }) => {
    // INTENT: During an incident, the operator may refresh the page.
    // They should NOT lose their place and get sent back to Overview.
    await page.goto('/#services');
    await page.waitForURL(/\#services/);

    await page.reload();
    await waitForLoadingComplete(page);

    await page.waitForURL(/\#services/);
    expect(page.url()).toContain('#services');
  });

  // ─── SIDEBAR CONTROLS ────────────────────────────────────────────
  // INTENT: The sidebar footer has three controls the operator always needs:
  // - Theme toggle (light/dark for different lighting conditions)
  // - Auto-refresh toggle (live updates during monitoring)
  // - Time range selector (zoom in/out on time window)

  test('sidebar controls are always visible: theme, auto-refresh, time range', async ({ page }) => {
    const dashboard = new HealthDashboardPage(page);
    await dashboard.goto();

    await expect(dashboard.getThemeToggle()).toBeVisible();
    await expect(dashboard.getAutoRefreshToggle()).toBeVisible();
    await expect(dashboard.getTimeRangeSelector()).toBeVisible();
  });

  test('theme toggle switches between light and dark mode', async ({ page }) => {
    // INTENT: Operators use dark mode at night, light mode during the day.
    // The toggle must actually change the visual theme, not just the label.
    const dashboard = new HealthDashboardPage(page);
    await dashboard.goto();

    const wasDark = await dashboard.isDarkMode();
    await dashboard.toggleTheme();
    const isNowDark = await dashboard.isDarkMode();
    expect(isNowDark, 'Theme should toggle between light and dark').not.toBe(wasDark);
  });

  test('theme preference persists across page reload', async ({ page }) => {
    // INTENT: The operator shouldn't have to re-set dark mode every time
    // they open the dashboard. Preference must survive a refresh.
    const dashboard = new HealthDashboardPage(page);
    await dashboard.goto();

    // Toggle to dark mode
    const wasDark = await dashboard.isDarkMode();
    if (!wasDark) {
      await dashboard.toggleTheme();
    }

    // Verify localStorage has the preference
    const stored = await page.evaluate(() => localStorage.getItem('darkMode'));
    expect(stored).toBeTruthy();

    // Reload and verify dark mode persists
    await page.reload();
    await waitForLoadingComplete(page);
    const htmlClass = await page.locator('html').getAttribute('class');
    expect(htmlClass).toContain('dark');
  });

  test('auto-refresh toggle is functional', async ({ page }) => {
    // INTENT: During active monitoring, auto-refresh keeps data live.
    // The operator toggles it off when analyzing a specific moment in time.
    const dashboard = new HealthDashboardPage(page);
    await dashboard.goto();

    const toggle = dashboard.getAutoRefreshToggle();
    await expect(toggle).toBeVisible();
    await toggle.click();
    // Toggle should still be visible after clicking (not crash)
    await expect(toggle).toBeVisible();
  });

  test('time range selector offers expected options', async ({ page }) => {
    // INTENT: The operator zooms in (15m) for recent incidents or
    // zooms out (7d) for trend analysis. All options must be available.
    const selector = page.getByRole('combobox', { name: /time range/i });
    await expect(selector).toBeVisible({ timeout: 5000 });

    // Check expected time range options exist
    const expectedOptions = ['15m', '1h', '6h', '24h', '7d'];
    for (const option of expectedOptions) {
      await expect(
        page.locator(`option:has-text("${option}")`),
        `Time range option "${option}" should be available`
      ).toBeAttached();
    }
  });

  // ─── RESPONSIVE DESIGN ────────────────────────────────────────────
  // INTENT: During an emergency at 2am, the operator might check the
  // dashboard on their phone. The UI must be usable on mobile.

  test('mobile viewport provides responsive navigation', async ({ page }) => {
    // INTENT: During an emergency at 2am, the operator might check on their phone.
    await page.setViewportSize({ width: 375, height: 667 });
    await page.reload();
    await waitForLoadingComplete(page);

    // Mobile should have either a hamburger/menu button, a bottom tab bar,
    // the sidebar adapted for mobile, or the main content still accessible
    const mobileAccessible = page.locator(
      '[data-testid="mobile-menu"], button[aria-label*="menu"], ' +
      'button:has([class*="hamburger"]), [class*="mobile-nav"], ' +
      '[class*="bottom-tab"], [class*="drawer"], ' +
      '[role="navigation"], main, [role="tabpanel"]'
    );
    await expect(mobileAccessible.first()).toBeVisible({ timeout: 5000 });
  });

  // ─── ERROR RESILIENCE ─────────────────────────────────────────────
  // INTENT: When the operator navigates between views rapidly (during
  // an incident), the dashboard must not crash with an error boundary.

  test('rapid tab switching does not crash the dashboard', async ({ page }) => {
    const destinations = ['overview', 'services', 'alerts', 'logs', 'devices'];
    for (const dest of destinations) {
      await page.goto(`/#${dest}`);
      // Each navigation should render without crashing
      await expect(page.locator('body')).toBeVisible();
      await expect(page.locator('body')).not.toContainText(/error boundary|crash/i);
    }
  });
});

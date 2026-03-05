/**
 * Page Object Model for Health Dashboard (Port 3000)
 *
 * INTENT: This page object abstracts the Health Dashboard's navigation
 * and controls so tests can focus on user intent, not DOM mechanics.
 *
 * SIDEBAR STRUCTURE (grouped navigation, not flat tabs):
 * - Overview (top-level button)
 * - Infrastructure ▶ Services, Groups, Dependencies, Configuration
 * - Devices & Data ▶ Devices, Events, Data Sources, Sports, Energy
 * - Quality ▶ Hygiene, Validation, Evaluation, Alerts
 * - Logs & Analytics ▶ Logs, Analytics
 *
 * NAVIGATION: Hash-based routing (/#services, /#alerts) auto-expands
 * the containing sidebar group. Use goToTab() for reliable navigation.
 */

import { Page, Locator, expect } from '@playwright/test';

/**
 * All navigable destinations in the Health Dashboard.
 * These are hash route IDs from Dashboard.tsx — note that IDs differ from
 * sidebar button labels in some cases:
 *   id="data-sources" → label="Data Feeds"
 *   id="hygiene"      → label="Device Health"
 *   id="validation"   → label="Automation Checks"
 *   id="evaluation"   → label="AI Performance"
 */
const HEALTH_DASHBOARD_TAB_IDS = [
  'overview',
  'services',
  'groups',
  'dependencies',
  'configuration',
  'devices',
  'events',
  'data-sources',
  'energy',
  'sports',
  'alerts',
  'hygiene',
  'validation',
  'evaluation',
  'logs',
  'analytics',
] as const;

/**
 * Sidebar groups and their sub-items.
 * Keys = group button text, Values = hash route IDs (not labels).
 */
const SIDEBAR_GROUPS = {
  'Infrastructure': ['services', 'groups', 'dependencies', 'configuration'],
  'Devices & Data': ['devices', 'events', 'data-sources', 'energy', 'sports'],
  'Quality': ['alerts', 'hygiene', 'validation', 'evaluation'],
  'Logs & Analytics': ['logs', 'analytics'],
} as const;

export type HealthDashboardTabId = (typeof HEALTH_DASHBOARD_TAB_IDS)[number];

export class HealthDashboardPage {
  constructor(private page: Page) {}

  /** Navigate to Health Dashboard root */
  async goto(path: string = '/') {
    await this.page.goto(path);
    await expect(this.getDashboardRoot()).toBeVisible({ timeout: 15000 });
  }

  getDashboardRoot(): Locator {
    return this.page.locator('[data-testid="dashboard-root"], [role="tabpanel"], main').first();
  }

  getHeader(): Locator {
    return this.page.locator('[data-testid="dashboard-header"], header').first();
  }

  getSidebar(): Locator {
    return this.page.getByRole('navigation', { name: /dashboard/i });
  }

  getThemeToggle(): Locator {
    // Match the actual button text/aria-label from the live page
    return this.page.locator(
      '[data-testid="theme-toggle"], ' +
      'button[aria-label*="dark"], button[aria-label*="light"], ' +
      'button:has-text("Dark Mode"), button:has-text("Light Mode")'
    ).first();
  }

  getAutoRefreshToggle(): Locator {
    return this.page.locator(
      '[data-testid="auto-refresh-toggle"], ' +
      'button[aria-label*="refresh"], button:has-text("Auto Refresh")'
    ).first();
  }

  getTimeRangeSelector(): Locator {
    return this.page.locator(
      '[data-testid="time-range-selector"], ' +
      'select[aria-label*="time range"], ' +
      'combobox[aria-label*="time range"]'
    ).first();
  }

  /**
   * Get a tab/destination button by its ID.
   * For overview, looks for the top-level button.
   * For grouped items, uses data-testid or data-tab attributes.
   */
  getTab(tabId: string): Locator {
    if (tabId === 'overview') {
      return this.page.locator(
        '[data-tab="overview"], button:has-text("Overview")'
      ).first();
    }
    return this.page.locator(
      `[data-testid="tab-${tabId}"], [data-tab="${tabId}"], ` +
      `button:has-text("${tabId.replace(/-/g, ' ')}")`
    ).first();
  }

  /**
   * Navigate to a tab by id using hash routing.
   * Hash routing auto-expands the containing sidebar group,
   * which is more reliable than clicking through the sidebar.
   */
  async goToTab(tabId: string): Promise<void> {
    await this.page.goto(`/#${tabId}`);
    await expect(this.getDashboardRoot()).toBeVisible({ timeout: 10000 });
  }

  /** All navigable destination IDs */
  static getTabIds(): readonly string[] {
    return HEALTH_DASHBOARD_TAB_IDS;
  }

  /** Sidebar group structure */
  static getSidebarGroups(): typeof SIDEBAR_GROUPS {
    return SIDEBAR_GROUPS;
  }

  /** Check if theme is dark (html has dark class) */
  async isDarkMode(): Promise<boolean> {
    const htmlClass = await this.page.locator('html').getAttribute('class');
    return htmlClass?.includes('dark') ?? false;
  }

  /** Toggle theme and return new dark state */
  async toggleTheme(): Promise<boolean> {
    const toggle = this.getThemeToggle();
    await expect(toggle).toBeVisible({ timeout: 2000 });
    await toggle.click();
    await this.page.waitForFunction(
      () => document.querySelector('html')?.classList !== undefined
    );
    return this.isDarkMode();
  }

  /** Toggle auto-refresh on/off */
  async toggleAutoRefresh(): Promise<void> {
    const toggle = this.getAutoRefreshToggle();
    await expect(toggle).toBeVisible({ timeout: 2000 });
    await toggle.click();
  }

  /** Select time range (e.g. "1h", "24h", "7d") */
  async selectTimeRange(value: string): Promise<void> {
    const selector = this.getTimeRangeSelector();
    await expect(selector).toBeVisible({ timeout: 2000 });
    await selector.selectOption({ label: value });
  }

  /**
   * Expand a sidebar group by name pattern.
   * Returns the sub-items that become visible.
   */
  async expandSidebarGroup(groupName: RegExp): Promise<Locator> {
    const sidebar = this.getSidebar();
    const groupButton = sidebar.getByRole('button', { name: groupName });
    await expect(groupButton).toBeVisible({ timeout: 3000 });
    await groupButton.click();
    // Return the expanded group's children container
    return groupButton.locator('..').locator('+ div, ~ div').first();
  }
}

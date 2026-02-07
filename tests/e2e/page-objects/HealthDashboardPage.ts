/**
 * Page Object Model for Health Dashboard (Port 3000)
 *
 * Covers header, theme toggle, auto-refresh, time range selector,
 * tab navigation, and dashboard root per Playwright Full UI Coverage plan.
 */

import { Page, Locator, expect } from '@playwright/test';

const HEALTH_DASHBOARD_TAB_IDS = [
  'overview',
  'setup',
  'services',
  'dependencies',
  'devices',
  'events',
  'logs',
  'sports',
  'data-sources',
  'energy',
  'analytics',
  'alerts',
  'hygiene',
  'validation',
  'synergies',
  'configuration',
] as const;

export type HealthDashboardTabId = (typeof HEALTH_DASHBOARD_TAB_IDS)[number];

export class HealthDashboardPage {
  constructor(private page: Page) {}

  /** Navigate to Health Dashboard root */
  async goto(path: string = '/') {
    await this.page.goto(path);
    await expect(this.getDashboardRoot()).toBeVisible({ timeout: 15000 });
  }

  getDashboardRoot(): Locator {
    return this.page.getByTestId('dashboard-root');
  }

  getHeader(): Locator {
    return this.page.getByTestId('dashboard-header');
  }

  getThemeToggle(): Locator {
    return this.page.getByTestId('theme-toggle');
  }

  getAutoRefreshToggle(): Locator {
    return this.page.getByTestId('auto-refresh-toggle');
  }

  getTimeRangeSelector(): Locator {
    return this.page.getByTestId('time-range-selector');
  }

  getTabNavigation(): Locator {
    return this.page.getByTestId('tab-navigation');
  }

  getTab(tabId: string): Locator {
    return this.page.getByTestId(`tab-${tabId}`);
  }

  /** Switch to a tab by id */
  async goToTab(tabId: string): Promise<void> {
    const tab = this.getTab(tabId);
    await expect(tab).toBeVisible({ timeout: 5000 });
    await tab.click();
    // URL hash may not update for all tabs (e.g. overview at root); allow gracefully
    await this.page.waitForURL(RegExp(`#${tabId.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`), { timeout: 3000 }).catch(() => {
      // Some tabs (e.g. overview) don't update the hash — this is expected
    });
  }

  /** All 16 tab ids from the plan */
  static getTabIds(): readonly string[] {
    return HEALTH_DASHBOARD_TAB_IDS;
  }

  /** Check if theme is dark (e.g. html has dark class) */
  async isDarkMode(): Promise<boolean> {
    const htmlClass = await this.page.locator('html').getAttribute('class');
    return htmlClass?.includes('dark') ?? false;
  }

  /** Toggle theme and return new dark state */
  async toggleTheme(): Promise<boolean> {
    const toggle = this.getThemeToggle();
    await expect(toggle).toBeVisible({ timeout: 2000 });
    await toggle.click();
    await this.page.waitForFunction(() => document.querySelector('html')?.classList !== undefined);
    return this.isDarkMode();
  }

  /** Toggle auto-refresh on/off */
  async toggleAutoRefresh(): Promise<void> {
    const toggle = this.getAutoRefreshToggle();
    await expect(toggle).toBeVisible({ timeout: 2000 });
    await toggle.click();
    await this.page.waitForFunction(() => document.querySelector('html')?.classList !== undefined);
  }

  /** Select time range (e.g. "1h", "24h", "7d") */
  async selectTimeRange(value: string): Promise<void> {
    const selector = this.getTimeRangeSelector();
    await expect(selector).toBeVisible({ timeout: 2000 });
    await selector.click();
    await this.page.getByRole('option', { name: new RegExp(value, 'i') }).click();
    await this.page.waitForFunction(() => document.querySelector('html')?.classList !== undefined);
  }
}

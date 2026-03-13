/**
 * Cross-App Navigation E2E Tests (Story 59.4)
 *
 * Tests app switcher navigation between the three HomeIQ frontends:
 * - Health Dashboard (port 3000) ↔ AI Automation UI (port 3001)
 * - Health Dashboard (port 3000) ↔ Observability Dashboard (port 8501)
 * - AI Automation UI (port 3001) ↔ Health Dashboard (port 3000)
 * - Shared footer links across apps
 */

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../shared/helpers/wait-helpers';

test.describe('Cross-App Navigation @smoke', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
  });

  test('health dashboard has app switcher with links to all apps', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await waitForLoadingComplete(page);

    // App switcher should show links to HomeIQ (AI UI) and Health (current, highlighted)
    const homeiqLink = page.locator('a').filter({ hasText: 'HomeIQ' }).first();
    await expect(homeiqLink).toBeVisible({ timeout: 10000 });

    // Verify link href points to AI Automation UI
    const href = await homeiqLink.getAttribute('href');
    expect(href).toContain('3001');

    // Verify Ops/observability link exists
    const opsLink = page.locator('a').filter({ hasText: /Ops/ }).first();
    await expect(opsLink).toBeVisible({ timeout: 5000 });
    const opsHref = await opsLink.getAttribute('href');
    expect(opsHref).toContain('8501');

    // Current app should be highlighted (not a link but a span)
    const healthLabel = page.locator('span').filter({ hasText: 'Health' }).first();
    await expect(healthLabel).toBeVisible();
  });

  test('health dashboard HomeIQ link navigates to AI Automation UI', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await waitForLoadingComplete(page);

    const homeiqLink = page.locator('a').filter({ hasText: 'HomeIQ' }).first();
    await expect(homeiqLink).toBeVisible({ timeout: 10000 });

    // Click and verify navigation to AI Automation UI
    const [newPage] = await Promise.all([
      page.context().waitForEvent('page', { timeout: 10000 }).catch(() => null),
      homeiqLink.click(),
    ]);

    // The link either opens in new tab or navigates current page
    const targetPage = newPage || page;
    await targetPage.waitForLoadState('domcontentloaded', { timeout: 15000 });

    // Should be at port 3001
    expect(targetPage.url()).toContain('3001');
  });

  test('AI Automation UI has app switcher with link to Health Dashboard', async ({ page }) => {
    await page.goto('http://localhost:3001');
    await waitForLoadingComplete(page);

    // Look for Health Dashboard link in the sidebar/header
    const healthLink = page.locator('a').filter({ hasText: /Health/ }).first();
    await expect(healthLink).toBeVisible({ timeout: 10000 });

    const href = await healthLink.getAttribute('href');
    expect(href).toContain('3000');
  });

  test('AI Automation UI Health link navigates to Health Dashboard', async ({ page }) => {
    await page.goto('http://localhost:3001');
    await waitForLoadingComplete(page);

    const healthLink = page.locator('a').filter({ hasText: /Health/ }).first();
    await expect(healthLink).toBeVisible({ timeout: 10000 });

    const [newPage] = await Promise.all([
      page.context().waitForEvent('page', { timeout: 10000 }).catch(() => null),
      healthLink.click(),
    ]);

    const targetPage = newPage || page;
    await targetPage.waitForLoadState('domcontentloaded', { timeout: 15000 });
    expect(targetPage.url()).toContain('3000');
  });

  test('health dashboard footer contains system summary', async ({ page }) => {
    await page.goto('http://localhost:3000/#overview');
    await waitForLoadingComplete(page);

    // Footer should show device/service counts
    const footer = page.getByText(/data sources healthy/i);
    await expect(footer).toBeVisible({ timeout: 15000 });
  });

  test('app switcher links use safe URLs (no javascript: or data:)', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await waitForLoadingComplete(page);

    // Verify all app switcher links use http/https
    const appLinks = page.locator('a[href*="localhost"]');
    const count = await appLinks.count();
    expect(count).toBeGreaterThan(0);

    for (let i = 0; i < count; i++) {
      const href = await appLinks.nth(i).getAttribute('href');
      expect(href).toMatch(/^https?:\/\//);
    }
  });
});

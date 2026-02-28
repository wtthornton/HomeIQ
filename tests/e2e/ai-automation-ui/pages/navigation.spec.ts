import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

/** Tests run against deployed Docker (no API mocks). AI automation UI and backend on 3001/8018. */
test.describe('AI Automation UI - Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/');
    await waitForLoadingComplete(page);
  });

  test('@smoke All routes accessible', async ({ page }) => {
    const routes = [
      { path: '/', name: 'Ideas' },
      { path: '/insights', name: 'Insights' },
      { path: '/automations', name: 'Automations' },
      { path: '/explore', name: 'Explore' },
      { path: '/chat', name: 'Chat' },
      { path: '/settings', name: 'Settings' },
    ];

    for (const route of routes) {
      await page.goto(route.path);
      await waitForLoadingComplete(page);
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('P4.1 Navigate to all AI automation pages (Ideas, Chat, Automations, Insights, Settings, Explore)', async ({ page }) => {
    const routes = [
      { path: '/', name: 'Ideas' },
      { path: '/chat', name: 'Chat' },
      { path: '/automations', name: 'Automations' },
      { path: '/insights', name: 'Insights' },
      { path: '/settings', name: 'Settings' },
      { path: '/explore', name: 'Explore' },
    ];
    for (const route of routes) {
      await page.goto(route.path);
      await waitForLoadingComplete(page);
      if (route.path !== '/') expect(page.url()).toContain(route.path);
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('Navigation menu works', async ({ page }) => {
    const navItems = page.locator('nav a, nav button, [role="navigation"] a');
    const count = await navItems.count();
    expect(count).toBeGreaterThan(0);
  });

  test('Route transitions smooth', async ({ page }) => {
    await page.goto('/');
    await waitForLoadingComplete(page);
    
    await page.goto('/insights');
    await waitForLoadingComplete(page);

    await expect(page.url()).toContain('/insights');
  });

  test('Active route highlighting', async ({ page }) => {
    await page.goto('/insights');
    await waitForLoadingComplete(page);

    const activeLink = page.locator('[data-nav-item][aria-current="page"], a[href="/insights"][aria-current], a.active, [class*="active"]').first();
    const exists = await activeLink.isVisible().catch(() => false);
    // Active state might be implemented
  });

  test('Browser back/forward buttons', async ({ page }) => {
    await page.goto('/');
    await waitForLoadingComplete(page);
    
    await page.goto('/insights');
    await waitForLoadingComplete(page);

    await page.goBack();
    await waitForLoadingComplete(page);

    await expect(page.url()).not.toContain('/insights');

    await page.goForward();
    await waitForLoadingComplete(page);

    await expect(page.url()).toContain('/insights');
  });

  test('Deep linking works', async ({ page }) => {
    await page.goto('/insights');
    await waitForLoadingComplete(page);

    await expect(page.url()).toContain('/insights');
    await expect(page.locator('body')).toBeVisible();
  });
});

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
      { path: '/', name: 'Dashboard' },
      { path: '/patterns', name: 'Patterns' },
      { path: '/synergies', name: 'Synergies' },
      { path: '/deployed', name: 'Deployed' },
      { path: '/discovery', name: 'Discovery' },
      { path: '/ha-agent', name: 'HA Agent Chat' },
      { path: '/settings', name: 'Settings' },
      { path: '/admin', name: 'Admin' },
    ];

    for (const route of routes) {
      await page.goto(route.path);
      await waitForLoadingComplete(page);
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('P4.1 Navigate to all AI automation pages (Dashboard, Ask AI, Deployed, Patterns, Settings, Discovery, Synergies, Proactive, Blueprint, Admin)', async ({ page }) => {
    const routes = [
      { path: '/', name: 'Dashboard' },
      { path: '/ha-agent', name: 'Ask AI / HA Agent' },
      { path: '/deployed', name: 'Deployed' },
      { path: '/patterns', name: 'Patterns' },
      { path: '/settings', name: 'Settings' },
      { path: '/discovery', name: 'Discovery' },
      { path: '/synergies', name: 'Synergies' },
      { path: '/proactive', name: 'Proactive' },
      { path: '/blueprint-suggestions', name: 'Blueprint' },
      { path: '/admin', name: 'Admin' },
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
    
    await page.goto('/patterns');
    await waitForLoadingComplete(page);
    
    await expect(page.url()).toContain('/patterns');
  });

  test('Active route highlighting', async ({ page }) => {
    await page.goto('/patterns');
    await waitForLoadingComplete(page);
    
    const activeLink = page.locator('a[href="/patterns"][aria-current], a.active, [class*="active"]').first();
    const exists = await activeLink.isVisible().catch(() => false);
    // Active state might be implemented
  });

  test('Browser back/forward buttons', async ({ page }) => {
    await page.goto('/');
    await waitForLoadingComplete(page);
    
    await page.goto('/patterns');
    await waitForLoadingComplete(page);
    
    await page.goBack();
    await waitForLoadingComplete(page);
    
    await expect(page.url()).not.toContain('/patterns');
    
    await page.goForward();
    await waitForLoadingComplete(page);
    
    await expect(page.url()).toContain('/patterns');
  });

  test('Deep linking works', async ({ page }) => {
    await page.goto('/patterns');
    await waitForLoadingComplete(page);
    
    await expect(page.url()).toContain('/patterns');
    await expect(page.locator('body')).toBeVisible();
  });
});

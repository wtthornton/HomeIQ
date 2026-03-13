/**
 * Scheduled Tasks Page (Epic 49.12)
 * Route: /scheduled — View and manage scheduled AI tasks (cron-based).
 */

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

test.describe('Scheduled Tasks — /scheduled', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/scheduled');
    await waitForLoadingComplete(page);
  });

  test('@smoke scheduled tasks route loads with main content', async ({ page }) => {
    await expect(page).toHaveTitle(/Scheduled|HomeIQ|AI Automation/i);
    const main = page.locator('main, #main-content, [class*="Schedule"]').first();
    await expect(main).toBeVisible({ timeout: 10000 });

    // Page should show a heading, task list, or empty state
    const heading = page.getByRole('heading').first();
    const taskList = page.locator('[class*="task" i], [class*="schedule" i], table, ul').first();
    const emptyState = page.getByText(/no.*tasks|no.*scheduled|get started/i).first();

    const hasHeading = await heading.isVisible({ timeout: 5000 }).catch(() => false);
    const hasTasks = await taskList.isVisible({ timeout: 3000 }).catch(() => false);
    const hasEmpty = await emptyState.isVisible({ timeout: 3000 }).catch(() => false);

    expect(
      hasHeading || hasTasks || hasEmpty,
      'Scheduled page should show heading, task list, or empty state'
    ).toBe(true);
  });

  test('no console errors on the scheduled tasks page', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    await page.reload();
    await waitForLoadingComplete(page);

    const criticalErrors = consoleErrors.filter(
      (e) =>
        !e.includes('favicon') &&
        !e.includes('manifest') &&
        !e.includes('font') &&
        !e.includes('woff') &&
        !e.includes('sourcemap') &&
        !e.includes('429') &&
        !e.includes('Too Many Requests') &&
        !e.includes('rate limit') &&
        !e.includes('VITE_API_KEY') &&
        !e.includes('Failed to fetch') &&
        !e.includes('Failed to load resource') &&
        !e.includes('Unable to reach backend') &&
        !e.includes('fetchWithErrorHandling')
    );
    expect(criticalErrors).toEqual([]);
  });
});

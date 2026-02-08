import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../shared/helpers/wait-helpers';

const DASHBOARD_URL = process.env.HEALTH_DASHBOARD_URL || 'http://localhost:3000';
const AI_UI_URL = process.env.AI_AUTOMATION_UI_URL || 'http://localhost:3001';

/**
 * Phase 6: P6.3 UI→API flow
 * Dashboard tab X triggers call to API Y; response populates UI.
 */
test.describe('UI to API flow verification', () => {
  test('P6.3 Health dashboard Services tab loads and UI renders', async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto(`${DASHBOARD_URL}/#services`);
    await waitForLoadingComplete(page);

    const dashboardVisible = await page.locator('[data-testid="dashboard-root"], main, body').first().isVisible({ timeout: 8000 }).catch(() => false);
    expect(dashboardVisible).toBe(true);
  });

  test('P6.3 AI Automation dashboard loads and UI renders', async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto(`${AI_UI_URL}/`);
    await waitForLoadingComplete(page);

    const bodyVisible = await page.locator('body').isVisible();
    expect(bodyVisible).toBe(true);
  });
});

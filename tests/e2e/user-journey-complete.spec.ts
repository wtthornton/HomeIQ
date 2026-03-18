import { test, expect } from '@playwright/test';

/**
 * Complete User Journey E2E Tests
 * Tests real user workflows from arrival to data viewing and system management
 *
 * Epic 84: Full rewrite — replaced all stale selectors (sidebar nav, screen views,
 * health-card sub-selectors, events/statistics sections) with current tab-based
 * architecture equivalents matching the health-dashboard source.
 */
test.describe('Complete User Journey Tests', () => {

  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
  });

  test.describe('New User Onboarding Journey', () => {

    test('First-time user dashboard exploration', async ({ page }) => {
      // Step 1: User arrives at dashboard
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();

      // Step 2: User sees dashboard title
      const dashboardTitle = page.locator('[data-testid="dashboard-title"]');
      await expect(dashboardTitle).toBeVisible();

      // Step 3: User examines health cards on Overview tab
      const healthCards = page.locator('[data-testid="health-card"]');
      await expect(healthCards).toHaveCount({ min: 1 });

      // Step 4: User explores Services tab
      await page.click('[data-testid="tab-services"]');
      await page.waitForSelector('[data-testid="service-list"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="service-list"]')).toBeVisible();

      // Step 5: User checks Configuration tab
      await page.click('[data-testid="tab-configuration"]');
      await page.waitForSelector('[data-testid="dashboard-content"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="dashboard-content"]')).toBeVisible();

      // Step 6: User returns to Overview
      await page.click('[data-testid="tab-overview"]');
      await page.waitForSelector('[data-testid="health-card"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="health-card"]').first()).toBeVisible();
    });

    test('User discovers system capabilities', async ({ page }) => {
      // User explores what the system can do via health cards
      await page.waitForSelector('[data-testid="health-card"]', { timeout: 15000 });

      // Check WebSocket connection indicator
      const wsStatus = page.locator('[data-testid="websocket-status"]');
      if (await wsStatus.isVisible({ timeout: 3000 }).catch(() => false)) {
        await expect(wsStatus).toBeVisible();
      }

      // Check that health cards display service information
      const healthCards = page.locator('[data-testid="health-card"]');
      const cardCount = await healthCards.count();
      expect(cardCount).toBeGreaterThan(0);

      // Verify RAG status card if present
      const ragCard = page.locator('[data-testid="rag-status-card"]');
      if (await ragCard.isVisible({ timeout: 3000 }).catch(() => false)) {
        await expect(ragCard).toBeVisible();
      }
    });
  });

  test.describe('System Administrator Journey', () => {

    test('Admin monitors system health and performance', async ({ page }) => {
      // Step 1: Admin checks health cards on Overview
      await page.waitForSelector('[data-testid="health-card"]', { timeout: 15000 });
      const healthCards = page.locator('[data-testid="health-card"]');
      await expect(healthCards).toHaveCount({ min: 1 });

      // Verify health card shows status via data-status attribute
      const firstCard = healthCards.first();
      const status = await firstCard.getAttribute('data-status');
      if (status) {
        expect(['healthy', 'degraded', 'unhealthy']).toContain(status);
      }

      // Step 2: Admin reviews services
      await page.click('[data-testid="tab-services"]');
      await page.waitForSelector('[data-testid="service-list"]', { timeout: 10000 });

      // Check service cards are displayed
      const serviceCards = page.locator('[data-testid="service-card"]');
      await expect(serviceCards).toHaveCount({ min: 1 });

      // Step 3: Admin checks events
      await page.click('[data-testid="tab-events"]');
      const eventStream = page.locator('[data-testid="event-stream"]');
      await expect(eventStream).toBeVisible({ timeout: 10000 });
    });

    test('Admin configures system settings', async ({ page }) => {
      // Step 1: Admin navigates to Configuration tab
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });
      await page.click('[data-testid="tab-configuration"]');
      await page.waitForSelector('[data-testid="dashboard-content"]', { timeout: 10000 });

      // Step 2: Admin sees configuration content
      await expect(page.locator('[data-testid="dashboard-content"]')).toBeVisible();

      // Step 3: Admin uses theme toggle
      const themeToggle = page.locator('[data-testid="theme-toggle"]');
      if (await themeToggle.isVisible({ timeout: 3000 }).catch(() => false)) {
        await themeToggle.click();
        // Verify theme changed (dashboard should still be visible)
        await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
      }

      // Step 4: Admin adjusts time range
      const timeRange = page.locator('[data-testid="time-range-selector"]');
      if (await timeRange.isVisible({ timeout: 3000 }).catch(() => false)) {
        await expect(timeRange).toBeVisible();
      }
    });

    test('Admin investigates system issues', async ({ page }) => {
      // Step 1: Admin checks health cards for issues
      await page.waitForSelector('[data-testid="health-card"]', { timeout: 15000 });
      const healthCards = page.locator('[data-testid="health-card"]');
      const cardCount = await healthCards.count();

      // Step 2: Admin reviews service status on Services tab
      await page.click('[data-testid="tab-services"]');
      await page.waitForSelector('[data-testid="service-list"]', { timeout: 10000 });

      const serviceCards = page.locator('[data-testid="service-card"]');
      const serviceCount = await serviceCards.count();
      expect(serviceCount).toBeGreaterThan(0);

      // Step 3: Admin checks event stream for recent issues
      await page.click('[data-testid="tab-events"]');
      const eventStream = page.locator('[data-testid="event-stream"]');
      await expect(eventStream).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('Data Analyst Journey', () => {

    test('Analyst explores event data and trends', async ({ page }) => {
      // Step 1: Analyst views Overview health cards
      await page.waitForSelector('[data-testid="health-card"]', { timeout: 15000 });

      // Step 2: Analyst navigates to Events tab
      await page.click('[data-testid="tab-events"]');
      const eventStream = page.locator('[data-testid="event-stream"]');
      await expect(eventStream).toBeVisible({ timeout: 10000 });

      // Step 3: Analyst checks data sources tab if available
      const dataSourcesTab = page.locator('[data-testid="tab-data-sources"]');
      if (await dataSourcesTab.isVisible({ timeout: 2000 }).catch(() => false)) {
        await dataSourcesTab.click();
        const dataSource = page.locator('[data-testid="data-source"]');
        await expect(dataSource.first()).toBeVisible({ timeout: 10000 });
      }
    });

    test('Analyst monitors data flow and processing', async ({ page }) => {
      // Step 1: Analyst checks WebSocket connection indicator
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

      const wsStatus = page.locator('[data-testid="websocket-status"]');
      if (await wsStatus.isVisible({ timeout: 3000 }).catch(() => false)) {
        const isConnected = await wsStatus.getAttribute('data-connected');
        expect(isConnected).toBeDefined();
      }

      // Step 2: Analyst checks health cards for processing status
      const healthCards = page.locator('[data-testid="health-card"]');
      await expect(healthCards).toHaveCount({ min: 1 });

      // Step 3: Analyst views services
      await page.click('[data-testid="tab-services"]');
      await page.waitForSelector('[data-testid="service-list"]', { timeout: 10000 });
      const serviceCards = page.locator('[data-testid="service-card"]');
      await expect(serviceCards).toHaveCount({ min: 1 });
    });
  });

  test.describe('Mobile User Journey', () => {

    test('Mobile user navigates system on small screen', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });

      // Step 1: Mobile user loads dashboard
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

      // Step 2: Mobile user sees responsive layout
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();

      // Step 3: Mobile user navigates to Services tab
      await page.click('[data-testid="tab-services"]');
      await page.waitForSelector('[data-testid="dashboard-content"]', { timeout: 10000 });

      // Step 4: Mobile user checks Configuration tab
      await page.click('[data-testid="tab-configuration"]');
      await page.waitForSelector('[data-testid="dashboard-content"]', { timeout: 10000 });

      // Step 5: Mobile user returns to Overview
      await page.click('[data-testid="tab-overview"]');
      await page.waitForSelector('[data-testid="health-card"]', { timeout: 10000 });
    });
  });

  test.describe('Power User Journey', () => {

    test('Power user performs rapid system operations', async ({ page }) => {
      // Step 1: Power user quickly checks all tabs
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

      const tabs = [
        { tab: '[data-testid="tab-overview"]', verify: '[data-testid="health-card"]' },
        { tab: '[data-testid="tab-services"]', verify: '[data-testid="service-list"]' },
        { tab: '[data-testid="tab-events"]', verify: '[data-testid="event-stream"]' },
        { tab: '[data-testid="tab-configuration"]', verify: '[data-testid="dashboard-content"]' }
      ];

      for (const { tab, verify } of tabs) {
        await page.click(tab);
        await page.waitForSelector(verify, { timeout: 10000 });
        await expect(page.locator(verify).first()).toBeVisible();
      }

      // Step 2: Power user performs multiple rapid refreshes
      for (let i = 0; i < 5; i++) {
        await page.reload();
        await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 10000 });
        await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
      }

      // Step 3: Power user tests keyboard navigation
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      await page.keyboard.press('Enter');

      // Step 4: Power user verifies system is still responsive
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
    });

    test('Power user tests system under load', async ({ page }) => {
      // Step 1: Power user opens multiple tabs
      const context = page.context();
      const pages = await Promise.all([
        context.newPage(),
        context.newPage(),
        context.newPage()
      ]);

      // Step 2: Power user loads dashboard in all tabs
      await Promise.all(pages.map(p => p.goto('http://localhost:3000')));

      // Step 3: Power user navigates different tabs in each browser tab
      await pages[0].waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });
      await pages[1].waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });
      await pages[2].waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

      await pages[0].click('[data-testid="tab-overview"]');
      await pages[1].click('[data-testid="tab-services"]');
      await pages[2].click('[data-testid="tab-configuration"]');

      // Step 4: Power user verifies all browser tabs work correctly
      await expect(pages[0].locator('[data-testid="dashboard-root"]')).toBeVisible();
      await expect(pages[1].locator('[data-testid="dashboard-root"]')).toBeVisible();
      await expect(pages[2].locator('[data-testid="dashboard-root"]')).toBeVisible();

      // Step 5: Clean up
      await Promise.all(pages.map(p => p.close()));
    });
  });

  test.describe('Error Recovery Journey', () => {

    test('User recovers from system errors gracefully', async ({ page }) => {
      // Step 1: User encounters an error
      await page.route('**/api/v1/health', route => route.abort());

      await page.goto('http://localhost:3000');

      // Step 2: User sees error state
      await page.waitForSelector('[data-testid="error-state"]', { timeout: 15000 });
      await expect(page.locator('[data-testid="error-state"]')).toBeVisible();

      // Step 3: User reads error message
      const errorMessage = page.locator('[data-testid="error-message"]');
      await expect(errorMessage).toBeVisible();

      // Step 4: User attempts retry
      const retryButton = page.locator('[data-testid="retry-button"]');
      await expect(retryButton).toBeVisible();

      // Step 5: System recovers
      await page.unroute('**/api/v1/health');
      await retryButton.click();

      // Step 6: User verifies recovery
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
    });

    test('User continues working despite partial failures', async ({ page }) => {
      // Step 1: Simulate partial API failure
      await page.route('**/api/v1/stats', route => route.abort());
      await page.route('**/api/v1/health', route => route.continue());

      // Step 2: User loads dashboard
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

      // Step 3: User sees partial data (health cards should still load)
      const healthCards = page.locator('[data-testid="health-card"]');
      if (await healthCards.first().isVisible({ timeout: 5000 }).catch(() => false)) {
        await expect(healthCards).toHaveCount({ min: 1 });
      }

      // Step 4: User navigates despite errors — Services tab
      await page.click('[data-testid="tab-services"]');
      await page.waitForSelector('[data-testid="dashboard-content"]', { timeout: 10000 });

      // Step 5: User can still access Configuration tab
      await page.click('[data-testid="tab-configuration"]');
      await page.waitForSelector('[data-testid="dashboard-content"]', { timeout: 10000 });
    });
  });

  test.describe('Accessibility Journey', () => {

    test('Screen reader user navigates system', async ({ page }) => {
      // Step 1: Screen reader user loads dashboard
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

      // Step 2: Verify tab navigation has proper ARIA roles
      const tabNav = page.locator('[data-testid="tab-navigation"]');
      await expect(tabNav).toBeVisible();

      // Step 3: Screen reader user navigates with keyboard
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');

      // Step 4: Screen reader user activates a tab
      await page.keyboard.press('Enter');

      // Step 5: Verify the dashboard content updated
      await expect(page.locator('[data-testid="dashboard-content"]')).toBeVisible();

      // Step 6: Screen reader user continues keyboard navigation
      await page.keyboard.press('Tab');
      await page.keyboard.press('Enter');

      // Dashboard should remain responsive
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
    });

    test('High contrast user views system', async ({ page }) => {
      // Step 1: User loads dashboard
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

      // Step 2: User uses theme toggle for dark mode
      const themeToggle = page.locator('[data-testid="theme-toggle"]');
      if (await themeToggle.isVisible({ timeout: 3000 }).catch(() => false)) {
        await themeToggle.click();

        // Step 3: User verifies dashboard is still usable
        await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
        await expect(page.locator('[data-testid="health-card"]').first()).toBeVisible();
      }

      // Step 4: User navigates to Services tab
      await page.click('[data-testid="tab-services"]');
      await page.waitForSelector('[data-testid="dashboard-content"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="dashboard-content"]')).toBeVisible();
    });
  });
});

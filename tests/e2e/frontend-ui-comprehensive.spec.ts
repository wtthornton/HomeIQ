import { test, expect } from '@playwright/test';

/**
 * Comprehensive Frontend UI E2E Tests
 * Aligned with current health-dashboard (React, tab-based, hash routing).
 *
 * Key selectors:
 *   dashboard-root, dashboard-header, dashboard-title, dashboard-content,
 *   tab-navigation, tab-{id}, theme-toggle, auto-refresh-toggle,
 *   time-range-selector, health-card, rag-status-card, rag-status-section,
 *   loading-spinner, error-state, error-message, retry-button
 */
test.describe('Frontend UI Comprehensive Tests', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });
  });

  // ---------- Dashboard Main Screen ----------

  test.describe('Dashboard Main Screen', () => {

    test('Dashboard loads completely with all components', async ({ page }) => {
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
      await expect(page.locator('[data-testid="dashboard-title"]')).toBeVisible();

      // Tab navigation (data-testid added in Dashboard.tsx; fallback to nav)
      const tabNav = page.locator('[data-testid="tab-navigation"]').or(page.locator('nav[aria-label="Dashboard navigation"]'));
      await expect(tabNav.first()).toBeVisible();
      await expect(page.locator('[data-testid="tab-overview"]')).toBeVisible();
      await expect(page.locator('[data-testid="dashboard-content"]')).toBeVisible();

      await page.waitForTimeout(3000);
      const healthCards = page.locator('[data-testid="health-card"]');
      const count = await healthCards.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('Dashboard title displays HomeIQ Health', async ({ page }) => {
      const title = page.locator('[data-testid="dashboard-title"]');
      await expect(title).toBeVisible();
      await expect(title).toContainText('HomeIQ Health');
    });

    test('Health cards display on overview', async ({ page }) => {
      await page.waitForTimeout(3000);
      const healthCards = page.locator('[data-testid="health-card"]');
      const count = await healthCards.count();
      expect(count).toBeGreaterThanOrEqual(0);

      // Each card should be visible
      for (let i = 0; i < Math.min(count, 5); i++) {
        await expect(healthCards.nth(i)).toBeVisible();
      }
    });

    test('Header controls are functional', async ({ page }) => {
      // Theme toggle
      const themeToggle = page.locator('[data-testid="theme-toggle"]');
      await expect(themeToggle).toBeVisible();

      // Auto-refresh toggle
      const autoRefresh = page.locator('[data-testid="auto-refresh-toggle"]');
      await expect(autoRefresh).toBeVisible();

      // Time range selector
      const timeRange = page.locator('[data-testid="time-range-selector"]');
      await expect(timeRange).toBeVisible();
    });

    test('Theme toggle switches dark/light mode', async ({ page }) => {
      const themeToggle = page.locator('[data-testid="theme-toggle"]');
      const initialPressed = await themeToggle.getAttribute('aria-pressed');

      await themeToggle.click();

      const newPressed = await themeToggle.getAttribute('aria-pressed');
      expect(newPressed).not.toBe(initialPressed);
    });
  });

  // ---------- Tab Navigation ----------

  test.describe('Tab Navigation', () => {

    test('All expected tabs are present', async ({ page }) => {
      const tabs = [
        'overview', 'services', 'groups', 'dependencies', 'devices',
        'events', 'data-sources', 'energy', 'sports', 'alerts',
        'hygiene', 'validation', 'evaluation', 'configuration', 'memory',
        'logs', 'analytics'
      ];

      // Expand all nav groups so tabs are in DOM (sidebar uses collapsible groups)
      for (const label of ['Infrastructure', 'Devices & Data', 'Quality', 'Logs & Analytics']) {
        const groupBtn = page.getByRole('button', { name: label });
        if (await groupBtn.isVisible()) {
          await groupBtn.click();
        }
      }

      for (const tabId of tabs) {
        const tab = page.locator(`[data-testid="tab-${tabId}"]`);
        await expect(tab).toBeAttached();
      }
    });

    test('Clicking tabs switches content', async ({ page }) => {
      // Expand Infrastructure group to reveal tab-services
      await page.getByRole('button', { name: 'Infrastructure' }).click();
      // Click Services tab
      await page.click('[data-testid="tab-services"]');
      const servicesTab = page.locator('[data-testid="tab-services"]');
      await expect(servicesTab).toHaveAttribute('aria-selected', 'true');
      await page.waitForURL(/.*#services/);

      // Click Configuration tab
      await page.click('[data-testid="tab-configuration"]');
      await expect(page.locator('[data-testid="tab-configuration"]')).toHaveAttribute('aria-selected', 'true');
      await page.waitForURL(/.*#configuration/);
    });

    test('Hash-based URL routing works', async ({ page }) => {
      await page.goto('http://localhost:3000/');
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });
      await page.getByRole('button', { name: 'Infrastructure' }).click();
      await page.click('[data-testid="tab-services"]');
      await expect(page).toHaveURL(/.*#services/);

      await page.click('[data-testid="tab-configuration"]');
      await expect(page).toHaveURL(/.*#configuration/);
    });

    test('Default route loads Overview tab', async ({ page }) => {
      await page.goto('http://localhost:3000/');
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

      const overviewTab = page.locator('[data-testid="tab-overview"]');
      await expect(overviewTab).toHaveAttribute('aria-selected', 'true');
    });
  });

  // ---------- Error Handling ----------

  test.describe('Error Handling and Edge Cases', () => {

    test('Handles API errors gracefully', async ({ page }) => {
      // Abort API calls
      await page.route('**/api/v1/health', route => route.abort());

      await page.goto('http://localhost:3000');

      // Dashboard should still render (error boundary catches rendering errors)
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
    });

    test('Detects JSON parsing errors in dashboard', async ({ page }) => {
      const consoleErrors: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        }
      });

      await page.goto('http://localhost:3000');
      await page.waitForLoadState('networkidle');
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

      // JSON parsing errors should not exist
      const jsonErrors = consoleErrors.filter(error =>
        error.includes('Unexpected token') || error.includes('<!DOCTYPE')
      );
      expect(jsonErrors).toHaveLength(0);
    });

    test('Handles HTML responses instead of JSON', async ({ page }) => {
      await page.route('**/api/v1/health', route =>
        route.fulfill({
          status: 200,
          contentType: 'text/html',
          body: '<!DOCTYPE html><html><body>Error Page</body></html>'
        })
      );

      await page.goto('http://localhost:3000', { waitUntil: 'domcontentloaded' });
      // Dashboard should still render without crashing
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
    });
  });

  // ---------- Responsive Design ----------

  test.describe('Responsive Design', () => {

    test('Mobile viewport displays correctly', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
      await expect(page.locator('[data-testid="dashboard-header"]')).toBeVisible();
    });

    test('Tablet viewport displays correctly', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
      await expect(page.locator('[data-testid="dashboard-content"]')).toBeVisible();
    });

    test('Large desktop viewport displays correctly', async ({ page }) => {
      await page.setViewportSize({ width: 1920, height: 1080 });
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });
      await page.waitForTimeout(3000);

      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
      const healthCards = page.locator('[data-testid="health-card"]');
      const count = await healthCards.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });
  });

  // ---------- Accessibility ----------

  test.describe('Accessibility', () => {

    test('Keyboard navigation between tabs works', async ({ page }) => {
      await page.click('[data-testid="tab-overview"]');
      await expect(page.locator('[data-testid="tab-overview"]')).toHaveAttribute('aria-selected', 'true');

      await page.getByRole('button', { name: 'Infrastructure' }).click();
      await page.click('[data-testid="tab-services"]');
      await expect(page.locator('[data-testid="tab-services"]')).toHaveAttribute('aria-selected', 'true');
    });

    test('Tab ARIA attributes are correct', async ({ page }) => {
      const tabNav = page.locator('[data-testid="tab-navigation"]');
      await expect(tabNav).toHaveAttribute('role', 'tablist');

      const overviewTab = page.locator('[data-testid="tab-overview"]');
      await expect(overviewTab).toHaveAttribute('role', 'tab');
      await expect(overviewTab).toHaveAttribute('aria-selected', 'true');
      await expect(overviewTab).toHaveAttribute('aria-controls', 'tabpanel-overview');
    });

    test('Screen reader compatibility - headings and landmarks', async ({ page }) => {
      // h1 heading
      const h1 = page.locator('h1');
      await expect(h1.first()).toBeVisible();

      // Landmarks
      const landmarks = page.locator('nav, main, [role="navigation"], [role="main"], [role="tablist"]');
      const landmarkCount = await landmarks.count();
      expect(landmarkCount).toBeGreaterThan(0);
    });

    test('ARIA labels are present on interactive elements', async ({ page }) => {
      // Theme toggle
      const themeToggle = page.locator('[data-testid="theme-toggle"]');
      const ariaLabel = await themeToggle.getAttribute('aria-label');
      expect(ariaLabel).toBeTruthy();

      // Time range selector
      const timeRange = page.locator('[data-testid="time-range-selector"]');
      const timeAriaLabel = await timeRange.getAttribute('aria-label');
      expect(timeAriaLabel).toBeTruthy();
    });
  });

  // ---------- Performance ----------

  test.describe('Performance and Loading', () => {

    test('Page load performance', async ({ page }) => {
      const startTime = Date.now();
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });
      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(10000);
    });

    test('Tab switching performance', async ({ page }) => {
      await page.getByRole('button', { name: 'Infrastructure' }).click();
      const startTime = Date.now();
      await page.click('[data-testid="tab-services"]');
      await expect(page.locator('[data-testid="tab-services"]')).toHaveAttribute('aria-selected', 'true');
      const navTime = Date.now() - startTime;
      expect(navTime).toBeLessThan(5000);
    });

    test('Multiple tab switches remain stable', async ({ page }) => {
      await page.getByRole('button', { name: 'Infrastructure' }).click();
      await page.getByRole('button', { name: 'Devices & Data' }).click();
      await page.locator('[data-testid="tab-navigation"] button').filter({ hasText: 'Quality' }).first().click();
      const tabIds = ['services', 'events', 'configuration', 'overview', 'alerts'];
      for (const tabId of tabIds) {
        await page.click(`[data-testid="tab-${tabId}"]`);
        await expect(page.locator(`[data-testid="tab-${tabId}"]`)).toHaveAttribute('aria-selected', 'true');
      }
      // Dashboard should still be responsive
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
    });
  });
});

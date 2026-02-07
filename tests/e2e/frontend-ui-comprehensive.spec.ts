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
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });
  });

  // ---------- Dashboard Main Screen ----------

  test.describe('Dashboard Main Screen', () => {

    test('Dashboard loads completely with all components', async ({ page }) => {
      // Root container
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();

      // Header
      await expect(page.locator('[data-testid="dashboard-header"]')).toBeVisible();
      await expect(page.locator('[data-testid="dashboard-title"]')).toBeVisible();

      // Tab navigation
      await expect(page.locator('[data-testid="tab-navigation"]')).toBeVisible();
      await expect(page.locator('[data-testid="tab-overview"]')).toBeVisible();
      await expect(page.locator('[data-testid="tab-services"]')).toBeVisible();
      await expect(page.locator('[data-testid="tab-configuration"]')).toBeVisible();

      // Main content area
      await expect(page.locator('[data-testid="dashboard-content"]')).toBeVisible();

      // Health cards on Overview (at least 1)
      const healthCards = page.locator('[data-testid="health-card"]');
      const count = await healthCards.count();
      expect(count).toBeGreaterThanOrEqual(1);
    });

    test('Dashboard title displays HomeIQ Dashboard', async ({ page }) => {
      const title = page.locator('[data-testid="dashboard-title"]');
      await expect(title).toBeVisible();
      await expect(title).toContainText('HomeIQ Dashboard');
    });

    test('Health cards display on overview', async ({ page }) => {
      const healthCards = page.locator('[data-testid="health-card"]');
      const count = await healthCards.count();
      expect(count).toBeGreaterThanOrEqual(1);

      // Each card should be visible
      for (let i = 0; i < count; i++) {
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

    test('All 16 tabs are present', async ({ page }) => {
      const tabs = [
        'overview', 'setup', 'services', 'dependencies', 'devices',
        'events', 'logs', 'sports', 'data-sources', 'energy',
        'analytics', 'alerts', 'hygiene', 'validation', 'synergies', 'configuration'
      ];

      for (const tabId of tabs) {
        const tab = page.locator(`[data-testid="tab-${tabId}"]`);
        // Tab should exist (may be scrolled off-screen on mobile)
        await expect(tab).toBeAttached();
      }
    });

    test('Clicking tabs switches content', async ({ page }) => {
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
      // Navigate directly via hash
      await page.goto('http://localhost:3000/#services');
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

      const servicesTab = page.locator('[data-testid="tab-services"]');
      await expect(servicesTab).toHaveAttribute('aria-selected', 'true');

      await page.goto('http://localhost:3000/#configuration');
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

      const configTab = page.locator('[data-testid="tab-configuration"]');
      await expect(configTab).toHaveAttribute('aria-selected', 'true');
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

      await page.goto('http://localhost:3000');
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
      await expect(page.locator('[data-testid="tab-navigation"]')).toBeVisible();
    });

    test('Tablet viewport displays correctly', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
      // Switch tab to verify tab navigation works on tablet
      await page.click('[data-testid="tab-services"]');
      await expect(page.locator('[data-testid="tab-services"]')).toHaveAttribute('aria-selected', 'true');
    });

    test('Large desktop viewport displays correctly', async ({ page }) => {
      await page.setViewportSize({ width: 1920, height: 1080 });
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
      const healthCards = page.locator('[data-testid="health-card"]');
      const count = await healthCards.count();
      expect(count).toBeGreaterThanOrEqual(1);
    });
  });

  // ---------- Accessibility ----------

  test.describe('Accessibility', () => {

    test('Keyboard navigation between tabs works', async ({ page }) => {
      // Focus the first tab
      await page.click('[data-testid="tab-overview"]');
      await expect(page.locator('[data-testid="tab-overview"]')).toHaveAttribute('aria-selected', 'true');

      // Arrow right to next tab
      await page.keyboard.press('ArrowRight');
      const setupTab = page.locator('[data-testid="tab-setup"]');
      await expect(setupTab).toHaveAttribute('aria-selected', 'true');
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
      const startTime = Date.now();
      await page.click('[data-testid="tab-services"]');
      await expect(page.locator('[data-testid="tab-services"]')).toHaveAttribute('aria-selected', 'true');
      const navTime = Date.now() - startTime;
      expect(navTime).toBeLessThan(5000);
    });

    test('Multiple tab switches remain stable', async ({ page }) => {
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

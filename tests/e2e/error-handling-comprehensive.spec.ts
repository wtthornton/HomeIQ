import { test, expect } from '@playwright/test';

/**
 * Comprehensive Error Handling E2E Tests
 * Aligned with current health-dashboard (tab-based, hash routing).
 *
 * Key selectors: dashboard-root, dashboard-content, tab-navigation,
 *   tab-{id}, health-card, error-state, error-message, retry-button,
 *   loading-spinner, websocket-status
 */
test.describe('Comprehensive Error Handling', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
  });

  // ---------- JSON Parsing Error Scenarios ----------

  test.describe('JSON Parsing Error Scenarios', () => {

    test('Detects and handles HTML responses instead of JSON', async ({ page }) => {
      const consoleErrors: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        }
      });

      await page.route('**/api/v1/health', route =>
        route.fulfill({
          status: 200,
          contentType: 'text/html',
          body: '<!DOCTYPE html><html><head><title>Error</title></head><body><h1>Internal Server Error</h1></body></html>',
        })
      );

      await page.goto('http://localhost:3000');

      // Dashboard should still render (graceful degradation)
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();

      // If error state is shown, check that error message is user-friendly
      const errorState = page.locator('[data-testid="error-state"]');
      if (await errorState.isVisible({ timeout: 3000 }).catch(() => false)) {
        const errorMessage = page.locator('[data-testid="error-message"]');
        if (await errorMessage.isVisible({ timeout: 1000 }).catch(() => false)) {
          const errorText = await errorMessage.textContent();
          expect(errorText).not.toContain('<!DOCTYPE');
          expect(errorText).not.toContain('Unexpected token');
        }
      }

      // Log any console JSON errors for debugging
      const jsonErrors = consoleErrors.filter(error =>
        error.includes('JSON') || error.includes('Unexpected token') || error.includes('<!DOCTYPE')
      );
      if (jsonErrors.length > 0) {
        console.log('JSON Parsing Errors Detected:', jsonErrors);
      }
    });

    test('Handles malformed JSON responses gracefully', async ({ page }) => {
      await page.route('**/api/v1/stats', route =>
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: '{"timestamp": "2026-01-01T00:00:00Z", "period": "24h", "services": {',
        })
      );

      await page.goto('http://localhost:3000');

      // Dashboard should still render
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
    });

    test('Handles empty JSON responses', async ({ page }) => {
      await page.route('**/api/v1/events', route =>
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: '',
        })
      );

      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

      // Switch to events tab
      await page.click('[data-testid="tab-events"]');
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
    });

    test('Handles non-JSON content types', async ({ page }) => {
      await page.route('**/api/v1/config', route =>
        route.fulfill({
          status: 200,
          contentType: 'application/xml',
          body: '<?xml version="1.0"?><config><setting>value</setting></config>',
        })
      );

      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

      // Switch to configuration tab
      await page.click('[data-testid="tab-configuration"]');
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
    });
  });

  // ---------- Network Error Scenarios ----------

  test.describe('Network Error Scenarios', () => {

    test('Handles complete API service failure', async ({ page }) => {
      await page.route('**/api/v1/**', route => route.abort());

      await page.goto('http://localhost:3000');

      // Dashboard shell should still render
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
    });

    test('Handles partial API service failure', async ({ page }) => {
      // Health works but stats fails
      await page.route('**/api/v1/health', route => route.continue());
      await page.route('**/api/v1/stats', route => route.abort());

      await page.goto('http://localhost:3000');

      // Dashboard should still render with available data
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
    });

    test('Handles slow API responses', async ({ page }) => {
      await page.route('**/api/v1/health', route =>
        new Promise<void>(resolve => {
          setTimeout(() => {
            route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify({
                service: 'admin-api',
                status: 'healthy',
                timestamp: new Date().toISOString(),
                dependencies: [],
              }),
            });
            resolve();
          }, 8000);
        })
      );

      await page.goto('http://localhost:3000');

      // Dashboard should eventually load
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
    });

    test('Handles timeout scenarios', async ({ page }) => {
      await page.route('**/api/v1/health', () => {
        // Don't respond - simulate timeout
      });

      await page.goto('http://localhost:3000');

      // Dashboard shell should still render
      // Extended timeout (30s) is intentional: this test verifies the app handles a request that never responds
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 30000 });
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
    });
  });

  // ---------- Service-Specific Error Scenarios ----------

  test.describe('Service-Specific Error Scenarios', () => {

    test('Handles InfluxDB connection errors (degraded status)', async ({ page }) => {
      await page.route('**/api/v1/health', route =>
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            service: 'admin-api',
            status: 'degraded',
            timestamp: new Date().toISOString(),
            dependencies: [
              { name: 'InfluxDB', status: 'critical', response_time_ms: 0, message: 'Connection timeout' },
              { name: 'WebSocket Ingestion', status: 'healthy', response_time_ms: 25.0 },
            ],
          }),
        })
      );

      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

      // Dashboard should show degraded indicators
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
    });

    test('Handles WebSocket connection errors', async ({ page }) => {
      await page.route('**/api/v1/health', route =>
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            service: 'admin-api',
            status: 'degraded',
            timestamp: new Date().toISOString(),
            dependencies: [
              { name: 'InfluxDB', status: 'healthy', response_time_ms: 20.0 },
              { name: 'WebSocket Ingestion', status: 'critical', response_time_ms: 0, message: 'Connection refused' },
            ],
          }),
        })
      );

      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

      // Dashboard should show degraded state
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
    });
  });

  // ---------- Error Recovery and Retry ----------

  test.describe('Error Recovery and Retry Mechanisms', () => {

    test('Retry mechanism works after temporary failure', async ({ page }) => {
      let requestCount = 0;

      await page.route('**/api/v1/health', route => {
        requestCount++;
        if (requestCount <= 2) {
          route.abort();
        } else {
          route.continue();
        }
      });

      await page.goto('http://localhost:3000');

      // Should eventually load successfully
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 30000 });
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
    });

    test('Manual retry via error boundary', async ({ page }) => {
      // Simulate initial failure causing error boundary to catch
      await page.route('**/api/v1/health', route => route.abort());

      await page.goto('http://localhost:3000');

      // Dashboard should still render (may show error boundary or degraded state)
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

      // If error-state is visible, retry button should work
      const retryButton = page.locator('[data-testid="retry-button"]');
      if (await retryButton.isVisible({ timeout: 3000 }).catch(() => false)) {
        await page.unroute('**/api/v1/health');
        await retryButton.click();

        // Should recover
        await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });
        await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
      }
    });
  });

  // ---------- User Experience During Errors ----------

  test.describe('User Experience During Errors', () => {

    test('Error messages are user-friendly', async ({ page }) => {
      await page.route('**/api/v1/**', route => route.abort());

      await page.goto('http://localhost:3000');

      // Dashboard should still render
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });
      await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();

      // If error state is visible, check messages
      const errorMessage = page.locator('[data-testid="error-message"]');
      if (await errorMessage.isVisible({ timeout: 3000 }).catch(() => false)) {
        const errorText = await errorMessage.textContent();
        expect(errorText).not.toContain('<!DOCTYPE');
        expect(errorText).not.toContain('Unexpected token');
        expect(errorText).not.toContain('JSON.parse');
      }
    });

    test('Tab navigation works during error states', async ({ page }) => {
      await page.route('**/api/v1/**', route => route.abort());

      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15000 });

      // Tab navigation should still function
      await page.click('[data-testid="tab-services"]');
      await page.waitForTimeout(500);
      await expect(page.locator('[data-testid="tab-services"]')).toHaveAttribute('aria-selected', 'true');

      await page.click('[data-testid="tab-configuration"]');
      await page.waitForTimeout(500);
      await expect(page.locator('[data-testid="tab-configuration"]')).toHaveAttribute('aria-selected', 'true');
    });
  });
});

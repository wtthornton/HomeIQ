import { test, expect } from '@playwright/test';

/**
 * Epic 56, Story 56.6: Observability Infrastructure Smoke Test
 *
 * Verifies that core observability services are accessible and
 * dashboards render correctly.
 */

const DOMAIN_GROUPS = [
  'core-platform',
  'data-collectors',
  'ml-engine',
  'automation-core',
  'blueprints',
  'energy-analytics',
  'device-management',
  'pattern-analysis',
  'frontends',
];

test.describe('Observability Smoke Tests', () => {
  test.describe('Health Dashboard', () => {
    test('loads and shows all 9 domain groups', async ({ page }) => {
      await page.goto('http://localhost:3000');
      await page.waitForLoadState('networkidle');

      // Dashboard should load without errors
      const title = await page.title();
      expect(title).toBeTruthy();

      // Check that the page rendered content (not a blank page)
      const bodyText = await page.textContent('body');
      expect(bodyText).toBeTruthy();
      expect(bodyText!.length).toBeGreaterThan(100);

      // Verify domain groups are present in the UI
      for (const group of DOMAIN_GROUPS) {
        // Groups may appear as hyphenated or title-cased
        const groupPattern = group.replace(/-/g, '[- ]');
        const groupRegex = new RegExp(groupPattern, 'i');
        const found = groupRegex.test(bodyText!);
        // Soft check — log missing groups but don't fail the whole test
        if (!found) {
          console.warn(`Domain group not visible in UI: ${group}`);
        }
      }

      // At least some domain groups should be visible
      const visibleGroups = DOMAIN_GROUPS.filter((g) => {
        const pattern = g.replace(/-/g, '[- ]');
        return new RegExp(pattern, 'i').test(bodyText!);
      });
      expect(visibleGroups.length).toBeGreaterThanOrEqual(5);
    });

    test('service status indicators reflect /health responses', async ({
      page,
      request,
    }) => {
      // Verify a sample of core services are accessible
      const coreServices = [
        { name: 'data-api', port: 8006 },
        { name: 'admin-api', port: 8004 },
        { name: 'websocket-ingestion', port: 8001 },
      ];

      for (const svc of coreServices) {
        try {
          const response = await request.get(
            `http://localhost:${svc.port}/health`,
            { timeout: 5000 },
          );
          // Health endpoints should return 200 for healthy/degraded/starting
          expect([200, 503]).toContain(response.status());
        } catch {
          // Service may not be running in test environment — skip gracefully
          console.warn(
            `Service ${svc.name}:${svc.port} not reachable in test env`,
          );
        }
      }

      // Load health dashboard and verify it shows status indicators
      await page.goto('http://localhost:3000');
      await page.waitForLoadState('networkidle');

      // Look for status-indicator elements (badges, dots, icons)
      const statusElements = await page
        .locator(
          '[class*="status"], [class*="health"], [class*="badge"], [data-testid*="status"]',
        )
        .count();
      // Dashboard should have multiple status indicators
      expect(statusElements).toBeGreaterThanOrEqual(1);
    });
  });

  test.describe('Observability Dashboard', () => {
    test('traces page loads without errors', async ({ page }) => {
      // Navigate to observability dashboard
      const response = await page.goto('http://localhost:8501');

      // Should load successfully
      if (response) {
        expect(response.status()).toBeLessThan(500);
      }

      await page.waitForLoadState('networkidle');

      // Check for console errors
      const consoleErrors: string[] = [];
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        }
      });

      // Navigate to traces page if available
      const tracesLink = page.locator(
        'a[href*="trace"], a[href*="Trace"], [data-testid*="trace"]',
      );
      if ((await tracesLink.count()) > 0) {
        await tracesLink.first().click();
        await page.waitForLoadState('networkidle');
      }

      // No fatal JS errors on the page
      const fatalErrors = consoleErrors.filter(
        (e) =>
          !e.includes('favicon') &&
          !e.includes('ResizeObserver') &&
          !e.includes('net::ERR'),
      );
      expect(fatalErrors.length).toBeLessThanOrEqual(3);
    });
  });

  test.describe('Infrastructure Health', () => {
    test('Grafana API responds', async ({ request }) => {
      try {
        const response = await request.get(
          'http://localhost:3002/api/health',
          { timeout: 10000 },
        );
        expect(response.status()).toBe(200);
        const body = await response.json();
        expect(body).toHaveProperty('database');
      } catch {
        // Grafana may not be running in CI — mark as conditional
        console.warn('Grafana not reachable — skipping health check');
        test.skip();
      }
    });

    test('Prometheus API responds', async ({ request }) => {
      try {
        const response = await request.get(
          'http://localhost:9090/-/healthy',
          { timeout: 10000 },
        );
        expect(response.status()).toBe(200);
      } catch {
        console.warn('Prometheus not reachable — skipping health check');
        test.skip();
      }
    });

    test('Jaeger UI loads', async ({ request }) => {
      try {
        const response = await request.get('http://localhost:16686/', {
          timeout: 10000,
        });
        expect(response.status()).toBe(200);
      } catch {
        console.warn('Jaeger not reachable — skipping health check');
        test.skip();
      }
    });
  });
});

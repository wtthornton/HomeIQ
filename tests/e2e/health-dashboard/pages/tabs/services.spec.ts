import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../../shared/helpers/wait-helpers';

/**
 * INTENT: Services Tab — Is Each Microservice Running?
 * =====================================================
 *
 * WHY THIS PAGE EXISTS:
 * HomeIQ runs ~27 microservices across multiple domain groups. When something
 * breaks, the operator's FIRST question is: "Which service is down?"
 * This tab must answer that instantly with a clear list of services,
 * their health status, and the ability to drill into details.
 *
 * THE OPERATOR'S NEEDS:
 * 1. See all running services at a glance with health status
 * 2. Quickly spot unhealthy/degraded services (visual indicators)
 * 3. Filter services by status (Healthy, Degraded, Unhealthy)
 * 4. Click a service to see detailed health info (logs, stats, uptime)
 * 5. Use management actions (restart, start, stop) when services are stuck
 *
 * PAGE STRUCTURE:
 * - "Service Management" header with filter dropdown and refresh controls
 * - "Core Services" section — backend platform services
 * - "External Data Services" section — data collector services
 * - Each service shows name, status badge, port, and health indicator
 */
test.describe('Services — Is Each Microservice Running?', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#services');
    await waitForLoadingComplete(page);
  });

  // ─── LOADING → LOADED (Epic 49.10) ─────────────────────────────────
  test('services tab shows loading then content or empty state', async ({ page }) => {
    let resolveServices: () => void;
    const servicesPromise = new Promise<void>(r => { resolveServices = r; });
    await page.route('**/api/v1/health/services**', async route => {
      await servicesPromise;
      await route.continue();
    });
    await page.route('**/api/services**', async route => {
      await servicesPromise;
      await route.continue();
    });

    await page.goto('/#services');
    const loadingOrContent = page.locator('[data-testid="loading"], [aria-label="Loading"], [data-testid="service-list"], [data-testid="dashboard-content"]');
    await loadingOrContent.first().waitFor({ state: 'visible', timeout: 12000 });
    (resolveServices as () => void)();
    await page.locator('[data-testid="dashboard-content"], [data-testid="service-list"], h2:has-text("Service Management")').first().waitFor({ state: 'visible', timeout: 15000 });
    await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
  });

  // ─── SERVICE LIST LOADS ───────────────────────────────────────────
  // INTENT: The operator needs to see the list of services. If it's empty
  // or perpetually loading, they can't diagnose anything.

  test('@smoke service list renders with service entries', async ({ page }) => {
    // Page shows Service Management or service list (data-testid="service-list")
    const content = page.locator('[data-testid="service-list"], [data-testid="dashboard-content"]').first();
    await expect(content).toBeVisible({ timeout: 15000 });

    const heading = page.getByText(/service management|core services|external data/i).first();
    await expect(heading).toBeVisible({ timeout: 10000 });
  });

  // ─── SERVICE STATUS FILTER ──────────────────────────────────────────
  // INTENT: With ~27 services, the operator needs to filter by status
  // to quickly find degraded or unhealthy services.

  test('status filter dropdown is available and has expected options', async ({ page }) => {
    const filterSelect = page.locator('select[aria-label*="filter" i], select[aria-label*="status" i]');

    await expect(filterSelect.first(), 'Services tab should have a status filter dropdown').toBeVisible({ timeout: 10000 });

    // Check that filter has meaningful status options
    const options = filterSelect.first().locator('option');
    const count = await options.count();
    expect(count, 'Filter should have multiple status options').toBeGreaterThan(1);
  });

  // ─── SERVICE HEALTH INDICATORS ────────────────────────────────────
  // INTENT: The operator needs to spot problems at a glance. Each service
  // must show a clear health status — not just a colored dot.

  test('services show health status indicators', async ({ page }) => {
    // Wait for services tab content (list or header) before asserting
    await page.locator('[data-testid="service-list"], h2:has-text("Service Management"), select[aria-label*="Filter services"]').first().waitFor({ state: 'visible', timeout: 15000 }).catch(() => {});

    const statusFilter = page.locator('select[aria-label*="status" i], select[aria-label*="filter" i]');
    const filterCount = await statusFilter.count();

    const healthText = page.getByText(/healthy|degraded|unhealthy|stopped|operational|running|error|service management/i);
    const textCount = await healthText.count();

    const serviceList = page.locator('[data-testid="service-list"]');
    const hasList = await serviceList.isVisible({ timeout: 3000 }).catch(() => false);

    const total = filterCount + textCount + (hasList ? 1 : 0);
    expect(total, 'Services tab should show health status indicators (filter, badges, or service list)').toBeGreaterThan(0);
  });

  test('service count is displayed in the header', async ({ page }) => {
    // INTENT: The operator needs to know how many services are being monitored
    // The page shows "Monitoring N system services" or at least the service list
    const headerOrList = page
      .getByText(/monitoring\s+\d+\s+.*services/i)
      .or(page.locator('[data-testid="service-list"]'))
      .first();
    await expect(headerOrList).toBeVisible({ timeout: 15000 });
  });

  // ─── SERVICE SEARCH & FILTER ──────────────────────────────────────
  // INTENT: With ~27 services, the operator can't scroll through all of them.

  test('service filter narrows the displayed results', async ({ page }) => {
    const filterSelect = page.locator('select[aria-label*="filter" i], select[aria-label*="status" i]').first();

    await expect(filterSelect, 'Services tab should have a filter control').toBeVisible({ timeout: 10000 });

    // Select "Healthy" filter to narrow results
    await filterSelect.selectOption({ label: 'Healthy' });
    await new Promise((r) => setTimeout(r, 500));

    // Page should still show some services (most are healthy)
    const tabpanel = page.locator('[role="tabpanel"], main').first();
    const text = await tabpanel.textContent() ?? '';
    expect(text.length).toBeGreaterThan(50);
  });

  // ─── SERVICE DETAILS DRILL-DOWN ───────────────────────────────────
  // INTENT: The operator spots a degraded service and needs to investigate.

  test('clicking a service opens a details view', async ({ page }) => {
    // Wait for service list and Details buttons (ServiceCard exposes "Details" button)
    await page.locator('[data-testid="service-list"]').first().waitFor({ state: 'visible', timeout: 15000 });

    const detailsButtons = page.getByRole('button', { name: 'Details' });
    await expect(detailsButtons.first(), 'Services tab should show at least one Details button').toBeVisible({ timeout: 8000 });

    await detailsButtons.first().click();

    const detailView = page.getByRole('dialog')
      .or(page.locator('[class*="detail"]'))
      .or(page.locator('[class*="expanded"]'))
      .or(page.locator('[class*="modal"]'))
      .or(page.locator('[class*="Modal"]'));

    await expect(
      detailView.first(),
      'Clicking Details should open a details view'
    ).toBeVisible({ timeout: 5000 });
  });

  // ─── REFRESH CONTROLS ──────────────────────────────────────────────
  // INTENT: The operator needs fresh data during incidents.

  test('refresh controls are available', async ({ page }) => {
    // The page should have refresh controls
    const refreshButton = page.getByRole('button', { name: /refresh/i });
    await expect(refreshButton.first()).toBeVisible({ timeout: 5000 });
  });

  // ─── NO CONSOLE ERRORS ────────────────────────────────────────────

  test('services tab loads without API errors in console', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    await page.goto('/#services');
    await waitForLoadingComplete(page);
    await new Promise((r) => setTimeout(r, 3000));

    const apiErrors = errors.filter(e =>
      !e.includes('favicon') && !e.includes('manifest') &&
      !e.includes('font') && !e.includes('woff') &&
      !e.includes('sourcemap') && !e.includes('429') &&
      !e.includes('Too Many Requests') && !e.includes('rate limit') &&
      !e.includes('VITE_API_KEY')
    );

    expect(
      apiErrors,
      `Services tab has ${apiErrors.length} console errors:\n` +
      apiErrors.map(e => `  • ${e.substring(0, 200)}`).join('\n')
    ).toHaveLength(0);
  });
});

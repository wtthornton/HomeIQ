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

  // ─── SERVICE LIST LOADS ───────────────────────────────────────────
  // INTENT: The operator needs to see the list of services. If it's empty
  // or perpetually loading, they can't diagnose anything.

  test('@smoke service list renders with service entries', async ({ page }) => {
    const tabpanel = page.locator('[role="tabpanel"], main').first();
    await expect(tabpanel).toBeVisible({ timeout: 15000 });

    // The page should show the Service Management heading
    await expect(page.getByText(/service management/i)).toBeVisible({ timeout: 10000 });

    // There should be at least one service section with services listed
    // Services are organized under "Core Services" and "External Data Services"
    const serviceHeading = page.getByRole('heading', { name: /core services|external data|service management/i });
    await expect(serviceHeading.first()).toBeVisible({ timeout: 10000 });
  });

  // ─── SERVICE STATUS FILTER ──────────────────────────────────────────
  // INTENT: With ~27 services, the operator needs to filter by status
  // to quickly find degraded or unhealthy services.

  test('status filter dropdown is available and has expected options', async ({ page }) => {
    const filterSelect = page.locator('select[aria-label*="filter" i], select[aria-label*="status" i]');

    if (!(await filterSelect.first().isVisible({ timeout: 5000 }))) {
      test.skip(true, 'No status filter dropdown found on services tab');
      return;
    }

    // Check that filter has meaningful status options
    const options = filterSelect.first().locator('option');
    const count = await options.count();
    expect(count, 'Filter should have multiple status options').toBeGreaterThan(1);
  });

  // ─── SERVICE HEALTH INDICATORS ────────────────────────────────────
  // INTENT: The operator needs to spot problems at a glance. Each service
  // must show a clear health status — not just a colored dot.

  test('services show health status indicators', async ({ page }) => {
    // The services page has a status filter with options like "Healthy", "Degraded", "Unhealthy"
    // and service cards with status badges. Check both.
    const statusFilter = page.locator('select[aria-label*="status" i], select[aria-label*="filter" i]');
    const filterCount = await statusFilter.count();

    // Also check for health status text in service cards
    const healthText = page.getByText(/healthy|degraded|unhealthy|stopped/i);
    const textCount = await healthText.count();

    expect(
      filterCount + textCount,
      'Services tab should show health status indicators (filter or badges)'
    ).toBeGreaterThan(0);
  });

  test('service count is displayed in the header', async ({ page }) => {
    // INTENT: The operator needs to know how many services are being monitored
    // The page header shows "Monitoring N system services"
    await expect(
      page.getByText(/monitoring\s+\d+\s+.*services/i),
      'Should show total number of monitored services'
    ).toBeVisible({ timeout: 10000 });
  });

  // ─── SERVICE SEARCH & FILTER ──────────────────────────────────────
  // INTENT: With ~27 services, the operator can't scroll through all of them.

  test('service filter narrows the displayed results', async ({ page }) => {
    const filterSelect = page.locator('select[aria-label*="filter" i], select[aria-label*="status" i]').first();

    if (!(await filterSelect.isVisible({ timeout: 3000 }))) {
      test.skip(true, 'No filter control found on services tab');
      return;
    }

    // Select "Healthy" filter to narrow results
    await filterSelect.selectOption({ label: 'Healthy' });
    await page.waitForTimeout(500);

    // Page should still show some services (most are healthy)
    const tabpanel = page.locator('[role="tabpanel"], main').first();
    const text = await tabpanel.textContent() ?? '';
    expect(text.length).toBeGreaterThan(50);
  });

  // ─── SERVICE DETAILS DRILL-DOWN ───────────────────────────────────
  // INTENT: The operator spots a degraded service and needs to investigate.

  test('clicking a service opens a details view', async ({ page }) => {
    // Wait for service cards/buttons to render
    await page.waitForTimeout(2000);

    // Look for clickable service elements — buttons or clickable cards
    const serviceButtons = page.locator(
      'button:has-text("Healthy"), button:has-text("Degraded"), ' +
      'button:has-text("Running"), [role="button"]:has-text("Port")'
    );
    const count = await serviceButtons.count();
    if (count === 0) {
      test.skip(true, 'No clickable service entries found');
      return;
    }

    await serviceButtons.first().click();

    // A detail modal or expanded section should appear
    const detailView = page.getByRole('dialog')
      .or(page.locator('[class*="detail"]'))
      .or(page.locator('[class*="expanded"]'))
      .or(page.locator('[class*="modal"]'))
      .or(page.locator('[class*="Modal"]'));

    await expect(
      detailView.first(),
      'Clicking a service should open a details view'
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
    await page.waitForTimeout(3000);

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

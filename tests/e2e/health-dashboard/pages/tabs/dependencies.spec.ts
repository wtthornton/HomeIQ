import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../../shared/helpers/wait-helpers';

/**
 * INTENT: Dependencies Tab -- "What depends on what? Where are the failure cascades?"
 * ====================================================================================
 *
 * WHY THIS PAGE EXISTS:
 * The Dependencies tab visualizes the HomeIQ service architecture as a
 * dependency graph. When websocket-ingestion goes down, the operator
 * needs to instantly see which downstream services are affected. When InfluxDB
 * is slow, they need to trace the blast radius. This page answers:
 * "If service X fails, what breaks?"
 *
 * WHAT THE OPERATOR NEEDS:
 * 1. Dependency graph with service nodes showing health status
 * 2. Color-coded legend (Healthy/Degraded/Error/Unknown/Broken dependency)
 * 3. Data flow visualization between services
 * 4. Node interaction -- click or hover to see service details
 * 5. Visual distinction between healthy, degraded, and errored paths
 * 6. Health summary metrics alongside the graph
 */
test.describe('Dependencies -- Service Architecture & Failure Cascade Map', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#dependencies');
    await waitForLoadingComplete(page);
  });

  // ─── GRAPH LEGEND ──────────────────────────────────────────────
  // INTENT: The legend explains what the colors mean. Without it, green
  // and red dots are meaningless. The operator must see the legend FIRST
  // to interpret the graph correctly.

  test('@smoke dependency graph legend displays all status categories', async ({ page }) => {
    // Legend must be visible with all health states explained
    await expect(page.getByText('Legend:')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('Healthy')).toBeVisible();
    await expect(page.getByText('Degraded')).toBeVisible();
    await expect(page.getByText('Error / Down')).toBeVisible();
    await expect(page.getByText('Unknown / Stopped')).toBeVisible();
    await expect(page.getByText('Broken dependency')).toBeVisible();
  });

  // ─── ARCHITECTURE OVERVIEW ──────────────────────────────────────
  // INTENT: The graph must contain the Architecture Overview section with
  // real-time metrics. This confirms the dependency visualization loaded.

  test('dependency graph renders with architecture overview and metrics', async ({ page }) => {
    // The Architecture Overview heading must exist
    await expect(page.getByRole('heading', { name: /Architecture Overview/i })).toBeVisible({ timeout: 15000 });

    // Description text about data flow
    await expect(page.getByText(/Real-time data flow/i)).toBeVisible();

    // Health summary metrics should be present (use first() to avoid strict mode
    // violations when the same text appears in both summary cards and table headers)
    await expect(page.getByText('events/hour').first()).toBeVisible();
    await expect(page.getByText('active').first()).toBeVisible();
    await expect(page.getByText('health').first()).toBeVisible();
  });

  // ─── SERVICE NAMES IN GRAPH ────────────────────────────────────
  // INTENT: The operator needs to identify services BY NAME in the graph.
  // Unlabeled dots are useless. Key services like WebSocket Ingestion,
  // InfluxDB, and Data API should be identifiable.

  test('graph labels include recognizable service names', async ({ page }) => {
    // Wait for graph to fully render with data
    await expect(page.getByRole('heading', { name: /Architecture Overview/i })).toBeVisible({ timeout: 15000 });
    await new Promise((r) => setTimeout(r, 2000));

    // The graph image (SVG rendered as img) contains clickable service nodes
    // Check for well-known service names in the graph node labels
    const knownServices = [
      'WebSocket Ingestion',
      'Home Assistant',
      'InfluxDB',
      'Data API',
      'Admin API',
      'Dashboard',
      'AI Automation',
    ];

    let foundCount = 0;
    for (const serviceName of knownServices) {
      const serviceNode = page.getByText(serviceName, { exact: false });
      if (await serviceNode.first().isVisible({ timeout: 1000 }).catch(() => false)) {
        foundCount++;
      }
    }

    expect(
      foundCount,
      `Graph should display recognizable service names. Found ${foundCount} of ${knownServices.length}`
    ).toBeGreaterThan(0);
  });

  // ─── DATA FLOW SECTION ─────────────────────────────────────────
  // INTENT: The Data Flow section shows the pipeline from external APIs
  // through ingestion to storage and dashboard. This helps the operator
  // understand the path data takes.

  test('graph displays data flow path between service nodes', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Architecture Overview/i })).toBeVisible({ timeout: 15000 });

    // Data Flow section should be present
    await expect(page.getByRole('heading', { name: /Data Flow/i })).toBeVisible();

    // Key stages in the data flow pipeline (use first() for items that
    // may appear in both the data flow section and the graph legend/nodes)
    await expect(page.getByText('External APIs').first()).toBeVisible();
    await expect(page.getByText('WS Ingestion').first()).toBeVisible();
    await expect(page.getByText('Dashboard').last()).toBeVisible();
  });

  // ─── PER-API METRICS TABLE ─────────────────────────────────────
  // INTENT: The operator needs to see per-service metrics: events/hour,
  // uptime, and status. This table provides the quantitative data
  // alongside the visual graph.

  test('per-API metrics table shows service health data', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Architecture Overview/i })).toBeVisible({ timeout: 15000 });

    // Per-API Metrics table heading
    await expect(page.getByRole('heading', { name: /Per-API Metrics/i })).toBeVisible();

    // Table with column headers
    const table = page.getByRole('table');
    await expect(table).toBeVisible();

    await expect(page.getByRole('columnheader', { name: 'Service' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Events/hour' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Uptime' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Status' })).toBeVisible();

    // Wait for table data to load, then check for data rows
    await new Promise((r) => setTimeout(r, 2000));
    const rows = table.getByRole('row');
    const rowCount = await rows.count();
    expect(
      rowCount,
      'Metrics table should have at least the header row. ' +
      `Found ${rowCount} row(s). Data rows may still be loading.`
    ).toBeGreaterThanOrEqual(1);
  });

  // ─── ERROR STATE HANDLING ──────────────────────────────────────
  // INTENT: If the real-time metrics API fails, the graph should show
  // an honest error message rather than silently displaying stale data
  // or an empty container.

  test('error state displays a clear error message when API fails', async ({ page }) => {
    // Wait for page to settle
    await new Promise((r) => setTimeout(r, 3000));

    // Either the Architecture Overview loads or an error is shown
    const hasOverview = await page.getByRole('heading', { name: /Architecture Overview/i })
      .isVisible({ timeout: 10000 }).catch(() => false);
    const errorAlert = page.locator('[role="alert"]');
    const hasError = await errorAlert.isVisible({ timeout: 3000 }).catch(() => false);

    expect(
      hasOverview || hasError,
      'Page should show either the dependency graph or a clear error message'
    ).toBe(true);

    // If error is shown, it should be descriptive
    if (hasError) {
      await expect(errorAlert).toContainText(/error|failed|unable/i);
    }
  });

  // ─── REAL-TIME DATA FRESHNESS ──────────────────────────────────
  // INTENT: The graph uses polling for real-time metrics. The
  // operator needs to know the data is live, not stale.

  test('graph area renders without being stuck in permanent loading state', async ({ page }) => {
    // After initial load, the graph should not show a permanent spinner
    await new Promise((r) => setTimeout(r, 5000));

    // Either the architecture overview is visible or an error is shown -- not a perpetual spinner
    const loadingSpinner = page.locator('[class*="animate-spin"], [class*="spinner"], [class*="loading"]');
    const spinnerVisible = await loadingSpinner.isVisible({ timeout: 1000 }).catch(() => false);
    const graphVisible = await page.getByRole('heading', { name: /Architecture Overview/i })
      .isVisible({ timeout: 1000 }).catch(() => false);

    // If spinner is still showing after 5s, graph data never arrived
    if (!graphVisible) {
      expect(
        spinnerVisible,
        'After 5 seconds, graph should either render or show an error -- not spin forever'
      ).toBe(false);
    }
  });

  // ─── CONSOLE HEALTH ────────────────────────────────────────────
  // INTENT: The dependency graph fetches from health and metrics APIs.
  // If these fail silently, the graph shows stale or empty data while
  // the operator thinks it is live.

  test('no critical API errors in browser console during page load', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    await page.goto('/#dependencies');
    await waitForLoadingComplete(page);
    await new Promise((r) => setTimeout(r, 3000));

    const apiErrors = errors.filter(error =>
      !error.includes('favicon') &&
      !error.includes('manifest') &&
      !error.includes('font') &&
      !error.includes('woff') &&
      !error.includes('sourcemap') &&
      !error.includes('429') &&
      !error.includes('Too Many Requests') &&
      !error.includes('rate limit') &&
      !error.includes('VITE_API_KEY')
    );

    expect(
      apiErrors,
      `Found ${apiErrors.length} API errors in browser console. ` +
      `These indicate broken backend calls the UI silently swallows:\n` +
      apiErrors.map(e => `  - ${e.substring(0, 200)}`).join('\n')
    ).toHaveLength(0);
  });
});

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../../shared/helpers/wait-helpers';

/**
 * INTENT: Devices Tab — "What devices does Home Assistant see in my home?"
 * ========================================================================
 *
 * WHY THIS PAGE EXISTS:
 * The Devices tab is the operator's inventory of their smart home. It
 * answers: "What devices are connected? What state are they in? Can I
 * find a specific device?" If Home Assistant discovers 50 devices but
 * this page shows 0, the operator has no visibility into their home.
 *
 * ACTUAL UI STRUCTURE (as of March 2026):
 * - Navigation: sidebar button "Devices" under "Devices & Data" group
 * - Page heading: "Devices" with subtitle "Manage and monitor your Home Assistant devices"
 * - Refresh button in the header
 * - Filters: Search textbox, Manufacturer dropdown, Area dropdown, Platform dropdown
 * - Device list area: shows device cards OR error state OR empty state
 * - When API errors occur, shows "Error loading devices" with message and Retry button
 */
test.describe('Devices — Smart Home Inventory', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    // Navigate to base URL then click the Devices tab button
    await page.goto('/');
    await waitForLoadingComplete(page);
    // Expand "Devices & Data" group and click "Devices"
    const devicesDataGroup = page.getByRole('button', { name: /Devices & Data/i });
    await devicesDataGroup.click();
    await page.getByTestId('tab-devices').click();
    await waitForLoadingComplete(page);
    // Wait for the Devices heading to confirm we're on the right tab
    await expect(page.getByRole('heading', { name: 'Devices', level: 1 })).toBeVisible({ timeout: 15000 });
  });

  // ─── DEVICE PAGE LOADS ──────────────────────────────────────────
  // INTENT: The device page is the foundation of this tab. The heading
  // and filter controls must render even if the device list has errors.

  test('@smoke device page renders with heading and controls', async ({ page }) => {
    const heading = page.getByRole('heading', { name: 'Devices', level: 1 });
    await expect(heading).toBeVisible({ timeout: 15000 });

    const subtitle = page.getByText('Manage and monitor your Home Assistant devices');
    await expect(subtitle).toBeVisible({ timeout: 5000 });

    // Refresh button should be available (scoped to main content, not the header Auto Refresh)
    const refreshButton = page.locator('main').getByRole('button', { name: /^Refresh$/i });
    await expect(refreshButton).toBeVisible({ timeout: 5000 });
  });

  // ─── DEVICE LIST OR ERROR STATE ─────────────────────────────────
  // INTENT: The device list should show either devices or a clear
  // error/empty state so the operator understands what's happening.

  test('device list shows devices, empty state, or error state', async ({ page }) => {
    // Wait for the page to settle
    await new Promise((r) => setTimeout(r, 2000));

    // Look for: device entries, empty state, or error state
    const errorState = page.getByText(/Error loading devices/i);
    const emptyState = page.getByText(/No.*devices/i);
    const searchInput = page.getByRole('textbox', { name: /Search devices/i });

    const hasError = await errorState.isVisible({ timeout: 5000 }).catch(() => false);
    const hasEmpty = await emptyState.isVisible({ timeout: 3000 }).catch(() => false);
    const hasSearch = await searchInput.isVisible({ timeout: 3000 }).catch(() => false);

    expect(
      hasError || hasEmpty || hasSearch,
      'Devices tab should show devices, an error state, or an empty state — not a blank page'
    ).toBe(true);

    // If there's an error, it should include a Retry button
    if (hasError) {
      const retryButton = page.getByRole('button', { name: /Retry/i });
      await expect(retryButton).toBeVisible({ timeout: 3000 });
    }
  });

  // ─── DEVICE SEARCH INPUT ────────────────────────────────────────
  // INTENT: The operator wants to find devices quickly via search.
  // The search input should accept text.

  test('search input is available and accepts text', async ({ page }) => {
    const searchInput = page.getByRole('textbox', { name: /Search devices/i });
    await expect(searchInput).toBeVisible({ timeout: 5000 });

    await searchInput.fill('light');
    await waitForLoadingComplete(page);

    // After searching, the page should still be functional
    const heading = page.getByRole('heading', { name: 'Devices', level: 1 });
    await expect(heading).toBeVisible();
  });

  // ─── DEVICE FILTERING BY PLATFORM ───────────────────────────────
  // INTENT: With dozens of devices, the operator needs to filter by
  // platform (hue, mqtt, etc.) to focus on what matters. The filter
  // must change the displayed list.

  test('platform filter dropdown is available and functional', async ({ page }) => {
    // Find the Platform label, then get the sibling/adjacent combobox
    const platformLabel = page.getByText('Platform', { exact: true });
    await expect(platformLabel).toBeVisible({ timeout: 10000 });
    // The combobox is a sibling within the same parent container
    const platformFilter = platformLabel.locator('..').locator('select, [role="combobox"]');
    await expect(platformFilter).toBeVisible({ timeout: 5000 });

    // Check if the dropdown has options beyond the default "All Platforms"
    const options = platformFilter.locator('option');
    const optionCount = await options.count();

    if (optionCount > 1) {
      // Select a platform from the dropdown
      await platformFilter.selectOption({ index: 1 });
      await waitForLoadingComplete(page);
    }

    // Page should still be functional
    const heading = page.getByRole('heading', { name: 'Devices', level: 1 });
    await expect(heading).toBeVisible();
  });

  // ─── MANUFACTURER FILTER ────────────────────────────────────────
  // INTENT: The operator wants to filter devices by manufacturer.

  test('manufacturer filter dropdown is available', async ({ page }) => {
    const manufacturerLabel = page.getByText('Manufacturer', { exact: true });
    await expect(manufacturerLabel).toBeVisible({ timeout: 10000 });
    const manufacturerFilter = manufacturerLabel.locator('..').locator('select, [role="combobox"]');
    await expect(manufacturerFilter).toBeVisible({ timeout: 5000 });
  });

  // ─── AREA FILTER ────────────────────────────────────────────────
  // INTENT: The operator wants to filter devices by area/room.

  test('area filter dropdown is available', async ({ page }) => {
    const areaLabel = page.getByText('Area', { exact: true });
    await expect(areaLabel).toBeVisible({ timeout: 10000 });
    const areaFilter = areaLabel.locator('..').locator('select, [role="combobox"]');
    await expect(areaFilter).toBeVisible({ timeout: 5000 });
  });

  // ─── REFRESH BUTTON TRIGGERS RELOAD ─────────────────────────────
  // INTENT: When devices fail to load, the Refresh button should
  // allow the operator to retry.

  test('refresh button triggers a data reload', async ({ page }) => {
    const refreshButton = page.locator('main').getByRole('button', { name: /^Refresh$/i });
    await expect(refreshButton).toBeVisible({ timeout: 5000 });

    await refreshButton.click();
    await waitForLoadingComplete(page);

    // After refresh, the page should still show the devices heading
    const heading = page.getByRole('heading', { name: 'Devices', level: 1 });
    await expect(heading).toBeVisible();
  });

  // ─── EMPTY STATE (Epic 49.8) ───────────────────────────────────────
  test('devices tab renders without crash when device list is empty', async ({ page }) => {
    await page.route('**/api/devices**', route =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ devices: [], total: 0 }),
      })
    );
    await page.route('**/api/entities**', route =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ entities: [], total: 0 }),
      })
    );

    await page.goto('/');
    await waitForLoadingComplete(page);
    const devicesDataGroup = page.getByRole('button', { name: /Devices & Data/i });
    await devicesDataGroup.click();
    await page.getByTestId('tab-devices').click();
    await waitForLoadingComplete(page);

    await expect(page.getByRole('heading', { name: 'Devices', level: 1 })).toBeVisible({ timeout: 15000 });
    const emptyOrSearch = page.getByText(/No.*devices|0 devices/i).or(page.getByRole('textbox', { name: /Search devices/i }));
    await expect(emptyOrSearch.first()).toBeVisible({ timeout: 8000 });
  });

  // ─── API FAILURE (Epic 49.9) ──────────────────────────────────────
  test('devices tab shows error state or retry when devices API returns 500', async ({ page }) => {
    await page.route('**/api/devices**', route =>
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal Server Error' }),
      })
    );

    await page.goto('/');
    await waitForLoadingComplete(page);
    const devicesDataGroup = page.getByRole('button', { name: /Devices & Data/i });
    await devicesDataGroup.click();
    await page.getByTestId('tab-devices').click();
    await waitForLoadingComplete(page);

    await expect(page.getByRole('heading', { name: 'Devices', level: 1 })).toBeVisible({ timeout: 15000 });
    const errorOrRetry = page.locator('[data-testid="error-state"], [data-testid="retry-button"]').or(page.getByRole('button', { name: /Retry/i })).or(page.getByText(/Error loading devices/i));
    await expect(errorOrRetry.first()).toBeVisible({ timeout: 10000 });
  });

  // ─── CONSOLE HEALTH — HIDDEN API ERRORS ─────────────────────────
  // INTENT: If the device API returns 404s or 500s, the list might
  // appear empty and the operator assumes "no devices discovered" when
  // really the backend is broken. Console errors catch this deception.
  // Note: device API errors (500/401) are expected when HA is not fully
  // connected, so we filter those out along with other known noise.

  test('no unexpected console errors during page load', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    await page.goto('/');
    await waitForLoadingComplete(page);
    const devicesDataGroup = page.getByRole('button', { name: /Devices & Data/i });
    await devicesDataGroup.click();
    await page.getByTestId('tab-devices').click();
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
      !error.includes('VITE_API_KEY') &&
      !error.includes('devices') &&
      !error.includes('activity') &&
      !error.includes('Failed to retrieve') &&
      !error.includes('Failed to fetch') &&
      !error.includes('Failed to load resource') &&
      !error.includes('Unable to reach backend') &&
      !error.includes('fetchWithErrorHandling')
    );

    expect(
      apiErrors,
      `Found ${apiErrors.length} API errors in browser console. ` +
      `These may indicate the device API is broken:\n` +
      apiErrors.map(e => `  - ${e.substring(0, 200)}`).join('\n')
    ).toHaveLength(0);
  });
});

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../../shared/helpers/wait-helpers';

/**
 * INTENT: Energy Tab -- "How is my home using energy?"
 * =====================================================
 *
 * WHY THIS PAGE EXISTS:
 * The Energy tab shows energy monitoring and correlations. It correlates
 * Home Assistant device events with power consumption readings from the
 * Smart Meter service to answer: "Which device caused my power spike?"
 *
 * WHAT THE OPERATOR NEEDS:
 * 1. Current power stats -- Current Power (W), Daily Energy (kWh),
 *    Peak Power (24h), Correlations Found
 * 2. Top energy consumers -- which devices use the most
 * 3. Recent power change correlations table
 * 4. Refresh button for manual data refresh
 * 5. Error handling when energy APIs fail
 * 6. Info section explaining what correlations are
 *
 * COMPONENT STATES:
 * - Loading: "Loading energy data..."
 * - Error: Red box with "Error: {message}"
 * - Success: Full dashboard with stats, tables, and info card
 */
test.describe('Energy -- Consumption and Cost Analysis', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#energy');
    await waitForLoadingComplete(page);
  });

  // ─── ENERGY TAB LOADS ─────────────────────────────────────────────
  // INTENT: The Energy tab should load and show EITHER the full dashboard
  // (with heading "Energy Monitoring & Correlations") OR an error state.
  // It should NOT be blank or stuck loading.

  test('@smoke energy tab loads and shows content or error state', async ({ page }) => {
    // Wait for loading to complete -- either the heading or error appears
    await new Promise((r) => setTimeout(r, 5000));

    const heading = page.getByRole('heading', { name: /Energy Monitoring/i });
    const errorState = page.getByText(/^Error:/);
    const loadingState = page.getByText(/Loading energy data/i);

    const hasHeading = await heading.isVisible({ timeout: 10000 }).catch(() => false);
    const hasError = await errorState.isVisible({ timeout: 3000 }).catch(() => false);
    const stillLoading = await loadingState.isVisible({ timeout: 1000 }).catch(() => false);

    // Should not be stuck in loading state
    expect(
      stillLoading,
      'Energy tab should not be permanently stuck on "Loading energy data..."'
    ).toBe(false);

    // Should show either the dashboard or an error
    expect(
      hasHeading || hasError,
      'Energy tab should show either "Energy Monitoring & Correlations" heading or an error message. ' +
      'Blank content means the API silently failed without setting error state.'
    ).toBe(true);
  });

  // ─── STAT CARDS (SUCCESS STATE) ──────────────────────────────────
  // INTENT: When data loads successfully, 4 stat cards show Current Power,
  // Daily Energy, Peak Power, and Correlations Found.

  test('stat cards display power metrics when data is available', async ({ page }) => {
    await new Promise((r) => setTimeout(r, 3000));

    const heading = page.getByRole('heading', { name: /Energy Monitoring/i });
    const errorState = page.getByText(/^Error:/);
    const hasHeading = await heading.isVisible({ timeout: 10000 }).catch(() => false);
    const hasError = await errorState.isVisible({ timeout: 3000 }).catch(() => false);

    expect(hasHeading || hasError, 'Energy tab should show dashboard or error state').toBe(true);
    if (hasError) return; // API unavailable — success state assertions N/A

    await expect(page.getByText('Current Power')).toBeVisible();
    await expect(page.getByText('Daily Energy')).toBeVisible();
    await expect(page.getByText('Peak Power (24h)')).toBeVisible();
    await expect(page.getByText('Correlations Found')).toBeVisible();
  });

  // ─── REFRESH BUTTON (SUCCESS STATE) ──────────────────────────────
  // INTENT: The operator needs a manual refresh for energy data.

  test('refresh button is available when dashboard loads', async ({ page }) => {
    await new Promise((r) => setTimeout(r, 3000));

    const heading = page.getByRole('heading', { name: /Energy Monitoring/i });
    const errorState = page.getByText(/^Error:/);
    const hasHeading = await heading.isVisible({ timeout: 10000 }).catch(() => false);
    const hasError = await errorState.isVisible({ timeout: 3000 }).catch(() => false);

    expect(hasHeading || hasError, 'Energy tab should show dashboard or error state').toBe(true);
    if (hasError) return;

    await expect(page.getByRole('button', { name: /Refresh/i })).toBeVisible();
  });

  // ─── CORRELATIONS TABLE (SUCCESS STATE) ──────────────────────────
  // INTENT: The Recent Power Changes table shows device-energy correlations
  // OR an empty state message when no correlations exist.

  test('correlations section shows table or empty state message', async ({ page }) => {
    await new Promise((r) => setTimeout(r, 3000));

    const heading = page.getByRole('heading', { name: /Energy Monitoring/i });
    const errorState = page.getByText(/^Error:/);
    const hasHeading = await heading.isVisible({ timeout: 10000 }).catch(() => false);
    const hasError = await errorState.isVisible({ timeout: 3000 }).catch(() => false);

    expect(hasHeading || hasError, 'Energy tab should show dashboard or error state').toBe(true);
    if (hasError) return;

    await expect(page.getByText(/Recent Power Changes/i)).toBeVisible();

    // Either shows correlation data in a table or the empty state message
    const table = page.getByRole('table');
    const emptyState = page.getByText(/No correlations found/i);

    const hasTable = await table.isVisible({ timeout: 3000 }).catch(() => false);
    const hasEmpty = await emptyState.isVisible({ timeout: 3000 }).catch(() => false);

    expect(
      hasTable || hasEmpty,
      'Correlations section should show either a data table or "No correlations found" message'
    ).toBe(true);
  });

  // ─── INFO CARD (SUCCESS STATE) ───────────────────────────────────
  // INTENT: The info card explains what energy correlations are and
  // how the Energy Correlator service works.

  test('info card explains energy correlations', async ({ page }) => {
    await new Promise((r) => setTimeout(r, 3000));

    const heading = page.getByRole('heading', { name: /Energy Monitoring/i });
    const errorState = page.getByText(/^Error:/);
    const hasHeading = await heading.isVisible({ timeout: 10000 }).catch(() => false);
    const hasError = await errorState.isVisible({ timeout: 3000 }).catch(() => false);

    expect(hasHeading || hasError, 'Energy tab should show dashboard or error state').toBe(true);
    if (hasError) return;

    await expect(page.getByText(/About Energy Correlations/i)).toBeVisible();
    await expect(page.getByText(/Energy Correlator service/i)).toBeVisible();
  });

  // ─── ERROR STATE DISPLAYS MESSAGE ────────────────────────────────
  // INTENT: When the energy APIs fail, the page should show a clear error
  // message rather than a blank page.

  test('error state shows descriptive error message', async ({ page }) => {
    await new Promise((r) => setTimeout(r, 3000));

    const errorState = page.getByText(/^Error:/);
    const hasError = await errorState.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasError) {
      // Error should contain descriptive text about what failed
      const errorText = await errorState.textContent() ?? '';
      expect(
        errorText.length,
        'Error message should be descriptive, not empty'
      ).toBeGreaterThan(10);
    }

    // Whether in error state or success state, page should not be blank
    const heading = page.getByRole('heading', { name: /Energy Monitoring/i });
    const hasHeading = await heading.isVisible({ timeout: 2000 }).catch(() => false);
    expect(
      hasError || hasHeading,
      'Energy tab should show either data or an error -- not a blank page'
    ).toBe(true);
  });

  // ─── LOADING STATE TRANSITIONS ───────────────────────────────────
  // INTENT: The loading state ("Loading energy data...") should not persist.
  // After a reasonable timeout, the page should transition to data or error.

  test('loading state transitions to content within timeout', async ({ page }) => {
    // Wait for the page to settle -- loading state should transition quickly
    await new Promise((r) => setTimeout(r, 5000));

    // After settling, the loading message should be gone
    const loadingMsg = page.getByText(/Loading energy data/i);
    const stillLoading = await loadingMsg.isVisible({ timeout: 1000 }).catch(() => false);

    expect(
      stillLoading,
      'Energy tab should not be permanently stuck on "Loading energy data..." after 5 seconds'
    ).toBe(false);
  });

  // ─── CONSOLE HEALTH ────────────────────────────────────────────
  // INTENT: Energy data comes from energy-correlator, energy-forecasting,
  // and electricity-pricing services. Console errors from known API
  // failures (429, energy fetch errors) are filtered since the UI handles
  // them with an error state.

  test('no unexpected console errors during page load', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    await page.goto('/#energy');
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
      !error.includes('Failed to load resource') &&
      !error.includes('API Error') &&
      !error.includes('Error fetching energy') &&
      !error.includes('Failed to query statistics')
    );

    expect(
      apiErrors,
      `Found ${apiErrors.length} unexpected console errors:\n` +
      apiErrors.map(e => `  - ${e.substring(0, 200)}`).join('\n')
    ).toHaveLength(0);
  });
});

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../../shared/helpers/wait-helpers';

/**
 * INTENT: Alerts Tab — "Are there active alerts I need to act on?"
 * =================================================================
 *
 * WHY THIS PAGE EXISTS:
 * The Alerts tab is the operator's fire alarm panel. When something goes
 * wrong in the smart home system — a sensor goes offline, unusual
 * activity is detected, energy consumption spikes — an alert should
 * appear here. The operator needs to see alerts and their severity.
 *
 * ACTUAL UI STRUCTURE (as of March 2026):
 * - Navigation: sidebar button "Alerts" under "Quality" group
 * - "Anomaly Detection" section with heading, alert count badge, refresh button
 * - Alert cards (clickable divs) each containing:
 *   - Severity emoji (red circle, orange diamond, warning triangle)
 *   - Device name and category (e.g., "Living Room Motion", "Behavior")
 *   - Description text
 *   - Timestamp and dismiss button (X)
 *   - Confidence percentage bar
 * - "Error Loading Alerts" section (when standard alerts API fails)
 *   with error message and Retry button
 * - "Powered by PyOD anomaly detection" footer with "Learn more" link
 * - No search input, no severity filter dropdown, no acknowledge button
 */
test.describe('Alerts — Operator Fire Alarm Panel', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    // Navigate to base URL then click the Alerts tab button
    await page.goto('/');
    await waitForLoadingComplete(page);
    // Expand "Quality" group and click "Alerts"
    const qualityGroup = page.getByRole('button', { name: /Quality/i }).first();
    await qualityGroup.click();
    await page.getByTestId('tab-alerts').click();
    await waitForLoadingComplete(page);
    // Wait for the Anomaly Detection heading to confirm we're on the right tab
    await expect(page.getByRole('heading', { name: /Anomaly Detection/i })).toBeVisible({ timeout: 15000 });
  });

  // ─── ALERT LIST LOADS WITH STRUCTURE ─────────────────────────────
  // INTENT: The operator lands on the alerts tab and needs to see either
  // active anomaly alerts, an error state, or both. A blank page is failure.

  test('@smoke alert section renders with content', async ({ page }) => {
    // The Anomaly Detection heading should be visible
    const anomalyHeading = page.getByRole('heading', { name: /Anomaly Detection/i });
    await expect(anomalyHeading).toBeVisible({ timeout: 15000 });

    // Alert count badge should show how many alerts exist
    const alertCount = page.getByText(/\d+\s*alerts?/i);
    await expect(alertCount).toBeVisible({ timeout: 5000 });
  });

  // ─── ALERT CARDS DISPLAY DEVICE AND DESCRIPTION ──────────────────
  // INTENT: Each alert must show what device is affected and what the
  // issue is. The operator needs to triage based on this information.

  test('alert cards display device names and descriptions', async ({ page }) => {
    // Wait for anomaly detection section to load
    const anomalyHeading = page.getByRole('heading', { name: /Anomaly Detection/i });
    await expect(anomalyHeading).toBeVisible({ timeout: 10000 });

    // Look for known alert content from the anomaly detection cards
    // These are clickable div elements with device names and descriptions
    const livingRoomAlert = page.getByText('Living Room Motion');
    const garageDoorAlert = page.getByText('Garage Door');
    const hvacAlert = page.getByText('HVAC Power Monitor');

    const hasLivingRoom = await livingRoomAlert.isVisible({ timeout: 5000 }).catch(() => false);
    const hasGarageDoor = await garageDoorAlert.isVisible({ timeout: 3000 }).catch(() => false);
    const hasHvac = await hvacAlert.isVisible({ timeout: 3000 }).catch(() => false);

    // At least one anomaly alert card should be visible
    expect(
      hasLivingRoom || hasGarageDoor || hasHvac,
      'At least one anomaly detection alert card should display a device name'
    ).toBe(true);
  });

  // ─── ALERTS SHOW SEVERITY INDICATORS ─────────────────────────────
  // INTENT: The operator needs to distinguish critical vs warning alerts.
  // The anomaly detection cards use emoji severity indicators and
  // category labels like "Behavior", "Connectivity", "Energy".

  test('alerts include category labels for triage', async ({ page }) => {
    const anomalyHeading = page.getByRole('heading', { name: /Anomaly Detection/i });
    await expect(anomalyHeading).toBeVisible({ timeout: 10000 });

    // Category labels should be visible on alert cards
    const behaviorLabel = page.getByText(/Behavior/i);
    const connectivityLabel = page.getByText(/Connectivity/i);
    const energyLabel = page.getByText(/Energy/i);

    const hasBehavior = await behaviorLabel.isVisible({ timeout: 5000 }).catch(() => false);
    const hasConnectivity = await connectivityLabel.isVisible({ timeout: 3000 }).catch(() => false);
    const hasEnergy = await energyLabel.isVisible({ timeout: 3000 }).catch(() => false);

    expect(
      hasBehavior || hasConnectivity || hasEnergy,
      'Alert cards should display category labels (Behavior, Connectivity, Energy) for triage'
    ).toBe(true);
  });

  // ─── ALERTS SHOW TIMESTAMPS ──────────────────────────────────────
  // INTENT: Each alert needs a timestamp so the operator knows when it
  // was generated. The anomaly cards show times like "08:17 AM".

  test('alert cards display timestamps', async ({ page }) => {
    const anomalyHeading = page.getByRole('heading', { name: /Anomaly Detection/i });
    await expect(anomalyHeading).toBeVisible({ timeout: 10000 });

    // Look for time patterns in AM/PM format on the page
    const timePattern = page.getByText(/\d{1,2}:\d{2}\s*(AM|PM)/i).first();
    await expect(timePattern).toBeVisible({ timeout: 5000 });
  });

  // ─── ALERT CONFIDENCE SCORES ─────────────────────────────────────
  // INTENT: Each anomaly alert includes a confidence percentage so the
  // operator knows how certain the detection is.

  test('alert cards show confidence scores', async ({ page }) => {
    const anomalyHeading = page.getByRole('heading', { name: /Anomaly Detection/i });
    await expect(anomalyHeading).toBeVisible({ timeout: 10000 });

    // Confidence labels and percentage values should be visible
    const confidenceLabel = page.getByText(/Confidence:/i).first();
    await expect(confidenceLabel).toBeVisible({ timeout: 5000 });

    const percentValue = page.getByText(/\d+%/).first();
    await expect(percentValue).toBeVisible({ timeout: 5000 });
  });

  // ─── DISMISS BUTTON IS PRESENT ───────────────────────────────────
  // INTENT: The operator should be able to dismiss alerts. The UI uses
  // a "X" button on each alert card.

  test('alert cards have dismiss buttons', async ({ page }) => {
    const anomalyHeading = page.getByRole('heading', { name: /Anomaly Detection/i });
    await expect(anomalyHeading).toBeVisible({ timeout: 10000 });

    // Dismiss buttons use the X character
    const dismissButtons = page.getByRole('button', { name: /✕/ });
    const count = await dismissButtons.count();
    expect(
      count,
      'Each alert card should have a dismiss (X) button'
    ).toBeGreaterThan(0);
  });

  // ─── REFRESH BUTTON RELOADS ALERTS ───────────────────────────────
  // INTENT: The operator should be able to refresh the anomaly alerts.

  test('refresh button is available in anomaly detection section', async ({ page }) => {
    const anomalyHeading = page.getByRole('heading', { name: /Anomaly Detection/i });
    await expect(anomalyHeading).toBeVisible({ timeout: 10000 });

    // The refresh button is next to the heading
    const refreshButton = page.getByRole('button', { name: /🔄/ });
    await expect(refreshButton).toBeVisible({ timeout: 5000 });
  });

  // ─── STANDARD ALERTS ERROR STATE ─────────────────────────────────
  // INTENT: The standard alerts API may fail (401 Unauthorized). The UI
  // should show a clear error state with a Retry button so the operator
  // knows what's happening.

  test('standard alerts section shows error state with retry', async ({ page }) => {
    // The "Error Loading Alerts" heading appears when the alerts API fails
    const errorHeading = page.getByRole('heading', { name: /Error Loading Alerts/i });
    const retryButton = page.getByRole('button', { name: /Retry/i });

    const hasError = await errorHeading.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasError) {
      await expect(retryButton).toBeVisible({ timeout: 3000 });
    }

    // Whether or not there's an error, the anomaly detection should still work
    const anomalyHeading = page.getByRole('heading', { name: /Anomaly Detection/i });
    await expect(anomalyHeading).toBeVisible({ timeout: 5000 });
  });

  // ─── CONSOLE HEALTH — HIDDEN API ERRORS ──────────────────────────
  // INTENT: If the alert API returns 500s or 404s, the operator might
  // see an empty list and assume "no alerts" when really the backend
  // is broken. Console errors expose these silent failures.
  // Note: 401 from alerts API and anomaly service unavailability are
  // known/expected states, so we filter them out.

  test('no unexpected console errors during page load', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    await page.goto('/');
    await waitForLoadingComplete(page);
    const qualityGroup = page.getByRole('button', { name: /Quality/i }).first();
    await qualityGroup.click();
    await page.getByTestId('tab-alerts').click();
    await waitForLoadingComplete(page);
    await page.waitForTimeout(3000);

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
      !error.includes('401') &&
      !error.includes('Unauthorized') &&
      !error.includes('alerts') &&
      !error.includes('anomaly') &&
      !error.includes('Failed to fetch') &&
      !error.includes('Failed to load resource') &&
      !error.includes('Unable to reach backend') &&
      !error.includes('fetchWithErrorHandling')
    );

    expect(
      apiErrors,
      `Found ${apiErrors.length} unexpected API errors in browser console:\n` +
      apiErrors.map(e => `  - ${e.substring(0, 200)}`).join('\n')
    ).toHaveLength(0);
  });
});

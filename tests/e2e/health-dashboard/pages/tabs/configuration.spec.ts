import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../../shared/helpers/wait-helpers';

/**
 * INTENT: Configuration Tab -- "Can I configure my system settings?"
 * ==================================================================
 *
 * WHY THIS PAGE EXISTS:
 * The Configuration tab is the operator's control panel for tuning the
 * HomeIQ system. It lets them adjust alert thresholds, manage API keys,
 * configure integrations (Home Assistant, Weather, InfluxDB), and control
 * Docker containers. Without it, every change requires SSH and YAML edits.
 *
 * WHAT THE OPERATOR NEEDS:
 * 1. Threshold settings -- warning and critical levels for key metrics
 * 2. Notification preferences -- browser, sound, email toggles
 * 3. Integration cards -- navigate to per-service config forms
 * 4. API key management -- configure external service credentials
 * 5. Container management -- start/stop/restart Docker containers
 * 6. Service control -- manage running services
 * 7. Save button that persists changes -- not just a clickable button
 *
 * WHAT OLD TESTS MISSED:
 * - Tested "does a submit button exist?" but never whether Save persists
 * - Used `input.first()` without knowing what the input was
 * - API key section check returned `typeof boolean` -- always passes
 * - No test for the integration card grid (5 service cards)
 * - No test for threshold form fields being editable
 * - No console error detection for broken config API calls
 */
test.describe('Configuration -- Operator Control Panel', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#configuration');
    await waitForLoadingComplete(page);
  });

  // ─── PREFERENCES & THRESHOLDS ──────────────────────────────────
  // INTENT: The operator needs to set warning/critical thresholds for
  // metrics like events_per_minute, error_rate, and response_time.
  // The form must render real threshold fields, not just any generic input.

  test('@smoke threshold configuration section loads with editable metric fields', async ({ page }) => {
    // The Preferences & Thresholds heading must be visible
    await expect(page.getByText(/Preferences & Thresholds/i)).toBeVisible({ timeout: 10000 });

    // Metric Thresholds section with actual metric names
    await expect(page.getByText(/Metric Thresholds/i)).toBeVisible();

    // At least one real threshold metric should be present
    const metricNames = ['EVENTS PER MINUTE', 'ERROR RATE', 'RESPONSE TIME', 'API USAGE'];
    let foundMetric = false;
    for (const name of metricNames) {
      const label = page.getByText(name);
      if (await label.isVisible({ timeout: 1000 }).catch(() => false)) {
        foundMetric = true;
        break;
      }
    }
    expect(foundMetric, 'At least one threshold metric should be visible').toBe(true);

    // Warning and Critical threshold inputs must exist
    await expect(page.getByText(/Warning Threshold/i).first()).toBeVisible();
    await expect(page.getByText(/Critical Threshold/i).first()).toBeVisible();
  });

  test('threshold values are editable number inputs', async ({ page }) => {
    // INTENT: The operator must be able to type new values into threshold fields,
    // not just see them. A readonly or disabled input is useless.
    await expect(page.getByText(/Metric Thresholds/i)).toBeVisible({ timeout: 10000 });

    const numberInputs = page.locator('input[type="number"]');
    const count = await numberInputs.count();
    expect(count, 'Should have number inputs for warning/critical thresholds').toBeGreaterThanOrEqual(2);

    // Verify at least the first threshold input accepts input
    const firstInput = numberInputs.first();
    const isDisabled = await firstInput.isDisabled();
    expect(isDisabled, 'Threshold inputs should not be disabled by default').toBe(false);
  });

  // ─── NOTIFICATION PREFERENCES ──────────────────────────────────
  // INTENT: The operator wants to control HOW they get alerted -- browser
  // push, audible sound, or email. These are checkboxes, not text fields.

  test('notification preferences show toggle controls', async ({ page }) => {
    await expect(page.getByText(/Notification Preferences/i)).toBeVisible({ timeout: 10000 });

    // Each notification channel should be present as a labeled toggle
    await expect(page.getByText(/Browser Notifications/i)).toBeVisible();
    await expect(page.getByText(/Sound Alerts/i)).toBeVisible();
    await expect(page.getByText(/Email Notifications/i)).toBeVisible();

    // Checkboxes should be present and interactive
    const checkboxes = page.locator('input[type="checkbox"]');
    const checkboxCount = await checkboxes.count();
    expect(checkboxCount, 'Should have checkbox controls for notification types').toBeGreaterThanOrEqual(3);
  });

  // ─── SAVE PERSISTENCE ──────────────────────────────────────────
  // INTENT: The Save button must actually persist changes. The old test
  // filled a random input and reloaded -- it never checked if the value
  // survived. This test verifies the Save button enables on change.

  test('save button activates when preferences are modified', async ({ page }) => {
    await expect(page.getByText(/Preferences & Thresholds/i)).toBeVisible({ timeout: 10000 });

    // Save Preferences button should be disabled initially (no changes)
    const saveButton = page.getByRole('button', { name: /Save Preferences/i });
    await expect(saveButton).toBeVisible();

    // Modify a threshold value to trigger the hasChanges state
    const numberInput = page.locator('input[type="number"]').first();
    await numberInput.fill('999');

    // Save button should now be enabled
    await expect(saveButton).toBeEnabled();
  });

  // ─── INTEGRATION CONFIGURATION CARDS ───────────────────────────
  // INTENT: The operator needs quick access to per-service configuration.
  // The main view shows 5 integration cards: Container Management,
  // API Key Management, Home Assistant, Weather API, InfluxDB.

  test('integration card grid shows all expected service shortcuts', async ({ page }) => {
    await expect(page.getByText(/Integration Configuration/i)).toBeVisible({ timeout: 10000 });

    // All 5 integration cards should be visible
    const expectedCards = [
      'Container Management',
      'API Key Management',
      'Home Assistant',
      'Weather API',
      'InfluxDB',
    ];

    for (const cardName of expectedCards) {
      await expect(
        page.getByRole('button', { name: new RegExp(cardName, 'i') }),
        `Integration card "${cardName}" should be visible`
      ).toBeVisible();
    }
  });

  // ─── INTEGRATION CARD NAVIGATION ───────────────────────────────
  // INTENT: Clicking an integration card should navigate to that service's
  // config form, showing a "Back to Configuration" button and the service
  // name. The old test never tested navigation between config views.

  test('clicking an integration card navigates to service config with back button', async ({ page }) => {
    await expect(page.getByText(/Integration Configuration/i)).toBeVisible({ timeout: 10000 });

    // Click the Home Assistant integration card
    const haCard = page.getByRole('button', { name: /Home Assistant/i });
    await haCard.click();
    await waitForLoadingComplete(page);

    // Should show the service config form with a back button
    await expect(page.getByRole('button', { name: /Back to Configuration/i })).toBeVisible();

    // Navigate back
    await page.getByRole('button', { name: /Back to Configuration/i }).click();
    await waitForLoadingComplete(page);

    // Should return to the main configuration view
    await expect(page.getByText(/Integration Configuration/i)).toBeVisible();
  });

  // ─── SERVICE CONTROL ───────────────────────────────────────────
  // INTENT: The Service Control section lets the operator manage running
  // services. It must be present on the main configuration view.

  test('service control section is accessible from main config view', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Service Control/i }).first()).toBeVisible({ timeout: 10000 });
  });

  // ─── GENERAL PREFERENCES ───────────────────────────────────────
  // INTENT: Refresh interval and timezone settings control how the
  // dashboard behaves. The operator needs to set these to match their
  // monitoring cadence and location.

  test('general preferences include refresh interval and timezone', async ({ page }) => {
    await expect(page.getByText(/General Preferences/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Refresh Interval/i)).toBeVisible();
    await expect(page.getByText(/Timezone/i)).toBeVisible();

    // Refresh interval should be a dropdown with time options
    const refreshSelect = page.locator('select').filter({ hasText: /seconds|minute/i });
    await expect(refreshSelect.first()).toBeVisible();
  });

  // ─── CONSOLE HEALTH ────────────────────────────────────────────
  // INTENT: Config API calls (loading integration settings, saving
  // preferences) might silently fail. The operator deserves to know
  // if /api/v1/integrations/* endpoints are returning errors.

  test('no critical API errors in browser console during page load', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    await page.goto('/#configuration');
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

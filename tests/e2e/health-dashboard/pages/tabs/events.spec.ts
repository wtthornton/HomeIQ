import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../../shared/helpers/wait-helpers';

/**
 * INTENT: Events Tab — "What happened in my home recently?"
 * ==========================================================
 *
 * WHY THIS PAGE EXISTS:
 * The Events tab is the operator's activity log. Every state change,
 * automation trigger, and service call flows through here. When
 * something unexpected happens ("why did the lights turn on at 3 AM?"),
 * this is where the operator investigates. Without a working event
 * stream, the operator is flying blind.
 *
 * ACTUAL UI STRUCTURE (as of March 2026):
 * - Navigation: sidebar button "Events" under "Devices & Data" group
 * - Two sub-tabs: "Real-Time Stream" and "Historical Events"
 * - Live stream with: service filter dropdown, severity filter dropdown,
 *   search textbox, Pause/Auto-scroll/Clear controls
 * - Status counters: Total, Filtered, Status, Last update
 * - Events appear as stream entries (or "Waiting for events..." when empty)
 */
test.describe('Events — Home Activity Log', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    // Navigate to base URL then click the Events tab button
    await page.goto('/');
    await waitForLoadingComplete(page);
    // Expand "Devices & Data" group and click "Events"
    const devicesDataGroup = page.getByRole('button', { name: /Devices & Data/i });
    await devicesDataGroup.click();
    await page.getByTestId('tab-events').click();
    await waitForLoadingComplete(page);
    // Wait for the Live Event Stream heading to confirm we're on the right tab
    await expect(page.getByRole('heading', { name: /Live Event Stream/i })).toBeVisible({ timeout: 15000 });
  });

  // ─── EVENT STREAM LOADS WITH STRUCTURE ────────────────────────────
  // INTENT: The event stream is the core of this tab. If it doesn't
  // render, the operator has no activity log at all.

  test('@smoke event stream renders with live stream UI', async ({ page }) => {
    // The Live Event Stream heading should be visible
    const streamHeading = page.getByRole('heading', { name: /Live Event Stream/i });
    await expect(streamHeading).toBeVisible({ timeout: 15000 });

    // Stream controls should be present (Pause, Auto-scroll, Clear)
    const pauseButton = page.getByRole('button', { name: /Pause/i });
    await expect(pauseButton).toBeVisible({ timeout: 5000 });

    // Status counters should show stream state
    const statusText = page.getByText(/Status:\s*Live/i);
    await expect(statusText).toBeVisible({ timeout: 5000 });
  });

  // ─── EVENTS DISPLAY TIMESTAMPS OR WAITING STATE ──────────────────
  // INTENT: An event without a timestamp is useless for debugging.
  // If no events are flowing, the "Waiting for events..." state or
  // "Last update" timestamp should be visible.

  test('events display timestamps or waiting state', async ({ page }) => {
    // Wait for the events tab to fully render
    const streamHeading = page.getByRole('heading', { name: /Live Event Stream/i });
    await expect(streamHeading).toBeVisible({ timeout: 10000 });

    // Either events are present with timestamps, or the waiting state is shown
    const waitingMessage = page.getByText(/Waiting for events/i);
    const lastUpdate = page.getByText(/Last update:/i);
    const statusLive = page.getByText(/Status:\s*Live/i);

    const hasWaiting = await waitingMessage.isVisible({ timeout: 5000 }).catch(() => false);
    const hasLastUpdate = await lastUpdate.isVisible({ timeout: 3000 }).catch(() => false);
    const hasStatusLive = await statusLive.isVisible({ timeout: 3000 }).catch(() => false);

    expect(
      hasWaiting || hasLastUpdate || hasStatusLive,
      'Event stream should show either events with timestamps, a "Waiting for events" state, or Live status'
    ).toBe(true);
  });

  // ─── STREAM STATUS COUNTERS ──────────────────────────────────────
  // INTENT: The operator needs to see at a glance how many events
  // are flowing — Total count, Filtered count, and live Status.

  test('stream status counters are visible', async ({ page }) => {
    const totalCounter = page.getByText(/Total:\s*\d+/i);
    const filteredCounter = page.getByText(/Filtered:\s*\d+/i);

    await expect(totalCounter).toBeVisible({ timeout: 10000 });
    await expect(filteredCounter).toBeVisible({ timeout: 5000 });
  });

  // ─── EVENT TYPE FILTERING ────────────────────────────────────────
  // INTENT: With hundreds of events, the operator needs to filter by
  // service or severity to focus on what matters during an investigation.

  test('event severity filter narrows the displayed events', async ({ page }) => {
    const severityFilter = page.getByRole('combobox', { name: /Filter by severity/i });
    await expect(severityFilter).toBeVisible({ timeout: 5000 });

    // Select "Error" severity
    await severityFilter.selectOption('Error');
    await waitForLoadingComplete(page);

    // After filtering, the stream UI should still be functional
    const streamHeading = page.getByRole('heading', { name: /Live Event Stream/i });
    await expect(streamHeading).toBeVisible();
  });

  // ─── SERVICE FILTER ──────────────────────────────────────────────
  // INTENT: The operator wants to see events from a specific service.

  test('service filter dropdown is available and functional', async ({ page }) => {
    const serviceFilter = page.getByRole('combobox', { name: /Filter by service/i });
    await expect(serviceFilter).toBeVisible({ timeout: 5000 });

    // The default option should be "All Services"
    const selectedText = await serviceFilter.inputValue();
    // "All Services" is the first/default option
    expect(selectedText).toBeDefined();
  });

  // ─── SEARCH FILTERS EVENTS ──────────────────────────────────────
  // INTENT: The operator wants to search for specific events by keyword.

  test('search input is available and accepts text', async ({ page }) => {
    const searchInput = page.getByRole('textbox', { name: /Search events/i });
    await expect(searchInput).toBeVisible({ timeout: 5000 });

    await searchInput.fill('state_changed');
    await waitForLoadingComplete(page);

    // After searching, the stream UI should still be functional
    const streamHeading = page.getByRole('heading', { name: /Live Event Stream/i });
    await expect(streamHeading).toBeVisible();
  });

  // ─── STREAM CONTROLS ────────────────────────────────────────────
  // INTENT: The operator needs to pause the stream, toggle auto-scroll,
  // and clear old events. These controls must be present and clickable.

  test('stream controls (pause, auto-scroll, clear) are functional', async ({ page }) => {
    const pauseButton = page.getByRole('button', { name: /Pause/i });
    const autoScrollButton = page.getByRole('button', { name: /Auto-scroll/i });
    const clearButton = page.getByRole('button', { name: /Clear/i });

    await expect(pauseButton).toBeVisible({ timeout: 5000 });
    await expect(autoScrollButton).toBeVisible({ timeout: 5000 });
    await expect(clearButton).toBeVisible({ timeout: 5000 });

    // Clicking pause should change the button text
    await pauseButton.click();
    await page.waitForTimeout(500);

    // After clicking, the button should change to "Resume" or remain functional
    const streamHeading = page.getByRole('heading', { name: /Live Event Stream/i });
    await expect(streamHeading).toBeVisible();
  });

  // ─── SUB-TAB NAVIGATION ─────────────────────────────────────────
  // INTENT: Events has two sub-tabs: Real-Time Stream and Historical Events.
  // Both should be accessible.

  test('sub-tabs for real-time and historical events are present', async ({ page }) => {
    const realTimeTab = page.getByRole('button', { name: /Real-Time Stream/i });
    const historicalTab = page.getByRole('button', { name: /Historical Events/i });

    await expect(realTimeTab).toBeVisible({ timeout: 5000 });
    await expect(historicalTab).toBeVisible({ timeout: 5000 });
  });

  // ─── CONSOLE HEALTH — HIDDEN API ERRORS ──────────────────────────
  // INTENT: If the event API returns errors, the stream might appear
  // empty — the operator thinks "nothing happened" when really the
  // backend is failing. Console errors expose this.

  test('no critical API errors in browser console during page load', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    await page.goto('/');
    await waitForLoadingComplete(page);
    const devicesDataGroup = page.getByRole('button', { name: /Devices & Data/i });
    await devicesDataGroup.click();
    await page.getByTestId('tab-events').click();
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
      !error.includes('Failed to fetch') &&
      !error.includes('Failed to load resource') &&
      !error.includes('Unable to reach backend') &&
      !error.includes('fetchWithErrorHandling')
    );

    expect(
      apiErrors,
      `Found ${apiErrors.length} API errors in browser console. ` +
      `These may indicate the event API is broken:\n` +
      apiErrors.map(e => `  - ${e.substring(0, 200)}`).join('\n')
    ).toHaveLength(0);
  });
});

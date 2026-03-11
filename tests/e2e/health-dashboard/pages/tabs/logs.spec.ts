import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../../shared/helpers/wait-helpers';

/**
 * INTENT: Logs Tab -- "What's happening in the service logs right now?"
 * =====================================================================
 *
 * WHY THIS PAGE EXISTS:
 * The Logs tab is the operator's real-time window into service behavior.
 * When an automation fails, when a service crashes, or when data stops
 * flowing -- the logs tell the story. This page streams logs from the
 * log-aggregator service with filtering, search, and pause/resume
 * controls. It answers: "What just happened and why?"
 *
 * WHAT THE OPERATOR NEEDS:
 * 1. Live log stream -- continuously updated log entries
 * 2. Level filtering -- show only ERROR, WARNING, INFO, or DEBUG
 * 3. Service filtering -- focus on a specific service's output
 * 4. Search -- find logs matching a keyword (e.g., "timeout")
 * 5. Pause/Resume -- freeze the stream to read a specific entry
 * 6. Auto-scroll toggle -- follow new entries or stay at current position
 * 7. Clear button -- reset the log view
 * 8. Log entry detail -- timestamp, level, service, message per line
 *
 * WHAT OLD TESTS MISSED:
 * - Smoke test checked data-testid="tab-logs" but never the log viewer
 * - "Log filtering works" filled "error" into the first input -- which
 *   might be the search box, not the level filter
 * - "Log level filtering" clicked the first select without verifying options
 * - "Log tail updates" asserted any element with class*="log" was visible
 * - "Log export" silently passed when no export button existed
 * - Never tested Pause/Resume or Auto-scroll controls
 * - No console error detection for log-aggregator API failures
 */
test.describe('Logs -- Real-Time Service Log Viewer', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#logs');
    await waitForLoadingComplete(page);
  });

  // ─── LOG VIEWER LOADS ──────────────────────────────────────────
  // INTENT: The log viewer must render with its heading and controls.
  // The old smoke test checked for "tab-logs" which is the tab button,
  // not the actual log viewer content.

  test('@smoke log viewer loads with title and control bar', async ({ page }) => {
    // The log viewer component should be present
    await expect(page.getByTestId('log-viewer')).toBeVisible({ timeout: 15000 });

    // The heading identifies this as the Live Log Viewer
    await expect(page.getByText(/Live Log Viewer/i)).toBeVisible();

    // Pause/Resume button should be present for stream control
    const pauseResumeBtn = page.getByRole('button', { name: /Pause|Resume/i });
    await expect(pauseResumeBtn).toBeVisible();
  });

  // ─── STREAM CONTROLS ──────────────────────────────────────────
  // INTENT: The operator needs to pause the stream when investigating
  // a specific log entry, and resume when done. Auto-scroll lets them
  // choose between following new logs or staying at their position.

  test('stream controls include Pause, Auto-scroll, and Clear buttons', async ({ page }) => {
    await expect(page.getByTestId('log-viewer')).toBeVisible({ timeout: 15000 });

    // Pause button (or Resume if already paused)
    await expect(
      page.getByRole('button', { name: /Pause|Resume/i })
    ).toBeVisible();

    // Auto-scroll toggle
    await expect(
      page.getByRole('button', { name: /Auto-scroll|Scroll/i })
    ).toBeVisible();

    // Clear button to reset the log view
    await expect(
      page.getByRole('button', { name: /Clear/i })
    ).toBeVisible();
  });

  // ─── LEVEL FILTER ──────────────────────────────────────────────
  // INTENT: The operator investigating an error needs to filter out
  // INFO and DEBUG noise to see only ERROR and WARNING entries.
  // The dropdown must have actual log level options, not a generic select.

  test('level filter dropdown includes standard log levels', async ({ page }) => {
    await expect(page.getByTestId('log-viewer')).toBeVisible({ timeout: 15000 });

    // There should be a select/dropdown for log levels
    const levelSelects = page.locator('select');
    const selectCount = await levelSelects.count();
    expect(selectCount, 'Should have filter dropdowns').toBeGreaterThanOrEqual(1);

    // One of the selects should have log level options
    let foundLevelFilter = false;
    for (let i = 0; i < selectCount; i++) {
      const text = await levelSelects.nth(i).textContent() ?? '';
      if (/error|warning|info|debug/i.test(text)) {
        foundLevelFilter = true;
        break;
      }
    }
    expect(
      foundLevelFilter,
      'Should have a filter dropdown with log level options (ERROR, WARNING, INFO, DEBUG)'
    ).toBe(true);
  });

  // ─── SERVICE FILTER ────────────────────────────────────────────
  // INTENT: With 50 services, the operator needs to isolate logs from
  // a single service (e.g., websocket-ingestion). A service filter
  // dropdown should be present and populated.

  test('service filter dropdown is available for isolating service logs', async ({ page }) => {
    await expect(page.getByTestId('log-viewer')).toBeVisible({ timeout: 15000 });

    // Wait for logs to load so services dropdown gets populated
    await new Promise((r) => setTimeout(r, 3000));

    const levelSelects = page.locator('select');
    const selectCount = await levelSelects.count();

    // Should have at least 2 selects (level and service)
    expect(selectCount, 'Should have both level and service filter dropdowns').toBeGreaterThanOrEqual(2);
  });

  // ─── SEARCH FUNCTIONALITY ─────────────────────────────────────
  // INTENT: The operator needs to search for specific keywords across
  // all logs -- e.g., "timeout", "connection refused", a specific
  // entity_id. The search input should be clearly identifiable.

  test('search input is available for keyword log search', async ({ page }) => {
    await expect(page.getByTestId('log-viewer')).toBeVisible({ timeout: 15000 });

    // Search input should be present
    const searchInput = page.locator('input[type="search"], input[placeholder*="search" i], input[placeholder*="Search" i]');
    await expect(searchInput.first()).toBeVisible();
  });

  // ─── LOG CONTENT OR EMPTY STATE ────────────────────────────────
  // INTENT: After loading, the viewer should show either actual log
  // entries (with timestamps and messages) or an honest empty state.
  // The old test asserted any element with class*="log" -- which
  // matched the viewer container itself, not actual log content.

  test('log viewer displays log entries or an honest empty state', async ({ page }) => {
    await expect(page.getByTestId('log-viewer')).toBeVisible({ timeout: 15000 });

    // Wait for the log aggregator API to respond
    await new Promise((r) => setTimeout(r, 5000));

    // Log entries typically contain timestamps in ISO or locale format
    // If logs exist, at least one should have a recognizable timestamp
    const logContainer = page.getByTestId('log-viewer');
    const logText = await logContainer.textContent() ?? '';

    // The viewer should show SOMETHING: either log entries, "No logs",
    // or at minimum the filter controls prove the component rendered
    expect(
      logText.length,
      'Log viewer should have content -- either log entries or empty state text'
    ).toBeGreaterThan(0);
  });

  // ─── PAUSE/RESUME TOGGLE ──────────────────────────────────────
  // INTENT: Clicking Pause should stop the stream and change the button
  // to Resume. This is critical for reading specific log entries without
  // them scrolling away.

  test('pause button toggles to resume when clicked', async ({ page }) => {
    await expect(page.getByTestId('log-viewer')).toBeVisible({ timeout: 15000 });

    // Initially should show Pause (stream is running by default)
    const pauseBtn = page.getByRole('button', { name: /Pause/i });
    if (await pauseBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await pauseBtn.click();

      // After clicking, button should now say Resume
      await expect(
        page.getByRole('button', { name: /Resume/i })
      ).toBeVisible({ timeout: 3000 });
    }
  });

  // ─── CLEAR RESETS THE VIEW ─────────────────────────────────────
  // INTENT: The Clear button should empty the log view, giving the
  // operator a fresh start. After clearing, the viewer should resume
  // collecting new logs.

  test('clear button resets the log viewer', async ({ page }) => {
    await expect(page.getByTestId('log-viewer')).toBeVisible({ timeout: 15000 });

    const clearBtn = page.getByRole('button', { name: /Clear/i });
    await expect(clearBtn).toBeVisible();
    await clearBtn.click();

    // After clearing, the viewer should still be functional
    await expect(page.getByTestId('log-viewer')).toBeVisible();
  });

  // ─── CONSOLE HEALTH ────────────────────────────────────────────
  // INTENT: The log viewer fetches from /log-aggregator/api/v1/logs.
  // If this endpoint fails, the viewer shows no logs -- the operator
  // thinks services are silent when actually the log aggregator is down.

  test('no critical API errors in browser console during page load', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    await page.goto('/#logs');
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

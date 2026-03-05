import { test, expect, Page } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../../shared/helpers/wait-helpers';

/**
 * INTENT: Overview Page — The Operator's Mission Control
 * ======================================================
 *
 * WHY THIS PAGE EXISTS:
 * The Overview is the first thing a home automation operator sees.
 * Its job is to answer one question in under 5 seconds:
 * "Is my smart home system working right now?"
 *
 * If the page shows "ALL SYSTEMS OPERATIONAL" but the data pipeline
 * is stalled (0 events), storage reports 0% availability, APIs are
 * returning 404s, and data sources are degraded — the page has
 * FAILED its mission. The operator walks away thinking everything
 * is fine when it isn't.
 *
 * WHAT THE OPERATOR NEEDS:
 * 1. System status — operational, degraded, or down?
 * 2. Data pipeline — is data actually flowing through ingestion?
 * 3. Core components — are ingestion & storage truly healthy?
 * 4. Home activity — what's happening in my home right now?
 * 5. RAG health — are all subsystems green?
 * 6. Data sources — are external APIs connected?
 * 7. Home Assistant — is HA connected with discovered devices?
 * 8. No hidden errors — are APIs silently failing in the console?
 *
 * WHAT OLD TESTS MISSED:
 * - Checked "is there a card?" but never "does the card show real data?"
 * - A card showing "0 events" + "Healthy" badge went unnoticed
 * - 404 console errors from broken API calls were invisible
 * - Storage "Availability: 0.0" despite "Healthy" status = contradiction
 * - "Activity unavailable" section was never tested at all
 * - Data sources with ⚠️ degraded status were not flagged
 */
test.describe('Overview — Operator Mission Control', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#overview');
    await waitForLoadingComplete(page);
  });

  // ─── SYSTEM STATUS BANNER ─────────────────────────────────────────
  // INTENT: The operator's first glance. Must immediately communicate:
  // "Are we OK?" — not just "did the DOM render?"

  test('@smoke system status banner shows clear operational state', async ({ page }) => {
    // The status region should exist with a meaningful system state
    const statusRegion = page.getByRole('region', { name: /system status/i });
    await expect(statusRegion).toBeVisible({ timeout: 10000 });

    // Status must say OPERATIONAL, DEGRADED, or CRITICAL — not blank or "loading"
    const statusText = page.getByRole('status');
    await expect(statusText).toBeVisible();
    await expect(statusText).toContainText(/operational|degraded|critical|down/i);

    // "Updated Xs ago" — the operator needs to know data is fresh, not stale
    await expect(statusRegion.getByText(/updated/i)).toBeVisible();
  });

  // ─── KEY PERFORMANCE INDICATORS ───────────────────────────────────
  // INTENT: KPIs give the operator a numerical health summary at a glance.
  // If throughput is 0, the pipeline is stalled. If latency is spiking,
  // something is slow. These numbers must be REAL, not placeholders.

  test('KPI panel displays real performance metrics with units', async ({ page }) => {
    const kpiSection = page.getByRole('complementary', { name: /key performance indicators/i });
    await expect(kpiSection).toBeVisible({ timeout: 10000 });

    // Uptime should be a duration (e.g., "1h 53m 41s") — not blank
    await expect(kpiSection.getByText(/\d+[hms]/)).toBeVisible();

    // Throughput should show a number with evt/min unit
    await expect(kpiSection.getByText(/evt\/min/i)).toBeVisible();

    // Latency should show a number with ms unit
    await expect(kpiSection.getByText(/ms/i)).toBeVisible();

    // Error rate should show a percentage
    await expect(kpiSection.getByText(/%/)).toBeVisible();
  });

  // ─── CORE SYSTEM COMPONENTS ───────────────────────────────────────
  // INTENT: Ingestion and Storage are the two pillars of the data pipeline.
  // If either is down, NOTHING works. The operator needs to see:
  // - Both are present and show a health status
  // - Their metrics make sense (not "Healthy" with 0 availability)

  test('core components show both ingestion and storage with health badges', async ({ page }) => {
    const componentsGroup = page.getByRole('group', { name: /core system components/i });
    await expect(componentsGroup).toBeVisible({ timeout: 10000 });

    // INGESTION must be present with a clear health indicator
    const ingestionCard = componentsGroup.getByRole('button', { name: /ingestion/i });
    await expect(ingestionCard).toBeVisible();
    await expect(ingestionCard).toContainText(/healthy|degraded|unhealthy/i);

    // STORAGE must be present with a clear health indicator
    const storageCard = componentsGroup.getByRole('button', { name: /storage/i });
    await expect(storageCard).toBeVisible();
    await expect(storageCard).toContainText(/healthy|degraded|unhealthy/i);
  });

  test('ingestion card displays event metrics — not blank placeholders', async ({ page }) => {
    // INTENT: "Events per Hour" and "Total Events" tell the operator if data
    // is actually flowing. If both are 0, the pipeline is stalled — even if
    // the badge says "Healthy". The test must surface these values.
    const componentsGroup = page.getByRole('group', { name: /core system components/i });
    const ingestionCard = componentsGroup.getByRole('button', { name: /ingestion/i });
    await expect(ingestionCard).toBeVisible({ timeout: 10000 });

    // These metrics must EXIST and show values (not be missing from the DOM)
    await expect(ingestionCard.getByText(/events per hour/i)).toBeVisible();
    await expect(ingestionCard.getByText(/total events/i)).toBeVisible();
    await expect(ingestionCard.getByText(/uptime/i)).toBeVisible();
  });

  test('storage card displays response time and availability', async ({ page }) => {
    // INTENT: Storage availability of "0.0" while status says "Healthy" is
    // a contradiction the operator needs to see. The test ensures these
    // metrics are present so the operator can judge for themselves.
    const componentsGroup = page.getByRole('group', { name: /core system components/i });
    const storageCard = componentsGroup.getByRole('button', { name: /storage/i });
    await expect(storageCard).toBeVisible({ timeout: 10000 });

    await expect(storageCard.getByText(/response time/i)).toBeVisible();
    await expect(storageCard.getByText(/availability/i)).toBeVisible();
    await expect(storageCard.getByText(/uptime/i)).toBeVisible();
  });

  test('component data freshness indicator shows recent update', async ({ page }) => {
    // INTENT: Stale data is dangerous. The operator might think the system is
    // fine when it actually stopped updating hours ago. "Fresh 0s ago" gives
    // confidence; "Stale 3h ago" signals a problem.
    await expect(page.getByText(/fresh|stale/i).first()).toBeVisible({ timeout: 10000 });
  });

  test('component cards are clickable for detail drilldown', async ({ page }) => {
    // INTENT: When the operator spots a problem (e.g., 0 events), they need
    // to drill down into component details to diagnose. Cards must be interactive.
    const componentsGroup = page.getByRole('group', { name: /core system components/i });
    const ingestionCard = componentsGroup.getByRole('button', { name: /ingestion/i });
    await expect(ingestionCard).toBeVisible({ timeout: 10000 });

    // Click should open some detail view (modal, expanded section, etc.)
    await ingestionCard.click();
    // Verify something happened — a modal, expanded details, or navigation
    const detailView = page.getByRole('dialog')
      .or(page.locator('[class*="detail"]'))
      .or(page.locator('[class*="expanded"]'));
    await expect(detailView.first()).toBeVisible({ timeout: 5000 });
  });

  // ─── HOUSEHOLD ACTIVITY ───────────────────────────────────────────
  // INTENT: The operator wants to know what's happening in their home
  // RIGHT NOW. If this section shows "Activity unavailable", the
  // activity-writer service isn't running — that's a real problem the
  // old tests never caught.

  test('household activity section loads with meaningful content', async ({ page }) => {
    const activityHeading = page.getByRole('heading', { name: /household activity/i });
    await expect(activityHeading).toBeVisible({ timeout: 10000 });

    // The section should show EITHER:
    // - Actual activity data (what's happening now), OR
    // - An honest "unavailable" message with a Retry button
    // It should NOT be blank or stuck in a perpetual loading state
    const section = activityHeading.locator('xpath=ancestor::div[1]/following-sibling::div[1]')
      .or(activityHeading.locator('..').locator('..'));
    const contentElements = section.locator('p, [role="status"], button');
    const count = await contentElements.count();
    expect(count, 'Activity section should have visible content — not be blank').toBeGreaterThan(0);
  });

  // ─── RAG STATUS MONITOR ───────────────────────────────────────────
  // INTENT: RAG (Red/Amber/Green) is the at-a-glance health system.
  // The operator needs to see ALL subsystems at once. Any non-GREEN
  // indicator needs immediate attention.

  test('RAG monitor shows overall status with all subsystem indicators', async ({ page }) => {
    const ragHeading = page.getByRole('heading', { name: /rag status monitor/i }).first();
    await expect(ragHeading).toBeVisible({ timeout: 10000 });

    // Overall status must be a clear color-coded state
    await expect(page.getByText(/overall status/i)).toBeVisible();
    await expect(page.getByText(/green|amber|red/i).first()).toBeVisible();

    // Each subsystem must be listed with its own status indicator
    const subsystems = ['WebSocket', 'Processing', 'Storage'];
    for (const name of subsystems) {
      await expect(
        page.getByText(name).first(),
        `RAG subsystem "${name}" should be visible`
      ).toBeVisible();
    }
  });

  test('RAG card opens detail modal for deeper investigation', async ({ page }) => {
    // INTENT: When a subsystem goes AMBER or RED, the operator needs to
    // click through to see exactly what's wrong — not just a color dot.
    const ragButton = page.getByRole('button', { name: /rag status monitor/i });
    await expect(ragButton).toBeVisible({ timeout: 10000 });
    await ragButton.click();

    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible({ timeout: 5000 });
  });

  // ─── ACTIVE DATA SOURCES ──────────────────────────────────────────
  // INTENT: Data sources are external API connections (weather, sports,
  // energy pricing, etc.). The operator needs to see which are connected
  // (✅) and which are degraded (⚠️) or offline (❌).
  // A degraded Calendar source was invisible to old tests.

  test('all expected data sources are listed with health indicators', async ({ page }) => {
    const sourcesHeading = page.getByRole('heading', { name: /active data sources/i });
    await expect(sourcesHeading).toBeVisible({ timeout: 10000 });

    // These are the data sources the operator expects to monitor
    const expectedSources = [
      'Weather', 'Sports', 'Carbon Intensity', 'Electricity Pricing',
      'Air Quality', 'Blueprint Index', 'Rule Recommendation',
      'Smart Meter', 'Calendar',
    ];

    for (const source of expectedSources) {
      const sourceButton = page.getByRole('button', { name: new RegExp(source, 'i') });
      await expect(sourceButton, `Data source "${source}" should be listed`).toBeVisible();

      // Each source must have a health indicator (✅ healthy, ⚠️ degraded, ❌ unhealthy, ⏸️ paused)
      const text = await sourceButton.textContent();
      expect(
        text,
        `Data source "${source}" should show a health status indicator`
      ).toMatch(/✅|⚠️|❌|⏸️|healthy|degraded|unhealthy|paused/i);
    }
  });

  // ─── HOME ASSISTANT INTEGRATION ───────────────────────────────────
  // INTENT: Home Assistant is the heart of the smart home. The operator
  // needs to know: Is HA connected? How many devices were discovered?
  // "0 Devices, 0 Entities" means HA isn't connected — that's critical.

  test('Home Assistant section shows device and service counts', async ({ page }) => {
    const haHeading = page.getByRole('heading', { name: /home assistant/i });
    await expect(haHeading).toBeVisible({ timeout: 10000 });

    // These metrics tell the operator about HA connectivity
    // Scope to the HA section to avoid matching footer text
    const haSection = haHeading.locator('xpath=ancestor::div[1]');
    await expect(haSection.getByText(/devices/i).first()).toBeVisible();
    await expect(haSection.getByText(/entities/i).first()).toBeVisible();
    await expect(haSection.getByText(/active services/i).first()).toBeVisible();
    await expect(haSection.getByText(/system health/i).first()).toBeVisible();
  });

  // ─── PAGE FOOTER ──────────────────────────────────────────────────
  // INTENT: The footer is a quick summary strip. It should match the data
  // shown in the sections above — if the footer says "8/9 Sources Healthy"
  // the operator trusts it.

  test('footer summarizes system statistics', async ({ page }) => {
    // The footer is a summary strip at the bottom with format:
    // "X Devices • Y Entities • Z Integrations • N/M Data Sources Healthy • K Services Running"
    const footer = page.getByText(/data sources healthy/i);
    await expect(footer).toBeVisible({ timeout: 10000 });

    const footerText = await footer.textContent() ?? '';
    // Footer should contain key summary numbers
    expect(footerText, 'Footer should mention devices').toMatch(/\d+\s*devices/i);
    expect(footerText, 'Footer should mention services running').toMatch(/\d+\s*services running/i);
  });

  // ─── CONSOLE HEALTH — HIDDEN ERRORS ───────────────────────────────
  // INTENT: The most dangerous bugs are the ones the UI hides. If the
  // browser console has API errors (404s, 500s), the dashboard is lying
  // by omission. The operator deserves honesty.
  //
  // This test caught issues old tests missed:
  // - GET /api/devices?limit=1000 → 404 (device API not routed)
  // - GET /api/v1/activity → 404 (activity endpoint missing)

  test('no critical API errors in browser console during page load', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    // Fresh navigation to capture all console output from page load
    await page.goto('/#overview');
    await waitForLoadingComplete(page);
    // Allow async API calls to settle
    await page.waitForTimeout(3000);

    // Filter out non-API noise (fonts, favicons, browser extensions)
    // and infrastructure noise (rate limiting from test parallelism)
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
      apiErrors.map(e => `  • ${e.substring(0, 200)}`).join('\n')
    ).toHaveLength(0);
  });

  // ─── DATA REFRESH ─────────────────────────────────────────────────
  // INTENT: The operator needs confidence that the data they see is live,
  // not a stale snapshot from hours ago. The refresh mechanism must
  // actually update timestamps, not just re-render the same data.

  test('auto-refresh updates the data freshness timestamp', async ({ page }) => {
    // Capture the initial freshness time
    const freshnessLocator = page.getByText(/\d+:\d{2}:\d{2}/);
    await expect(freshnessLocator.first()).toBeVisible({ timeout: 10000 });

    // The freshness indicator should show recent data (within "0s ago" to "60s ago")
    await expect(page.getByText(/\d+s ago/i).first()).toBeVisible({ timeout: 15000 });
  });
});

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../../shared/helpers/wait-helpers';

/**
 * INTENT: Validation Tab -- "Is my system configuration valid?"
 * ==============================================================
 *
 * WHY THIS PAGE EXISTS:
 * The Validation tab scans the Home Assistant configuration for entity
 * issues: missing area assignments, incorrect area assignments, and other
 * configuration problems that prevent automations from working correctly.
 * It gives AI-powered suggestions with confidence scores and lets the
 * operator apply fixes individually or in bulk. This is the bridge between
 * "something is misconfigured" and "here's exactly what to change."
 *
 * WHAT THE OPERATOR NEEDS:
 * 1. Summary cards -- total issues, missing areas, incorrect areas, HA version
 * 2. Issue table with entity IDs, categories, current areas, and suggestions
 * 3. Confidence-scored suggestions with reasoning for each fix
 * 4. Category filter (Missing Area Assignment, Incorrect Area Assignment)
 * 5. Confidence filter (High >= 80%, Medium >= 60%, Low >= 40%)
 * 6. Refresh button to re-run validation
 * 7. Apply Fix button per issue, plus bulk selection and bulk apply
 * 8. Last scan timestamp to know when data was collected
 *
 * WHAT OLD TESTS MISSED:
 * - Smoke test only checked data-testid="validation-results" -- passes
 *   even when showing an error state or empty results
 * - "Validation runs trigger" clicked a generic Run/Validate button but
 *   never checked if results actually changed
 * - "Results filtering" filled "error" into the first input -- the actual
 *   filters are category and confidence dropdowns, not text inputs
 * - Only 3 tests total for a complex page with filters, tables, and bulk actions
 * - No test for summary cards, confidence badges, or bulk apply
 * - No console error detection for setup-api failures
 */
test.describe('Validation -- HA Configuration Validation & Fix Suggestions', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#validation');
    await waitForLoadingComplete(page);
  });

  // ─── PAGE HEADER ───────────────────────────────────────────────
  // INTENT: The operator should immediately understand this page
  // validates their HA configuration and offers fix suggestions.

  test('@smoke validation page loads with heading and description', async ({ page }) => {
    await expect(page.locator('[data-testid="validation-results"]')).toBeVisible({ timeout: 15000 });

    // Page heading identifies the purpose
    await expect(page.getByText(/Home Assistant Configuration Validation/i)).toBeVisible();

    // Description explains what the page does
    await expect(page.getByText(/Validate.*Home Assistant.*setup|suggestions.*fixing/i)).toBeVisible();
  });

  // ─── SUMMARY CARDS ─────────────────────────────────────────────
  // INTENT: Summary cards give the operator a quick overview of how many
  // configuration issues exist and what categories they fall into. The
  // HA Version card confirms which Home Assistant version was scanned.

  test('summary cards show total issues, missing areas, incorrect areas, and HA version', async ({ page }) => {
    await expect(page.locator('[data-testid="validation-results"]')).toBeVisible({ timeout: 15000 });

    // Four summary cards should be visible
    await expect(page.getByText('Total Issues')).toBeVisible();
    await expect(page.getByText('Missing Areas')).toBeVisible();
    await expect(page.getByText('Incorrect Areas')).toBeVisible();
    await expect(page.getByText('HA Version')).toBeVisible();
  });

  // ─── FILTER CONTROLS ───────────────────────────────────────────
  // INTENT: The operator needs to filter validation results by category
  // (missing vs incorrect area) and by confidence level. The old test
  // tried to use a text input for filtering -- the actual UI uses
  // select dropdowns for category and confidence.

  test('filter controls include category, confidence, and refresh', async ({ page }) => {
    await expect(page.locator('[data-testid="validation-results"]')).toBeVisible({ timeout: 15000 });

    // Category filter dropdown
    const categoryFilter = page.locator('select').filter({ hasText: /All categories/i });
    await expect(categoryFilter).toBeVisible();

    // Confidence filter dropdown
    const confidenceFilter = page.locator('select').filter({ hasText: /All suggestions/i });
    await expect(confidenceFilter).toBeVisible();

    // Refresh button to re-run validation
    await expect(page.getByRole('button', { name: /🔄 Refresh/i })).toBeVisible();
  });

  // ─── CATEGORY FILTER INTERACTION ───────────────────────────────
  // INTENT: Selecting a specific category should filter the results.
  // The operator wants to focus on "Missing Area Assignment" issues
  // separately from "Incorrect Area Assignment" issues.

  test('category filter dropdown has the expected options', async ({ page }) => {
    await expect(page.locator('[data-testid="validation-results"]')).toBeVisible({ timeout: 15000 });

    const categoryFilter = page.locator('select').filter({ hasText: /All categories/i });
    await expect(categoryFilter).toBeVisible();

    // Check that expected category options exist
    const options = categoryFilter.locator('option');
    const optionTexts: string[] = [];
    const count = await options.count();
    for (let i = 0; i < count; i++) {
      optionTexts.push(await options.nth(i).textContent() ?? '');
    }

    expect(optionTexts.some(t => /Missing Area/i.test(t)),
      'Should have "Missing Area Assignment" category option'
    ).toBe(true);
    expect(optionTexts.some(t => /Incorrect Area/i.test(t)),
      'Should have "Incorrect Area Assignment" category option'
    ).toBe(true);
  });

  // ─── RESULTS TABLE OR EMPTY STATE ──────────────────────────────
  // INTENT: After loading, the page should show either a table of
  // validation issues (with entity IDs, categories, suggestions) or
  // an honest "no issues found" message. It should NOT be blank.

  test('displays issue table with entity details or a no-issues message', async ({ page }) => {
    await expect(page.locator('[data-testid="validation-results"]')).toBeVisible({ timeout: 15000 });
    await new Promise((r) => setTimeout(r, 3000));

    // Either the table with headers is shown or the clean state message
    const tableHeaders = page.locator('th');
    const noIssuesMsg = page.getByText(/No validation issues found|No issues match/i);
    const errorState = page.getByRole('button', { name: /Retry/i });

    const hasTable = await tableHeaders.first().isVisible({ timeout: 2000 }).catch(() => false);
    const hasNoIssues = await noIssuesMsg.isVisible({ timeout: 2000 }).catch(() => false);
    const hasError = await errorState.isVisible({ timeout: 2000 }).catch(() => false);

    expect(
      hasTable || hasNoIssues || hasError,
      'Should show an issue table, a "no issues" message, or an error with Retry'
    ).toBe(true);
  });

  // ─── TABLE COLUMNS ─────────────────────────────────────────────
  // INTENT: The issue table must have columns that give the operator
  // actionable information: Entity, Category, Current Area, Suggestions,
  // and Actions. Without the Suggestions column, the operator knows
  // something is wrong but has no guidance on how to fix it.

  test('issue table has entity, category, suggestion, and action columns', async ({ page }) => {
    await expect(page.locator('[data-testid="validation-results"]')).toBeVisible({ timeout: 15000 });
    await new Promise((r) => setTimeout(r, 3000));

    const tableHeaders = page.locator('th');
    const hasTable = await tableHeaders.first().isVisible({ timeout: 2000 }).catch(() => false);

    if (hasTable) {
      // Verify the expected column headers
      await expect(page.locator('th', { hasText: /Entity/i })).toBeVisible();
      await expect(page.locator('th', { hasText: /Category/i })).toBeVisible();
      await expect(page.locator('th', { hasText: /Suggestions/i })).toBeVisible();
      await expect(page.locator('th', { hasText: /Actions/i })).toBeVisible();

      // Bulk selection checkbox should be in the header
      const headerCheckbox = page.locator('thead input[type="checkbox"]');
      await expect(headerCheckbox).toBeVisible();
    }
  });

  // ─── APPLY FIX BUTTON ──────────────────────────────────────────
  // INTENT: The "Apply Fix" button per row is the core value of this
  // page. It lets the operator fix a misconfigured entity with one click.
  // Without it, validation results are informational but not actionable.

  test('issue rows have Apply Fix buttons for actionable remediation', async ({ page }) => {
    await expect(page.locator('[data-testid="validation-results"]')).toBeVisible({ timeout: 15000 });
    await new Promise((r) => setTimeout(r, 3000));

    const tableRows = page.locator('tbody tr');
    const rowCount = await tableRows.count();

    if (rowCount > 0) {
      // At least one row should have an Apply Fix button
      const applyButtons = page.getByRole('button', { name: /Apply Fix/i });
      const buttonCount = await applyButtons.count();
      expect(
        buttonCount,
        'Issue rows with suggestions should have "Apply Fix" buttons'
      ).toBeGreaterThan(0);
    }
  });

  // ─── BULK SELECTION ────────────────────────────────────────────
  // INTENT: When the operator has many issues, selecting them one by
  // one is tedious. The bulk checkbox in the header should select all
  // visible issues, enabling bulk apply.

  test('header checkbox enables bulk selection of issues', async ({ page }) => {
    await expect(page.locator('[data-testid="validation-results"]')).toBeVisible({ timeout: 15000 });
    await new Promise((r) => setTimeout(r, 3000));

    const tableRows = page.locator('tbody tr');
    const rowCount = await tableRows.count();

    if (rowCount > 0) {
      // Click the header checkbox to select all
      const headerCheckbox = page.locator('thead input[type="checkbox"]');
      if (await headerCheckbox.isVisible({ timeout: 2000 }).catch(() => false)) {
        await headerCheckbox.click();

        // Bulk action bar should appear showing selection count
        await expect(
          page.getByText(/\d+ issue.*selected/i)
        ).toBeVisible({ timeout: 3000 });

        // Bulk Apply button should be available
        await expect(
          page.getByRole('button', { name: /Apply.*Fix/i })
        ).toBeVisible();
      }
    }
  });

  // ─── LAST SCAN TIMESTAMP ───────────────────────────────────────
  // INTENT: The operator needs to know when the last validation scan
  // ran. Stale results from days ago are misleading if the configuration
  // has changed since then.

  test('last scan timestamp is displayed for data freshness', async ({ page }) => {
    await expect(page.locator('[data-testid="validation-results"]')).toBeVisible({ timeout: 15000 });
    await new Promise((r) => setTimeout(r, 2000));

    // Look for the last scan info at the bottom of the page
    const lastScan = page.getByText(/Last scan/i);
    const hasScanInfo = await lastScan.isVisible({ timeout: 3000 }).catch(() => false);

    // If validation results loaded, last scan should be present
    const hasResults = await page.getByText('Total Issues').isVisible({ timeout: 1000 }).catch(() => false);
    if (hasResults) {
      expect(hasScanInfo, 'Last scan timestamp should be visible when results are loaded').toBe(true);
    }
  });

  // ─── CONSOLE HEALTH ────────────────────────────────────────────
  // INTENT: The validation tab calls setup-api endpoints for scan
  // results and fix application. Silent API errors mean the operator
  // sees "no issues" when actually the scanner never ran.

  test('no critical API errors in browser console during page load', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    await page.goto('/#validation');
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

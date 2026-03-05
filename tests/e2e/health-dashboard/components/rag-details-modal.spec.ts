/**
 * RAG Details Modal -- Subsystem Health Inspection
 *
 * WHY THIS MATTERS:
 * The RAG (Retrieval-Augmented Generation) pipeline is the backbone of
 * HomeIQ's AI features. When AI answers seem off or automation suggestions
 * stop appearing, the operator opens the RAG Details Modal from the
 * Overview page to check store/retrieve/search operations, cache hit
 * rates, latency, and error rates. This modal must show ONLY RAG-specific
 * metrics -- mixing in unrelated data (WebSocket events, device counts)
 * would confuse the investigation.
 *
 * WHAT THE OPERATOR USES IT FOR:
 * - Verifying that RAG store, retrieve, and search operations are healthy
 * - Checking cache hit rate to ensure the knowledge base is warm
 * - Spotting latency spikes or elevated error rates
 * - Ruling out RAG as the cause when AI features misbehave
 */

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForModalOpen } from '../../../shared/helpers/wait-helpers';

/** Open the RAG Details Modal from the Overview page. */
async function openRagModal(page: import('@playwright/test').Page) {
  const ragStatusCard = page.locator('[data-testid="rag-status-card"]');
  await expect(ragStatusCard).toBeVisible({ timeout: 15000 });
  await ragStatusCard.click();
  await waitForModalOpen(page);
  const modal = page.locator('[role="dialog"]').filter({ hasText: 'RAG Status Details' });
  await expect(modal).toBeVisible({ timeout: 3000 });
  return modal;
}

test.describe('RAG Details Modal -- subsystem health inspection', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#overview');
    await page.waitForLoadState('networkidle');
  });

  test('@smoke RAG Status Card exists and opens the details modal', async ({ page }) => {
    // The operator sees a RAG Status section on the Overview page and can
    // click it to drill into RAG-specific metrics.
    const ragSection = page.locator('[data-testid="rag-status-section"]');
    await expect(ragSection).toBeVisible({ timeout: 10000 });

    const modal = await openRagModal(page);

    // Modal title confirms the operator is looking at RAG data
    await expect(modal.locator('h2:has-text("RAG Status Details")')).toBeVisible();
  });

  test('modal displays all expected RAG metric labels so the operator knows what to check', async ({ page }) => {
    const modal = await openRagModal(page);

    // These are the key operational metrics an operator would look for
    const expectedMetrics = [
      'Total RAG Calls',
      'Store Operations',
      'Retrieve Operations',
      'Search Operations',
      'Cache Hit Rate',
      'Avg Latency',
      'Error Rate',
      'Avg Success Score',
    ];

    for (const metric of expectedMetrics) {
      await expect(
        modal.locator(`text=${metric}`).first()
      ).toBeVisible({ timeout: 2000 });
    }
  });

  test('modal shows actual numeric values, not just labels', async ({ page }) => {
    // The operator needs to see real numbers (e.g. "42", "85.3%", "12ms"),
    // not just metric names with empty values.
    const modal = await openRagModal(page);
    await expect(modal.locator('text=Total RAG Calls').first()).toBeVisible({ timeout: 5000 });

    const hasNumericValue = await modal
      .locator('text=/\\d+(\\.\\d+)?%?/')
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasNumericValue).toBe(true);
  });

  test('non-RAG sections are NOT displayed -- keeps investigation focused', async ({ page }) => {
    // Showing WebSocket, device, or event metrics in the RAG modal would
    // mislead the operator into thinking those are RAG-related.
    const modal = await openRagModal(page);

    const nonRAGSections = [
      'Data Metrics',
      'Data Breakdown',
      'Events Processed',
      'Unique Entities',
      'Events per Entity',
      'Events/Minute',
      'Total Events',
      'Throughput',
      'Connection Attempts',
      'WebSocket Connection',
      'Event Processing',
      'Data Storage',
      'Component Health Breakdown',
    ];

    for (const section of nonRAGSections) {
      const element = modal.locator(`text=${section}`);
      await expect(element).not.toBeVisible({ timeout: 1000 });
    }
  });

  test('Overall Status section is absent from the modal content area', async ({ page }) => {
    // "Overall Status" belongs on the card itself, not inside the modal
    // where it could be confused with RAG-specific status.
    const modal = await openRagModal(page);

    const modalContent = modal.locator('.p-6');
    const overallStatus = modalContent.locator('text=Overall Status');
    const count = await overallStatus.count();
    expect(count).toBe(0);
  });

  test('modal closes via close button', async ({ page }) => {
    const modal = await openRagModal(page);

    const closeButton = modal.locator(
      'button[aria-label="Close modal"], button:has-text("Close")'
    ).first();
    await closeButton.click();
    await expect(modal).not.toBeVisible({ timeout: 3000 });
  });

  test('modal closes via Escape key', async ({ page }) => {
    const modal = await openRagModal(page);

    await page.keyboard.press('Escape');
    await expect(modal).not.toBeVisible({ timeout: 3000 });
  });

  test('modal closes via backdrop click', async ({ page }) => {
    const modal = await openRagModal(page);

    // Click outside the modal to close it — try the overlay/backdrop area
    const backdrop = page.locator(
      '[class*="fixed"][class*="inset"], [class*="overlay"], [class*="backdrop"]'
    ).first();
    if (await backdrop.isVisible({ timeout: 1000 })) {
      await backdrop.click({ position: { x: 10, y: 10 }, force: true });
    } else {
      // Fall back to pressing Escape if no backdrop element found
      await page.keyboard.press('Escape');
    }
    await expect(modal).not.toBeVisible({ timeout: 3000 });
  });

  test('modal is accessible: correct ARIA attributes and labelled title', async ({ page }) => {
    const modal = await openRagModal(page);

    // role="dialog" is already matched by the locator
    await expect(modal).toHaveAttribute('aria-modal', 'true');
    await expect(modal).toHaveAttribute('aria-labelledby', 'rag-modal-title');

    // The referenced title element must exist and have the expected text
    const title = modal.locator('#rag-modal-title');
    await expect(title).toBeVisible();
    await expect(title).toHaveText('RAG Status Details');

    // Close button must have an aria-label for screen readers
    const closeButton = modal.locator('button[aria-label="Close modal"]');
    await expect(closeButton).toBeVisible();
  });

  test('modal renders correctly in both light and dark modes', async ({ page }) => {
    // Operator may use either theme -- the modal must be readable in both
    const modal = await openRagModal(page);
    const lightBg = modal.locator('.bg-white, .bg-gray-800').first();
    await expect(lightBg).toBeVisible();

    // Close and switch to dark mode if possible
    await page.keyboard.press('Escape');
    await expect(modal).not.toBeVisible({ timeout: 3000 });

    const themeToggle = page.locator(
      '[data-testid="theme-toggle"], button[aria-label*="theme" i], button[aria-label*="dark" i]'
    ).first();

    if (await themeToggle.isVisible({ timeout: 2000 })) {
      await themeToggle.click();

      const ragStatusCard = page.locator('[data-testid="rag-status-card"]');
      await ragStatusCard.click();
      await waitForModalOpen(page);

      const darkModal = page.locator('[role="dialog"]').filter({ hasText: 'RAG Status Details' });
      await expect(darkModal).toBeVisible();

      const darkBg = darkModal.locator('.bg-gray-800').first();
      await expect(darkBg).toBeVisible();
    }
  });

  test.skip('loading state displays while RAG metrics are fetched (requires API mock with delay)', async ({ page }) => {
    const modal = await openRagModal(page);
    const loading = modal.locator('text=Loading RAG metrics');
    await expect(loading).toBeVisible({ timeout: 1000 });
  });

  test.skip('error state displays when RAG service is unavailable (requires API mock)', async ({ page }) => {
    const modal = await openRagModal(page);
    await expect(modal.locator('text=RAG Service Metrics Unavailable')).toBeVisible({ timeout: 3000 });
  });
});

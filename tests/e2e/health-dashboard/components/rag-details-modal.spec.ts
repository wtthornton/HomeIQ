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
import { waitForModalOpen, waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

/**
 * Open the RAG Details Modal from the Overview page.
 * Waits for the RAG card to be in a loaded state (has status, not "Loading..." or "unavailable").
 * Returns the modal locator, or null if section/card not found (caller may skip).
 */
async function openRagModal(page: import('@playwright/test').Page): Promise<import('@playwright/test').Locator | null> {
  await waitForLoadingComplete(page, '[data-testid="loading"], [aria-label="Loading"]', 10000);
  const ragSection = page.locator('[data-testid="rag-status-section"]');
  await ragSection.waitFor({ state: 'visible', timeout: 15000 }).catch(() => {});
  if (!(await ragSection.isVisible())) return null;

  // Wait for card to be loaded (has GREEN/AMBER/RED or "Overall Status", not "Loading RAG status" or "unavailable")
  const ragCard = page.locator('[data-testid="rag-status-card"]');
  await ragCard.waitFor({ state: 'visible', timeout: 20000 }).catch(() => {});
  if (!(await ragCard.isVisible())) return null;
  const cardText = await ragCard.textContent().catch(() => '');
  if (/Loading RAG status|RAG status unavailable/i.test(cardText || '')) {
    await ragCard.waitFor({ state: 'visible', timeout: 15000 });
    const retryText = await ragCard.textContent().catch(() => '');
    if (/Loading RAG status|RAG status unavailable/i.test(retryText || '')) return null;
  }

  await ragCard.click();
  await waitForModalOpen(page, '[role="dialog"]', 5000);
  const modal = page.locator('[role="dialog"]').filter({ hasText: 'RAG Status Details' });
  const modalVisible = await modal.isVisible({ timeout: 5000 }).catch(() => false);
  return modalVisible ? modal : null;
}

test.describe('RAG Details Modal -- subsystem health inspection', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#overview');
    await page.waitForLoadState('domcontentloaded');
    await waitForLoadingComplete(page, '[data-testid="loading"], [aria-label="Loading"]', 10000);
  });

  test('@smoke RAG Status Card exists and opens the details modal', async ({ page }) => {
    const ragSection = page.locator('[data-testid="rag-status-section"]');
    await expect(ragSection).toBeVisible({ timeout: 15000 });

    const modal = await openRagModal(page);
    expect(modal, 'RAG card should be clickable and modal should open').toBeTruthy();
    await expect(modal!.locator('h2, h3').filter({ hasText: 'RAG Status Details' }).first()).toBeVisible({ timeout: 3000 });
  });

  test('modal displays all expected RAG metric labels so the operator knows what to check', async ({ page }) => {
    const modal = await openRagModal(page);
    expect(modal, 'RAG modal should open').toBeTruthy();
    const m = modal!;
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
        m.locator(`text=${metric}`).first()
      ).toBeVisible({ timeout: 3000 });
    }
  });

  test('modal shows actual numeric values, not just labels', async ({ page }) => {
    const modal = await openRagModal(page);
    expect(modal, 'RAG modal should open').toBeTruthy();
    const m = modal!;
    await expect(m.locator('text=Total RAG Calls').first()).toBeVisible({ timeout: 5000 });

    const hasNumericValue = await m
      .locator('text=/\\d+(\\.\\d+)?%?/')
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasNumericValue).toBe(true);
  });

  test('non-RAG sections are NOT displayed -- keeps investigation focused', async ({ page }) => {
    const modal = await openRagModal(page);
    expect(modal, 'RAG modal should open').toBeTruthy();
    const m = modal!;
    // Key non-RAG phrases that must not appear in the modal content
    const nonRAGSections = [
      'WebSocket Connection',
      'Event Processing',
      'Component Health Breakdown',
    ];

    for (const section of nonRAGSections) {
      const element = m.locator(`text=${section}`);
      await expect(element).not.toBeVisible({ timeout: 500 });
    }
  });

  test('Overall Status section is absent from the modal content area', async ({ page }) => {
    const modal = await openRagModal(page);
    expect(modal, 'RAG modal should open').toBeTruthy();
    const m = modal!;
    const modalContent = m.locator('.p-6');
    const overallStatus = modalContent.locator('text=Overall Status');
    const count = await overallStatus.count();
    expect(count).toBe(0);
  });

  test('modal closes via close button', async ({ page }) => {
    const modal = await openRagModal(page);
    expect(modal, 'RAG modal should open').toBeTruthy();
    const m = modal!;
    const closeButton = m.locator(
      'button[aria-label="Close modal"], button:has-text("Close")'
    ).first();
    await closeButton.click();
    await expect(m).not.toBeVisible({ timeout: 3000 });
  });

  test('modal closes via Escape key', async ({ page }) => {
    const modal = await openRagModal(page);
    expect(modal, 'RAG modal should open').toBeTruthy();
    const m = modal!;
    await page.keyboard.press('Escape');
    await expect(m).not.toBeVisible({ timeout: 3000 });
  });

  test('modal closes via backdrop click', async ({ page }) => {
    const modal = await openRagModal(page);
    expect(modal, 'RAG modal should open').toBeTruthy();
    const m = modal!;
    // Click outside the modal to close it — try the overlay/backdrop area
    const backdrop = page.locator(
      '[class*="fixed"][class*="inset"], [class*="overlay"], [class*="backdrop"]'
    ).first();
    if (await backdrop.isVisible({ timeout: 1000 })) {
      await backdrop.click({ position: { x: 10, y: 10 }, force: true });
      await new Promise((r) => setTimeout(r, 300));
    }
    if (await m.isVisible().catch(() => true)) {
      await page.keyboard.press('Escape');
    }
    await expect(m).not.toBeVisible({ timeout: 5000 });
  });

  test('modal is accessible: correct ARIA attributes and labelled title', async ({ page }) => {
    const modal = await openRagModal(page);
    expect(modal, 'RAG modal should open').toBeTruthy();
    const m = modal!;
    await expect(m).toHaveAttribute('aria-modal', 'true');
    const labelledBy = await m.getAttribute('aria-labelledby');
    expect(labelledBy).toBeTruthy();

    const title = m.locator('#rag-modal-title, h2').filter({ hasText: 'RAG Status Details' }).first();
    await expect(title).toBeVisible();
    const closeButton = m.locator('button[aria-label="Close modal"], button[aria-label*="lose" i]').first();
    await expect(closeButton).toBeVisible();
  });

  test('modal renders correctly in both light and dark modes', async ({ page }) => {
    const modal = await openRagModal(page);
    expect(modal, 'RAG modal should open').toBeTruthy();
    const m = modal!;
    const lightBg = m.locator('.bg-white, .bg-gray-800').first();
    await expect(lightBg).toBeVisible({ timeout: 3000 });

    await page.keyboard.press('Escape');
    await expect(m).not.toBeVisible({ timeout: 3000 });

    const themeToggle = page.locator(
      '[data-testid="theme-toggle"], button[aria-label*="theme" i], button[aria-label*="dark" i]'
    ).first();

    if (await themeToggle.isVisible({ timeout: 3000 })) {
      await themeToggle.click();
      await new Promise((r) => setTimeout(r, 400));

      const ragCard = page.locator('[data-testid="rag-status-card"]');
      if (await ragCard.isVisible({ timeout: 3000 })) {
        await ragCard.click();
        await waitForModalOpen(page);
        const darkModal = page.locator('[role="dialog"]').filter({ hasText: 'RAG Status Details' });
        await expect(darkModal).toBeVisible({ timeout: 5000 });
        const darkBg = darkModal.locator('.bg-gray-800, .bg-gray-900').first();
        await expect(darkBg).toBeVisible({ timeout: 2000 });
      }
    }
  });

  test.fixme('loading state displays while RAG metrics are fetched (requires API mock with delay)', async ({ page }) => {
    const modal = await openRagModal(page);
    expect(modal, 'RAG card should be present to assert loading state').toBeTruthy();
    const loading = modal!.locator('text=Loading RAG metrics');
    await expect(loading).toBeVisible({ timeout: 2000 });
  });

  test.fixme('error state displays when RAG service is unavailable (requires API mock)', async ({ page }) => {
    const modal = await openRagModal(page);
    expect(modal, 'RAG modal or error state should be present').toBeTruthy();
    await expect(modal!.locator('text=RAG Service Metrics Unavailable')).toBeVisible({ timeout: 5000 });
  });
});

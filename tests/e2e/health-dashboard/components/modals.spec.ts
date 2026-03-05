/**
 * Modals -- Detailed Information for Operator Investigation
 *
 * WHY THIS MATTERS:
 * When the operator clicks a service card, they need a focused view of
 * that service's details -- metrics, status, and configuration. Modals
 * serve as the drill-down mechanism. If a modal fails to open, shows
 * blank content, or traps the operator (cannot close), it breaks the
 * investigation workflow and forces a page reload.
 *
 * WHAT THE OPERATOR USES IT FOR:
 * - Clicking a service card to see detailed health metrics
 * - Reading specific error messages or status details
 * - Closing the modal to return to the list view and check the next service
 */

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForModalOpen, waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

/**
 * Navigate to the Services tab by clicking the sidebar navigation buttons.
 * Direct hash navigation is unreliable due to the app's routing behavior,
 * so we click Infrastructure > Services in the sidebar.
 */
async function navigateToServices(page: import('@playwright/test').Page) {
  await page.goto('/');
  await waitForLoadingComplete(page);

  // Expand Infrastructure section if collapsed (shows ▶), then click Services
  const infraBtn = page.locator('button:has-text("Infrastructure")').first();
  await expect(infraBtn).toBeVisible({ timeout: 10000 });
  await infraBtn.click();
  await page.waitForTimeout(300);

  const servicesBtn = page.locator('button:has-text("Services")').first();
  await expect(servicesBtn).toBeVisible({ timeout: 5000 });
  await servicesBtn.click();
  await waitForLoadingComplete(page);
  // Wait for service cards to render
  await page.waitForTimeout(1000);
}

/**
 * Open a service details modal by clicking the first visible "Details" button.
 * The service cards on the Services tab expose "Details" buttons rather than
 * being clickable cards themselves.
 */
async function openFirstServiceModal(page: import('@playwright/test').Page) {
  const detailsButton = page.getByRole('button', { name: 'Details' }).first();
  await expect(detailsButton).toBeVisible({ timeout: 10000 });
  await detailsButton.click();
  await waitForModalOpen(page);
}

test.describe('Modals -- operator investigation drill-down', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await navigateToServices(page);
  });

  test('clicking a service Details button opens a modal with meaningful content', async ({ page }) => {
    // The operator clicks "Details" on a service to investigate its health
    await openFirstServiceModal(page);

    const modal = page.locator('[role="dialog"]').first();
    await expect(modal).toBeVisible({ timeout: 3000 });

    // The modal must show actual content, not just an empty shell.
    // Look for headings, text, or data within the modal.
    const modalText = await modal.textContent();
    expect(modalText?.trim().length).toBeGreaterThan(10);
  });

  test('modal closes via the close button so the operator can return to the list', async ({ page }) => {
    await openFirstServiceModal(page);

    const modal = page.locator('[role="dialog"]').first();
    await expect(modal).toBeVisible();

    // The modal has two close buttons:
    // 1. Icon button with aria-label="Close dialog" (top-right X)
    // 2. Text button with aria-label="Close service details dialog" (bottom)
    const closeButton = modal.locator(
      'button[aria-label="Close dialog"], button[aria-label="Close service details dialog"]'
    ).first();
    await expect(closeButton).toBeVisible();
    await closeButton.click();

    await expect(modal).not.toBeVisible({ timeout: 3000 });
  });

  test('pressing Escape closes the modal for keyboard-driven operators', async ({ page }) => {
    await openFirstServiceModal(page);

    const modal = page.locator('[role="dialog"]').first();
    await expect(modal).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(modal).not.toBeVisible({ timeout: 3000 });
  });

  test('clicking the backdrop closes the modal', async ({ page }) => {
    await openFirstServiceModal(page);

    const modal = page.locator('[role="dialog"]').first();
    await expect(modal).toBeVisible();

    // The dialog element itself is the full-screen backdrop (class="fixed inset-0").
    // Clicking at position (5,5) targets the backdrop area outside the modal content.
    await modal.click({ position: { x: 5, y: 5 }, force: true });
    await expect(modal).not.toBeVisible({ timeout: 3000 });
  });

  test('modal has correct ARIA attributes for screen-reader operators', async ({ page }) => {
    await openFirstServiceModal(page);

    const modal = page.locator('[role="dialog"]').first();
    await expect(modal).toBeVisible();

    // role="dialog" is already verified by the locator.
    // aria-modal tells assistive tech to restrict interaction to the modal.
    await expect(modal).toHaveAttribute('aria-modal', 'true');

    // The modal is labelled via aria-labelledby pointing to the modal title heading
    const ariaLabel = await modal.getAttribute('aria-label');
    const ariaLabelledBy = await modal.getAttribute('aria-labelledby');
    expect(ariaLabel || ariaLabelledBy).toBeTruthy();
  });

  test('focus moves into the modal when opened (focus trap)', async ({ page }) => {
    await openFirstServiceModal(page);

    // After opening, focus should be inside the modal -- typically on the
    // close button or the first focusable element within the dialog.
    const modal = page.locator('[role="dialog"]').first();

    // The focused element should be a descendant of the modal
    const focusInsideModal = await modal.locator(':focus').count();
    expect(focusInsideModal).toBeGreaterThanOrEqual(1);
  });
});

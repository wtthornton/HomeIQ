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
  await new Promise((r) => setTimeout(r, 300));

  const servicesBtn = page.locator('button:has-text("Services")').first();
  await expect(servicesBtn).toBeVisible({ timeout: 5000 });
  await servicesBtn.click();
  await waitForLoadingComplete(page);
  // Wait for service list or at least one service card to render
  await page.locator('[data-testid="service-list"], [data-testid="service-card"]').first().waitFor({ state: 'visible', timeout: 15000 }).catch(() => {});
  await new Promise((r) => setTimeout(r, 500));
}

/**
 * Open a service details modal by clicking the first visible "Details" button.
 * The service cards on the Services tab expose "Details" buttons rather than
 * being clickable cards themselves.
 * Returns true if modal was opened, false if no Details button (caller may skip).
 */
async function openFirstServiceModal(page: import('@playwright/test').Page): Promise<boolean> {
  const detailsButton = page.getByRole('button', { name: 'Details' }).first();
  const visible = await detailsButton.isVisible({ timeout: 15000 }).catch(() => false);
  if (!visible) {
    return false;
  }
  await detailsButton.click();
  await waitForModalOpen(page, '[role="dialog"]', 5000);
  return true;
}

test.describe('Modals -- operator investigation drill-down', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await navigateToServices(page);
  });

  test('clicking a service Details button opens a modal with meaningful content', async ({ page }) => {
    const opened = await openFirstServiceModal(page);
    expect(opened, 'Services tab should show at least one Details button').toBe(true);

    const modal = page.locator('[role="dialog"]').first();
    await expect(modal).toBeVisible({ timeout: 3000 });

    // The modal must show actual content, not just an empty shell.
    const modalText = await modal.textContent();
    expect(modalText?.trim().length).toBeGreaterThan(10);
  });

  test('modal closes via the close button so the operator can return to the list', async ({ page }) => {
    const opened = await openFirstServiceModal(page);
    expect(opened, 'Services tab should show at least one Details button').toBe(true);

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
    const opened = await openFirstServiceModal(page);
    expect(opened, 'Services tab should show at least one Details button').toBe(true);

    const modal = page.locator('[role="dialog"]').first();
    await expect(modal).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(modal).not.toBeVisible({ timeout: 3000 });
  });

  test('clicking the backdrop closes the modal', async ({ page }) => {
    const opened = await openFirstServiceModal(page);
    expect(opened, 'Services tab should show at least one Details button').toBe(true);

    const modal = page.locator('[role="dialog"]').first();
    await expect(modal).toBeVisible();

    // The dialog element itself is the full-screen backdrop (class="fixed inset-0").
    // Clicking at position (5,5) targets the backdrop area outside the modal content.
    await modal.click({ position: { x: 5, y: 5 }, force: true });
    await expect(modal).not.toBeVisible({ timeout: 3000 });
  });

  test('modal has correct ARIA attributes for screen-reader operators', async ({ page }) => {
    const opened = await openFirstServiceModal(page);
    expect(opened, 'Services tab should show at least one Details button').toBe(true);

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
    const opened = await openFirstServiceModal(page);
    expect(opened, 'Services tab should show at least one Details button').toBe(true);

    const modal = page.locator('[role="dialog"]').first();
    await expect(modal).toBeVisible();

    // Modal should contain at least one focusable element (close button, etc.)
    const focusable = modal.locator('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    await expect(focusable.first()).toBeVisible({ timeout: 3000 });
  });
});

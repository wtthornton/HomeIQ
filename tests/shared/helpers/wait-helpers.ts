import { Page, Locator } from '@playwright/test';

/**
 * Custom Wait Utilities
 * Helper functions for waiting on specific conditions
 */

/**
 * Wait for element to be visible and stable
 */
export async function waitForStable(
  locator: Locator,
  timeout: number = 5000
): Promise<void> {
  await locator.waitFor({ state: 'visible', timeout });
  // Wait for any animations to complete
  await locator.page().waitForTimeout(300);
}

/**
 * Wait for network to be idle
 */
export async function waitForNetworkIdle(
  page: Page,
  timeout: number = 5000
): Promise<void> {
  await page.waitForLoadState('networkidle', { timeout });
}

/**
 * Wait for API response
 */
export async function waitForApiResponse(
  page: Page,
  urlPattern: string | RegExp,
  timeout: number = 10000
): Promise<void> {
  await page.waitForResponse(
    (response) => {
      const url = response.url();
      if (typeof urlPattern === 'string') {
        return url.includes(urlPattern);
      }
      return urlPattern.test(url);
    },
    { timeout }
  );
}

/**
 * Wait for element to stop animating
 */
export async function waitForAnimationComplete(
  locator: Locator,
  timeout: number = 2000
): Promise<void> {
  const startPosition = await locator.boundingBox();
  if (!startPosition) return;

  await locator.page().waitForTimeout(100);

  let stableCount = 0;
  const maxStableChecks = 5;

  for (let i = 0; i < maxStableChecks; i++) {
    await locator.page().waitForTimeout(100);
    const currentPosition = await locator.boundingBox();

    if (
      currentPosition &&
      Math.abs(currentPosition.x - startPosition.x) < 1 &&
      Math.abs(currentPosition.y - startPosition.y) < 1
    ) {
      stableCount++;
      if (stableCount >= 3) {
        return;
      }
    } else {
      stableCount = 0;
    }
  }
}

/**
 * Wait for loading spinner to disappear
 */
export async function waitForLoadingComplete(
  page: Page,
  spinnerSelector: string = '[data-testid="loading"], .loading, .spinner',
  timeout: number = 10000
): Promise<void> {
  try {
    const spinner = page.locator(spinnerSelector).first();
    await spinner.waitFor({ state: 'hidden', timeout });
  } catch {
    // Spinner might not exist, which is fine
  }
}

/**
 * Wait for chart to render
 */
export async function waitForChartRender(
  locator: Locator,
  timeout: number = 5000
): Promise<void> {
  await locator.waitFor({ state: 'visible', timeout });
  // Wait for canvas or SVG to be rendered
  await locator.locator('canvas, svg').first().waitFor({ state: 'visible', timeout });
}

/**
 * Wait for modal to fully open
 */
export async function waitForModalOpen(
  page: Page,
  modalSelector: string = '[role="dialog"], .modal',
  timeout: number = 3000
): Promise<void> {
  const modal = page.locator(modalSelector).first();
  await modal.waitFor({ state: 'visible', timeout });
  // Wait for modal animation
  await page.waitForTimeout(200);
}

/**
 * Wait for toast notification
 */
export async function waitForToast(
  page: Page,
  timeout: number = 3000
): Promise<void> {
  await page.waitForSelector('[role="alert"], .toast, .notification', {
    state: 'visible',
    timeout,
  });
}

/**
 * Wait for data to load (check for empty state to disappear)
 */
export async function waitForDataLoad(
  page: Page,
  emptyStateSelector: string = '[data-testid="empty-state"], .empty-state',
  timeout: number = 10000
): Promise<void> {
  try {
    const emptyState = page.locator(emptyStateSelector).first();
    await emptyState.waitFor({ state: 'hidden', timeout });
  } catch {
    // Empty state might not exist, which means data is loaded
  }
}

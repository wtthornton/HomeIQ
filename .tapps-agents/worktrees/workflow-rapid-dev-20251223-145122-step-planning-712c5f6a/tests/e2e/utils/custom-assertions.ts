/**
 * Custom Assertions for AI Automation Testing
 * 
 * Specialized assertion helpers that use Playwright's web-first assertions
 * with auto-wait and retry capabilities
 */

import { Page, expect } from '@playwright/test';

/**
 * Assert that a suggestion with given ID is visible
 * Uses web-first assertion with auto-wait
 * 
 * @param page - Playwright page
 * @param id - Suggestion ID
 * 
 * @example
 * await expectSuggestionVisible(page, 'sug-123');
 */
export async function expectSuggestionVisible(page: Page, id: string): Promise<void> {
  const suggestion = page.getByTestId(`suggestion-${id}`);
  await expect(suggestion).toBeVisible();
  await expect(suggestion).toContainText(id);
}

/**
 * Assert toast notification appears with message
 * Waits up to 5 seconds for toast to appear
 * 
 * @param page - Playwright page
 * @param type - Toast type: 'success' | 'error' | 'warning' | 'info'
 * @param message - Expected message (partial match)
 * 
 * @example
 * await expectToastMessage(page, 'success', 'Successfully deployed');
 */
export async function expectToastMessage(
  page: Page,
  type: 'success' | 'error' | 'warning' | 'info',
  message: string
): Promise<void> {
  const toast = page.getByTestId(`toast-${type}`);
  await expect(toast).toBeVisible({ timeout: 5000 });
  await expect(toast).toContainText(message);
}

/**
 * Assert pattern list has expected count
 * 
 * @param page - Playwright page
 * @param count - Expected number of patterns
 * 
 * @example
 * await expectPatternCount(page, 5);
 */
export async function expectPatternCount(page: Page, count: number): Promise<void> {
  const patterns = page.getByTestId('pattern-item');
  await expect(patterns).toHaveCount(count);
}

/**
 * Assert automation deployed successfully
 * Checks for success toast and verifies automation in deployed tab
 * 
 * @param page - Playwright page
 * @param id - Automation ID
 * 
 * @example
 * await expectDeploymentSuccess(page, 'sug-123');
 */
export async function expectDeploymentSuccess(page: Page, id: string): Promise<void> {
  // Check success toast
  await expectToastMessage(page, 'success', 'deployed');
  
  // Navigate to deployed tab and verify
  await page.goto('http://localhost:3001/deployed');
  const automation = page.getByTestId(`deployed-automation-${id}`);
  await expect(automation).toBeVisible();
}

/**
 * Assert suggestion is not visible (has been hidden/removed)
 * 
 * @param page - Playwright page
 * @param id - Suggestion ID
 * 
 * @example
 * await expectSuggestionHidden(page, 'sug-123');
 */
export async function expectSuggestionHidden(page: Page, id: string): Promise<void> {
  const suggestion = page.getByTestId(`suggestion-${id}`);
  await expect(suggestion).not.toBeVisible();
}

/**
 * Assert analysis is running
 * Checks for progress modal and status indicators
 * 
 * @param page - Playwright page
 * 
 * @example
 * await expectAnalysisRunning(page);
 */
export async function expectAnalysisRunning(page: Page): Promise<void> {
  const progressModal = page.getByTestId('analysis-progress-modal');
  await expect(progressModal).toBeVisible();
  
  const progressBar = page.getByTestId('progress-bar');
  await expect(progressBar).toBeVisible();
}

/**
 * Assert pattern chart is rendered
 * Validates that canvas element exists and has drawing context
 * 
 * @param page - Playwright page
 * 
 * @example
 * await expectChartRendered(page);
 */
export async function expectChartRendered(page: Page): Promise<void> {
  const canvas = page.locator('canvas').first();
  await expect(canvas).toBeVisible();
  
  // Verify canvas has actual context (is rendered)
  const hasContext = await page.evaluate(() => {
    const canvas = document.querySelector('canvas');
    return canvas?.getContext('2d') !== null;
  });
  
  expect(hasContext).toBe(true);
}

/**
 * Assert no console errors on page
 * Useful for smoke tests and general page health
 * 
 * @param page - Playwright page
 * @param excludePatterns - Optional patterns to exclude (e.g., '404', 'favicon')
 * 
 * @example
 * await expectNoConsoleErrors(page, ['404', 'favicon']);
 */
export async function expectNoConsoleErrors(
  page: Page,
  excludePatterns: string[] = ['404', 'favicon']
): Promise<void> {
  const consoleErrors: string[] = [];
  
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });
  
  // Wait a moment for any errors to appear
  await page.waitForTimeout(1000);
  
  // Filter out excluded patterns
  const criticalErrors = consoleErrors.filter(log => 
    !excludePatterns.some(pattern => log.includes(pattern))
  );
  
  expect(criticalErrors.length).toBe(0);
}

/**
 * Assert suggestion count matches expected value
 * 
 * @param page - Playwright page
 * @param count - Expected count
 * 
 * @example
 * await expectSuggestionCount(page, 10);
 */
export async function expectSuggestionCount(page: Page, count: number): Promise<void> {
  const suggestions = page.getByTestId('suggestion-card');
  await expect(suggestions).toHaveCount(count);
}

/**
 * Assert field has validation error
 * 
 * @param page - Playwright page
 * @param fieldLabel - Field label
 * @param errorMessage - Expected error message
 * 
 * @example
 * await expectFieldValidationError(page, 'API Key', 'Invalid format');
 */
export async function expectFieldValidationError(
  page: Page,
  fieldLabel: string,
  errorMessage: string
): Promise<void> {
  const field = page.getByLabel(fieldLabel);
  const errorElement = field.locator('..').getByText(errorMessage);
  await expect(errorElement).toBeVisible();
}

/**
 * Assert loading spinner is visible
 * 
 * @param page - Playwright page
 * 
 * @example
 * await expectLoadingSpinner(page);
 */
export async function expectLoadingSpinner(page: Page): Promise<void> {
  const spinner = page.getByTestId('loading-spinner');
  await expect(spinner).toBeVisible();
}

/**
 * Assert loading spinner is hidden
 * 
 * @param page - Playwright page
 * 
 * @example
 * await expectLoadingComplete(page);
 */
export async function expectLoadingComplete(page: Page): Promise<void> {
  const spinner = page.getByTestId('loading-spinner');
  await expect(spinner).not.toBeVisible();
}


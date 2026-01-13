/**
 * Settings Page 404 Error Handling Test
 * Validates that settings page handles 404 errors gracefully
 */

import { test, expect } from '@playwright/test';

async function mockSettingsAPI(page: any) {
  await page.route('**/api/settings*', route => {
    const method = route.request().method();
    if (method === 'GET') {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          scheduleEnabled: true,
          scheduleTime: '03:00',
          minConfidence: 70,
          maxSuggestions: 10,
          enabledCategories: {
            energy: true,
            comfort: true,
            security: true,
            convenience: true,
          },
          budgetLimit: 10,
          notificationsEnabled: false,
          notificationEmail: '',
          softPromptEnabled: true,
          softPromptModelDir: 'data/ask_ai_soft_prompt',
          softPromptConfidenceThreshold: 0.85,
          guardrailEnabled: true,
          guardrailModelName: 'unitary/toxic-bert',
          guardrailThreshold: 0.6,
          enableParallelModelTesting: false,
        })
      });
    } else {
      route.continue();
    }
  });
}

test.describe('Settings Page - 404 Error Handling', () => {
  test('should handle 404 error from preferences API gracefully', async ({ page }) => {
    // Mock settings API
    await mockSettingsAPI(page);
    
    // Mock preferences API to return 404
    await page.route('**/api/v1/preferences*', route => {
      const method = route.request().method();
      if (method === 'GET') {
        route.fulfill({
          status: 404,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Not Found' })
        });
      } else {
        route.continue();
      }
    });

    // Navigate to settings page
    await page.goto('http://localhost:3001/settings');
    await expect(page.getByTestId('settings-container')).toBeVisible({ timeout: 10000 });

    // Wait for preference section to load
    await expect(page.getByTestId('preference-settings-section')).toBeVisible({ timeout: 10000 });

    // Verify that NO error message is shown (404 handled gracefully)
    const errorMessage = page.getByText(/failed to load preferences/i);
    await expect(errorMessage).not.toBeVisible({ timeout: 2000 });

    // Verify preference controls are visible and working with defaults
    await expect(page.getByTestId('max-suggestions-slider')).toBeVisible();
    await expect(page.getByTestId('max-suggestions-slider')).toHaveValue('10'); // default value

    await expect(page.getByTestId('creativity-level-dropdown')).toBeVisible();
    await expect(page.getByTestId('creativity-level-dropdown')).toHaveValue('balanced'); // default value

    await expect(page.getByTestId('blueprint-preference-dropdown')).toBeVisible();
    await expect(page.getByTestId('blueprint-preference-dropdown')).toHaveValue('medium'); // default value
  });

  test('should allow saving preferences after 404 error', async ({ page }) => {
    // Mock settings API
    await mockSettingsAPI(page);
    
    let getCalled = false;
    let putCalled = false;

    // Mock preferences API
    await page.route('**/api/v1/preferences*', route => {
      const method = route.request().method();
      const url = new URL(route.request().url());
      
      if (method === 'GET') {
        getCalled = true;
        // First call returns 404, subsequent calls return data
        route.fulfill({
          status: 404,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Not Found' })
        });
      } else if (method === 'PUT') {
        putCalled = true;
        const requestBody = route.request().postDataJSON();
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            max_suggestions: requestBody.max_suggestions ?? 10,
            creativity_level: requestBody.creativity_level ?? 'balanced',
            blueprint_preference: requestBody.blueprint_preference ?? 'medium'
          })
        });
      }
    });

    // Navigate to settings page
    await page.goto('http://localhost:3001/settings');
    await expect(page.getByTestId('preference-settings-section')).toBeVisible({ timeout: 10000 });

    // Verify no error is shown
    const errorMessage = page.getByText(/failed to load preferences/i);
    await expect(errorMessage).not.toBeVisible({ timeout: 2000 });

    // Update a preference
    const slider = page.getByTestId('max-suggestions-slider');
    await slider.fill('25');

    // Wait for PUT request
    await page.waitForResponse(response => 
      response.url().includes('/api/v1/preferences') && 
      response.request().method() === 'PUT',
      { timeout: 5000 }
    );

    // Verify success
    await expect(page.getByText(/preferences saved successfully/i)).toBeVisible({ timeout: 3000 });
  });

  test('should handle network errors gracefully', async ({ page }) => {
    // Mock settings API
    await mockSettingsAPI(page);
    
    // Mock preferences API to fail with network error
    await page.route('**/api/v1/preferences*', route => {
      route.abort('failed');
    });

    // Navigate to settings page
    await page.goto('http://localhost:3001/settings');
    await expect(page.getByTestId('settings-container')).toBeVisible({ timeout: 10000 });

    // Wait a bit for the request to fail
    await page.waitForTimeout(2000);

    // Preference section should still be visible with defaults
    // (component should handle network errors gracefully)
    const preferenceSection = page.getByTestId('preference-settings-section');
    await expect(preferenceSection).toBeVisible({ timeout: 5000 });

    // Verify default values are used
    await expect(page.getByTestId('max-suggestions-slider')).toHaveValue('10');
  });
});

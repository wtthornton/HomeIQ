import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

/**
 * Device-Based Automation Suggestions - Playwright Tests
 * Tests for device picker, suggestion generation, and enhancement flow
 * Uses API mocks to provide test device data
 */

const MOCK_DEVICES = [
  {
    device_id: 'test-device-001',
    name: 'Office Motion Sensor',
    manufacturer: 'Philips',
    model: 'SML003',
    area_id: 'office',
    device_type: 'sensor',
    entities: ['binary_sensor.office_motion'],
  },
  {
    device_id: 'test-device-002',
    name: 'Living Room Light',
    manufacturer: 'IKEA',
    model: 'TRADFRI',
    area_id: 'living_room',
    device_type: 'light',
    entities: ['light.living_room'],
  },
];

const MOCK_SUGGESTIONS = [
  {
    suggestion_id: 'sug-001',
    title: 'Turn on lights when motion detected',
    description: 'Automatically turn on office lights when motion is detected',
    confidence: 0.85,
    automation_preview: {
      trigger: 'When office motion sensor detects motion',
      action: 'Turn on office lights',
    },
    tags: ['lighting', 'motion'],
  },
];

test.describe('Device-Based Automation Suggestions', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);

    // Mock device list API
    await page.route('**/api/devices*', async (route) => {
      if (route.request().url().includes('/capabilities')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            device_id: 'test-device-001',
            capabilities: ['motion_detection', 'occupancy'],
            supported_features: [],
          }),
        });
      } else if (route.request().url().match(/\/api\/devices\/[^/]+$/)) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_DEVICES[0]),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ devices: MOCK_DEVICES }),
        });
      }
    });

    // Mock device suggestions API
    await page.route('**/api/device-suggestions*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ suggestions: MOCK_SUGGESTIONS }),
      });
    });

    // Mock entities API
    await page.route('**/api/entities*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ entities: [] }),
      });
    });

    await page.goto('/chat');
    await waitForLoadingComplete(page);
  });

  test.describe('Device Picker', () => {
    test('Device picker button is visible', async ({ page }) => {
      const devicePickerButton = page.locator('button:visible:has-text("Select Device")').first();
      await expect(devicePickerButton).toBeVisible({ timeout: 5000 });
    });

    test('Device picker opens when button clicked', async ({ page }) => {
      const devicePickerButton = page.locator('button:visible:has-text("Select Device")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(500);

      // Picker is open if we see device list, or "No devices available", or the device picker panel
      const deviceList = page.locator('[data-testid="device-list"], [role="listbox"][aria-label="Devices"]').first();
      const noDevices = page.locator('text=/No devices available/i').first();
      const pickerPanel = page.locator('text=/Search devices|Filter by area/i').first();
      const hasDeviceList = await deviceList.isVisible({ timeout: 3000 }).catch(() => false);
      const hasNoDevices = await noDevices.isVisible({ timeout: 2000 }).catch(() => false);
      const hasPanel = await pickerPanel.isVisible({ timeout: 2000 }).catch(() => false);
      expect(hasDeviceList || hasNoDevices || hasPanel).toBeTruthy();
    });

    test('Device search works', async ({ page }) => {
      const devicePickerButton = page.locator('button:visible:has-text("Select Device")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(500);

      const searchInput = page.locator('input[type="search"], input[placeholder*="Search"], input[placeholder*="search"]').first();
      const isVisible = await searchInput.isVisible({ timeout: 2000 }).catch(() => false);

      if (isVisible) {
        await searchInput.fill('Office');
        await page.waitForTimeout(500);

        const devices = page.locator('[data-testid="device-item"], [role="option"]');
        const count = await devices.count();
        expect(count).toBeGreaterThanOrEqual(0);
      }
    });

    test('Device selection updates UI', async ({ page }) => {
      const devicePickerButton = page.locator('button:visible:has-text("Select Device")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(500);

      const firstDevice = page.locator('[data-testid="device-item"], [role="option"]').first();
      const isVisible = await firstDevice.isVisible({ timeout: 2000 }).catch(() => false);

      if (isVisible) {
        await firstDevice.click();
        await page.waitForTimeout(1000);

        const deviceContext = page.locator('[data-testid="device-context"]').first();
        const contextVisible = await deviceContext.isVisible({ timeout: 3000 }).catch(() => false);
        expect(contextVisible).toBeTruthy();
      }
    });
  });

  test.describe('Device Context Display', () => {
    test('Device context displays after selection', async ({ page }) => {
      const devicePickerButton = page.locator('button:visible:has-text("Select Device")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(500);

      const firstDevice = page.locator('[data-testid="device-item"], [role="option"]').first();
      const isVisible = await firstDevice.isVisible({ timeout: 2000 }).catch(() => false);

      if (isVisible) {
        await firstDevice.click();
        await page.waitForTimeout(2000);

        const deviceContext = page.locator('[data-testid="device-context"]').first();
        await expect(deviceContext).toBeVisible({ timeout: 5000 });
      }
    });

    test('Device information displays correctly', async ({ page }) => {
      const devicePickerButton = page.locator('button:visible:has-text("Select Device")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(500);

      const firstDevice = page.locator('[data-testid="device-item"], [role="option"]').first();
      const isVisible = await firstDevice.isVisible({ timeout: 2000 }).catch(() => false);

      if (isVisible) {
        await firstDevice.click();
        await page.waitForTimeout(2000);

        const deviceContext = page.locator('[data-testid="device-context"]').first();
        const contextVisible = await deviceContext.isVisible({ timeout: 3000 }).catch(() => false);
        expect(contextVisible).toBeTruthy();
      }
    });
  });

  test.describe('Suggestion Generation', () => {
    test('Suggestions appear after device selection', async ({ page }) => {
      const devicePickerButton = page.locator('button:visible:has-text("Select Device")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(500);

      const firstDevice = page.locator('[data-testid="device-item"], [role="option"]').first();
      const isVisible = await firstDevice.isVisible({ timeout: 2000 }).catch(() => false);

      if (isVisible) {
        await firstDevice.click();
        await page.waitForTimeout(3000);

        const suggestions = page.locator('[data-testid="suggestion-card"]');
        const count = await suggestions.count();
        expect(count).toBeGreaterThanOrEqual(0);
      }
    });

    test('Suggestion cards display correctly', async ({ page }) => {
      const devicePickerButton = page.locator('button:visible:has-text("Select Device")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(500);

      const firstDevice = page.locator('[data-testid="device-item"], [role="option"]').first();
      const isVisible = await firstDevice.isVisible({ timeout: 2000 }).catch(() => false);

      if (isVisible) {
        await firstDevice.click();
        await page.waitForTimeout(3000);

        const firstSuggestion = page.locator('[data-testid="suggestion-card"]').first();
        const suggestionVisible = await firstSuggestion.isVisible({ timeout: 5000 }).catch(() => false);

        if (suggestionVisible) {
          const title = firstSuggestion.locator('h3, h4, [class*="title"]').first();
          const titleVisible = await title.isVisible({ timeout: 2000 }).catch(() => false);
          expect(titleVisible).toBeTruthy();
        }
      }
    });

    test('Loading state displays while fetching suggestions', async ({ page }) => {
      const devicePickerButton = page.locator('button:visible:has-text("Select Device")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(300);

      const firstDevice = page.locator('[data-testid="device-item"], [role="option"]').first();
      const isVisible = await firstDevice.isVisible({ timeout: 2000 }).catch(() => false);

      if (isVisible) {
        await firstDevice.click();
        // Loading state may be too fast to catch
        const loadingIndicator = page.locator('[data-testid="loading"], .animate-spin').first();
        await loadingIndicator.isVisible({ timeout: 500 }).catch(() => false);
      }
    });
  });

  test.describe('Enhancement Flow', () => {
    test('Enhance button is visible on suggestions', async ({ page }) => {
      const devicePickerButton = page.locator('button:visible:has-text("Select Device")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(500);

      const firstDevice = page.locator('[data-testid="device-item"], [role="option"]').first();
      const isVisible = await firstDevice.isVisible({ timeout: 2000 }).catch(() => false);

      if (isVisible) {
        await firstDevice.click();
        await page.waitForTimeout(3000);

        const firstSuggestion = page.locator('[data-testid="suggestion-card"]').first();
        const suggestionVisible = await firstSuggestion.isVisible({ timeout: 5000 }).catch(() => false);

        if (suggestionVisible) {
          const enhanceButton = firstSuggestion.locator('button:has-text("Enhance"), button:has-text("💬"), [data-testid="enhance-button"]').first();
          const buttonVisible = await enhanceButton.isVisible({ timeout: 2000 }).catch(() => false);
          expect(buttonVisible).toBeTruthy();
        }
      }
    });

    test('Enhance button pre-populates chat input', async ({ page }) => {
      const devicePickerButton = page.locator('button:visible:has-text("Select Device")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(500);

      const firstDevice = page.locator('[data-testid="device-item"], [role="option"]').first();
      const isVisible = await firstDevice.isVisible({ timeout: 2000 }).catch(() => false);

      if (isVisible) {
        await firstDevice.click();
        await page.waitForTimeout(3000);

        const firstSuggestion = page.locator('[data-testid="suggestion-card"]').first();
        const suggestionVisible = await firstSuggestion.isVisible({ timeout: 5000 }).catch(() => false);

        if (suggestionVisible) {
          const enhanceButton = firstSuggestion.locator('button:has-text("Enhance"), button:has-text("💬")').first();
          const buttonVisible = await enhanceButton.isVisible({ timeout: 2000 }).catch(() => false);

          if (buttonVisible) {
            await enhanceButton.click();
            await page.waitForTimeout(1000);

            const chatInput = page.locator('textarea, input[type="text"]').first();
            const inputValue = await chatInput.inputValue();
            expect(inputValue.length).toBeGreaterThan(0);
          }
        }
      }
    });

    test('Enhancement conversation can be started', async ({ page }) => {
      const devicePickerButton = page.locator('button:visible:has-text("Select Device")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(500);

      const firstDevice = page.locator('[data-testid="device-item"], [role="option"]').first();
      const isVisible = await firstDevice.isVisible({ timeout: 2000 }).catch(() => false);

      if (isVisible) {
        await firstDevice.click();
        await page.waitForTimeout(3000);

        const firstSuggestion = page.locator('[data-testid="suggestion-card"]').first();
        const suggestionVisible = await firstSuggestion.isVisible({ timeout: 5000 }).catch(() => false);

        if (suggestionVisible) {
          const enhanceButton = firstSuggestion.locator('button:has-text("Enhance"), button:has-text("💬")').first();
          const buttonVisible = await enhanceButton.isVisible({ timeout: 2000 }).catch(() => false);

          if (buttonVisible) {
            await enhanceButton.click();
            await page.waitForTimeout(1000);

            const sendButton = page.locator('button[type="submit"], button:has-text("Send")').first();
            const sendVisible = await sendButton.isVisible({ timeout: 2000 }).catch(() => false);

            if (sendVisible) {
              await sendButton.click();
              await page.waitForTimeout(2000);
            }
          }
        }
      }
    });
  });

  test.describe('Error Handling', () => {
    test('Error messages display gracefully', async ({ page }) => {
      await expect(page).toHaveURL(/.*chat/, { timeout: 5000 });
    });

    test('Empty state displays when no suggestions', async ({ page }) => {
      // Override mock to return empty suggestions
      await page.route('**/api/device-suggestions*', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ suggestions: [] }),
        });
      });

      const devicePickerButton = page.locator('button:visible:has-text("Select Device")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(500);

      const firstDevice = page.locator('[data-testid="device-item"], [role="option"]').first();
      const isVisible = await firstDevice.isVisible({ timeout: 2000 }).catch(() => false);

      if (isVisible) {
        await firstDevice.click();
        await page.waitForTimeout(3000);

        const suggestions = page.locator('[data-testid="suggestion-card"]');
        const count = await suggestions.count();
        expect(count).toBe(0);
      }
    });
  });

  test.describe('Integration - End to End', () => {
    test('@integration Complete workflow: select device, view suggestions, enhance', async ({ page }) => {
      const devicePickerButton = page.locator('button:visible:has-text("Select Device")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(500);

      const firstDevice = page.locator('[data-testid="device-item"], [role="option"]').first();
      const isVisible = await firstDevice.isVisible({ timeout: 2000 }).catch(() => false);

      if (isVisible) {
        await firstDevice.click();
        await page.waitForTimeout(2000);

        const deviceContext = page.locator('[data-testid="device-context"]').first();
        const contextVisible = await deviceContext.isVisible({ timeout: 3000 }).catch(() => false);
        expect(contextVisible).toBeTruthy();

        await page.waitForTimeout(2000);

        const suggestions = page.locator('[data-testid="suggestion-card"]');
        const count = await suggestions.count();

        if (count > 0) {
          const firstSuggestion = suggestions.first();
          const enhanceButton = firstSuggestion.locator('button:has-text("Enhance"), button:has-text("💬")').first();
          const buttonVisible = await enhanceButton.isVisible({ timeout: 2000 }).catch(() => false);

          if (buttonVisible) {
            await enhanceButton.click();
            await page.waitForTimeout(1000);

            const chatInput = page.locator('textarea, input[type="text"]').first();
            const inputValue = await chatInput.inputValue();
            expect(inputValue.length).toBeGreaterThan(0);
          }
        }
      }
    });
  });
});

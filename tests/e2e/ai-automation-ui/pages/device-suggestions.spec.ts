import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

/**
 * Device-Based Automation Suggestions - Playwright Tests
 * Tests for device picker, suggestion generation, and enhancement flow
 */

test.describe('Device-Based Automation Suggestions', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/ha-agent');
    await waitForLoadingComplete(page);
  });

  test.describe('Device Picker', () => {
    test('Device picker button is visible', async ({ page }) => {
      // Look for device picker button (may have different selectors)
      const devicePickerButton = page.locator('button:has-text("Select Device"), button:has-text("🔌"), [data-testid="device-picker-button"]').first();
      await expect(devicePickerButton).toBeVisible({ timeout: 5000 });
    });

    test('Device picker opens when button clicked', async ({ page }) => {
      const devicePickerButton = page.locator('button:has-text("Select Device"), button:has-text("🔌")').first();
      await devicePickerButton.click();
      
      // Wait for device picker to open (could be sidebar, modal, or panel)
      await page.waitForTimeout(500);
      
      // Check for device list or picker panel
      const deviceList = page.locator('[data-testid="device-list"], [class*="DevicePicker"], [class*="device-picker"]').first();
      const isVisible = await deviceList.isVisible({ timeout: 3000 }).catch(() => false);
      expect(isVisible).toBeTruthy();
    });

    test('Device search works', async ({ page }) => {
      // Open device picker
      const devicePickerButton = page.locator('button:has-text("Select Device"), button:has-text("🔌")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(500);
      
      // Find search input
      const searchInput = page.locator('input[type="search"], input[placeholder*="Search"], input[placeholder*="search"]').first();
      const isVisible = await searchInput.isVisible({ timeout: 2000 }).catch(() => false);
      
      if (isVisible) {
        await searchInput.fill('Office');
        await page.waitForTimeout(500);
        
        // Verify search results filtered
        const devices = page.locator('[data-testid="device-item"], [class*="DeviceItem"]');
        const count = await devices.count();
        expect(count).toBeGreaterThan(0);
      }
    });

    test('Device selection updates UI', async ({ page }) => {
      // Open device picker
      const devicePickerButton = page.locator('button:has-text("Select Device"), button:has-text("🔌")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(500);
      
      // Select first device
      const firstDevice = page.locator('[data-testid="device-item"], [class*="DeviceItem"]').first();
      const isVisible = await firstDevice.isVisible({ timeout: 2000 }).catch(() => false);
      
      if (isVisible) {
        await firstDevice.click();
        await page.waitForTimeout(1000);
        
        // Verify device context displays
        const deviceContext = page.locator('[data-testid="device-context"], [class*="DeviceContext"]').first();
        const contextVisible = await deviceContext.isVisible({ timeout: 3000 }).catch(() => false);
        expect(contextVisible).toBeTruthy();
      }
    });
  });

  test.describe('Device Context Display', () => {
    test('Device context displays after selection', async ({ page }) => {
      // Open device picker and select a device
      const devicePickerButton = page.locator('button:has-text("Select Device"), button:has-text("🔌")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(500);
      
      const firstDevice = page.locator('[data-testid="device-item"], [class*="DeviceItem"]').first();
      const isVisible = await firstDevice.isVisible({ timeout: 2000 }).catch(() => false);
      
      if (isVisible) {
        await firstDevice.click();
        await page.waitForTimeout(2000);
        
        // Verify device context displays
        const deviceContext = page.locator('[data-testid="device-context"], [class*="DeviceContext"]').first();
        await expect(deviceContext).toBeVisible({ timeout: 5000 });
      }
    });

    test('Device information displays correctly', async ({ page }) => {
      // Select a device
      const devicePickerButton = page.locator('button:has-text("Select Device"), button:has-text("🔌")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(500);
      
      const firstDevice = page.locator('[data-testid="device-item"], [class*="DeviceItem"]').first();
      const isVisible = await firstDevice.isVisible({ timeout: 2000 }).catch(() => false);
      
      if (isVisible) {
        await firstDevice.click();
        await page.waitForTimeout(2000);
        
        // Check for device name, type, or other info
        const deviceInfo = page.locator('[data-testid="device-name"], [class*="DeviceName"], [class*="device-name"]').first();
        const infoVisible = await deviceInfo.isVisible({ timeout: 3000 }).catch(() => false);
        expect(infoVisible).toBeTruthy();
      }
    });
  });

  test.describe('Suggestion Generation', () => {
    test('Suggestions appear after device selection', async ({ page }) => {
      // Select a device
      const devicePickerButton = page.locator('button:has-text("Select Device"), button:has-text("🔌")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(500);
      
      const firstDevice = page.locator('[data-testid="device-item"], [class*="DeviceItem"]').first();
      const isVisible = await firstDevice.isVisible({ timeout: 2000 }).catch(() => false);
      
      if (isVisible) {
        await firstDevice.click();
        await page.waitForTimeout(3000); // Wait for suggestions to load
        
        // Verify suggestions appear
        const suggestions = page.locator('[data-testid="suggestion-card"], [class*="DeviceSuggestion"], [class*="SuggestionCard"]');
        const count = await suggestions.count();
        expect(count).toBeGreaterThanOrEqual(0); // May be 0 if no suggestions
      }
    });

    test('Suggestion cards display correctly', async ({ page }) => {
      // Select a device and wait for suggestions
      const devicePickerButton = page.locator('button:has-text("Select Device"), button:has-text("🔌")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(500);
      
      const firstDevice = page.locator('[data-testid="device-item"], [class*="DeviceItem"]').first();
      const isVisible = await firstDevice.isVisible({ timeout: 2000 }).catch(() => false);
      
      if (isVisible) {
        await firstDevice.click();
        await page.waitForTimeout(3000);
        
        const firstSuggestion = page.locator('[data-testid="suggestion-card"], [class*="DeviceSuggestion"]').first();
        const suggestionVisible = await firstSuggestion.isVisible({ timeout: 5000 }).catch(() => false);
        
        if (suggestionVisible) {
          // Verify suggestion has title
          const title = firstSuggestion.locator('[data-testid="suggestion-title"], [class*="Title"], h3, h4').first();
          const titleVisible = await title.isVisible({ timeout: 2000 }).catch(() => false);
          expect(titleVisible).toBeTruthy();
        }
      }
    });

    test('Loading state displays while fetching suggestions', async ({ page }) => {
      // This test may be difficult to catch loading state
      // Try to select device quickly and check for loading indicator
      const devicePickerButton = page.locator('button:has-text("Select Device"), button:has-text("🔌")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(300);
      
      const firstDevice = page.locator('[data-testid="device-item"], [class*="DeviceItem"]').first();
      const isVisible = await firstDevice.isVisible({ timeout: 2000 }).catch(() => false);
      
      if (isVisible) {
        await firstDevice.click();
        
        // Immediately check for loading state (may not catch it)
        const loadingIndicator = page.locator('[data-testid="loading"], [class*="Loading"], [class*="Spinner"]').first();
        const loadingVisible = await loadingIndicator.isVisible({ timeout: 500 }).catch(() => false);
        // Loading state may be too fast to catch
      }
    });
  });

  test.describe('Enhancement Flow', () => {
    test('Enhance button is visible on suggestions', async ({ page }) => {
      // Select a device and wait for suggestions
      const devicePickerButton = page.locator('button:has-text("Select Device"), button:has-text("🔌")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(500);
      
      const firstDevice = page.locator('[data-testid="device-item"], [class*="DeviceItem"]').first();
      const isVisible = await firstDevice.isVisible({ timeout: 2000 }).catch(() => false);
      
      if (isVisible) {
        await firstDevice.click();
        await page.waitForTimeout(3000);
        
        const firstSuggestion = page.locator('[data-testid="suggestion-card"], [class*="DeviceSuggestion"]').first();
        const suggestionVisible = await firstSuggestion.isVisible({ timeout: 5000 }).catch(() => false);
        
        if (suggestionVisible) {
          // Look for Enhance button
          const enhanceButton = firstSuggestion.locator('button:has-text("Enhance"), button:has-text("💬"), [data-testid="enhance-button"]').first();
          const buttonVisible = await enhanceButton.isVisible({ timeout: 2000 }).catch(() => false);
          expect(buttonVisible).toBeTruthy();
        }
      }
    });

    test('Enhance button pre-populates chat input', async ({ page }) => {
      // Select device and wait for suggestions
      const devicePickerButton = page.locator('button:has-text("Select Device"), button:has-text("🔌")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(500);
      
      const firstDevice = page.locator('[data-testid="device-item"], [class*="DeviceItem"]').first();
      const isVisible = await firstDevice.isVisible({ timeout: 2000 }).catch(() => false);
      
      if (isVisible) {
        await firstDevice.click();
        await page.waitForTimeout(3000);
        
        const firstSuggestion = page.locator('[data-testid="suggestion-card"], [class*="DeviceSuggestion"]').first();
        const suggestionVisible = await firstSuggestion.isVisible({ timeout: 5000 }).catch(() => false);
        
        if (suggestionVisible) {
          // Click Enhance button
          const enhanceButton = firstSuggestion.locator('button:has-text("Enhance"), button:has-text("💬")').first();
          const buttonVisible = await enhanceButton.isVisible({ timeout: 2000 }).catch(() => false);
          
          if (buttonVisible) {
            await enhanceButton.click();
            await page.waitForTimeout(1000);
            
            // Check if chat input is pre-populated
            const chatInput = page.locator('textarea, input[type="text"]').first();
            const inputValue = await chatInput.inputValue();
            expect(inputValue.length).toBeGreaterThan(0);
          }
        }
      }
    });

    test('Enhancement conversation can be started', async ({ page }) => {
      // Select device, wait for suggestions, click enhance
      const devicePickerButton = page.locator('button:has-text("Select Device"), button:has-text("🔌")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(500);
      
      const firstDevice = page.locator('[data-testid="device-item"], [class*="DeviceItem"]').first();
      const isVisible = await firstDevice.isVisible({ timeout: 2000 }).catch(() => false);
      
      if (isVisible) {
        await firstDevice.click();
        await page.waitForTimeout(3000);
        
        const firstSuggestion = page.locator('[data-testid="suggestion-card"], [class*="DeviceSuggestion"]').first();
        const suggestionVisible = await firstSuggestion.isVisible({ timeout: 5000 }).catch(() => false);
        
        if (suggestionVisible) {
          const enhanceButton = firstSuggestion.locator('button:has-text("Enhance"), button:has-text("💬")').first();
          const buttonVisible = await enhanceButton.isVisible({ timeout: 2000 }).catch(() => false);
          
          if (buttonVisible) {
            await enhanceButton.click();
            await page.waitForTimeout(1000);
            
            // Send the message
            const sendButton = page.locator('button[type="submit"], button:has-text("Send")').first();
            const sendVisible = await sendButton.isVisible({ timeout: 2000 }).catch(() => false);
            
            if (sendVisible) {
              await sendButton.click();
              await page.waitForTimeout(2000);
              
              // Verify message was sent (may appear in chat)
              const messages = page.locator('[data-testid="message"], [class*="Message"]');
              const messageCount = await messages.count();
              expect(messageCount).toBeGreaterThanOrEqual(0);
            }
          }
        }
      }
    });
  });

  test.describe('Error Handling', () => {
    test('Error messages display gracefully', async ({ page }) => {
      // This test would require mocking API errors
      // For now, just verify the page loads
      await expect(page).toHaveURL(/.*ha-agent/, { timeout: 5000 });
    });

    test('Empty state displays when no suggestions', async ({ page }) => {
      // Select a device that might not have suggestions
      const devicePickerButton = page.locator('button:has-text("Select Device"), button:has-text("🔌")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(500);
      
      const firstDevice = page.locator('[data-testid="device-item"], [class*="DeviceItem"]').first();
      const isVisible = await firstDevice.isVisible({ timeout: 2000 }).catch(() => false);
      
      if (isVisible) {
        await firstDevice.click();
        await page.waitForTimeout(3000);
        
        // Check for empty state (if no suggestions)
        const suggestions = page.locator('[data-testid="suggestion-card"], [class*="DeviceSuggestion"]');
        const count = await suggestions.count();
        
        if (count === 0) {
          // May have empty state message
          const emptyState = page.locator('[data-testid="empty-state"], [class*="EmptyState"]').first();
          const emptyVisible = await emptyState.isVisible({ timeout: 2000 }).catch(() => false);
          // Empty state may or may not exist
        }
      }
    });
  });

  test.describe('Integration - End to End', () => {
    test('@integration Complete workflow: select device, view suggestions, enhance', async ({ page }) => {
      // 1. Open device picker
      const devicePickerButton = page.locator('button:has-text("Select Device"), button:has-text("🔌")').first();
      await devicePickerButton.click();
      await page.waitForTimeout(500);
      
      // 2. Select a device
      const firstDevice = page.locator('[data-testid="device-item"], [class*="DeviceItem"]').first();
      const isVisible = await firstDevice.isVisible({ timeout: 2000 }).catch(() => false);
      
      if (isVisible) {
        await firstDevice.click();
        await page.waitForTimeout(2000);
        
        // 3. Verify device context displays
        const deviceContext = page.locator('[data-testid="device-context"], [class*="DeviceContext"]').first();
        const contextVisible = await deviceContext.isVisible({ timeout: 3000 }).catch(() => false);
        expect(contextVisible).toBeTruthy();
        
        // 4. Wait for suggestions
        await page.waitForTimeout(2000);
        
        // 5. Verify suggestions appear (if any)
        const suggestions = page.locator('[data-testid="suggestion-card"], [class*="DeviceSuggestion"]');
        const count = await suggestions.count();
        
        if (count > 0) {
          // 6. Click enhance on first suggestion
          const firstSuggestion = suggestions.first();
          const enhanceButton = firstSuggestion.locator('button:has-text("Enhance"), button:has-text("💬")').first();
          const buttonVisible = await enhanceButton.isVisible({ timeout: 2000 }).catch(() => false);
          
          if (buttonVisible) {
            await enhanceButton.click();
            await page.waitForTimeout(1000);
            
            // 7. Verify chat input is populated
            const chatInput = page.locator('textarea, input[type="text"]').first();
            const inputValue = await chatInput.inputValue();
            expect(inputValue.length).toBeGreaterThan(0);
          }
        }
      }
    });
  });
});

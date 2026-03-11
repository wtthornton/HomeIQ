/**
 * Device Picker Filters Test - "Can I filter devices effectively in the picker?"
 *
 * WHY THIS COMPONENT EXISTS:
 * The DevicePicker on the Chat page lets users select a specific device before
 * asking the AI for suggestions. When a user has dozens or hundreds of smart
 * devices, they need filters to find the right one quickly. The picker provides
 * search, device type, area, and manufacturer filters that narrow the list.
 *
 * WHAT THE USER NEEDS:
 * - Search by device name to find a specific device quickly
 * - Filter by device type (light, sensor, fan, etc.) to browse categories
 * - Filter by area (office, kitchen, etc.) to find devices by room
 * - Filter by manufacturer to find devices from a specific brand
 * - Combine multiple filters for precise results
 * - Clear all filters to see the full device list again
 *
 * WHAT OLD TESTS MISSED:
 * - P5.4 test had `expect(true).toBe(true)` fallback that always passed
 * - "should maintain filter state" documented a known behavior (filters reset on remount)
 *   but the assertion accepted both outcomes
 * - "should handle filter changes without errors" set up console listener AFTER the
 *   actions, so it could never catch errors from those actions
 */

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../shared/helpers/auth-helpers';
import { isIgnorableConsoleError } from '../../shared/helpers/console-filters';
import { waitForLoadingComplete } from '../../shared/helpers/wait-helpers';

test.describe('Device Picker Filters - Can I filter devices effectively?', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/chat');
    await waitForLoadingComplete(page);
    await page.waitForLoadState('domcontentloaded');

    // Open the device picker
    const selectDeviceButton = page.getByRole('button', { name: /Select Device|Choose Device/i }).first();
    if (await selectDeviceButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      await selectDeviceButton.click();
      await page.waitForFunction(
        () => document.querySelector('[role="listbox"], [role="dialog"], [class*="picker"]') !== null,
        { timeout: 5000 }
      ).catch(() => {});
    }
  });

  test('all filter controls are displayed in the picker', async ({ page }) => {
    const searchInput = page.getByPlaceholder('Search devices...');
    await expect(searchInput).toBeVisible();

    const deviceTypeSelect = page.locator('select').filter({ hasText: /All Device Types/i });
    await expect(deviceTypeSelect).toBeVisible();

    const areaInput = page.getByPlaceholder('Filter by area...');
    await expect(areaInput).toBeVisible();

    const manufacturerInput = page.getByPlaceholder('Filter by manufacturer...');
    await expect(manufacturerInput).toBeVisible();
  });

  test('search by name filters the device list', async ({ page }) => {
    const searchInput = page.getByPlaceholder('Search devices...');
    const deviceListbox = page.locator('[role="listbox"][aria-label="Devices"]');

    const initialDevices = await deviceListbox.locator('[role="option"]').count();

    await searchInput.fill('office');
    await page.waitForTimeout(1000);

    const filteredDevices = await deviceListbox.locator('[role="option"]').count();
    expect(filteredDevices).toBeLessThanOrEqual(initialDevices);

    // All visible devices should contain the search term
    const deviceTexts = await deviceListbox.locator('[role="option"]').allTextContents();
    for (const text of deviceTexts) {
      expect(text.toLowerCase()).toContain('office');
    }
  });

  test('device type dropdown filters by category', async ({ page }) => {
    const deviceTypeSelect = page.locator('select').filter({ hasText: /All Device Types/i });
    const deviceListbox = page.locator('[role="listbox"][aria-label="Devices"]');

    await page.waitForTimeout(1000);
    const initialDevices = await deviceListbox.locator('[role="option"]').count();
    expect(initialDevices, 'Device picker should have at least one device option to filter').toBeGreaterThan(0);

    await deviceTypeSelect.selectOption('fan');
    await page.waitForTimeout(2000);

    const filteredDevices = await deviceListbox.locator('[role="option"]').count();

    if (filteredDevices === 0) {
      // Valid: no fans available, should show empty state
      const emptyState = page.locator('text=/No devices found/i');
      await expect(emptyState).toBeVisible({ timeout: 5000 });
    } else {
      // All visible devices should be fans
      const deviceTexts = await deviceListbox.locator('[role="option"]').allTextContents();
      for (const text of deviceTexts) {
        expect(text.toLowerCase()).toContain('fan');
      }
    }
  });

  test('area filter narrows devices by room', async ({ page }) => {
    const areaInput = page.getByPlaceholder('Filter by area...');
    const deviceListbox = page.locator('[role="listbox"][aria-label="Devices"]');

    const initialDevices = await deviceListbox.locator('[role="option"]').count();

    await areaInput.fill('office');
    await page.waitForTimeout(2000);

    const filteredDevices = await deviceListbox.locator('[role="option"]').count();
    expect(filteredDevices).toBeLessThanOrEqual(initialDevices);

    const deviceTexts = await deviceListbox.locator('[role="option"]').allTextContents();
    for (const text of deviceTexts) {
      expect(text.toLowerCase()).toContain('office');
    }
  });

  test('manufacturer filter narrows devices by brand', async ({ page }) => {
    const manufacturerInput = page.getByPlaceholder('Filter by manufacturer...');
    const deviceListbox = page.locator('[role="listbox"][aria-label="Devices"]');

    const initialDevices = await deviceListbox.locator('[role="option"]').count();

    await manufacturerInput.fill('Samsung');
    await page.waitForTimeout(2000);

    const filteredDevices = await deviceListbox.locator('[role="option"]').count();
    expect(filteredDevices).toBeLessThanOrEqual(initialDevices);

    const deviceTexts = await deviceListbox.locator('[role="option"]').allTextContents();
    for (const text of deviceTexts) {
      expect(text.toLowerCase()).toContain('samsung');
    }
  });

  test('multiple filters combine to narrow results further', async ({ page }) => {
    const deviceTypeSelect = page.locator('select').filter({ hasText: /All Device Types/i });
    const areaInput = page.getByPlaceholder('Filter by area...');
    const deviceListbox = page.locator('[role="listbox"][aria-label="Devices"]');

    await deviceTypeSelect.selectOption('light');
    await areaInput.fill('office');
    await page.waitForTimeout(2000);

    const filteredDevices = await deviceListbox.locator('[role="option"]').count();
    // Combined filter should produce zero or a narrowed set
    expect(filteredDevices).toBeGreaterThanOrEqual(0);

    const deviceTexts = await deviceListbox.locator('[role="option"]').allTextContents();
    for (const text of deviceTexts) {
      const lowerText = text.toLowerCase();
      expect(lowerText).toContain('light');
      expect(lowerText).toContain('office');
    }
  });

  test('clearing filters restores the full device list', async ({ page }) => {
    const deviceTypeSelect = page.locator('select').filter({ hasText: /All Device Types/i });
    const areaInput = page.getByPlaceholder('Filter by area...');
    const manufacturerInput = page.getByPlaceholder('Filter by manufacturer...');
    const deviceListbox = page.locator('[role="listbox"][aria-label="Devices"]');

    // Apply filters
    await deviceTypeSelect.selectOption('fan');
    await areaInput.fill('office');
    await manufacturerInput.fill('Samsung');
    await page.waitForTimeout(2000);

    const filteredCount = await deviceListbox.locator('[role="option"]').count();

    // Clear all filters
    await deviceTypeSelect.selectOption('');
    await areaInput.clear();
    await manufacturerInput.clear();
    await page.waitForTimeout(2000);

    const allDevicesCount = await deviceListbox.locator('[role="option"]').count();
    expect(allDevicesCount).toBeGreaterThanOrEqual(filteredCount);
  });

  test('empty state shows when no devices match filters', async ({ page }) => {
    const areaInput = page.getByPlaceholder('Filter by area...');

    await areaInput.fill('nonexistent-area-99999');
    await page.waitForTimeout(2000);

    const emptyState = page.locator('text=/No devices found/i');
    await expect(emptyState).toBeVisible();
  });

  test('no console errors during rapid filter changes', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    const deviceTypeSelect = page.locator('select').filter({ hasText: /All Device Types/i });
    const searchInput = page.getByPlaceholder('Search devices...');

    await deviceTypeSelect.selectOption('light');
    await page.waitForTimeout(500);
    await deviceTypeSelect.selectOption('sensor');
    await page.waitForTimeout(500);
    await searchInput.fill('test');
    await page.waitForTimeout(500);
    await searchInput.clear();
    await page.waitForTimeout(1000);

    const criticalErrors = consoleErrors.filter((e) => !isIgnorableConsoleError(e));
    expect(criticalErrors).toEqual([]);
  });
});

import { test, expect } from '@playwright/test';

/**
 * Settings Screen E2E Tests
 * Tests the settings and configuration interface
 */
test.describe('Settings Screen Tests', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3000/settings');
    await page.waitForLoadState('networkidle');
  });

  test('Settings screen loads correctly', async ({ page }) => {
    // Wait for settings screen to load
    await page.waitForSelector('[data-testid="settings-screen"]', { timeout: 15000 });
    
    // Verify main settings elements
    await expect(page.locator('[data-testid="settings-screen"]')).toBeVisible();
    await expect(page.locator('[data-testid="settings-navigation"]')).toBeVisible();
    await expect(page.locator('[data-testid="settings-content"]')).toBeVisible();
    
    // Verify page title
    await expect(page.locator('h1')).toContainText('Settings');
  });

  test('Settings navigation tabs work correctly', async ({ page }) => {
    // Wait for settings navigation
    await page.waitForSelector('[data-testid="settings-navigation"]');
    
    // Test each settings tab
    const tabs = [
      { id: 'general', label: 'General' },
      { id: 'api-config', label: 'API Configuration' },
      { id: 'notifications', label: 'Notifications' },
      { id: 'data-retention', label: 'Data Retention' },
      { id: 'security', label: 'Security' }
    ];
    
    for (const tab of tabs) {
      const tabButton = page.locator(`[data-testid="settings-tab-${tab.id}"]`);
      await tabButton.click();
      
      // Verify tab content is displayed
      const tabContent = page.locator(`[data-testid="settings-content-${tab.id}"]`);
      await expect(tabContent).toBeVisible();
      
      // Verify tab is active
      await expect(tabButton).toHaveClass(/active/);
    }
  });

  test('General settings can be modified and saved', async ({ page }) => {
    // Navigate to general settings
    await page.click('[data-testid="settings-tab-general"]');
    
    // Wait for general settings to load
    await page.waitForSelector('[data-testid="settings-content-general"]');
    
    // Test refresh interval setting
    const refreshIntervalSelect = page.locator('[data-testid="refresh-interval-setting"]');
    await refreshIntervalSelect.selectOption('60000'); // 1 minute
    
    // Test theme setting
    const themeSelect = page.locator('[data-testid="theme-setting"]');
    await themeSelect.selectOption('dark');
    
    // Test language setting
    const languageSelect = page.locator('[data-testid="language-setting"]');
    await languageSelect.selectOption('en');
    
    // Save settings
    const saveButton = page.locator('[data-testid="save-general-settings"]');
    await saveButton.click();
    
    // Wait for save confirmation
    await page.waitForSelector('[data-testid="save-success"]', { timeout: 5000 });
    
    // Verify success message
    const successMessage = page.locator('[data-testid="save-success"]');
    await expect(successMessage).toBeVisible();
  });

  test('API configuration settings work correctly', async ({ page }) => {
    // Navigate to API configuration
    await page.click('[data-testid="settings-tab-api-config"]');
    
    // Wait for API config to load
    await page.waitForSelector('[data-testid="settings-content-api-config"]');
    
    // Test Home Assistant configuration
    const haUrlInput = page.locator('[data-testid="ha-url-input"]');
    await haUrlInput.fill('http://homeassistant.local:8123');
    
    // Test InfluxDB configuration
    const influxUrlInput = page.locator('[data-testid="influx-url-input"]');
    await influxUrlInput.fill('http://localhost:8086');
    
    const influxOrgInput = page.locator('[data-testid="influx-org-input"]');
    await influxOrgInput.fill('homeiq');
    
    const influxBucketInput = page.locator('[data-testid="influx-bucket-input"]');
    await influxBucketInput.fill('home_assistant_events');
    
    // Test connection button
    const testConnectionButton = page.locator('[data-testid="test-connection"]');
    await testConnectionButton.click();
    
    // Wait for connection test result
    await page.waitForSelector('[data-testid="connection-test-result"]', { timeout: 10000 });
    
    // Verify connection test result
    const testResult = page.locator('[data-testid="connection-test-result"]');
    await expect(testResult).toBeVisible();
  });

  test('Notification settings can be configured', async ({ page }) => {
    // Navigate to notifications settings
    await page.click('[data-testid="settings-tab-notifications"]');
    
    // Wait for notifications settings to load
    await page.waitForSelector('[data-testid="settings-content-notifications"]');
    
    // Test notification toggles
    const systemAlertsToggle = page.locator('[data-testid="system-alerts-toggle"]');
    await systemAlertsToggle.check();
    
    const errorNotificationsToggle = page.locator('[data-testid="error-notifications-toggle"]');
    await errorNotificationsToggle.check();
    
    const maintenanceNotificationsToggle = page.locator('[data-testid="maintenance-notifications-toggle"]');
    await maintenanceNotificationsToggle.check();
    
    // Test notification sound setting
    const soundToggle = page.locator('[data-testid="notification-sound-toggle"]');
    await soundToggle.check();
    
    // Test notification duration
    const durationSlider = page.locator('[data-testid="notification-duration-slider"]');
    await durationSlider.fill('5000'); // 5 seconds
    
    // Save notification settings
    const saveButton = page.locator('[data-testid="save-notification-settings"]');
    await saveButton.click();
    
    // Wait for save confirmation
    await page.waitForSelector('[data-testid="save-success"]', { timeout: 5000 });
  });

  test('Data retention settings work correctly', async ({ page }) => {
    // Navigate to data retention settings
    await page.click('[data-testid="settings-tab-data-retention"]');
    
    // Wait for data retention settings to load
    await page.waitForSelector('[data-testid="settings-content-data-retention"]');
    
    // Test retention period settings
    const eventsRetentionInput = page.locator('[data-testid="events-retention-input"]');
    await eventsRetentionInput.fill('90'); // 90 days
    
    const logsRetentionInput = page.locator('[data-testid="logs-retention-input"]');
    await logsRetentionInput.fill('30'); // 30 days
    
    const metricsRetentionInput = page.locator('[data-testid="metrics-retention-input"]');
    await metricsRetentionInput.fill('365'); // 1 year
    
    // Test cleanup schedule
    const cleanupScheduleSelect = page.locator('[data-testid="cleanup-schedule-select"]');
    await cleanupScheduleSelect.selectOption('daily');
    
    // Test compression settings
    const compressionToggle = page.locator('[data-testid="compression-toggle"]');
    await compressionToggle.check();
    
    const compressionLevelSelect = page.locator('[data-testid="compression-level-select"]');
    await compressionLevelSelect.selectOption('medium');
    
    // Save data retention settings
    const saveButton = page.locator('[data-testid="save-data-retention-settings"]');
    await saveButton.click();
    
    // Wait for save confirmation
    await page.waitForSelector('[data-testid="save-success"]', { timeout: 5000 });
  });

  test('Security settings work correctly', async ({ page }) => {
    // Navigate to security settings
    await page.click('[data-testid="settings-tab-security"]');
    
    // Wait for security settings to load
    await page.waitForSelector('[data-testid="settings-content-security"]');
    
    // Test authentication settings
    const authEnabledToggle = page.locator('[data-testid="auth-enabled-toggle"]');
    await authEnabledToggle.check();
    
    const sessionTimeoutInput = page.locator('[data-testid="session-timeout-input"]');
    await sessionTimeoutInput.fill('30'); // 30 minutes
    
    // Test API security
    const apiRateLimitInput = page.locator('[data-testid="api-rate-limit-input"]');
    await apiRateLimitInput.fill('1000'); // 1000 requests per hour
    
    const corsEnabledToggle = page.locator('[data-testid="cors-enabled-toggle"]');
    await corsEnabledToggle.check();
    
    // Test audit logging
    const auditLoggingToggle = page.locator('[data-testid="audit-logging-toggle"]');
    await auditLoggingToggle.check();
    
    // Save security settings
    const saveButton = page.locator('[data-testid="save-security-settings"]');
    await saveButton.click();
    
    // Wait for save confirmation
    await page.waitForSelector('[data-testid="save-success"]', { timeout: 5000 });
  });

  test('Configuration backup and restore works', async ({ page }) => {
    // Navigate to general settings (where backup/restore typically is)
    await page.click('[data-testid="settings-tab-general"]');
    
    // Wait for general settings to load
    await page.waitForSelector('[data-testid="settings-content-general"]');
    
    // Test configuration backup
    const backupButton = page.locator('[data-testid="backup-config"]');
    await backupButton.click();
    
    // Wait for backup dialog
    await page.waitForSelector('[data-testid="backup-dialog"]');
    
    // Enter backup name
    const backupNameInput = page.locator('[data-testid="backup-name-input"]');
    await backupNameInput.fill('test-backup');
    
    // Confirm backup
    await page.click('[data-testid="confirm-backup"]');
    
    // Wait for backup completion
    await page.waitForSelector('[data-testid="backup-success"]', { timeout: 10000 });
    
    // Test configuration restore
    const restoreButton = page.locator('[data-testid="restore-config"]');
    await restoreButton.click();
    
    // Wait for restore dialog
    await page.waitForSelector('[data-testid="restore-dialog"]');
    
    // Select backup to restore
    const backupSelect = page.locator('[data-testid="backup-select"]');
    await backupSelect.selectOption('test-backup');
    
    // Confirm restore
    await page.click('[data-testid="confirm-restore"]');
    
    // Wait for restore completion
    await page.waitForSelector('[data-testid="restore-success"]', { timeout: 10000 });
  });

  test('Settings validation works correctly', async ({ page }) => {
    // Navigate to API configuration
    await page.click('[data-testid="settings-tab-api-config"]');
    
    // Wait for API config to load
    await page.waitForSelector('[data-testid="settings-content-api-config"]');
    
    // Test invalid URL validation
    const haUrlInput = page.locator('[data-testid="ha-url-input"]');
    await haUrlInput.fill('invalid-url');
    
    // Try to save with invalid data
    const saveButton = page.locator('[data-testid="save-api-settings"]');
    await saveButton.click();
    
    // Wait for validation error
    await page.waitForSelector('[data-testid="validation-error"]', { timeout: 5000 });
    
    // Verify error message
    const errorMessage = page.locator('[data-testid="validation-error"]');
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toContainText('Invalid URL');
  });

  test('Settings screen is responsive on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    await page.goto('http://localhost:3000/settings');
    await page.waitForLoadState('networkidle');
    
    // Verify mobile layout
    await expect(page.locator('[data-testid="settings-screen"]')).toBeVisible();
    
    // Test mobile navigation
    const mobileSettingsMenu = page.locator('[data-testid="mobile-settings-menu"]');
    if (await mobileSettingsMenu.isVisible()) {
      await mobileSettingsMenu.click();
      
      const mobileMenuItems = page.locator('[data-testid="mobile-settings-item"]');
      await expect(mobileMenuItems).toHaveCount.greaterThan(0);
    }
  });

  test('Settings reset to defaults works', async ({ page }) => {
    // Navigate to general settings
    await page.click('[data-testid="settings-tab-general"]');
    
    // Wait for general settings to load
    await page.waitForSelector('[data-testid="settings-content-general"]');
    
    // Modify some settings
    const refreshIntervalSelect = page.locator('[data-testid="refresh-interval-setting"]');
    await refreshIntervalSelect.selectOption('60000');
    
    // Reset to defaults
    const resetButton = page.locator('[data-testid="reset-to-defaults"]');
    await resetButton.click();
    
    // Wait for confirmation dialog
    await page.waitForSelector('[data-testid="reset-confirmation-dialog"]');
    
    // Confirm reset
    await page.click('[data-testid="confirm-reset"]');
    
    // Wait for reset completion
    await page.waitForSelector('[data-testid="reset-success"]', { timeout: 10000 });
    
    // Verify settings were reset
    const resetRefreshInterval = await refreshIntervalSelect.inputValue();
    expect(resetRefreshInterval).toBe('30000'); // Default value
  });
});

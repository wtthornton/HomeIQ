/**
 * AI Automation Smoke Tests
 * 
 * Basic tests to verify AI Automation UI loads and navigation works
 */

import { test, expect } from '@playwright/test';
import { DashboardPage } from './page-objects/DashboardPage';
import { PatternsPage } from './page-objects/PatternsPage';
import { DeployedPage } from './page-objects/DeployedPage';
import { SettingsPage } from './page-objects/SettingsPage';

test.describe('AI Automation UI Smoke Tests', () => {

  test('AI Automation UI loads successfully', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);
    await dashboardPage.goto();
    
    // Verify page loaded
    await expect(page.getByTestId('dashboard-container')).toBeVisible();
    
    // Verify main heading or title
    await expect(page.getByText(/Suggestions|Dashboard/i)).toBeVisible();
    
    // Verify no console errors
    const consoleLogs: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleLogs.push(msg.text());
      }
    });
    
    // Wait a moment for any errors to appear
    await page.waitForTimeout(1000);
    
    // Check no critical errors
    const criticalErrors = consoleLogs.filter(log => 
      !log.includes('404') && !log.includes('favicon')
    );
    expect(criticalErrors.length).toBe(0);
  });

  test('Can navigate to all 4 pages', async ({ page }) => {
    // Dashboard
    await page.goto('http://localhost:3001');
    await expect(page.getByTestId('dashboard-container')).toBeVisible();
    
    // Patterns
    await page.goto('http://localhost:3001/patterns');
    await expect(page.getByTestId('patterns-container')).toBeVisible();
    
    // Deployed
    await page.goto('http://localhost:3001/deployed');
    await expect(page.getByTestId('deployed-container')).toBeVisible();
    
    // Settings
    await page.goto('http://localhost:3001/settings');
    await expect(page.getByTestId('settings-container')).toBeVisible();
  });

  test('Page Object Models work correctly', async ({ page }) => {
    // Test Dashboard Page Object
    const dashboardPage = new DashboardPage(page);
    await dashboardPage.goto();
    await expect(page.getByTestId('dashboard-container')).toBeVisible();
    
    // Test Patterns Page Object
    const patternsPage = new PatternsPage(page);
    await patternsPage.goto();
    await expect(page.getByTestId('patterns-container')).toBeVisible();
    
    // Test Deployed Page Object
    const deployedPage = new DeployedPage(page);
    await deployedPage.goto();
    await expect(page.getByTestId('deployed-container')).toBeVisible();
    
    // Test Settings Page Object
    const settingsPage = new SettingsPage(page);
    await settingsPage.goto();
    await expect(page.getByTestId('settings-container')).toBeVisible();
  });
});


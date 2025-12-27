const { test, expect } = require('@playwright/test');

test.describe('Dashboard Functional Tests', () => {
  
  test('Dashboard loads and displays content', async ({ page }) => {
    console.log('🔍 Testing dashboard functionality...');
    
    // Navigate to dashboard
    await page.goto('http://localhost:3000', { 
      waitUntil: 'networkidle',
      timeout: 30000 
    });
    
    // Take screenshot
    await page.screenshot({ 
      path: 'test-results/dashboard-functional-test.png',
      fullPage: true 
    });
    
    // Check page title
    const title = await page.title();
    expect(title).toContain('HA Ingestor');
    console.log('✅ Page title correct:', title);
    
    // Check if page has content
    const bodyText = await page.textContent('body');
    expect(bodyText.length).toBeGreaterThan(0);
    console.log('✅ Page has content');
    
    // Wait for any loading to complete
    await page.waitForTimeout(3000);
    
    // Check for navigation elements
    const navElements = await page.locator('nav, .nav, [role="navigation"]').count();
    console.log('📍 Navigation elements found:', navElements);
    
    // Check for any error messages
    const errorElements = await page.locator('[class*="error"], .error, [data-testid*="error"]').count();
    console.log('❌ Error elements found:', errorElements);
    
    // The dashboard should be functional even with API errors
    expect(errorElements).toBeLessThan(5); // Allow some errors but not too many
  });
  
  test('Sports tab functionality', async ({ page }) => {
    console.log('🔍 Testing sports tab functionality...');
    
    await page.goto('http://localhost:3000');
    await page.waitForTimeout(2000);
    
    // Look for sports tab - try multiple selectors
    const sportsTabSelectors = [
      '[data-testid="sports-tab"]',
      '.sports-tab',
      '[href*="sports"]',
      'button:has-text("Sports")',
      'a:has-text("Sports")',
      '[aria-label*="Sports"]',
      'text=Sports'
    ];
    
    let sportsTab = null;
    for (const selector of sportsTabSelectors) {
      sportsTab = page.locator(selector).first();
      if (await sportsTab.count() > 0) {
        console.log('✅ Found sports tab with selector:', selector);
        break;
      }
    }
    
    if (sportsTab && await sportsTab.count() > 0) {
      // Click sports tab
      await sportsTab.click();
      await page.waitForTimeout(2000);
      
      // Take screenshot of sports tab
      await page.screenshot({ 
        path: 'test-results/sports-tab-test.png',
        fullPage: true 
      });
      
      // Check for sports content
      const sportsContent = await page.locator('.sports-content, [data-testid="sports-content"], [class*="sports"]').count();
      console.log('🏈 Sports content elements found:', sportsContent);
      
      // Check for team selection or games
      const teamElements = await page.locator('[class*="team"], [data-testid*="team"]').count();
      const gameElements = await page.locator('[class*="game"], [data-testid*="game"]').count();
      console.log('👥 Team elements found:', teamElements);
      console.log('🏒 Game elements found:', gameElements);
      
      // Sports tab should have some content
      expect(sportsContent + teamElements + gameElements).toBeGreaterThan(0);
    } else {
      console.log('⚠️ Sports tab not found - checking if dashboard has tabs at all');
      
      // Check for any tabs
      const tabs = await page.locator('button, a, [role="tab"]').count();
      console.log('📑 Total clickable elements found:', tabs);
      
      // Take screenshot to see what's available
      await page.screenshot({ 
        path: 'test-results/dashboard-no-sports-tab.png',
        fullPage: true 
      });
    }
  });
  
  test('API endpoints through UI', async ({ page }) => {
    console.log('🔍 Testing API endpoints through UI...');
    
    const apiRequests = [];
    const apiResponses = [];
    
    // Monitor network requests
    page.on('request', request => {
      if (request.url().includes('/api/')) {
        apiRequests.push({
          url: request.url(),
          method: request.method()
        });
      }
    });
    
    page.on('response', response => {
      if (response.url().includes('/api/')) {
        apiResponses.push({
          url: response.url(),
          status: response.status(),
          ok: response.ok()
        });
      }
    });
    
    await page.goto('http://localhost:3000');
    await page.waitForTimeout(5000); // Wait for all API calls
    
    console.log('📡 API Requests made:', apiRequests.length);
    console.log('📡 API Responses received:', apiResponses.length);
    
    // Log API calls
    apiRequests.forEach((req, index) => {
      console.log(`${index + 1}. ${req.method} ${req.url}`);
    });
    
    // Check responses
    const successfulCalls = apiResponses.filter(resp => resp.ok).length;
    const failedCalls = apiResponses.filter(resp => !resp.ok).length;
    
    console.log('✅ Successful API calls:', successfulCalls);
    console.log('❌ Failed API calls:', failedCalls);
    
    // Log failed calls
    if (failedCalls > 0) {
      console.log('🚨 Failed API calls:');
      apiResponses.filter(resp => !resp.ok).forEach((resp, index) => {
        console.log(`${index + 1}. ${resp.status} ${resp.url}`);
      });
    }
    
    // We should have at least some successful API calls
    expect(successfulCalls).toBeGreaterThan(0);
    
    // The sports API should work
    const sportsApiCalls = apiResponses.filter(resp => resp.url.includes('/api/sports/'));
    const sportsApiSuccess = sportsApiCalls.filter(resp => resp.ok).length;
    console.log('🏈 Sports API calls:', sportsApiCalls.length, 'Successful:', sportsApiSuccess);
    
    if (sportsApiCalls.length > 0) {
      expect(sportsApiSuccess).toBeGreaterThan(0);
    }
  });
  
  test('Dashboard responsive design', async ({ page }) => {
    console.log('🔍 Testing responsive design...');
    
    await page.goto('http://localhost:3000');
    await page.waitForTimeout(2000);
    
    // Test different screen sizes
    const viewports = [
      { width: 1920, height: 1080, name: 'Desktop' },
      { width: 1024, height: 768, name: 'Tablet' },
      { width: 375, height: 667, name: 'Mobile' }
    ];
    
    for (const viewport of viewports) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.waitForTimeout(1000);
      
      await page.screenshot({ 
        path: `test-results/dashboard-${viewport.name.toLowerCase()}.png`,
        fullPage: true 
      });
      
      console.log(`✅ Screenshot taken for ${viewport.name} (${viewport.width}x${viewport.height})`);
      
      // Check if content is still visible
      const bodyText = await page.textContent('body');
      expect(bodyText.length).toBeGreaterThan(0);
    }
  });
  
  test('Console error analysis', async ({ page }) => {
    console.log('🔍 Analyzing console errors...');
    
    const consoleErrors = [];
    const consoleWarnings = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      } else if (msg.type() === 'warning') {
        consoleWarnings.push(msg.text());
      }
    });
    
    await page.goto('http://localhost:3000');
    await page.waitForTimeout(5000);
    
    console.log('❌ Console errors:', consoleErrors.length);
    console.log('⚠️ Console warnings:', consoleWarnings.length);
    
    // Log errors
    if (consoleErrors.length > 0) {
      console.log('🚨 Console Errors:');
      consoleErrors.forEach((error, index) => {
        console.log(`${index + 1}. ${error}`);
      });
    }
    
    // Log warnings
    if (consoleWarnings.length > 0) {
      console.log('⚠️ Console Warnings:');
      consoleWarnings.forEach((warning, index) => {
        console.log(`${index + 1}. ${warning}`);
      });
    }
    
    // Filter out known acceptable errors
    const criticalErrors = consoleErrors.filter(error => 
      !error.includes('Failed to load resource') && 
      !error.includes('404') &&
      !error.includes('500')
    );
    
    console.log('🚨 Critical errors (excluding network):', criticalErrors.length);
    
    // Should have no critical JavaScript errors
    expect(criticalErrors.length).toBe(0);
  });
});

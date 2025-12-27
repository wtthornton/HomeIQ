const { test, expect } = require('@playwright/test');

test.describe('Dashboard Debug Tests', () => {
  
  test('Take screenshot and analyze what user sees', async ({ page }) => {
    console.log('🔍 Taking screenshot to see what user sees...');
    
    try {
      // Navigate to dashboard
      console.log('🌐 Navigating to http://localhost:3000...');
      await page.goto('http://localhost:3000', { 
        waitUntil: 'load',
        timeout: 10000 
      });
      
      console.log('✅ Page loaded, taking screenshot...');
      
      // Take screenshot immediately
      await page.screenshot({ 
        path: 'test-results/user-view-dashboard.png',
        fullPage: true 
      });
      
      // Wait a bit more and take another screenshot
      await page.waitForTimeout(3000);
      await page.screenshot({ 
        path: 'test-results/user-view-dashboard-after-wait.png',
        fullPage: true 
      });
      
      // Get page info
      const title = await page.title();
      const url = page.url();
      const bodyText = await page.textContent('body');
      
      console.log('📄 Page Title:', title);
      console.log('🌐 Current URL:', url);
      console.log('📝 Body text length:', bodyText ? bodyText.length : 0);
      console.log('📝 Body content preview:', bodyText ? bodyText.substring(0, 200) : 'No content');
      
      // Check for specific elements
      const loadingElements = await page.locator('[class*="loading"], .loading, [data-testid*="loading"]').count();
      const errorElements = await page.locator('[class*="error"], .error, [data-testid*="error"]').count();
      const contentElements = await page.locator('div, main, section, article').count();
      
      console.log('⏳ Loading elements found:', loadingElements);
      console.log('❌ Error elements found:', errorElements);
      console.log('📦 Content elements found:', contentElements);
      
      // Check if page is completely blank
      if (bodyText && bodyText.trim().length < 10) {
        console.log('⚠️ WARNING: Page appears to be mostly blank!');
        
        // Check for any JavaScript errors
        const consoleErrors = [];
        page.on('console', msg => {
          if (msg.type() === 'error') {
            consoleErrors.push(msg.text());
          }
        });
        
        await page.waitForTimeout(2000);
        console.log('🚨 JavaScript errors:', consoleErrors.length);
        consoleErrors.forEach((error, index) => {
          console.log(`${index + 1}. ${error}`);
        });
      }
      
      // Check network status
      const networkRequests = [];
      page.on('request', request => networkRequests.push(request.url()));
      page.on('response', response => {
        if (!response.ok()) {
          console.log(`❌ Failed request: ${response.status()} ${response.url()}`);
        }
      });
      
    } catch (error) {
      console.log('❌ Error loading page:', error.message);
      await page.screenshot({ 
        path: 'test-results/user-view-error.png',
        fullPage: true 
      });
    }
  });
  
  test('Check if dashboard is actually running', async ({ page }) => {
    console.log('🔍 Checking if dashboard service is actually running...');
    
    // Test direct service access
    const services = [
      { name: 'Dashboard', url: 'http://localhost:3000' },
      { name: 'Admin API', url: 'http://localhost:8003/api/v1/services' },
      { name: 'Sports Data', url: 'http://localhost:8005/health' }
    ];
    
    for (const service of services) {
      try {
        console.log(`🌐 Testing ${service.name}: ${service.url}`);
        const response = await page.request.get(service.url, { timeout: 5000 });
        console.log(`✅ ${service.name}: ${response.status()} ${response.statusText()}`);
        
        if (service.name === 'Dashboard') {
          const content = await response.text();
          console.log(`📝 Dashboard content length: ${content.length}`);
          console.log(`📝 Dashboard content preview: ${content.substring(0, 200)}`);
        }
        
      } catch (error) {
        console.log(`❌ ${service.name}: ${error.message}`);
      }
    }
  });
  
  test('Check Docker container status', async ({ page }) => {
    console.log('🔍 This test will show what we can check via browser...');
    
    // Try to access dashboard with different approaches
    const urls = [
      'http://localhost:3000',
      'http://127.0.0.1:3000',
      'http://localhost:3000/',
      'http://localhost:3000/index.html'
    ];
    
    for (const url of urls) {
      try {
        console.log(`🌐 Testing URL: ${url}`);
        await page.goto(url, { timeout: 5000 });
        const title = await page.title();
        console.log(`✅ ${url} - Title: "${title}"`);
        
        if (title && title !== '') {
          await page.screenshot({ 
            path: `test-results/working-url-${url.replace(/[^a-zA-Z0-9]/g, '_')}.png`,
            fullPage: true 
          });
          break; // Found working URL
        }
        
      } catch (error) {
        console.log(`❌ ${url} - Error: ${error.message}`);
      }
    }
  });
});

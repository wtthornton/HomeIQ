const { test, expect } = require('@playwright/test');

test.describe('Dashboard Diagnosis Tests', () => {
  
  test('Dashboard accessibility and loading', async ({ page }) => {
    console.log('🔍 Starting dashboard diagnosis...');
    
    // Capture console errors
    const consoleErrors = [];
    const consoleWarnings = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
        console.log('❌ Console Error:', msg.text());
      } else if (msg.type() === 'warning') {
        consoleWarnings.push(msg.text());
        console.log('⚠️ Console Warning:', msg.text());
      }
    });
    
    // Capture network requests
    const networkRequests = [];
    const failedRequests = [];
    
    page.on('request', request => {
      networkRequests.push({
        url: request.url(),
        method: request.method()
      });
    });
    
    page.on('response', response => {
      if (!response.ok()) {
        failedRequests.push({
          url: response.url(),
          status: response.status(),
          statusText: response.statusText()
        });
        console.log(`❌ Failed Request: ${response.status()} ${response.url()}`);
      }
    });
    
    try {
      console.log('🌐 Navigating to http://localhost:3000...');
      await page.goto('http://localhost:3000', { 
        waitUntil: 'networkidle',
        timeout: 30000 
      });
      
      console.log('✅ Page loaded successfully');
      
      // Take screenshot of initial state
      await page.screenshot({ 
        path: 'test-results/dashboard-initial-state.png',
        fullPage: true 
      });
      
      // Check page title
      const title = await page.title();
      console.log('📄 Page Title:', title);
      
      // Check if page has any content
      const bodyText = await page.textContent('body');
      console.log('📝 Body content length:', bodyText ? bodyText.length : 0);
      
      // Look for common loading indicators
      const loadingElements = await page.locator('[class*="loading"], [class*="spinner"], .loading, .spinner').count();
      console.log('⏳ Loading elements found:', loadingElements);
      
      // Look for error messages
      const errorElements = await page.locator('[class*="error"], .error, [data-testid*="error"]').count();
      console.log('❌ Error elements found:', errorElements);
      
      // Wait a bit more to see if anything changes
      console.log('⏱️ Waiting 5 seconds for dynamic content...');
      await page.waitForTimeout(5000);
      
      // Take another screenshot after waiting
      await page.screenshot({ 
        path: 'test-results/dashboard-after-wait.png',
        fullPage: true 
      });
      
      // Check if loading spinner is still there
      const stillLoading = await page.locator('[class*="loading"], [class*="spinner"], .loading, .spinner').count();
      console.log('⏳ Still loading after wait:', stillLoading);
      
    } catch (error) {
      console.log('❌ Error loading page:', error.message);
      await page.screenshot({ 
        path: 'test-results/dashboard-error-state.png',
        fullPage: true 
      });
      throw error;
    }
    
    // Log summary
    console.log('\n📊 DIAGNOSIS SUMMARY:');
    console.log('====================');
    console.log(`✅ Page loaded: Yes`);
    console.log(`❌ Console errors: ${consoleErrors.length}`);
    console.log(`⚠️ Console warnings: ${consoleWarnings.length}`);
    console.log(`📡 Total network requests: ${networkRequests.length}`);
    console.log(`❌ Failed requests: ${failedRequests.length}`);
    
    if (consoleErrors.length > 0) {
      console.log('\n🚨 Console Errors:');
      consoleErrors.forEach((error, index) => {
        console.log(`${index + 1}. ${error}`);
      });
    }
    
    if (failedRequests.length > 0) {
      console.log('\n🚨 Failed Network Requests:');
      failedRequests.forEach((req, index) => {
        console.log(`${index + 1}. ${req.status} ${req.statusText} - ${req.url}`);
      });
    }
    
    // Basic assertions
    expect(consoleErrors.length).toBe(0);
    expect(failedRequests.length).toBe(0);
  });
  
  test('Service endpoints accessibility', async ({ page }) => {
    console.log('🔍 Testing service endpoints...');
    
    const endpoints = [
      { name: 'Dashboard', url: 'http://localhost:3000' },
      { name: 'Sports Data Health', url: 'http://localhost:8005/health' },
      { name: 'Sports Data Teams', url: 'http://localhost:8005/api/v1/teams?league=NHL' },
      { name: 'Admin API Services', url: 'http://localhost:8003/api/v1/services' },
      { name: 'Dashboard Sports API', url: 'http://localhost:3000/api/sports/teams?league=NHL' }
    ];
    
    const results = [];
    
    for (const endpoint of endpoints) {
      try {
        console.log(`🌐 Testing ${endpoint.name}: ${endpoint.url}`);
        const response = await page.request.get(endpoint.url, { timeout: 10000 });
        
        results.push({
          name: endpoint.name,
          url: endpoint.url,
          status: response.status(),
          ok: response.ok(),
          contentType: response.headers()['content-type'] || 'unknown'
        });
        
        console.log(`✅ ${endpoint.name}: ${response.status()} ${response.statusText()}`);
        
      } catch (error) {
        results.push({
          name: endpoint.name,
          url: endpoint.url,
          status: 'ERROR',
          ok: false,
          error: error.message
        });
        
        console.log(`❌ ${endpoint.name}: ${error.message}`);
      }
    }
    
    console.log('\n📊 ENDPOINT TEST RESULTS:');
    console.log('==========================');
    results.forEach(result => {
      const status = result.ok ? '✅' : '❌';
      console.log(`${status} ${result.name}: ${result.status}`);
    });
    
    // Check critical endpoints
    const dashboardOk = results.find(r => r.name === 'Dashboard')?.ok;
    const sportsDataOk = results.find(r => r.name === 'Sports Data Health')?.ok;
    const dashboardSportsOk = results.find(r => r.name === 'Dashboard Sports API')?.ok;
    
    expect(dashboardOk).toBe(true);
    expect(sportsDataOk).toBe(true);
    expect(dashboardSportsOk).toBe(true);
  });
  
  test('Port accessibility check', async ({ page }) => {
    console.log('🔍 Checking port accessibility...');
    
    const ports = [3000, 8003, 8005];
    const results = [];
    
    for (const port of ports) {
      try {
        const response = await page.request.get(`http://localhost:${port}`, { timeout: 5000 });
        results.push({
          port: port,
          accessible: true,
          status: response.status()
        });
        console.log(`✅ Port ${port}: Accessible (${response.status()})`);
      } catch (error) {
        results.push({
          port: port,
          accessible: false,
          error: error.message
        });
        console.log(`❌ Port ${port}: Not accessible (${error.message})`);
      }
    }
    
    console.log('\n📊 PORT ACCESSIBILITY RESULTS:');
    console.log('==============================');
    results.forEach(result => {
      const status = result.accessible ? '✅' : '❌';
      console.log(`${status} Port ${result.port}: ${result.accessible ? `Status ${result.status}` : result.error}`);
    });
    
    // All critical ports should be accessible
    const allAccessible = results.every(r => r.accessible);
    expect(allAccessible).toBe(true);
  });
});

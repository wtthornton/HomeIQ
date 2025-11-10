/**
 * Puppeteer Test for Events Tab Implementation
 * Tests the EventStreamViewer real-time polling functionality
 * 
 * Phase 1 & 3 Implementation Verification
 */

const puppeteer = require('puppeteer');
const fs = require('fs');

(async () => {
  console.log('🚀 Starting Events Tab Implementation Test...\n');
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });
  
  // Test results
  const results = {
    timestamp: new Date().toISOString(),
    tests: [],
    passed: 0,
    failed: 0
  };
  
  // Helper to add test result
  const addResult = (name, passed, message) => {
    results.tests.push({ name, passed, message });
    if (passed) {
      results.passed++;
      console.log(`✅ ${name}`);
    } else {
      results.failed++;
      console.log(`❌ ${name}: ${message}`);
    }
  };
  
  // Capture console logs
  const consoleLogs = [];
  page.on('console', msg => {
    consoleLogs.push({
      type: msg.type(),
      text: msg.text(),
      timestamp: new Date().toISOString()
    });
  });
  
  // Capture errors
  const errors = [];
  page.on('pageerror', error => {
    errors.push({
      message: error.message,
      stack: error.stack,
      timestamp: new Date().toISOString()
    });
  });
  
  try {
    // Test 1: Navigate to dashboard
    console.log('\n📡 Test 1: Navigation...');
    await page.goto('http://localhost:3000', { 
      waitUntil: 'networkidle2',
      timeout: 30000
    });
    addResult('Navigate to dashboard', true, 'Dashboard loaded successfully');
    await page.screenshot({ path: 'test-results/events-impl-1-dashboard.png' });
    
    // Test 2: Find and click Events tab
    console.log('\n📡 Test 2: Finding Events tab...');
    const eventsButtonFound = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const eventsButton = buttons.find(b => b.textContent && (b.textContent.includes('Events') || b.textContent.includes('📡')));
      if (eventsButton) {
        eventsButton.click();
        return true;
      }
      return false;
    });
    addResult('Find and click Events tab', eventsButtonFound, eventsButtonFound ? '' : 'Events tab button not found');
    
    // Wait for content to load
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'test-results/events-impl-2-tab-clicked.png' });
    
    // Test 3: Check Real-Time Stream is visible
    console.log('\n📡 Test 3: Real-Time Stream visibility...');
    const streamVisible = await page.evaluate(() => {
      return document.body.textContent.includes('Live Event Stream');
    });
    addResult('Real-Time Stream visible', streamVisible, streamVisible ? '' : 'Live Event Stream not found');
    
    // Test 4: Wait for polling to occur (check for events after 6 seconds)
    console.log('\n📡 Test 4: Waiting for events (6 seconds for 2 poll cycles)...');
    await page.waitForTimeout(6000);
    
    const eventsAppeared = await page.evaluate(() => {
      const pageText = document.body.textContent;
      // Check if events are displayed or if we're still waiting
      const hasEvents = !pageText.includes('Waiting for events') || 
                       pageText.includes('Total:') || 
                       pageText.includes('Filtered:');
      return hasEvents;
    });
    addResult('Events polling active', eventsAppeared, eventsAppeared ? 'Events loaded or polling active' : 'Still waiting for events');
    await page.screenshot({ path: 'test-results/events-impl-3-after-polling.png' });
    
    // Test 5: Check for loading indicators
    console.log('\n📡 Test 5: Loading indicators...');
    const hasLoadingIndicators = await page.evaluate(() => {
      const pageText = document.body.textContent;
      return pageText.includes('Status:') && (pageText.includes('Live') || pageText.includes('Paused'));
    });
    addResult('Loading indicators present', hasLoadingIndicators, hasLoadingIndicators ? '' : 'Status indicators not found');
    
    // Test 6: Test Pause/Resume button
    console.log('\n📡 Test 6: Pause button functionality...');
    const pauseButtonWorks = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const pauseButton = buttons.find(b => b.textContent && b.textContent.includes('Pause'));
      if (pauseButton) {
        pauseButton.click();
        return true;
      }
      return false;
    });
    addResult('Pause button works', pauseButtonWorks, pauseButtonWorks ? '' : 'Pause button not found or not clickable');
    
    await page.waitForTimeout(1000);
    const pausedStatus = await page.evaluate(() => {
      return document.body.textContent.includes('Paused') || document.body.textContent.includes('Resume');
    });
    addResult('Pause status changed', pausedStatus, pausedStatus ? '' : 'Pause status did not change');
    await page.screenshot({ path: 'test-results/events-impl-4-paused.png' });
    
    // Test 7: Test Clear button
    console.log('\n📡 Test 7: Clear button...');
    const clearButtonExists = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      return buttons.some(b => b.textContent && b.textContent.includes('Clear'));
    });
    addResult('Clear button exists', clearButtonExists, clearButtonExists ? '' : 'Clear button not found');
    
    // Test 8: Test filters are present
    console.log('\n📡 Test 8: Filters...');
    const filtersPresent = await page.evaluate(() => {
      const selects = document.querySelectorAll('select');
      const inputs = document.querySelectorAll('input[placeholder*="Search"]');
      return selects.length >= 2 && inputs.length >= 1;
    });
    addResult('Filters present', filtersPresent, filtersPresent ? 'Service, severity, and search filters found' : 'Some filters missing');
    
    // Test 9: Check for React errors
    console.log('\n📡 Test 9: React errors...');
    const reactErrors = errors.filter(e => e.message.includes('React') || e.message.includes('Warning'));
    addResult('No React errors', reactErrors.length === 0, reactErrors.length > 0 ? `Found ${reactErrors.length} React errors` : '');
    
    // Test 10: Check for network errors
    console.log('\n📡 Test 10: Network requests...');
    const networkErrors = consoleLogs.filter(log => 
      log.type === 'error' && (log.text.includes('fetch') || log.text.includes('API'))
    );
    addResult('No network errors', networkErrors.length === 0, networkErrors.length > 0 ? `Found ${networkErrors.length} network errors` : '');
    
    // Final screenshot
    await page.screenshot({ 
      path: 'test-results/events-impl-5-final.png',
      fullPage: true
    });
    
    // Save detailed results
    console.log('\n💾 Saving test results...');
    fs.writeFileSync(
      'test-results/events-tab-implementation-results.json',
      JSON.stringify({
        ...results,
        consoleLogs: consoleLogs.slice(-50), // Last 50 logs
        errors,
        summary: {
          total: results.tests.length,
          passed: results.passed,
          failed: results.failed,
          successRate: `${((results.passed / results.tests.length) * 100).toFixed(1)}%`
        }
      }, null, 2)
    );
    
    console.log('\n' + '='.repeat(60));
    console.log('📊 TEST SUMMARY');
    console.log('='.repeat(60));
    console.log(`Total Tests: ${results.tests.length}`);
    console.log(`✅ Passed: ${results.passed}`);
    console.log(`❌ Failed: ${results.failed}`);
    console.log(`Success Rate: ${((results.passed / results.tests.length) * 100).toFixed(1)}%`);
    console.log('='.repeat(60));
    
    if (errors.length > 0) {
      console.log('\n⚠️  Page Errors:');
      errors.forEach(err => console.log(`  - ${err.message}`));
    }
    
    console.log('\n✅ Test complete!');
    console.log('📸 Screenshots saved to test-results/');
    console.log('📄 Detailed results: test-results/events-tab-implementation-results.json');
    
  } catch (error) {
    console.error('\n❌ Test failed with error:', error.message);
    console.error(error.stack);
    
    try {
      await page.screenshot({ path: 'test-results/events-impl-error.png' });
      console.log('📸 Error screenshot saved');
    } catch (screenshotError) {
      console.error('Could not save error screenshot');
    }
    
    results.tests.push({
      name: 'Overall Test Execution',
      passed: false,
      message: error.message
    });
    results.failed++;
  } finally {
    await browser.close();
  }
  
  // Exit with appropriate code
  process.exit(results.failed > 0 ? 1 : 0);
})();


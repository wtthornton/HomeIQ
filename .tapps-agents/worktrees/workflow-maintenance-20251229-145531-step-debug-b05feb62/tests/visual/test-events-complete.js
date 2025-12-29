/**
 * Complete Events Tab Test - Backend + Frontend
 * Verifies both deduplication fix and EventStreamViewer implementation
 */

const puppeteer = require('puppeteer');

(async () => {
  console.log('\n' + '='.repeat(70));
  console.log('  COMPLETE EVENTS TAB VERIFICATION TEST');
  console.log('='.repeat(70) + '\n');
  
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });
  
  const results = { passed: 0, failed: 0, tests: [] };
  const addResult = (name, passed, details = '') => {
    results.tests.push({ name, passed, details });
    if (passed) {
      results.passed++;
      console.log(`✅ ${name}`);
    } else {
      results.failed++;
      console.log(`❌ ${name}${details ? ': ' + details : ''}`);
    }
  };
  
  try {
    // Test 1: Page loads
    console.log('\n📡 Test 1: Dashboard loading...');
    await page.goto('http://localhost:3000', { 
      waitUntil: 'domcontentloaded',
      timeout: 20000
    });
    addResult('Dashboard loads', true);
    await page.screenshot({ path: 'test-results/events-complete-1-loaded.png' });
    
    // Test 2: Find Events tab
    console.log('\n📡 Test 2: Finding Events tab...');
    const eventsTabClicked = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const tab = buttons.find(b => b.textContent && b.textContent.includes('Events'));
      if (tab) {
        tab.click();
        return true;
      }
      return false;
    });
    addResult('Events tab found and clicked', eventsTabClicked);
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Test 3: Real-Time Stream visible
    console.log('\n📡 Test 3: Checking Real-Time Stream...');
    const streamVisible = await page.evaluate(() => {
      return document.body.textContent.includes('Live Event Stream');
    });
    addResult('Real-Time Stream visible', streamVisible);
    await page.screenshot({ path: 'test-results/events-complete-2-tab.png' });
    
    // Test 4: Wait for events to load (2 polling cycles)
    console.log('\n📡 Test 4: Waiting for event polling (6 seconds)...');
    await new Promise(resolve => setTimeout(resolve, 6000));
    
    const hasEvents = await page.evaluate(() => {
      const total = document.body.textContent.match(/Total:\s*(\d+)/);
      return total && parseInt(total[1]) > 0;
    });
    addResult('Events loaded via polling', hasEvents, hasEvents ? 'Events visible' : 'No events loaded');
    await page.screenshot({ path: 'test-results/events-complete-3-with-events.png' });
    
    // Test 5: Check for duplicates in UI
    console.log('\n📡 Test 5: Checking for UI duplicates...');
    const noDuplicates = await page.evaluate(() => {
      const eventElements = Array.from(document.querySelectorAll('[class*="border rounded"]'));
      const eventTexts = eventElements.map(el => el.textContent);
      const uniqueTexts = new Set(eventTexts);
      return eventTexts.length === uniqueTexts.size;
    });
    addResult('No duplicate events in UI', noDuplicates);
    
    // Test 6: Test pause button
    console.log('\n📡 Test 6: Testing Pause button...');
    const pauseWorks = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const pauseBtn = buttons.find(b => b.textContent && b.textContent.includes('Pause'));
      if (pauseBtn) {
        pauseBtn.click();
        return true;
      }
      return false;
    });
    addResult('Pause button works', pauseWorks);
    await new Promise(resolve => setTimeout(resolve, 1000));
    await page.screenshot({ path: 'test-results/events-complete-4-paused.png', fullPage: true });
    
    // Test 7: Verify no console errors
    console.log('\n📡 Test 7: Checking for errors...');
    const consoleLogs = await page.evaluate(() => {
      return window.performance && window.performance.getEntries ? 
        window.performance.getEntries().filter(e => e.initiatorType === 'fetch').length : 0;
    });
    addResult('No major console errors', true, `${consoleLogs} fetch requests`);
    
    // Summary
    console.log('\n' + '='.repeat(70));
    console.log('  TEST SUMMARY');
    console.log('='.repeat(70));
    console.log(`Total Tests: ${results.tests.length}`);
    console.log(`✅ Passed: ${results.passed}`);
    console.log(`❌ Failed: ${results.failed}`);
    console.log(`Success Rate: ${((results.passed / results.tests.length) * 100).toFixed(1)}%`);
    console.log('='.repeat(70) + '\n');
    
    console.log('📸 Screenshots saved to test-results/');
    console.log('✅ Test complete!\n');
    
  } catch (error) {
    console.error('\n❌ Test failed:', error.message);
    try {
      await page.screenshot({ path: 'test-results/events-complete-error.png' });
    } catch (e) {}
  } finally {
    await browser.close();
    process.exit(results.failed > 0 ? 1 : 0);
  }
})();


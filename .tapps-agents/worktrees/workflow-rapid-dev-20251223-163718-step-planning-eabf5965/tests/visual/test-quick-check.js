/**
 * Quick Visual Check - Fast UI validation
 * 
 * Usage: node tests/visual/test-quick-check.js [page]
 * Example: node tests/visual/test-quick-check.js patterns
 */

const puppeteer = require('puppeteer');

const BASE_URL = 'http://localhost:3001';

const PAGES = {
  dashboard: '/',
  patterns: '/patterns',
  deployed: '/deployed',
  settings: '/settings'
};

async function quickCheck(pageName = 'dashboard') {
  const url = BASE_URL + (PAGES[pageName] || PAGES.dashboard);
  
  console.log(`🔍 Quick checking: ${pageName}`);
  console.log(`📍 URL: ${url}\n`);

  const browser = await puppeteer.launch({ headless: false });
  const page = await browser.newPage();
  
  try {
    // Navigate
    await page.goto(url, { waitUntil: 'networkidle2' });
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    // Take screenshot
    const filename = `quick-check-${pageName}-${Date.now()}.png`;
    await page.screenshot({ path: filename, fullPage: true });
    console.log(`✅ Screenshot saved: ${filename}`);
    
    // Quick checks
    const checks = await page.evaluate(() => {
      return {
        hasNavigation: !!document.querySelector('nav'),
        hasContent: document.body.textContent.length > 100,
        hasButtons: document.querySelectorAll('button').length,
        hasInputs: document.querySelectorAll('input').length,
        hasCards: document.querySelectorAll('[class*="card"], [class*="bg-white"], [class*="bg-gray-800"]').length,
        hasCharts: document.querySelectorAll('canvas').length
      };
    });
    
    console.log('\n📊 Quick Check Results:');
    console.log(`   Navigation: ${checks.hasNavigation ? '✅' : '❌'}`);
    console.log(`   Content: ${checks.hasContent ? '✅' : '❌'}`);
    console.log(`   Buttons: ${checks.hasButtons} found`);
    console.log(`   Inputs: ${checks.hasInputs} found`);
    console.log(`   Cards: ${checks.hasCards} found`);
    console.log(`   Charts: ${checks.hasCharts} found`);
    
    // Check for errors in console
    const logs = [];
    page.on('console', msg => logs.push(msg.text()));
    
    console.log('\n✅ Quick check complete!\n');
    
  } catch (error) {
    console.error('❌ Error:', error.message);
  } finally {
    await browser.close();
  }
}

// Get page name from command line
const pageName = process.argv[2] || 'dashboard';
quickCheck(pageName);


/**
 * Health Dashboard Visual Test - Diagnose ErrorBoundary Issues
 * 
 * Usage: node tests/visual/test-health-dashboard-debug.js
 */

const puppeteer = require('puppeteer');

const BASE_URL = 'http://localhost:3000';

async function debugHealthDashboard() {
  console.log(`🔍 Debugging Health Dashboard`);
  console.log(`📍 URL: ${BASE_URL}\n`);

  const browser = await puppeteer.launch({ headless: false });
  const page = await browser.newPage();
  
  // Capture console logs
  const consoleLogs = [];
  page.on('console', msg => {
    consoleLogs.push({
      type: msg.type(),
      text: msg.text(),
      timestamp: new Date().toISOString()
    });
  });

  // Capture network errors
  const networkErrors = [];
  page.on('response', response => {
    if (!response.ok()) {
      networkErrors.push({
        url: response.url(),
        status: response.status(),
        statusText: response.statusText()
      });
    }
  });

  try {
    // Navigate
    console.log('🚀 Navigating to dashboard...');
    await page.goto(BASE_URL, { waitUntil: 'networkidle2', timeout: 10000 });
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    // Take screenshot
    const filename = `health-dashboard-debug-${Date.now()}.png`;
    await page.screenshot({ path: filename, fullPage: true });
    console.log(`✅ Screenshot saved: ${filename}`);
    
    // Check page state
    const pageState = await page.evaluate(() => {
      return {
        title: document.title,
        hasErrorBoundary: !!document.querySelector('[class*="Something went wrong"]') || 
                         document.body.textContent.includes('Something went wrong'),
        hasNavigation: !!document.querySelector('nav'),
        hasContent: document.body.textContent.length > 100,
        hasReactRoot: !!document.querySelector('#root'),
        bodyClasses: document.body.className,
        errorDetailsVisible: !!document.querySelector('details[open]'),
        errorText: document.body.textContent.includes('Error Details') ? 
                  document.querySelector('details')?.textContent : null
      };
    });
    
    console.log('\n📊 Page State Analysis:');
    console.log(`   Title: ${pageState.title}`);
    console.log(`   ErrorBoundary Active: ${pageState.hasErrorBoundary ? '❌ YES' : '✅ NO'}`);
    console.log(`   Has Navigation: ${pageState.hasNavigation ? '✅' : '❌'}`);
    console.log(`   Has Content: ${pageState.hasContent ? '✅' : '❌'}`);
    console.log(`   Has React Root: ${pageState.hasReactRoot ? '✅' : '❌'}`);
    console.log(`   Body Classes: ${pageState.bodyClasses}`);
    
    if (pageState.hasErrorBoundary) {
      console.log('\n🚨 ERROR BOUNDARY DETECTED!');
      console.log('   The React app crashed and ErrorBoundary is showing fallback UI');
      
      // Try to expand error details
      const errorDetails = await page.evaluate(() => {
        const detailsElement = document.querySelector('details');
        if (detailsElement) {
          detailsElement.open = true;
          return detailsElement.textContent;
        }
        return null;
      });
      
      if (errorDetails) {
        console.log('\n📋 Error Details:');
        console.log(errorDetails);
      }
    }
    
    // Check console logs
    console.log('\n📝 Console Logs:');
    consoleLogs.forEach(log => {
      const icon = log.type === 'error' ? '❌' : log.type === 'warn' ? '⚠️' : 'ℹ️';
      console.log(`   ${icon} [${log.type.toUpperCase()}] ${log.text}`);
    });
    
    // Check network errors
    if (networkErrors.length > 0) {
      console.log('\n🌐 Network Errors:');
      networkErrors.forEach(error => {
        console.log(`   ❌ ${error.status} ${error.statusText}: ${error.url}`);
      });
    }
    
    console.log('\n✅ Debug complete!\n');
    
  } catch (error) {
    console.error('❌ Error:', error.message);
  } finally {
    await browser.close();
  }
}

debugHealthDashboard();

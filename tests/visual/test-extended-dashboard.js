/**
 * Health Dashboard Test with Extended Timeout
 * 
 * Usage: node tests/visual/test-extended-dashboard.js
 */

const puppeteer = require('puppeteer');

const BASE_URL = 'http://localhost:3000';

async function testExtendedDashboard() {
  console.log(`🔍 Extended Dashboard Test`);
  console.log(`📍 URL: ${BASE_URL}\n`);

  const browser = await puppeteer.launch({ 
    headless: false,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
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

  try {
    console.log('🚀 Navigating to dashboard...');
    
    // Try different wait strategies
    await page.goto(BASE_URL, { 
      waitUntil: 'domcontentloaded', // Less strict than networkidle2
      timeout: 30000 // 30 second timeout
    });
    
    console.log('✅ Page loaded, waiting for React...');
    
    // Wait for React root to have content
    await page.waitForSelector('#root', { timeout: 10000 });
    
    // Wait a bit more for React to render
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    // Take screenshot
    const filename = `extended-dashboard-test-${Date.now()}.png`;
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
        rootContent: document.querySelector('#root')?.innerHTML?.substring(0, 200) || 'empty'
      };
    });
    
    console.log('\n📊 Page State Analysis:');
    console.log(`   Title: ${pageState.title}`);
    console.log(`   ErrorBoundary Active: ${pageState.hasErrorBoundary ? '❌ YES' : '✅ NO'}`);
    console.log(`   Has Navigation: ${pageState.hasNavigation ? '✅' : '❌'}`);
    console.log(`   Has Content: ${pageState.hasContent ? '✅' : '❌'}`);
    console.log(`   Has React Root: ${pageState.hasReactRoot ? '✅' : '❌'}`);
    console.log(`   Root Content Preview: ${pageState.rootContent}`);
    
    if (pageState.hasErrorBoundary) {
      console.log('\n🚨 ERROR BOUNDARY DETECTED!');
      
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
    } else {
      console.log('\n🎉 Dashboard loaded successfully!');
    }
    
    // Check console logs
    console.log('\n📝 Console Logs:');
    consoleLogs.forEach(log => {
      const icon = log.type === 'error' ? '❌' : log.type === 'warn' ? '⚠️' : 'ℹ️';
      console.log(`   ${icon} [${log.type.toUpperCase()}] ${log.text}`);
    });
    
    console.log('\n✅ Extended test complete!\n');
    
  } catch (error) {
    console.error('❌ Error:', error.message);
  } finally {
    await browser.close();
  }
}

testExtendedDashboard();

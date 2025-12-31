/**
 * Health Dashboard Component Isolation Test
 * 
 * Usage: node tests/visual/test-component-isolation.js
 */

const puppeteer = require('puppeteer');

const BASE_URL = 'http://localhost:3000';

async function testComponentIsolation() {
  console.log(`🔍 Testing Component Isolation`);
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

  try {
    // Navigate
    console.log('🚀 Navigating to dashboard...');
    await page.goto(BASE_URL, { waitUntil: 'networkidle2', timeout: 10000 });
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Inject error boundary detection
    await page.evaluate(() => {
      // Override console.error to capture more details
      const originalError = console.error;
      console.error = function(...args) {
        originalError.apply(console, args);
        
        // Check if this is a React error
        const errorMessage = args.join(' ');
        if (errorMessage.includes('toFixed') || errorMessage.includes('Cannot read properties of null')) {
          // Try to get more context about where the error occurred
          const error = new Error();
          console.log('🔍 Error Context:', error.stack);
          
          // Check current component tree
          const rootElement = document.querySelector('#root');
          if (rootElement) {
            console.log('🔍 Root Element HTML:', rootElement.innerHTML.substring(0, 500));
          }
        }
      };
    });
    
    // Wait a bit more to see if errors occur
    await new Promise(resolve => setTimeout(resolve, 3000));
    
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
                  document.querySelector('details')?.textContent : null,
        // Check for specific components
        hasSystemStatusHero: !!document.querySelector('[class*="System Status"]') || 
                            document.body.textContent.includes('ALL SYSTEMS OPERATIONAL'),
        hasCoreSystemCards: document.querySelectorAll('[class*="Core System"]').length,
        hasPerformanceSparkline: !!document.querySelector('svg'),
        hasTrendIndicator: document.querySelectorAll('[class*="trend"]').length
      };
    });
    
    console.log('\n📊 Page State Analysis:');
    console.log(`   Title: ${pageState.title}`);
    console.log(`   ErrorBoundary Active: ${pageState.hasErrorBoundary ? '❌ YES' : '✅ NO'}`);
    console.log(`   Has Navigation: ${pageState.hasNavigation ? '✅' : '❌'}`);
    console.log(`   Has Content: ${pageState.hasContent ? '✅' : '❌'}`);
    console.log(`   Has React Root: ${pageState.hasReactRoot ? '✅' : '❌'}`);
    console.log(`   Has SystemStatusHero: ${pageState.hasSystemStatusHero ? '✅' : '❌'}`);
    console.log(`   Has CoreSystemCards: ${pageState.hasCoreSystemCards}`);
    console.log(`   Has PerformanceSparkline: ${pageState.hasPerformanceSparkline ? '✅' : '❌'}`);
    console.log(`   Has TrendIndicator: ${pageState.hasTrendIndicator}`);
    
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
    }
    
    // Check console logs
    console.log('\n📝 Console Logs:');
    consoleLogs.forEach(log => {
      const icon = log.type === 'error' ? '❌' : log.type === 'warn' ? '⚠️' : 'ℹ️';
      console.log(`   ${icon} [${log.type.toUpperCase()}] ${log.text}`);
    });
    
    // Take screenshot
    const filename = `component-isolation-test-${Date.now()}.png`;
    await page.screenshot({ path: filename, fullPage: true });
    console.log(`✅ Screenshot saved: ${filename}`);
    
    console.log('\n✅ Component isolation test complete!\n');
    
  } catch (error) {
    console.error('❌ Error:', error.message);
  } finally {
    await browser.close();
  }
}

testComponentIsolation();

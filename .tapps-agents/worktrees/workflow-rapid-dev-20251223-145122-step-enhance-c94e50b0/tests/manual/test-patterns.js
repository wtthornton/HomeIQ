const puppeteer = require('puppeteer');

async function testPatterns() {
  const browser = await puppeteer.launch({ headless: false });
  const page = await browser.newPage();
  
  try {
    console.log('Navigating to patterns page...');
    await page.goto('http://localhost:3001/patterns', { waitUntil: 'networkidle2' });
    
    console.log('Waiting for patterns to load...');
    await page.waitForSelector('[data-testid="pattern-chart"], .chart, canvas', { timeout: 10000 });
    
    console.log('Taking screenshot...');
    await page.screenshot({ path: 'patterns-test.png', fullPage: true });
    
    // Check if device names are readable
    const chartLabels = await page.evaluate(() => {
      const chart = document.querySelector('canvas');
      if (!chart) return [];
      
      // Try to get chart data from Chart.js
      const chartInstance = Chart.getChart(chart);
      if (chartInstance && chartInstance.data && chartInstance.data.labels) {
        return chartInstance.data.labels;
      }
      return [];
    });
    
    console.log('Chart labels:', chartLabels);
    
    // Check pattern list
    const patternNames = await page.evaluate(() => {
      const patterns = document.querySelectorAll('[class*="font-semibold"]');
      return Array.from(patterns).map(p => p.textContent).slice(0, 5);
    });
    
    console.log('Pattern names:', patternNames);
    
    await browser.close();
    
    // Check if names are readable (not just hashes)
    const hasReadableNames = chartLabels.some(label => 
      !label.includes('+') && 
      !label.match(/^[a-f0-9]{32,}$/) && 
      label.length < 50
    );
    
    if (hasReadableNames) {
      console.log('✅ SUCCESS: Found readable device names!');
    } else {
      console.log('❌ FAILED: Still showing hash IDs instead of readable names');
    }
    
  } catch (error) {
    console.error('Error:', error);
    await browser.close();
  }
}

testPatterns();

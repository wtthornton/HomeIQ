const puppeteer = require('puppeteer');
const fs = require('fs');

async function takeScreenshot() {
  try {
    console.log('Starting browser...');
    const browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    await page.setViewport({ width: 1920, height: 1080 });
    
    console.log('Navigating to dashboard...');
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle2' });
    
    // Wait for the dependencies tab to be visible
    console.log('Waiting for dependencies tab...');
    await page.waitForSelector('[data-tab="dependencies"]', { timeout: 10000 });
    
    // Click on dependencies tab
    await page.click('[data-tab="dependencies"]');
    
    // Wait for the graph to load
    await page.waitForTimeout(2000);
    
    // Take screenshot of the dependencies section
    console.log('Taking screenshot...');
    const screenshot = await page.screenshot({
      path: 'dependencies-tab.png',
      fullPage: true
    });
    
    console.log('Screenshot saved as dependencies-tab.png');
    
    await browser.close();
  } catch (error) {
    console.error('Error taking screenshot:', error);
  }
}

takeScreenshot();

import { chromium } from 'playwright';

async function takeScreenshot() {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  try {
    // Navigate to the dashboard
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    
    // Navigate to Dependencies tab
    await page.click('text=Dependencies');
    await page.waitForTimeout(2000); // Wait for animations
    
    // Take screenshot
    await page.screenshot({ 
      path: 'dashboard-dependencies-updated.png',
      fullPage: true 
    });
    
    console.log('Screenshot saved as dashboard-dependencies-updated.png');
    
  } catch (error) {
    console.error('Error taking screenshot:', error);
  } finally {
    await browser.close();
  }
}

takeScreenshot();

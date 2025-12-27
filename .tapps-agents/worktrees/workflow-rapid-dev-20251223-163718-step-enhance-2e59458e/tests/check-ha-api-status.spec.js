const { test } = require('@playwright/test');

test('Check HA Devices API Status indicator', async ({ page }) => {
  console.log('🚀 Opening dashboard...');
  
  await page.goto('http://localhost:3000', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);
  
  console.log('✓ Page loaded');
  
  // Scroll to HA Integration section
  const haHeading = await page.locator('h2:has-text("Home Assistant Integration")').first();
  await haHeading.scrollIntoViewIfNeeded();
  await page.waitForTimeout(500);
  
  // Check for the API status indicator
  const apiStatus = await page.locator('text=HA Devices API Status').count();
  
  if (apiStatus > 0) {
    console.log('\n✅ FOUND: HA Devices API Status indicator');
    
    // Get the status text
    const statusText = await page.locator('text=HA Devices API Status').locator('..').locator('..').textContent();
    console.log('📊 Status:', statusText?.trim());
    
    // Check for View Details button
    const viewDetailsButton = await page.locator('button:has-text("View Details")').count();
    console.log(`✅ View Details button: ${viewDetailsButton > 0 ? 'Present' : 'Missing'}`);
    
    // Take screenshot
    await page.screenshot({ path: 'ha-api-status-indicator.png', fullPage: true });
    console.log('✓ Screenshot saved: ha-api-status-indicator.png');
    
  } else {
    console.log('\n❌ HA Devices API Status indicator NOT FOUND');
  }
  
  console.log('\n✅ Check complete!');
});


const { test } = require('@playwright/test');

test('Review Devices Tab', async ({ page }) => {
  console.log('🚀 Opening dashboard...');
  
  await page.goto('http://localhost:3000', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);
  
  // Click on Devices tab
  console.log('📱 Clicking Devices tab...');
  const devicesTab = await page.locator('text=📱 Devices').first();
  await devicesTab.click();
  await page.waitForTimeout(3000);
  
  // Get the content
  const bodyText = await page.locator('body').textContent();
  
  // Take screenshot
  await page.screenshot({ path: 'devices-tab-view.png', fullPage: true });
  console.log('✓ Screenshot saved: devices-tab-view.png');
  
  // Check for summary cards
  const totalDevices = await page.locator('text=Total Devices').count();
  const totalEntities = await page.locator('text=Total Entities').count();
  const integrations = await page.locator('text=Integrations').count();
  
  console.log('\n📊 DEVICES TAB SUMMARY:');
  console.log('========================');
  
  if (totalDevices > 0) {
    console.log('✅ Has "Total Devices" card');
  }
  if (totalEntities > 0) {
    console.log('✅ Has "Total Entities" card');
  }
  if (integrations > 0) {
    console.log('✅ Has "Integrations" card');
  }
  
  // Check for search and filters
  const searchBox = await page.locator('input[placeholder*="Search"]').count();
  const manufacturerFilter = await page.locator('text=All Manufacturers').count();
  const areaFilter = await page.locator('text=All Areas').count();
  
  if (searchBox > 0) console.log('✅ Has Search box');
  if (manufacturerFilter > 0) console.log('✅ Has Manufacturer filter');
  if (areaFilter > 0) console.log('✅ Has Area filter');
  
  // Check for device grid or empty state
  const noDevices = await page.locator('text=No devices found').count();
  const deviceCards = await page.locator('[class*="grid"]').count();
  
  if (noDevices > 0) {
    console.log('\n📦 STATUS: Empty state - No devices discovered');
  } else if (deviceCards > 0) {
    console.log('\n📦 STATUS: Device grid present');
  }
  
  // Get actual numbers if visible
  const deviceCountElements = await page.locator('.text-3xl.font-bold').allTextContents();
  if (deviceCountElements.length > 0) {
    console.log('\n📈 COUNTS:');
    deviceCountElements.forEach((count, idx) => {
      console.log(`  ${idx + 1}. ${count}`);
    });
  }
  
  console.log('\n✅ Review complete!');
});


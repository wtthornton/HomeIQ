const { test, expect } = require('@playwright/test');

test('View HA Integration section on dashboard', async ({ page }) => {
  console.log('🚀 Opening dashboard at http://localhost:3000...');
  
  // Navigate to dashboard
  await page.goto('http://localhost:3000', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(5000); // Wait for everything to load
  
  console.log('✓ Page loaded');
  
  // Take full page screenshot
  await page.screenshot({ path: 'dashboard-full-view.png', fullPage: true });
  console.log('✓ Full page screenshot saved: dashboard-full-view.png');
  
  // Get the page content to see what's actually there
  const bodyText = await page.locator('body').textContent();
  console.log('\n📄 Page contains text:', bodyText.substring(0, 500));
  
  // Try to find the HA Integration heading
  const haHeading = page.locator('h2:has-text("Home Assistant Integration")');
  const haHeadingExists = await haHeading.count();
  
  if (haHeadingExists > 0) {
    console.log('\n✅ Found HA Integration heading!');
    
    // Scroll to it
    await haHeading.first().scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);
    
    // Take a screenshot of the HA Integration section
    await page.screenshot({ path: 'ha-integration-section.png', fullPage: false });
    console.log('✓ HA Integration section screenshot saved: ha-integration-section.png');
    
    // Check for summary cards
    const devicesText = await page.locator('text=Devices').count();
    const entitiesText = await page.locator('text=Entities').count();
    const integrationsText = await page.locator('text=Integrations').count();
    const healthText = await page.locator('text=Health').count();
    
    console.log(`\n📊 Summary Cards Found:`);
    console.log(`  - Devices: ${devicesText > 0 ? '✅' : '❌'}`);
    console.log(`  - Entities: ${entitiesText > 0 ? '✅' : '❌'}`);
    console.log(`  - Integrations: ${integrationsText > 0 ? '✅' : '❌'}`);
    console.log(`  - Health: ${healthText > 0 ? '✅' : '❌'}`);
    
    // Check for View All Devices button
    const viewAllButton = await page.locator('button:has-text("View All Devices")').count();
    console.log(`  - View All Devices button: ${viewAllButton > 0 ? '✅' : '❌'}`);
    
    // Check for empty state
    const emptyState = await page.locator('text=No Home Assistant devices').count();
    if (emptyState > 0) {
      console.log('\n📦 Empty state displayed (no devices discovered yet)');
    }
    
  } else {
    console.log('\n❌ HA Integration heading NOT found on page');
    console.log('Taking screenshot for debugging...');
    await page.screenshot({ path: 'dashboard-debug.png', fullPage: true });
  }
  
  console.log('\n✅ Test complete! Check the screenshots.');
});


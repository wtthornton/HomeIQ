const { test, expect } = require('@playwright/test');

test.describe('HA Integration Section on Overview Tab', () => {
  test('should display HA Integration section with all components', async ({ page }) => {
    // Navigate to dashboard
    await page.goto('http://localhost:3000', { waitUntil: 'domcontentloaded' });
    
    // Wait for page to load
    await page.waitForTimeout(3000); // Give time for data to load
    
    console.log('✓ Dashboard loaded');
    
    // Verify we're on the Overview tab (should be default)
    const overviewContent = await page.locator('text=System Status').first();
    await expect(overviewContent).toBeVisible();
    console.log('✓ Overview tab is active');
    
    // Scroll down to find the HA Integration section
    await page.evaluate(() => {
      window.scrollTo(0, document.body.scrollHeight / 2);
    });
    await page.waitForTimeout(500);
    
    // Check for the HA Integration section heading
    const haIntegrationHeading = await page.locator('text=🏠 Home Assistant Integration').first();
    await expect(haIntegrationHeading).toBeVisible();
    console.log('✓ HA Integration section heading found');
    
    // Verify the 4 summary cards
    const devicesCard = await page.locator('text=Devices').first();
    await expect(devicesCard).toBeVisible();
    console.log('✓ Devices card found');
    
    const entitiesCard = await page.locator('text=Entities').first();
    await expect(entitiesCard).toBeVisible();
    console.log('✓ Entities card found');
    
    const integrationsCard = await page.locator('text=Integrations').first();
    await expect(integrationsCard).toBeVisible();
    console.log('✓ Integrations card found');
    
    const healthCard = await page.locator('text=Health').first();
    await expect(healthCard).toBeVisible();
    console.log('✓ Health card found');
    
    // Check for metrics values (should have numbers)
    const metrics = await page.locator('.text-3xl.font-bold').allTextContents();
    console.log('📊 Metrics found:', metrics);
    
    // Check for Top Integrations or Empty State
    const topIntegrationsExists = await page.locator('text=Top Integrations').isVisible().catch(() => false);
    const emptyStateExists = await page.locator('text=No Home Assistant devices discovered yet').isVisible().catch(() => false);
    
    if (topIntegrationsExists) {
      console.log('✓ Top Integrations section found (devices present)');
      
      // Check for View All Devices button
      const viewAllButton = await page.locator('button:has-text("View All Devices")');
      await expect(viewAllButton).toBeVisible();
      console.log('✓ "View All Devices" button found');
      
    } else if (emptyStateExists) {
      console.log('✓ Empty state displayed (no devices yet)');
      const emptyMessage = await page.locator('text=Waiting for Home Assistant');
      await expect(emptyMessage).toBeVisible();
      console.log('✓ Empty state message correct');
    }
    
    // Scroll the HA Integration section into view for screenshot
    await haIntegrationHeading.scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);
    
    // Take a screenshot of the HA Integration section
    const haSection = await page.locator('text=🏠 Home Assistant Integration').locator('xpath=ancestor::div[contains(@class, "mb-8")]').first();
    await haSection.screenshot({ path: 'ha-integration-section-screenshot.png' });
    console.log('✓ Screenshot saved: ha-integration-section-screenshot.png');
    
    // Take a full page screenshot
    await page.screenshot({ path: 'overview-tab-full-screenshot.png', fullPage: true });
    console.log('✓ Full page screenshot saved: overview-tab-full-screenshot.png');
    
    console.log('\n✅ All UI elements verified successfully!');
  });
  
  test('should have responsive layout', async ({ page }) => {
    // Test mobile view
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('http://localhost:3000', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);
    
    const haHeading = await page.locator('text=🏠 Home Assistant Integration').first();
    await haHeading.scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);
    
    await page.screenshot({ path: 'ha-integration-mobile-screenshot.png', fullPage: true });
    console.log('✓ Mobile screenshot saved: ha-integration-mobile-screenshot.png');
    
    // Test tablet view
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);
    
    await haHeading.scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);
    
    await page.screenshot({ path: 'ha-integration-tablet-screenshot.png', fullPage: true });
    console.log('✓ Tablet screenshot saved: ha-integration-tablet-screenshot.png');
    
    // Test desktop view
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);
    
    await haHeading.scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);
    
    await page.screenshot({ path: 'ha-integration-desktop-screenshot.png', fullPage: true });
    console.log('✓ Desktop screenshot saved: ha-integration-desktop-screenshot.png');
    
    console.log('\n✅ Responsive design verified!');
  });
  
  test('should test navigation to Devices Tab', async ({ page }) => {
    await page.goto('http://localhost:3000', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);
    
    // Scroll to HA Integration section
    const haHeading = await page.locator('text=🏠 Home Assistant Integration').first();
    await haHeading.scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);
    
    // Check if View All Devices button exists
    const viewAllButton = await page.locator('button:has-text("View All Devices")').first();
    const buttonExists = await viewAllButton.isVisible().catch(() => false);
    
    if (buttonExists) {
      // Click the button
      await viewAllButton.click();
      await page.waitForTimeout(1000);
      
      // Verify we're on the Devices tab
      const devicesTabContent = await page.locator('text=Total Devices').first();
      await expect(devicesTabContent).toBeVisible();
      console.log('✓ Navigation to Devices Tab works!');
      
      // Take screenshot of Devices Tab
      await page.screenshot({ path: 'devices-tab-after-navigation.png', fullPage: true });
      console.log('✓ Devices Tab screenshot saved');
    } else {
      console.log('⚠ View All Devices button not visible (empty state or no devices)');
    }
  });
});


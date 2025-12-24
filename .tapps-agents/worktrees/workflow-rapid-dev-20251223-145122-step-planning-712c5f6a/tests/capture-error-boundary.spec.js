const { test } = require('@playwright/test');

test('Capture Error Boundary Details', async ({ page }) => {
  console.log('Opening dashboard...');
  
  // Capture console for detailed errors
  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('Tab rendering error') || text.includes('Error caught by boundary')) {
      console.log(`\n🔴 ERROR BOUNDARY CAUGHT:`);
      console.log(text);
    }
  });
  
  await page.goto('http://localhost:3000', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(8000);
  
  // Check if error boundary is showing
  const errorHeading = await page.locator('h2:has-text("Something went wrong")').first();
  const isErrorBoundaryVisible = await errorHeading.isVisible().catch(() => false);
  
  if (isErrorBoundaryVisible) {
    console.log('\n✅ Error Boundary IS showing!');
    
    // Click details to expand
    const details = await page.locator('summary:has-text("Error Details")').first();
    if (await details.isVisible()) {
      await details.click();
      await page.waitForTimeout(1000);
      
      // Get error text
      const errorText = await page.locator('pre').first().textContent();
      console.log('\n📋 Error Message:');
      console.log(errorText);
      
      // Get stack trace if available
      const stackElements = await page.locator('pre').all();
      if (stackElements.length > 1) {
        const stack = await stackElements[1].textContent();
        console.log('\n📚 Component Stack:');
        console.log(stack);
      }
    }
    
    await page.screenshot({ path: 'error-boundary-details.png', fullPage: true });
    console.log('\n📸 Screenshot saved: error-boundary-details.png');
  } else {
    console.log('\n❌ Error Boundary NOT visible - page might be working OR error happened before boundary');
    await page.screenshot({ path: 'page-state.png', fullPage: true });
    
    // Check for blank page
    const bodyText = await page.locator('body').textContent();
    console.log(`\n📄 Page body text length: ${bodyText.length} chars`);
    if (bodyText.trim().length === 0) {
      console.log('⚠️  Page is completely blank - error before React loaded');
    }
  }
});


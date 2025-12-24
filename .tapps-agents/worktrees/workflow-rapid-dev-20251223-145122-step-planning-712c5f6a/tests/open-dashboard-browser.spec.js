const { test } = require('@playwright/test');

test('Open dashboard in browser for manual inspection', async ({ page }) => {
  console.log('\n🌐 Opening dashboard in browser...\n');
  console.log('Dashboard URL: http://localhost:3000');
  console.log('\nThe browser will stay open for 60 seconds so you can inspect it.');
  console.log('You can interact with the page and check the console for errors.\n');
  
  // Navigate to dashboard
  await page.goto('http://localhost:3000');
  
  // Wait and keep browser open
  await page.waitForTimeout(60000);
  
  console.log('\n✅ Browser session complete\n');
});

const { test } = require('@playwright/test');

test('Get Exact JavaScript Error', async ({ page, browser }) => {
  const errors = [];
  const pageErrors = [];
  
  page.on('console', msg => {
    console.log(`[CONSOLE ${msg.type()}] ${msg.text()}`);
  });
  
  page.on('pageerror', error => {
    pageErrors.push(error);
    console.log(`\n🔴 PAGE ERROR:\n${error.stack || error.message}`);
  });
  
  page.on('requestfailed', request => {
    console.log(`\n⚠️  Request failed: ${request.url()} - ${request.failure().errorText}`);
  });
  
  console.log('Loading page...');
  await page.goto('http://localhost:3000');
  await page.waitForTimeout(10000);
  
  console.log(`\n📊 Summary:`);
  console.log(`- Page errors: ${pageErrors.length}`);
  console.log(`- Page title: ${await page.title()}`);
  console.log(`- Body text: "${(await page.locator('body').textContent()).substring(0, 100)}"`);
  
  await page.screenshot({ path: 'exact-error-state.png', fullPage: true });
});


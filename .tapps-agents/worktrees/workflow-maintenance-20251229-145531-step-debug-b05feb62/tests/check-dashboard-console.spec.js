const { test } = require('@playwright/test');

test('Check dashboard console errors', async ({ page }) => {
  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });
  
  page.on('pageerror', error => {
    console.log(`Page error: ${error.message}`);
  });
  
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
  await page.waitForTimeout(5000);
  
  console.log(`\nConsole errors (${errors.length}):`);
  errors.forEach((err, idx) => {
    console.log(`${idx + 1}. ${err}`);
  });
  
  await page.screenshot({ path: 'dashboard-console-check.png', fullPage: true });
  console.log('\nScreenshot saved: dashboard-console-check.png');
});


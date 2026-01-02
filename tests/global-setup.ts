import { chromium, FullConfig } from '@playwright/test';

/**
 * Global Setup
 * Runs once before all tests
 */
async function globalSetup(config: FullConfig) {
  // Optional: Start services, seed database, etc.
  console.log('Global setup: Preparing test environment...');
  
  // Example: Verify services are running
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  try {
    // Check Health Dashboard
    await page.goto('http://localhost:3000', { timeout: 10000 });
    console.log('✓ Health Dashboard is accessible');
  } catch (error) {
    console.warn('⚠ Health Dashboard might not be running:', error);
  }
  
  try {
    // Check AI Automation UI
    await page.goto('http://localhost:3001', { timeout: 10000 });
    console.log('✓ AI Automation UI is accessible');
  } catch (error) {
    console.warn('⚠ AI Automation UI might not be running:', error);
  }
  
  await browser.close();
  console.log('Global setup complete');
}

export default globalSetup;

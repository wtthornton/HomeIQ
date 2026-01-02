import { FullConfig } from '@playwright/test';

/**
 * Global Teardown
 * Runs once after all tests
 */
async function globalTeardown(config: FullConfig) {
  // Optional: Cleanup, stop services, etc.
  console.log('Global teardown: Cleaning up test environment...');
  
  // Add any cleanup logic here
  // Example: Stop test services, clean up test data, etc.
  
  console.log('Global teardown complete');
}

export default globalTeardown;

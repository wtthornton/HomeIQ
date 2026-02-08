import { defineConfig, devices } from '@playwright/test';

/**
 * Root Playwright Configuration
 * Multi-project configuration for Health Dashboard and AI Automation UI
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './e2e',
  
  /* Run tests in files in parallel */
  fullyParallel: true,
  
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,
  
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/results.xml' }],
    ['list'],
  ],
  
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
    /* Take screenshot on failure */
    screenshot: 'only-on-failure',
    /* Record video on failure */
    video: 'retain-on-failure',
    /* Global timeout for each test */
    actionTimeout: 10000,
    /* Global timeout for navigation */
    navigationTimeout: 30000,
  },
  
  /* Configure projects for major browsers */
  projects: [
    {
      name: 'health-dashboard-chromium',
      testDir: './e2e/health-dashboard',
      use: { 
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:3000',
      },
    },
    {
      name: 'health-dashboard-firefox',
      testDir: './e2e/health-dashboard',
      use: { 
        ...devices['Desktop Firefox'],
        baseURL: 'http://localhost:3000',
      },
    },
    {
      name: 'health-dashboard-webkit',
      testDir: './e2e/health-dashboard',
      use: { 
        ...devices['Desktop Safari'],
        baseURL: 'http://localhost:3000',
      },
    },
    {
      name: 'ai-automation-ui-chromium',
      testDir: './e2e/ai-automation-ui',
      use: { 
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:3001',
      },
    },
    {
      name: 'ai-automation-ui-firefox',
      testDir: './e2e/ai-automation-ui',
      use: { 
        ...devices['Desktop Firefox'],
        baseURL: 'http://localhost:3001',
      },
    },
    {
      name: 'ai-automation-ui-webkit',
      testDir: './e2e/ai-automation-ui',
      use: { 
        ...devices['Desktop Safari'],
        baseURL: 'http://localhost:3001',
      },
    },
    /* Test against mobile viewports. */
    {
      name: 'health-dashboard-mobile-chrome',
      testDir: './e2e/health-dashboard',
      use: { 
        ...devices['Pixel 5'],
        baseURL: 'http://localhost:3000',
      },
    },
    {
      name: 'ai-automation-ui-mobile-chrome',
      testDir: './e2e/ai-automation-ui',
      use: { 
        ...devices['Pixel 5'],
        baseURL: 'http://localhost:3001',
      },
    },
    {
      name: 'api-integration',
      testDir: './e2e/api-integration',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  
  /* Global setup and teardown */
  globalSetup: './global-setup.ts',
  globalTeardown: './global-teardown.ts',
  
  /* Test timeout */
  timeout: 30 * 1000,
  
  expect: {
    /* Timeout for expect() assertions */
    timeout: 5000,
  },
  
  /* Output directory for test artifacts */
  outputDir: 'test-results/',
});

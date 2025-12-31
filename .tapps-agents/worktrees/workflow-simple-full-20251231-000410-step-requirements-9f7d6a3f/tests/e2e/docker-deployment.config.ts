import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright Configuration for Docker Deployment Testing
 * This configuration is specifically designed to test against the local Docker deployment
 */
export default defineConfig({
  testDir: './',
  
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
    ['html', { outputFolder: '../../test-results/e2e-html-report' }],
    ['json', { outputFile: '../../test-results/e2e-results.json' }],
    ['junit', { outputFile: '../../test-results/e2e-results.xml' }],
    ['list'],
    ['github']
  ],
  
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: 'http://localhost:3000',
    
    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
    
    /* Take screenshot on failure */
    screenshot: 'only-on-failure',
    
    /* Record video on failure */
    video: 'retain-on-failure',
    
    /* Global timeout for each test */
    actionTimeout: 15000,
    
    /* Global timeout for navigation */
    navigationTimeout: 30000,
    
    /* Ignore HTTPS errors for local Docker setup */
    ignoreHTTPSErrors: true,
    
    /* Extra HTTP headers */
    extraHTTPHeaders: {
      'Accept': 'application/json, text/plain, */*',
      'User-Agent': 'Playwright-E2E-Tests'
    }
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'docker-chromium',
      use: { 
        ...devices['Desktop Chrome'],
        // Use Docker-specific settings
        launchOptions: {
          args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--no-first-run',
            '--no-zygote',
            '--single-process'
          ]
        }
      },
    },
    {
      name: 'docker-firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'docker-webkit',
      use: { ...devices['Desktop Safari'] },
    },
    /* Test against mobile viewports for Docker deployment */
    {
      name: 'docker-mobile-chrome',
      use: { 
        ...devices['Pixel 5'],
        launchOptions: {
          args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage'
          ]
        }
      },
    },
    {
      name: 'docker-mobile-safari',
      use: { ...devices['iPhone 12'] },
    }
  ],

  /* Run your local dev server before starting the tests */
  webServer: {
    command: 'echo "Using existing Docker deployment at http://localhost:3000"',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
    timeout: 120 * 1000,
    ignoreHTTPSErrors: true
  },

  /* Global setup and teardown for Docker environment */
  globalSetup: require.resolve('./docker-global-setup.ts'),
  globalTeardown: require.resolve('./docker-global-teardown.ts'),

  /* Test timeout */
  timeout: 60 * 1000, // 60 seconds for Docker environment
  
  expect: {
    /* Timeout for expect() assertions */
    timeout: 10000,
  },

  /* Output directory for test artifacts */
  outputDir: 'test-results/',
  
  /* Test match patterns */
  testMatch: [
    '**/system-health.spec.ts',
    '**/dashboard-functionality.spec.ts',
    '**/monitoring-screen.spec.ts',
    '**/settings-screen.spec.ts',
    '**/visual-regression.spec.ts',
    '**/integration.spec.ts',
    '**/performance.spec.ts',
    '**/api-endpoints.spec.ts',
    '**/frontend-ui-comprehensive.spec.ts',
    '**/integration-performance-enhanced.spec.ts',
    '**/dashboard-data-loading.spec.ts',
    '**/error-handling-comprehensive.spec.ts',
    '**/user-journey-complete.spec.ts',
    '**/cross-service-integration.spec.ts'
  ],
  
  /* Test ignore patterns */
  testIgnore: [
    '**/node_modules/**',
    '**/dist/**',
    '**/coverage/**'
  ]
});

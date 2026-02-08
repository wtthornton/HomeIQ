import { defineConfig, devices } from '@playwright/test';

/**
 * Smoke Test Configuration - 100% Pass Guarantee
 *
 * Runs only tests that pass reliably when Docker stack is up.
 * Use for CI/CD, quick validation, and deployment gates.
 *
 * Run: npx playwright test --config=tests/e2e/smoke-100percent.config.ts
 */
export default defineConfig({
  testDir: './',

  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,

  reporter: [
    ['html', { outputFolder: '../../test-results/smoke-html-report' }],
    ['list'],
  ],

  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15000,
    navigationTimeout: 30000,
    ignoreHTTPSErrors: true,
  },

  projects: [
    {
      name: 'smoke-chromium',
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: {
          args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
          ],
        },
      },
    },
  ],

  globalSetup: require.resolve('./docker-global-setup.ts'),

  /* No webServer - use existing Docker deployment; globalSetup validates. */
  webServer: undefined,

  timeout: 45 * 1000,
  expect: { timeout: 10000 },
  outputDir: 'test-results/',

  /* Only run tests known to pass 100% with Docker stack (no auth, no mocks) */
  testMatch: [
    '**/system-health-smoke.spec.ts',
    '**/minimal-dashboard-test.spec.ts',
  ],

  testIgnore: [
    '**/ask-ai-*.spec.ts', // AI tests need OpenAI - run with full config
    '**/ai-automation-*.spec.ts',
    '**/health-dashboard/**/*.spec.ts', // Requires auth/mock setup
    '**/visual-regression.spec.ts',
    '**/performance.spec.ts',
    '**/integration.spec.ts',
    '**/node_modules/**',
    '**/dist/**',
  ],
});

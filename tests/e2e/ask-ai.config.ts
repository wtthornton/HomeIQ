import { defineConfig, devices } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

// Load .env from project root so HOME_ASSISTANT_TOKEN is available to yaml-validator
const envPath = path.resolve(__dirname, '../../.env');
if (fs.existsSync(envPath)) {
  for (const line of fs.readFileSync(envPath, 'utf8').split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx > 0) {
      const key = trimmed.slice(0, eqIdx);
      const value = trimmed.slice(eqIdx + 1).replace(/^["']|["']$/g, '');
      if (!process.env[key]) process.env[key] = value;
    }
  }
}

/**
 * Playwright config for Ask AI E2E tests.
 *
 * Runs against the LOCAL Docker stack (localhost).
 * Prerequisites: HomeIQ stack running via scripts/start-stack.sh or domain.sh.
 *
 * Usage:
 *   npx playwright test --config=ask-ai.config.ts
 *   npx playwright test --config=ask-ai.config.ts --headed
 *   npx playwright test --config=ask-ai.config.ts --ui
 */
export default defineConfig({
  testDir: './',
  testMatch: [
    '**/ask-ai-complete.spec.ts',
    '**/ask-ai-to-ha-automation.spec.ts',
  ],

  fullyParallel: false, // sequential — OpenAI rate limits + shared chat state
  retries: 0,
  workers: 1,

  reporter: [
    ['list'],
    ['html', { outputFolder: '../../test-results/ask-ai-html-report', open: 'on-failure' }],
    ['json', { outputFile: '../../test-results/ask-ai-results.json' }],
  ],

  use: {
    baseURL: 'http://localhost:3001',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15000,
    navigationTimeout: 30000,
    ignoreHTTPSErrors: true,
  },

  projects: [
    {
      name: 'ask-ai-chromium',
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:3001',
      },
    },
  ],

  // Tests hit the already-running Docker stack — no webServer needed
  webServer: undefined,

  // OpenAI round-trips take 30-40s; multi-round tests need up to 4 minutes
  timeout: 120_000,

  expect: {
    timeout: 10_000,
  },

  outputDir: 'test-results/',
});

/**
 * API Mocking Utilities for AI Automation Testing
 * 
 * Provides mock handlers for backend API endpoints to enable
 * deterministic and fast test execution without external dependencies
 */

import { Page, Route } from '@playwright/test';
import { MockDataGenerator, Suggestion, Pattern, Automation } from './mock-data-generators';

/**
 * Mock the suggestions API endpoint
 * Returns list of AI-generated automation suggestions
 * 
 * @param page - Playwright page
 * @param data - Mock suggestions (or generate if not provided)
 * @param delay - Optional delay in ms for loading state testing
 * 
 * @example
 * await mockSuggestionsEndpoint(page);
 * await mockSuggestionsEndpoint(page, customSuggestions, 1000);
 */
export async function mockSuggestionsEndpoint(
  page: Page,
  data?: Suggestion[],
  delay: number = 0
): Promise<void> {
  const suggestions = data || MockDataGenerator.generateSuggestions({ count: 10 });
  
  await page.route('**/api/suggestions', async (route: Route) => {
    await new Promise(resolve => setTimeout(resolve, delay));
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(suggestions),
    });
  });
}

/**
 * Mock the deployment endpoint
 * Simulates deploying automation to Home Assistant
 * 
 * @param page - Playwright page
 * @param success - Whether deployment should succeed
 * @param delay - Optional delay in ms
 * 
 * @example
 * await mockDeployEndpoint(page, true);
 * await mockDeployEndpoint(page, false); // Test error handling
 */
export async function mockDeployEndpoint(
  page: Page,
  success: boolean = true,
  delay: number = 0
): Promise<void> {
  await page.route('**/api/deploy/*', async (route: Route) => {
    await new Promise(resolve => setTimeout(resolve, delay));
    
    if (success) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          automation_id: 'automation.ai_generated_' + Date.now(),
          message: 'Successfully deployed to Home Assistant',
        }),
      });
    } else {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Home Assistant connection failed',
          details: 'MQTT broker unavailable',
        }),
      });
    }
  });
}

/**
 * Mock the rejection endpoint
 * Simulates rejecting a suggestion with feedback
 * 
 * @param page - Playwright page
 * @param success - Whether rejection should succeed
 * @param delay - Optional delay in ms
 * 
 * @example
 * await mockRejectEndpoint(page, true);
 */
export async function mockRejectEndpoint(
  page: Page,
  success: boolean = true,
  delay: number = 0
): Promise<void> {
  await page.route('**/api/suggestions/*/reject', async (route: Route) => {
    await new Promise(resolve => setTimeout(resolve, delay));
    
    if (success) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          message: 'Suggestion rejected',
        }),
      });
    } else {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Database connection failed',
        }),
      });
    }
  });
}

/**
 * Mock the patterns endpoint
 * Returns detected automation patterns
 * 
 * @param page - Playwright page
 * @param data - Mock patterns (or generate if not provided)
 * @param delay - Optional delay in ms
 * 
 * @example
 * await mockPatternsEndpoint(page);
 */
export async function mockPatternsEndpoint(
  page: Page,
  data?: Pattern[],
  delay: number = 0
): Promise<void> {
  const patterns = data || MockDataGenerator.generatePatterns({ count: 8 });
  
  await page.route('**/api/patterns', async (route: Route) => {
    await new Promise(resolve => setTimeout(resolve, delay));
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(patterns),
    });
  });
}

/**
 * Mock the analysis trigger endpoint
 * Simulates starting manual analysis job
 * 
 * @param page - Playwright page
 * @param delay - Job duration in ms (default 5000)
 * 
 * @example
 * await mockAnalysisTriggerEndpoint(page, 3000);
 */
export async function mockAnalysisTriggerEndpoint(
  page: Page,
  delay: number = 5000
): Promise<void> {
  const jobId = 'job-' + Date.now();
  
  await page.route('**/api/analysis/trigger', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'started',
        job_id: jobId,
        estimated_duration: Math.floor(delay / 1000),
      }),
    });
  });
  
  // Mock status endpoint for progress tracking
  await page.route(`**/api/analysis/status/${jobId}`, async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'running',
        progress: 50,
        message: 'Analyzing patterns...',
      }),
    });
  });
}

/**
 * Mock the deployed automations endpoint
 * Returns list of deployed automations
 * 
 * @param page - Playwright page
 * @param data - Mock automations (or generate if not provided)
 * @param delay - Optional delay in ms
 * 
 * @example
 * await mockDeployedAutomationsEndpoint(page);
 */
export async function mockDeployedAutomationsEndpoint(
  page: Page,
  data?: Automation[],
  delay: number = 0
): Promise<void> {
  const automations = data || MockDataGenerator.generateDeployedAutomations({ count: 5 });
  
  await page.route('**/api/deployed', async (route: Route) => {
    await new Promise(resolve => setTimeout(resolve, delay));
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(automations),
    });
  });
}

/**
 * Mock the device utilization endpoint
 * Returns device intelligence metrics
 * 
 * @param page - Playwright page
 * @param delay - Optional delay in ms
 * 
 * @example
 * await mockDeviceUtilizationEndpoint(page);
 */
export async function mockDeviceUtilizationEndpoint(
  page: Page,
  delay: number = 0
): Promise<void> {
  const capabilities = MockDataGenerator.generateDeviceCapabilities({ count: 10 });
  
  await page.route('**/api/device-intelligence/utilization', async (route: Route) => {
    await new Promise(resolve => setTimeout(resolve, delay));
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(capabilities),
    });
  });
}

/**
 * Mock the settings endpoints
 * Handles get and save operations
 * 
 * @param page - Playwright page
 * @param currentSettings - Current settings object
 * 
 * @example
 * await mockSettingsEndpoints(page, { openai_api_key: 'sk-test-123' });
 */
export async function mockSettingsEndpoints(
  page: Page,
  currentSettings: Record<string, any> = {}
): Promise<void> {
  let settings = {
    openai_api_key: '',
    ha_url: 'http://192.168.1.86:8123',
    ha_token: '',
    analysis_schedule: '0 3 * * *',
    auto_deploy: false,
    ...currentSettings,
  };
  
  // GET settings
  await page.route('**/api/settings', async (route: Route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(settings),
      });
    } else if (route.request().method() === 'PUT') {
      // Update settings
      const newSettings = JSON.parse(route.request().postData() || '{}');
      settings = { ...settings, ...newSettings };
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          message: 'Settings saved successfully',
        }),
      });
    }
  });
}

/**
 * Mock all AI automation endpoints
 * Convenience method to set up all common mocks at once
 * 
 * @param page - Playwright page
 * 
 * @example
 * await mockAllEndpoints(page);
 */
export async function mockAllEndpoints(page: Page): Promise<void> {
  await mockSuggestionsEndpoint(page);
  await mockPatternsEndpoint(page);
  await mockDeployedAutomationsEndpoint(page);
  await mockDeployEndpoint(page, true);
  await mockRejectEndpoint(page, true);
  await mockDeviceUtilizationEndpoint(page);
  await mockSettingsEndpoints(page);
}

/**
 * Clear all route mocks
 * Useful for resetting between tests
 * 
 * @param page - Playwright page
 * 
 * @example
 * await clearAllMocks(page);
 */
export async function clearAllMocks(page: Page): Promise<void> {
  await page.unrouteAll();
}


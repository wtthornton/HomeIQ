import { Page, Route } from '@playwright/test';

/**
 * API Mocking Utilities
 * Helper functions for mocking API responses in Playwright tests
 */

export interface MockResponse {
  status?: number;
  body?: any;
  headers?: Record<string, string>;
  delay?: number;
}

/**
 * Create a mock API response handler
 */
export function createMockResponse(mock: MockResponse): (route: Route) => Promise<void> {
  return async (route: Route) => {
    await route.fulfill({
      status: mock.status || 200,
      body: JSON.stringify(mock.body || {}),
      headers: {
        'Content-Type': 'application/json',
        ...mock.headers,
      },
    });
  };
}

/**
 * Mock API endpoint with response
 */
export async function mockApiEndpoint(
  page: Page,
  urlPattern: string | RegExp,
  response: MockResponse
): Promise<void> {
  await page.route(urlPattern, createMockResponse(response));
}

/**
 * Mock multiple API endpoints
 */
export async function mockApiEndpoints(
  page: Page,
  endpoints: Array<{ pattern: string | RegExp; response: MockResponse }>
): Promise<void> {
  for (const endpoint of endpoints) {
    await mockApiEndpoint(page, endpoint.pattern, endpoint.response);
  }
}

/**
 * Simulate API error response
 */
export async function mockApiError(
  page: Page,
  urlPattern: string | RegExp,
  statusCode: number = 500,
  errorMessage?: string
): Promise<void> {
  await page.route(urlPattern, async (route) => {
    await route.fulfill({
      status: statusCode,
      body: JSON.stringify({
        error: errorMessage || 'Internal Server Error',
        status: statusCode,
      }),
      headers: { 'Content-Type': 'application/json' },
    });
  });
}

/**
 * Simulate slow API response
 */
export async function mockSlowApi(
  page: Page,
  urlPattern: string | RegExp,
  delay: number = 2000,
  response: MockResponse = { status: 200, body: {} }
): Promise<void> {
  await page.route(urlPattern, async (route) => {
    await new Promise((resolve) => setTimeout(resolve, delay));
    await createMockResponse(response)(route);
  });
}

/**
 * Wait for API request to complete
 */
export async function waitForApiRequest(
  page: Page,
  urlPattern: string | RegExp,
  timeout: number = 10000
): Promise<void> {
  await page.waitForResponse(
    (response) => {
      const url = response.url();
      if (typeof urlPattern === 'string') {
        return url.includes(urlPattern);
      }
      return urlPattern.test(url);
    },
    { timeout }
  );
}

/**
 * Intercept and log API requests
 */
export async function interceptApiRequests(
  page: Page,
  urlPattern: string | RegExp
): Promise<Array<{ url: string; method: string; postData?: string }>> {
  const requests: Array<{ url: string; method: string; postData?: string }> = [];

  page.on('request', (request) => {
    const url = request.url();
    const matches = typeof urlPattern === 'string' 
      ? url.includes(urlPattern)
      : urlPattern.test(url);
    
    if (matches) {
      requests.push({
        url,
        method: request.method(),
        postData: request.postData() || undefined,
      });
    }
  });

  return requests;
}

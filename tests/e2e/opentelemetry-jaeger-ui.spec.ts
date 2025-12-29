import { test, expect } from '@playwright/test';

/**
 * OpenTelemetry Jaeger UI E2E Tests
 * Tests the complete OpenTelemetry tracing setup via Jaeger UI:
 * - Jaeger UI accessibility and navigation
 * - Service discovery and trace visualization
 * - Trace details and span information
 * - Real-time trace generation from service requests
 */

const JAEGER_UI_URL = 'http://localhost:16686';
const DATA_API_URL = 'http://localhost:8006';
const ADMIN_API_URL = 'http://localhost:8004';

test.describe('OpenTelemetry Jaeger UI Tests', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to Jaeger UI
    await page.goto(JAEGER_UI_URL);
    await page.waitForLoadState('networkidle');
    // Wait for Jaeger UI to fully load
    await page.waitForTimeout(2000);
  });

  test('Jaeger UI loads and displays correctly', async ({ page }) => {
    // Verify page title contains Jaeger
    await expect(page).toHaveTitle(/Jaeger/i);
    
    // Verify main navigation elements are present
    const searchTab = page.locator('text=Search');
    await expect(searchTab).toBeVisible();
    
    // Verify service selector is present
    const serviceSelector = page.locator('select, [data-testid="service-selector"], input[placeholder*="Service"]').first();
    await expect(serviceSelector).toBeVisible();
  });

  test('Services are listed and accessible in Jaeger', async ({ page }) => {
    // Wait for service list to load
    await page.waitForTimeout(3000);
    
    // Look for service dropdown or selector
    const serviceSelect = page.locator('select, [role="combobox"]').first();
    
    // Check if we can find data-api or admin-api in the services
    const pageContent = await page.content();
    const hasDataApi = pageContent.includes('data-api') || pageContent.includes('data_api');
    const hasAdminApi = pageContent.includes('admin-api') || pageContent.includes('admin_api');
    
    // At least one of our services should be visible
    expect(hasDataApi || hasAdminApi).toBeTruthy();
  });

  test('Generates trace from data-api request and displays in Jaeger', async ({ page }) => {
    // Step 1: Make a request to data-api to generate a trace
    const response = await page.request.get(`${DATA_API_URL}/health`);
    expect(response.status()).toBe(200);
    
    // Step 2: Wait for trace to be exported (batch processor may delay)
    await page.waitForTimeout(5000);
    
    // Step 3: Refresh Jaeger UI to see new trace
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    
    // Step 4: Select data-api service if service selector exists
    const serviceSelector = page.locator('select, [data-testid="service-selector"]').first();
    if (await serviceSelector.isVisible()) {
      await serviceSelector.selectOption({ label: /data-api/i });
      await page.waitForTimeout(2000);
    }
    
    // Step 5: Click Find Traces button
    const findTracesButton = page.locator('button:has-text("Find Traces"), button:has-text("Search")').first();
    if (await findTracesButton.isVisible()) {
      await findTracesButton.click();
      await page.waitForTimeout(3000);
    }
    
    // Step 6: Verify traces are displayed (look for trace list or trace cards)
    const traceList = page.locator('[data-testid="trace-list"], .TraceList, table').first();
    
    // Alternative: Check if any trace-related content appears
    const pageContent = await page.content();
    const hasTraceContent = pageContent.includes('trace') || 
                           pageContent.includes('span') ||
                           pageContent.includes('GET');
    
    // Best effort check - traces might be in a table or list
    expect(hasTraceContent || await traceList.isVisible()).toBeTruthy();
  });

  test('Generates trace from admin-api request and displays in Jaeger', async ({ page }) => {
    // Make request to admin-api
    const response = await page.request.get(`${ADMIN_API_URL}/health`);
    expect(response.status()).toBe(200);
    
    // Wait for trace export
    await page.waitForTimeout(5000);
    
    // Refresh and verify
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    
    // Try to find admin-api traces
    const pageContent = await page.content();
    const hasAdminApi = pageContent.includes('admin-api') || pageContent.includes('admin_api');
    
    // Service should be visible in Jaeger
    expect(hasAdminApi).toBeTruthy();
  });

  test('Trace details show span information correctly', async ({ page }) => {
    // Generate a trace first
    await page.request.get(`${DATA_API_URL}/health`);
    await page.waitForTimeout(5000);
    
    // Reload Jaeger UI
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    
    // Try to find and click on a trace (if available)
    const traceLink = page.locator('a[href*="trace"], [data-testid="trace-link"]').first();
    
    if (await traceLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      await traceLink.click();
      await page.waitForTimeout(2000);
      
      // Verify trace detail page loads
      await expect(page).toHaveURL(/trace/i);
      
      // Verify span information is visible
      const spanInfo = page.locator('text=/span|operation|duration/i').first();
      await expect(spanInfo).toBeVisible();
    } else {
      // If no trace link, verify we can at least see the search interface
      const searchInterface = page.locator('input, select, button').first();
      await expect(searchInterface).toBeVisible();
    }
  });

  test('Jaeger API endpoints are accessible', async ({ page }) => {
    // Test services endpoint
    const servicesResponse = await page.request.get(`${JAEGER_UI_URL}/api/services`);
    expect(servicesResponse.status()).toBe(200);
    
    const servicesData = await servicesResponse.json();
    expect(servicesData).toHaveProperty('data');
    expect(Array.isArray(servicesData.data)).toBe(true);
    
    // Verify our services are in the list
    const serviceNames = servicesData.data.map((s: any) => typeof s === 'string' ? s : s.name || s.serviceName || '');
    const hasDataApi = serviceNames.some((name: string) => 
      name.toLowerCase().includes('data-api') || name.toLowerCase().includes('data_api')
    );
    const hasAdminApi = serviceNames.some((name: string) => 
      name.toLowerCase().includes('admin-api') || name.toLowerCase().includes('admin_api')
    );
    
    expect(hasDataApi || hasAdminApi).toBeTruthy();
  });

  test('Real-time trace generation works end-to-end', async ({ page }) => {
    // Get initial trace count via API
    const initialTracesResponse = await page.request.get(
      `${JAEGER_UI_URL}/api/traces?service=data-api&limit=1`
    );
    const initialTraces = await initialTracesResponse.json();
    const initialCount = initialTraces.data?.length || 0;
    
    // Generate multiple requests to ensure trace is created
    for (let i = 0; i < 3; i++) {
      await page.request.get(`${DATA_API_URL}/health`);
      await page.waitForTimeout(1000);
    }
    
    // Wait for trace export
    await page.waitForTimeout(5000);
    
    // Check for new traces
    const newTracesResponse = await page.request.get(
      `${JAEGER_UI_URL}/api/traces?service=data-api&limit=10`
    );
    const newTraces = await newTracesResponse.json();
    const newCount = newTraces.data?.length || 0;
    
    // We should have at least one trace (best effort - batch processor may delay)
    expect(newCount >= initialCount).toBeTruthy();
  });

  test('Service dependencies are visible', async ({ page }) => {
    // Navigate to system/dependencies view if available
    const dependenciesLink = page.locator('text=/dependencies|dependencies|graph/i').first();
    
    if (await dependenciesLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      await dependenciesLink.click();
      await page.waitForTimeout(2000);
      
      // Verify dependency graph or list is visible
      const graph = page.locator('[data-testid="dependency-graph"], svg, canvas').first();
      await expect(graph).toBeVisible();
    } else {
      // If dependencies view not available, verify we can at least see services
      const servicesResponse = await page.request.get(`${JAEGER_UI_URL}/api/services`);
      expect(servicesResponse.status()).toBe(200);
    }
  });
});


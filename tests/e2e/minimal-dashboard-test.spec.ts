import { test, expect } from '@playwright/test';

/**
 * Minimal Dashboard Test - No Complex Setup Required
 * Tests that the dashboard loads without JSON parsing errors
 */
test.describe('Minimal Dashboard Test', () => {
  
  test('Dashboard loads without JSON parsing errors', async ({ page }) => {
    // Set up console error monitoring
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Navigate to dashboard
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    
    // Wait for dashboard to load
    await page.waitForSelector('body', { timeout: 15000 });
    
    // Check for JSON parsing errors
    const jsonErrors = consoleErrors.filter(error => 
      error.includes('JSON') || 
      error.includes('Unexpected token') ||
      error.includes('<!DOCTYPE')
    );
    
    // Log any errors for debugging
    if (consoleErrors.length > 0) {
      console.log('Console errors found:', consoleErrors);
    }
    
    // The test should pass if no JSON parsing errors
    expect(jsonErrors).toHaveLength(0);
  });

  test('API endpoints return valid JSON', async ({ page }) => {
    // Test health endpoint
    const response = await page.request.get('http://localhost:3000/api/v1/health');
    expect(response.status()).toBe(200);
    
    // Verify Content-Type is JSON
    const contentType = response.headers()['content-type'];
    expect(contentType).toContain('application/json');
    
    // Verify response can be parsed as JSON
    const data = await response.json();
    expect(data).toBeDefined();
    expect(typeof data).toBe('object');
    
    // Verify response doesn't contain HTML
    const responseText = await response.text();
    expect(responseText).not.toContain('<!DOCTYPE');
    expect(responseText).not.toContain('<html');
  });

  test('Dashboard displays content', async ({ page }) => {
    // Navigate to dashboard
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    
    // Check that page loaded
    const title = await page.title();
    expect(title).toBeDefined();
    expect(title.length).toBeGreaterThan(0);
    
    // Check that page has content
    const body = await page.locator('body').textContent();
    expect(body).toBeDefined();
    expect(body!.length).toBeGreaterThan(0);
  });
});

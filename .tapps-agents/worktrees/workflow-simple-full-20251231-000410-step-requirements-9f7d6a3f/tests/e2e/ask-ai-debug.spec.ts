/**
 * Debug test for Ask AI
 */

import { test, expect } from '@playwright/test';

test('Debug: Submit query and wait for response', async ({ page }) => {
  // Go to Ask AI page
  await page.goto('http://localhost:3001/ask-ai');
  await page.waitForLoadState('networkidle');
  
  console.log('Page loaded');
  
  // Find input
  const input = page.locator('input[placeholder*="Ask me about"]');
  await expect(input).toBeVisible();
  console.log('Input visible');
  
  // Type query
  await input.fill('Make the Office feel like an EDC party with flashing lights including LED lights');
  console.log('Query typed');
  
  // Find and click send button
  const sendButton = page.getByRole('button', { name: /send/i });
  await expect(sendButton).toBeEnabled();
  console.log('Send button enabled');
  
  await sendButton.click();
  console.log('Send button clicked');
  
  // Wait a bit
  await page.waitForTimeout(10000);
  console.log('Waited 10 seconds');
  
  // Check for any toasts
  const body = await page.locator('body').textContent();
  console.log('Page content sample:', body?.substring(0, 500));
  
  // Take screenshot
  await page.screenshot({ path: 'test-results/debug-screenshot.png', fullPage: true });
  console.log('Screenshot saved');
});

test('Debug: Test API call with specific IDs', async ({ page }) => {
  const queryId = 'query-5849c3e4';
  const suggestionId = 'ask-ai-bb5a3072';
  
  console.log(`🧪 Testing API with query_id: ${queryId}, suggestion_id: ${suggestionId}`);
  
  // Make direct API call to test endpoint
  const response = await page.request.post(
    `http://localhost:8018/api/v1/ask-ai/query/${queryId}/suggestions/${suggestionId}/test`,
    {
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );
  
  console.log(`Response status: ${response.status()}`);
  
  const responseBody = await response.json();
  console.log('Response body:', JSON.stringify(responseBody, null, 2));
  
  // Log key information
  if (responseBody.valid !== undefined) {
    console.log(`✅ Valid: ${responseBody.valid}`);
  }
  if (responseBody.executed !== undefined) {
    console.log(`✅ Executed: ${responseBody.executed}`);
  }
  if (responseBody.automation_id) {
    console.log(`✅ Automation ID: ${responseBody.automation_id}`);
  }
  if (responseBody.validation_details) {
    console.log(`Validation details:`, JSON.stringify(responseBody.validation_details, null, 2));
  }
  if (responseBody.quality_report) {
    console.log(`Quality report:`, JSON.stringify(responseBody.quality_report, null, 2));
  }
  
  // Assertions
  expect(response.status()).toBeLessThan(500); // Should not be server error
});


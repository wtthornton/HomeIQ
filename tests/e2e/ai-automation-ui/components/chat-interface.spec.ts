import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

test.describe('AI Automation UI - Chat Interface Component', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/ha-agent');
    await waitForLoadingComplete(page);
  });

  test('Input field works', async ({ page }) => {
    const input = page.locator('textarea, input[type="text"]').first();
    await expect(input).toBeVisible({ timeout: 5000 });
    
    await input.fill('Test message');
    await expect(input).toHaveValue('Test message');
  });

  test('Send button works', async ({ page }) => {
    const input = page.locator('textarea, input[type="text"]').first();
    const sendButton = page.locator('button[type="submit"], button:has-text("Send")').first();
    
    await input.fill('Test');
    await sendButton.click();
    await page.waitForTimeout(2000);
  });

  test('Message display works', async ({ page }) => {
    const input = page.locator('textarea, input[type="text"]').first();
    const sendButton = page.locator('button[type="submit"], button:has-text("Send")').first();
    
    await input.fill('Test message');
    await sendButton.click();
    await page.waitForTimeout(2000);
    
    const messages = page.locator('[data-testid="message"], [class*="Message"]');
    await expect(messages.first()).toBeVisible({ timeout: 5000 });
  });
});

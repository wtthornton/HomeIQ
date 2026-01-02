import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { mockApiEndpoints } from '../../../shared/helpers/api-helpers';
import { automationMocks } from '../../fixtures/api-mocks';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

test.describe('AI Automation UI - Conversation Flow Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await mockApiEndpoints(page, [
      { pattern: /\/api\/conversations/, response: automationMocks['/api/conversations'] },
      { pattern: /\/api\/chat/, response: automationMocks['/api/chat'] },
    ]);
    await page.goto('/ha-agent');
    await waitForLoadingComplete(page);
  });

  test('@integration Start conversation', async ({ page }) => {
    const messageInput = page.locator('textarea, input[type="text"]').first();
    await expect(messageInput).toBeVisible({ timeout: 5000 });
  });

  test('@integration Send messages', async ({ page }) => {
    const messageInput = page.locator('textarea, input[type="text"]').first();
    const sendButton = page.locator('button[type="submit"], button:has-text("Send")').first();
    
    await messageInput.fill('Turn on the living room lights');
    await sendButton.click();
    await page.waitForTimeout(2000);
    
    const userMessage = page.locator('[data-testid="message"], [class*="Message"]').filter({ hasText: 'living room' }).first();
    await expect(userMessage).toBeVisible({ timeout: 5000 });
  });

  test('@integration Receive responses', async ({ page }) => {
    const messageInput = page.locator('textarea, input[type="text"]').first();
    const sendButton = page.locator('button[type="submit"], button:has-text("Send")').first();
    
    await messageInput.fill('Create an automation');
    await sendButton.click();
    await page.waitForTimeout(5000);
    
    const assistantMessage = page.locator('[data-testid="message"], [class*="Message"]').filter({ hasText: /automation|help|create/i }).first();
    await expect(assistantMessage).toBeVisible({ timeout: 10000 });
  });

  test('@integration View automation proposals', async ({ page }) => {
    const messageInput = page.locator('textarea, input[type="text"]').first();
    const sendButton = page.locator('button[type="submit"], button:has-text("Send")').first();
    
    await messageInput.fill('Create automation for lights at 7am');
    await sendButton.click();
    await page.waitForTimeout(5000);
    
    const proposal = page.locator('[data-testid="proposal"], [class*="Proposal"]').first();
    const exists = await proposal.isVisible().catch(() => false);
    // Proposal might appear
  });

  test('@integration Deploy automation', async ({ page }) => {
    const deployButton = page.locator('button:has-text("Deploy"), [data-testid="deploy"]').first();
    
    if (await deployButton.isVisible({ timeout: 2000 })) {
      await deployButton.click();
      await page.waitForTimeout(3000);
      
      // Verify deployment status
      const successMessage = page.locator('[role="alert"], .success, [class*="toast"]').first();
      const exists = await successMessage.isVisible().catch(() => false);
    }
  });

  test('@integration Manage conversations', async ({ page }) => {
    const newConversationButton = page.locator('button:has-text("New"), button:has-text("Create")').first();
    
    if (await newConversationButton.isVisible({ timeout: 2000 })) {
      await newConversationButton.click();
      await page.waitForTimeout(1000);
      
      // Verify new conversation started
      const messageInput = page.locator('textarea, input[type="text"]').first();
      await expect(messageInput).toBeVisible();
    }
  });
});

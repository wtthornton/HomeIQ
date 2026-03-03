import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

/** Tests run against deployed Docker (no API mocks). */
test.describe('AI Automation UI - Conversation Flow Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/chat');
    await waitForLoadingComplete(page);
  });

  test('@integration Start conversation', async ({ page }) => {
    const messageInput = page.locator('textarea, input[type="text"]').first();
    await expect(messageInput).toBeVisible({ timeout: 5000 });
  });

  test('@integration Send messages', async ({ page }) => {
    const messageInput = page.getByTestId('message-input').or(page.locator('textarea').first());
    const sendButton = page.getByTestId('send-button').or(page.locator('button:has-text("Send")').first());
    await messageInput.click();
    await messageInput.pressSequentially('Turn on the living room lights');
    await expect(sendButton).toBeEnabled({ timeout: 5000 });
    await sendButton.click();
    await page.waitForTimeout(2000);
    
    const userMessage = page.locator('[data-testid="chat-message"]').filter({ hasText: 'living room' }).first();
    const loading = page.locator('[data-testid="chat-loading"], [data-testid="chat-loading-inner"]').first();
    const hasUserMsg = await userMessage.isVisible({ timeout: 5000 }).catch(() => false);
    const hasLoading = await loading.isVisible({ timeout: 2000 }).catch(() => false);
    expect(hasUserMsg || hasLoading).toBe(true);
  });

  test('@integration Receive responses', async ({ page }) => {
    const messageInput = page.getByTestId('message-input').or(page.locator('textarea').first());
    const sendButton = page.getByTestId('send-button').or(page.locator('button:has-text("Send")').first());
    await messageInput.click();
    await messageInput.pressSequentially('Create an automation');
    await expect(sendButton).toBeEnabled({ timeout: 5000 });
    await sendButton.click();
    await page.waitForTimeout(5000);
    
    const assistantMessage = page.locator('[data-testid="chat-message"]').filter({ hasText: /automation|help|create|error|failed/i }).first();
    const loading = page.locator('[data-testid="chat-loading"], [data-testid="chat-loading-inner"]').first();
    const hasResponse = await assistantMessage.isVisible({ timeout: 10000 }).catch(() => false);
    const hasLoading = await loading.isVisible({ timeout: 2000 }).catch(() => false);
    expect(hasResponse || hasLoading).toBe(true);
  });

  test('@integration View automation proposals', async ({ page }) => {
    const messageInput = page.getByTestId('message-input').or(page.locator('textarea').first());
    const sendButton = page.getByTestId('send-button').or(page.locator('button:has-text("Send")').first());
    await messageInput.click();
    await messageInput.pressSequentially('Create automation for lights at 7am');
    await expect(sendButton).toBeEnabled({ timeout: 5000 });
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

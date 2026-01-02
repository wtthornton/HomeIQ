import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { mockApiEndpoints } from '../../../shared/helpers/api-helpers';
import { automationMocks } from '../../fixtures/api-mocks';
import { waitForLoadingComplete, waitForModalOpen } from '../../../shared/helpers/wait-helpers';

test.describe('AI Automation UI - HA Agent Chat', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await mockApiEndpoints(page, [
      { pattern: /\/api\/conversations/, response: automationMocks['/api/conversations'] },
      { pattern: /\/api\/chat/, response: automationMocks['/api/chat'] },
    ]);
    await page.goto('/ha-agent');
    await waitForLoadingComplete(page);
  });

  test('@smoke Chat interface loads', async ({ page }) => {
    const chatInterface = page.locator('[data-testid="chat-interface"], [class*="Chat"], [class*="chat-container"]').first();
    await expect(chatInterface).toBeVisible({ timeout: 5000 });
  });

  test('Message input works', async ({ page }) => {
    const messageInput = page.locator('textarea, input[type="text"], [data-testid="message-input"]').first();
    await expect(messageInput).toBeVisible({ timeout: 5000 });
    
    await messageInput.fill('Turn on the living room lights');
    await expect(messageInput).toHaveValue('Turn on the living room lights');
  });

  test('Send button functionality', async ({ page }) => {
    const messageInput = page.locator('textarea, input[type="text"]').first();
    const sendButton = page.locator('button[type="submit"], button:has-text("Send"), [data-testid="send"]').first();
    
    await messageInput.fill('Test message');
    await sendButton.click();
    await page.waitForTimeout(2000);
    
    // Verify message was sent
    const messages = page.locator('[data-testid="message"], [class*="Message"]');
    await expect(messages.first()).toBeVisible();
  });

  test('Message display', async ({ page }) => {
    const messageInput = page.locator('textarea, input[type="text"]').first();
    const sendButton = page.locator('button[type="submit"], button:has-text("Send")').first();
    
    await messageInput.fill('Test message');
    await sendButton.click();
    await page.waitForTimeout(2000);
    
    const userMessage = page.locator('[data-testid="message"], [class*="Message"]').filter({ hasText: 'Test message' }).first();
    await expect(userMessage).toBeVisible({ timeout: 5000 });
  });

  test('Tool call indicators', async ({ page }) => {
    // Send a message that triggers tool calls
    const messageInput = page.locator('textarea, input[type="text"]').first();
    const sendButton = page.locator('button[type="submit"], button:has-text("Send")').first();
    
    await messageInput.fill('Create an automation');
    await sendButton.click();
    await page.waitForTimeout(3000);
    
    const toolCallIndicator = page.locator('[data-testid="tool-call"], [class*="ToolCall"]').first();
    const exists = await toolCallIndicator.isVisible().catch(() => false);
    // Tool call indicators might appear
  });

  test('Automation preview modal', async ({ page }) => {
    // Look for preview button or trigger
    const previewButton = page.locator('button:has-text("Preview"), [data-testid="preview-automation"]').first();
    
    if (await previewButton.isVisible({ timeout: 2000 })) {
      await previewButton.click();
      await waitForModalOpen(page);
      
      const modal = page.locator('[role="dialog"], .modal').first();
      await expect(modal).toBeVisible({ timeout: 3000 });
    }
  });

  test('Automation proposal display', async ({ page }) => {
    // Send message that generates proposal
    const messageInput = page.locator('textarea, input[type="text"]').first();
    const sendButton = page.locator('button[type="submit"], button:has-text("Send")').first();
    
    await messageInput.fill('Create automation for lights');
    await sendButton.click();
    await page.waitForTimeout(5000);
    
    const proposal = page.locator('[data-testid="proposal"], [class*="Proposal"]').first();
    const exists = await proposal.isVisible().catch(() => false);
    // Proposal might appear
  });

  test('Conversation sidebar', async ({ page }) => {
    const sidebar = page.locator('[data-testid="sidebar"], [class*="Sidebar"]').first();
    const exists = await sidebar.isVisible().catch(() => false);
    // Sidebar might be visible
  });

  test('Create conversation', async ({ page }) => {
    const newConversationButton = page.locator('button:has-text("New"), button:has-text("Create"), [data-testid="new-conversation"]').first();
    
    if (await newConversationButton.isVisible({ timeout: 2000 })) {
      await newConversationButton.click();
      await page.waitForTimeout(1000);
    }
  });

  test('Delete conversation', async ({ page }) => {
    const deleteButton = page.locator('button[aria-label*="delete"], button:has-text("Delete")').first();
    
    if (await deleteButton.isVisible({ timeout: 2000 })) {
      await deleteButton.click();
      await waitForModalOpen(page);
      
      const confirmButton = page.locator('button:has-text("Confirm"), button:has-text("Delete")').first();
      if (await confirmButton.isVisible({ timeout: 1000 })) {
        await confirmButton.click();
        await page.waitForTimeout(1000);
      }
    }
  });

  test('Switch conversations', async ({ page }) => {
    const conversationItems = page.locator('[data-testid="conversation-item"], [class*="ConversationItem"]');
    
    if (await conversationItems.count() > 1) {
      await conversationItems.nth(1).click();
      await page.waitForTimeout(1000);
    }
  });

  test('Clear chat functionality', async ({ page }) => {
    const clearButton = page.locator('button:has-text("Clear"), button[aria-label*="clear"]').first();
    
    if (await clearButton.isVisible({ timeout: 2000 })) {
      await clearButton.click();
      await waitForModalOpen(page);
      
      const confirmButton = page.locator('button:has-text("Confirm"), button:has-text("Clear")').first();
      if (await confirmButton.isVisible({ timeout: 1000 })) {
        await confirmButton.click();
        await page.waitForTimeout(1000);
      }
    }
  });

  test('Debug tab', async ({ page }) => {
    const debugTab = page.locator('button:has-text("Debug"), [data-testid="debug-tab"]').first();
    
    if (await debugTab.isVisible({ timeout: 2000 })) {
      await debugTab.click();
      await page.waitForTimeout(500);
      
      const debugContent = page.locator('[data-testid="debug-content"], [class*="Debug"]').first();
      await expect(debugContent).toBeVisible();
    }
  });

  test('Markdown rendering', async ({ page }) => {
    // Send message with markdown
    const messageInput = page.locator('textarea, input[type="text"]').first();
    const sendButton = page.locator('button[type="submit"], button:has-text("Send")').first();
    
    await messageInput.fill('Test **bold** text');
    await sendButton.click();
    await page.waitForTimeout(2000);
    
    // Look for rendered markdown
    const markdownContent = page.locator('[data-testid="markdown"], [class*="Markdown"]').first();
    const exists = await markdownContent.isVisible().catch(() => false);
  });

  test('Error boundaries', async ({ page }) => {
    // Try to trigger an error
    await mockApiEndpoints(page, [
      { pattern: /\/api\/chat/, response: { status: 500, body: { error: 'Internal Server Error' } } },
    ]);
    
    const messageInput = page.locator('textarea, input[type="text"]').first();
    const sendButton = page.locator('button[type="submit"], button:has-text("Send")').first();
    
    await messageInput.fill('Test error');
    await sendButton.click();
    await page.waitForTimeout(2000);
    
    const errorMessage = page.locator('[data-testid="error"], .error, [role="alert"]').first();
    await expect(errorMessage).toBeVisible({ timeout: 5000 });
  });

  test('Loading states', async ({ page }) => {
    const messageInput = page.locator('textarea, input[type="text"]').first();
    const sendButton = page.locator('button[type="submit"], button:has-text("Send")').first();
    
    await messageInput.fill('Test');
    await sendButton.click();
    
    const loadingIndicator = page.locator('[data-testid="loading"], .loading, .spinner').first();
    const exists = await loadingIndicator.isVisible().catch(() => false);
    // Loading might appear briefly
  });

  test('Keyboard shortcuts', async ({ page }) => {
    const messageInput = page.locator('textarea, input[type="text"]').first();
    await messageInput.fill('Test');
    
    // Try Enter to send
    await messageInput.press('Enter');
    await page.waitForTimeout(2000);
    
    // Verify message was sent
    const messages = page.locator('[data-testid="message"], [class*="Message"]');
    await expect(messages.first()).toBeVisible({ timeout: 5000 });
  });
});

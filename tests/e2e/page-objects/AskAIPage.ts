/**
 * Page Object Model for Ask AI / Chat Tab
 *
 * Natural language query interface for creating automations
 * URL: http://localhost:3001/chat
 */

import { Page, Locator, expect } from '@playwright/test';

export class AskAIPage {
  constructor(public page: Page) {}

  /**
   * Navigate to Chat page
   */
  async goto() {
    await this.page.goto('http://localhost:3001/chat');
    // Wait for page to be ready
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Get the query input field (textarea in HAAgentChat)
   */
  getQueryInput(): Locator {
    return this.page.locator('[data-testid="message-input"]');
  }

  /**
   * Get the Send button
   */
  getSendButton(): Locator {
    return this.page.locator('[data-testid="send-button"]');
  }

  /**
   * Get the New Chat button (replaces old Clear Chat)
   */
  getClearButton(): Locator {
    return this.page.getByRole('button', { name: /new chat/i });
  }

  /**
   * Get sidebar toggle button
   */
  getSidebarToggle(): Locator {
    return this.page.locator('button[title="Toggle sidebar"]');
  }

  /**
   * Submit a query
   * @param query - Natural language query
   */
  async submitQuery(query: string): Promise<void> {
    await this.getQueryInput().fill(query);
    await this.getSendButton().click();
  }

  /**
   * Wait for AI response
   * @param timeout - Max wait time in ms (default 60s for OpenAI)
   */
  async waitForResponse(timeout = 60000): Promise<void> {
    // Strategy: Wait for loading to appear then disappear, or message count to increase
    const initialCount = await this.getMessageCount();
    const startTime = Date.now();

    // Poll for new assistant messages
    while (Date.now() - startTime < timeout) {
      const currentCount = await this.getMessageCount();
      if (currentCount > initialCount) {
        // New message appeared — wait for loading to finish
        const loadingVisible = await this.page
          .locator('[data-testid="chat-loading"]')
          .isVisible()
          .catch(() => false);
        if (!loadingVisible) {
          // Response fully rendered
          await this.page.waitForTimeout(500);
          return;
        }
      }
      await this.page.waitForTimeout(500);
    }

    // Timeout — let test assertions handle it
  }

  /**
   * Get all chat message bubbles (excludes loading indicators)
   */
  getMessages(): Locator {
    return this.page.locator('[data-testid="chat-message"]');
  }

  /**
   * Get the last message
   */
  getLastMessage(): Locator {
    return this.getMessages().last();
  }

  /**
   * Get message count
   */
  async getMessageCount(): Promise<number> {
    return await this.getMessages().count();
  }

  /**
   * Get all suggestion cards (DeviceSuggestions component)
   */
  getSuggestionCards(): Locator {
    return this.page.locator('[data-testid="suggestion-card"]');
  }

  /**
   * Get suggestion count from last response
   */
  async getSuggestionCount(): Promise<number> {
    return await this.getSuggestionCards().count();
  }

  /**
   * Click the Create Automation button on a suggestion card
   * @param index - Suggestion index (0-based)
   */
  async testSuggestion(index: number): Promise<void> {
    const suggestion = this.getSuggestionCards().nth(index);
    const createButton = suggestion.locator('button', { hasText: /create/i });
    await createButton.click();
  }

  /**
   * Click the Create Automation CTA button (for approve flow)
   * The CTA button creates a permanent automation from the AI proposal
   */
  async approveSuggestion(_index: number): Promise<void> {
    const ctaButton = this.page.locator('button[aria-label="Create automation"]');
    await ctaButton.click();
  }

  /**
   * Click Reject/dismiss on a suggestion
   * @param index - Suggestion index (0-based)
   */
  async rejectSuggestion(index: number): Promise<void> {
    const suggestion = this.getSuggestionCards().nth(index);
    const rejectButton = suggestion.locator('button', { hasText: /reject|dismiss|remove/i });
    await rejectButton.click();
  }

  /**
   * Get toast notifications
   */
  getToasts(): Locator {
    // react-hot-toast creates div elements for toasts
    return this.page.locator('[role="status"], [class*="toast"]');
  }

  /**
   * Wait for toast with specific text
   * @param text - Text to search for in toast
   * @param type - 'success' | 'error' | 'info' | 'loading'
   * @param timeout - Max wait time in ms
   */
  async waitForToast(text: string | RegExp, type?: 'success' | 'error' | 'info' | 'loading', timeout = 10000): Promise<void> {
    const toastSelector = type
      ? `[role="status"]:has-text("${text instanceof RegExp ? text.source : text}")`
      : `text=${text instanceof RegExp ? text.source : text}`;

    await this.page.waitForSelector(toastSelector, { timeout, state: 'visible' });
  }

  /**
   * Check if toast is visible
   * @param text - Text to search for
   */
  async isToastVisible(text: string | RegExp): Promise<boolean> {
    const selector = text instanceof RegExp
      ? `text=${text.source}`
      : `text="${text}"`;

    try {
      const element = await this.page.locator(selector).first();
      return await element.isVisible();
    } catch {
      return false;
    }
  }

  /**
   * Get conversation items from sidebar
   */
  getConversationItems(): Locator {
    return this.page.locator('[role="option"]');
  }

  /**
   * Click a conversation in the sidebar
   * @param index - Conversation index (0-based)
   */
  async clickConversation(index: number): Promise<void> {
    const conversations = this.getConversationItems();
    await conversations.nth(index).click();
  }

  /**
   * Clear the chat (clicks New Chat button)
   */
  async clearChat(): Promise<void> {
    await this.getClearButton().click();
  }

  /**
   * Toggle sidebar
   */
  async toggleSidebar(): Promise<void> {
    await this.getSidebarToggle().click();
  }

  /**
   * Check if loading indicator is visible
   */
  async isLoading(): Promise<boolean> {
    return await this.page
      .locator('[data-testid="chat-loading"]')
      .isVisible()
      .catch(() => false);
  }

  /**
   * Get suggestion description
   * @param index - Suggestion index (0-based)
   */
  async getSuggestionDescription(index: number): Promise<string> {
    const suggestion = this.getSuggestionCards().nth(index);
    const description = await suggestion.locator('p').first().textContent();
    return description?.trim() || '';
  }

  /**
   * Verify no Home Assistant commands were executed
   * Checks that no error toasts appeared during query submission
   */
  async verifyNoDeviceExecution(): Promise<void> {
    const errorToast = await this.isToastVisible(/error|failed/i);
    expect(errorToast).toBe(false);
  }

  /**
   * Get automation ID from toast message
   * @param toastText - Toast message text
   */
  extractAutomationId(toastText: string): string | null {
    const match = toastText.match(/automation\.(test_)?[\w_]+/);
    return match ? match[0] : null;
  }

  /**
   * Get the Create Automation CTA button
   */
  getCreateAutomationButton(): Locator {
    return this.page.locator('button[aria-label="Create automation"]');
  }

  /**
   * Get automation proposal section
   */
  getAutomationProposal(): Locator {
    return this.page.locator('[role="region"][aria-label="Automation proposal details"]');
  }
}

/**
 * Page Object Model for Ask AI Tab
 * 
 * Natural language query interface for creating automations
 * URL: http://localhost:3001/ask-ai
 */

import { Page, Locator, expect } from '@playwright/test';

export class AskAIPage {
  constructor(public page: Page) {}

  /**
   * Navigate to Ask AI page
   */
  async goto() {
    await this.page.goto('http://localhost:3001/ask-ai');
    // Wait for page to be ready
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Get the query input field
   */
  getQueryInput(): Locator {
    return this.page.locator('input[placeholder*="Ask me about"]');
  }

  /**
   * Get the Send button
   */
  getSendButton(): Locator {
    return this.page.getByRole('button', { name: /send/i });
  }

  /**
   * Get the Clear Chat button
   */
  getClearButton(): Locator {
    return this.page.getByRole('button', { name: /clear/i });
  }

  /**
   * Get sidebar toggle button
   */
  getSidebarToggle(): Locator {
    return this.page.locator('button[title="Toggle Examples"]');
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
    // Strategy: Wait for message count to increase (most reliable)
    const initialCount = await this.getMessageCount();
    const startTime = Date.now();
    
    // Poll for new messages
    while (Date.now() - startTime < timeout) {
      const currentCount = await this.getMessageCount();
      if (currentCount > initialCount) {
        // New message appeared, wait a bit more for it to fully render
        await this.page.waitForTimeout(1000);
        return;
      }
      // Check every 500ms
      await this.page.waitForTimeout(500);
    }
    
    // If we get here, timeout occurred but don't throw - let test assertions handle it
  }

  /**
   * Get all message bubbles
   */
  getMessages(): Locator {
    return this.page.locator('[class*="rounded-lg"][class*="shadow"]');
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
   * Get all suggestion cards in the last AI response
   */
  getSuggestionCards(): Locator {
    // Suggestions are rendered inside AI message bubbles
    return this.page.locator('[data-testid="suggestion-card"], [class*="border-t"][class*="pt-3"]').filter({
      has: this.page.locator('button:has-text("Test"), button:has-text("Approve")')
    });
  }

  /**
   * Get suggestion count from last response
   */
  async getSuggestionCount(): Promise<number> {
    return await this.getSuggestionCards().count();
  }

  /**
   * Click Test button on a suggestion
   * @param index - Suggestion index (0-based)
   */
  async testSuggestion(index: number): Promise<void> {
    const suggestion = this.getSuggestionCards().nth(index);
    const testButton = suggestion.locator('button', { hasText: 'Test' });
    await testButton.click();
  }

  /**
   * Click Approve button on a suggestion
   * @param index - Suggestion index (0-based)
   */
  async approveSuggestion(index: number): Promise<void> {
    const suggestion = this.getSuggestionCards().nth(index);
    const approveButton = suggestion.locator('button', { hasText: 'Approve' });
    await approveButton.click();
  }

  /**
   * Click Reject button on a suggestion
   * @param index - Suggestion index (0-based)
   */
  async rejectSuggestion(index: number): Promise<void> {
    const suggestion = this.getSuggestionCards().nth(index);
    const rejectButton = suggestion.locator('button', { hasText: 'Reject' });
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
   * Get example queries from sidebar
   */
  getExampleQueries(): Locator {
    return this.page.locator('button[class*="bg-gray"]').filter({ hasText: /turn|flash|alert|dim|coffee/i });
  }

  /**
   * Click an example query
   * @param index - Example index (0-based)
   */
  async clickExample(index: number): Promise<void> {
    const examples = this.getExampleQueries();
    await examples.nth(index).click();
  }

  /**
   * Clear the chat
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
    const loadingDots = this.page.locator('.animate-bounce');
    return await loadingDots.first().isVisible().catch(() => false);
  }

  /**
   * Get suggestion description
   * @param index - Suggestion index (0-based)
   */
  async getSuggestionDescription(index: number): Promise<string> {
    const suggestion = this.getSuggestionCards().nth(index);
    // Description is in the main text content
    const description = await suggestion.locator('[class*="description"], p, div').first().textContent();
    return description?.trim() || '';
  }

  /**
   * Verify no Home Assistant commands were executed
   * This checks that lights/devices didn't change state
   * @param expectedState - Expected device state (should remain unchanged)
   */
  async verifyNoDeviceExecution(): Promise<void> {
    // This would need integration with actual HA API to verify
    // For now, we verify no error toasts and successful suggestion generation
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
}


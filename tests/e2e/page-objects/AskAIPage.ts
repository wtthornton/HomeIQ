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
   * Get sidebar toggle button (hamburger menu or close button)
   */
  getSidebarToggle(): Locator {
    // ConversationSidebar: mobile toggle "☰" or close "✕" button
    return this.page.locator('button:has-text("☰"), button:has-text("✕")').first();
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
   * Wait for AI response (assistant message to appear and loading to finish)
   * @param timeout - Max wait time in ms (default 60s for OpenAI)
   */
  async waitForResponse(timeout = 60000): Promise<void> {
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
   * Get only assistant messages
   */
  getAssistantMessages(): Locator {
    return this.page.locator('[data-testid="chat-message"][data-role="assistant"]');
  }

  /**
   * Get the last message
   */
  getLastMessage(): Locator {
    return this.getMessages().last();
  }

  /**
   * Get the last assistant message
   */
  getLastAssistantMessage(): Locator {
    return this.getAssistantMessages().last();
  }

  /**
   * Get message count
   */
  async getMessageCount(): Promise<number> {
    return await this.getMessages().count();
  }

  /**
   * Get assistant message count
   */
  async getAssistantMessageCount(): Promise<number> {
    return await this.getAssistantMessages().count();
  }

  // ── Automation Proposals (chat flow) ──────────────────────────────────

  /**
   * Get all automation proposal sections rendered in assistant messages
   */
  getAutomationProposals(): Locator {
    return this.page.locator('[data-testid="automation-proposal"]');
  }

  /**
   * Get automation proposal count
   */
  async getProposalCount(): Promise<number> {
    return await this.getAutomationProposals().count();
  }

  /**
   * Get the Create Automation CTA button(s)
   */
  getCreateAutomationButtons(): Locator {
    return this.page.locator('[data-testid="cta-create-button"]');
  }

  /**
   * Click the first visible Create Automation CTA button
   */
  async clickCreateAutomation(): Promise<void> {
    const ctaButton = this.getCreateAutomationButtons().first();
    await ctaButton.scrollIntoViewIfNeeded();
    await ctaButton.click();
  }

  /**
   * Check if the AI responded with automation content (proposal or YAML)
   */
  async hasAutomationResponse(): Promise<boolean> {
    const proposalCount = await this.getProposalCount();
    if (proposalCount > 0) return true;

    // Also check for Preview Automation buttons (YAML detected in message)
    const previewButtons = await this.page
      .locator('button:has-text("Preview Automation")')
      .count();
    return previewButtons > 0;
  }

  /**
   * Wait for an automation response (proposal or CTA button to appear)
   * @param timeout - Max wait time in ms
   */
  async waitForAutomationResponse(timeout = 60000): Promise<void> {
    // Wait for either an automation proposal or a CTA create button
    await this.page
      .locator('[data-testid="automation-proposal"], [data-testid="cta-create-button"], button:has-text("Preview Automation")')
      .first()
      .waitFor({ state: 'visible', timeout });
  }

  // ── Suggestion Cards (DeviceSuggestions panel) ────────────────────────

  /**
   * Get all suggestion cards (DeviceSuggestions panel — requires device selection)
   */
  getSuggestionCards(): Locator {
    return this.page.locator('[data-testid="suggestion-card"]');
  }

  /**
   * Get suggestion count (from DeviceSuggestions panel)
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
   * Works with both chat CTA buttons and suggestion card approve buttons
   */
  async approveSuggestion(_index: number): Promise<void> {
    await this.clickCreateAutomation();
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

  // ── Toasts ────────────────────────────────────────────────────────────

  /**
   * Get toast notifications
   */
  getToasts(): Locator {
    return this.page.locator('[role="status"], [class*="toast"]');
  }

  /**
   * Wait for toast with specific text (supports regex)
   * @param text - Text or regex to match
   * @param type - Optional toast type filter
   * @param timeout - Max wait time in ms
   */
  async waitForToast(text: string | RegExp, type?: 'success' | 'error' | 'info' | 'loading', timeout = 10000): Promise<void> {
    if (text instanceof RegExp) {
      // Use locator filter for regex matching
      const locator = this.getToasts().filter({ hasText: text });
      await locator.first().waitFor({ state: 'visible', timeout });
    } else {
      const selector = type
        ? `[role="status"]:has-text("${text}")`
        : `text="${text}"`;
      await this.page.waitForSelector(selector, { timeout, state: 'visible' });
    }
  }

  /**
   * Check if toast is visible
   * @param text - Text to search for
   */
  async isToastVisible(text: string | RegExp): Promise<boolean> {
    try {
      if (text instanceof RegExp) {
        const locator = this.getToasts().filter({ hasText: text });
        return await locator.first().isVisible();
      }
      return await this.page.locator(`text="${text}"`).first().isVisible();
    } catch {
      return false;
    }
  }

  // ── Sidebar ───────────────────────────────────────────────────────────

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
   * Toggle sidebar open/closed
   */
  async toggleSidebar(): Promise<void> {
    await this.getSidebarToggle().click();
  }

  /**
   * Check if sidebar is open (heading "Conversations" visible)
   */
  async isSidebarOpen(): Promise<boolean> {
    return await this.page
      .locator('h2:has-text("Conversations")')
      .isVisible()
      .catch(() => false);
  }

  // ── Loading & state ───────────────────────────────────────────────────

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
   * Get suggestion description (from DeviceSuggestions panel)
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
   * Get the Create Automation CTA button (first visible)
   */
  getCreateAutomationButton(): Locator {
    return this.page.locator('[data-testid="cta-create-button"]').first();
  }

  /**
   * Get automation proposal section (first visible)
   */
  getAutomationProposal(): Locator {
    return this.page.locator('[data-testid="automation-proposal"]').first();
  }
}

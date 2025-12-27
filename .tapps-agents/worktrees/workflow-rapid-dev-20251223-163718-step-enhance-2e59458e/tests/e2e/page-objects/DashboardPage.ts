/**
 * Page Object Model for AI Automation Dashboard Page
 * 
 * Main suggestion browsing, filtering, and approval interface
 * URL: http://localhost:3001/
 */

import { Page, Locator, expect } from '@playwright/test';

export class DashboardPage {
  constructor(private page: Page) {}

  /**
   * Navigate to AI Automation Dashboard
   */
  async goto() {
    await this.page.goto('http://localhost:3001');
    // Wait for page to be ready
    await expect(this.page.getByTestId('dashboard-container')).toBeVisible();
  }

  /**
   * Get all suggestion cards
   * @returns Locator for suggestion cards
   */
  async getSuggestionCards(): Promise<Locator> {
    return this.page.getByTestId('suggestion-card');
  }

  /**
   * Get count of visible suggestions
   * @returns Number of suggestions
   */
  async getSuggestionCount(): Promise<number> {
    const cards = await this.getSuggestionCards();
    return await cards.count();
  }

  /**
   * Get suggestion ID by index
   * @param index - Index of suggestion (0-based)
   * @returns Suggestion ID
   */
  async getSuggestionId(index: number): Promise<string | null> {
    const card = (await this.getSuggestionCards()).nth(index);
    return await card.getAttribute('data-id');
  }

  /**
   * Approve a suggestion by index
   * @param index - Index of suggestion to approve (0-based)
   */
  async approveSuggestion(index: number): Promise<void> {
    const card = (await this.getSuggestionCards()).nth(index);
    await card.getByRole('button', { name: 'Approve' }).click();
  }

  /**
   * Reject a suggestion by index
   * Opens the feedback modal
   * @param index - Index of suggestion to reject (0-based)
   */
  async rejectSuggestion(index: number): Promise<void> {
    const card = (await this.getSuggestionCards()).nth(index);
    await card.getByRole('button', { name: 'Reject' }).click();
  }

  /**
   * Deploy an approved suggestion
   * @param id - Suggestion ID to deploy
   */
  async deploySuggestion(id: string): Promise<void> {
    const deployButton = this.page.getByTestId(`deploy-${id}`);
    await deployButton.click();
  }

  /**
   * Filter suggestions by category
   * @param category - Category to filter by
   */
  async filterByCategory(category: 'energy' | 'comfort' | 'security' | 'convenience'): Promise<void> {
    await this.page.getByRole('combobox', { name: 'Category' }).selectOption(category);
    // Wait for filtered results
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Filter suggestions by confidence level
   * @param level - Confidence level to filter by
   */
  async filterByConfidence(level: 'high' | 'medium' | 'low'): Promise<void> {
    await this.page.getByRole('combobox', { name: 'Confidence' }).selectOption(level);
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Search suggestions by keyword
   * @param keyword - Search term
   */
  async searchSuggestions(keyword: string): Promise<void> {
    await this.page.getByPlaceholder('Search suggestions').fill(keyword);
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Get filter dropdown locator
   * @param name - Filter name
   * @returns Locator for filter
   */
  async getFilterDropdown(name: string): Promise<Locator> {
    return this.page.getByRole('combobox', { name });
  }

  /**
   * Expect specific number of suggestions
   * @param count - Expected count
   */
  async expectSuggestionCount(count: number): Promise<void> {
    const cards = await this.getSuggestionCards();
    await expect(cards).toHaveCount(count);
  }

  /**
   * Expect no suggestions displayed
   */
  async expectNoSuggestions(): Promise<void> {
    await expect(this.page.getByText('No suggestions available')).toBeVisible();
  }

  /**
   * Expect success toast message
   * @param message - Expected message (partial match)
   */
  async expectSuccessToast(message: string): Promise<void> {
    const toast = this.page.getByTestId('toast-success');
    await expect(toast).toBeVisible();
    await expect(toast).toContainText(message);
  }

  /**
   * Expect error toast message
   * @param message - Expected message (partial match)
   */
  async expectErrorToast(message: string): Promise<void> {
    const toast = this.page.getByTestId('toast-error');
    await expect(toast).toBeVisible();
    await expect(toast).toContainText(message);
  }
}


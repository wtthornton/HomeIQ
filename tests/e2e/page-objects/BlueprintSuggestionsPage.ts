/**
 * Page Object Model for Blueprint Suggestions Page
 * 
 * URL: http://localhost:3001/blueprint-suggestions
 * 
 * Provides methods to interact with the Blueprint Suggestions page:
 * - Navigation and page load
 * - Stats display
 * - Filters (min_score, use_case, status, blueprint_id)
 * - Suggestion cards (accept/decline)
 * - Generate form
 * - Delete all functionality
 * - Pagination
 */

import { Page, Locator, expect } from '@playwright/test';

export class BlueprintSuggestionsPage {
  constructor(public page: Page) {}

  /**
   * Navigate to Blueprint Suggestions page
   */
  async goto() {
    await this.page.goto('http://localhost:3001/blueprint-suggestions');
    await this.page.waitForLoadState('networkidle');
    // Wait for initial data to load
    await this.waitForPageReady();
  }

  /**
   * Wait for page to be ready (stats loaded, suggestions loaded or empty state)
   */
  async waitForPageReady() {
    // Wait for either stats to appear or loading to complete
    await Promise.race([
      this.page.waitForSelector('text=Total', { timeout: 5000 }).catch(() => null),
      this.page.waitForSelector('text=Loading suggestions...', { timeout: 5000 }).catch(() => null),
      this.page.waitForSelector('text=No suggestions found', { timeout: 5000 }).catch(() => null),
    ]);
    
    // Wait for loading to complete
    await this.page.waitForSelector('text=Loading suggestions...', { state: 'hidden', timeout: 10000 }).catch(() => null);
  }

  // ==================== Header Elements ====================

  /**
   * Get page title
   */
  getPageTitle(): Locator {
    return this.page.locator('h1:has-text("Blueprint Suggestions")');
  }

  /**
   * Get page description
   */
  getPageDescription(): Locator {
    return this.page.locator('text=Discover proven automations matched to your devices');
  }

  /**
   * Get Generate Suggestions button
   */
  getGenerateButton(): Locator {
    return this.page.getByRole('button', { name: /Generate Suggestions/i });
  }

  /**
   * Get Delete All button
   */
  getDeleteAllButton(): Locator {
    return this.page.getByRole('button', { name: /Delete All/i });
  }

  // ==================== Stats Section ====================

  /**
   * Get stats container
   */
  getStatsContainer(): Locator {
    return this.page.locator('text=Total').locator('..').locator('..');
  }

  /**
   * Get total suggestions stat
   */
  getTotalStat(): Locator {
    return this.page.locator('text=Total').locator('..').locator('..').locator('text=/\\d+/').first();
  }

  /**
   * Get pending count stat
   */
  getPendingStat(): Locator {
    return this.page.locator('text=Pending').locator('..').locator('..').locator('text=/\\d+/').first();
  }

  /**
   * Get accepted count stat
   */
  getAcceptedStat(): Locator {
    return this.page.locator('text=Accepted').locator('..').locator('..').locator('text=/\\d+/').first();
  }

  /**
   * Get average score stat
   */
  getAverageScoreStat(): Locator {
    return this.page.locator('text=Avg Score').locator('..').locator('..').locator('text=/\\d+%/').first();
  }

  // ==================== Generate Form ====================

  /**
   * Check if generate form is visible
   */
  async isGenerateFormVisible(): Promise<boolean> {
    return await this.page.locator('text=Generate Blueprint Suggestions').isVisible().catch(() => false);
  }

  /**
   * Toggle generate form visibility
   */
  async toggleGenerateForm() {
    await this.getGenerateButton().click();
  }

  /**
   * Get max suggestions input
   */
  getMaxSuggestionsInput(): Locator {
    return this.page.locator('label:has-text("Max Suggestions")').locator('..').locator('input[type="number"]');
  }

  /**
   * Get min score slider in generate form
   */
  getGenerateMinScoreSlider(): Locator {
    return this.page.locator('label:has-text("Min Score")').locator('..').locator('input[type="range"]');
  }

  /**
   * Get complexity select
   */
  getComplexitySelect(): Locator {
    return this.page.locator('label:has-text("Complexity")').locator('..').locator('select');
  }

  /**
   * Get use case select in generate form
   */
  getGenerateUseCaseSelect(): Locator {
    return this.page.locator('label:has-text("Use Case")').locator('..').locator('select');
  }

  /**
   * Get domain input
   */
  getDomainInput(): Locator {
    return this.page.locator('label:has-text("Domain")').locator('..').locator('input[type="text"]');
  }

  /**
   * Get min quality score input
   */
  getMinQualityScoreInput(): Locator {
    return this.page.locator('label:has-text("Min Quality Score")').locator('..').locator('input[type="number"]');
  }

  /**
   * Get Generate button in form
   */
  getFormGenerateButton(): Locator {
    return this.page.locator('button:has-text("Generate")').filter({ hasText: /^Generate$/ });
  }

  /**
   * Get Cancel button in form
   */
  getFormCancelButton(): Locator {
    return this.page.locator('button:has-text("Cancel")');
  }

  /**
   * Fill generate form
   */
  async fillGenerateForm(params: {
    maxSuggestions?: number;
    minScore?: number;
    complexity?: 'simple' | 'medium' | 'high';
    useCase?: 'convenience' | 'security' | 'energy' | 'comfort';
    domain?: string;
    minQualityScore?: number;
  }) {
    if (params.maxSuggestions !== undefined) {
      await this.getMaxSuggestionsInput().fill(params.maxSuggestions.toString());
    }
    if (params.minScore !== undefined) {
      await this.getGenerateMinScoreSlider().fill(params.minScore.toString());
    }
    if (params.complexity !== undefined) {
      await this.getComplexitySelect().selectOption(params.complexity);
    }
    if (params.useCase !== undefined) {
      await this.getGenerateUseCaseSelect().selectOption(params.useCase);
    }
    if (params.domain !== undefined) {
      await this.getDomainInput().fill(params.domain);
    }
    if (params.minQualityScore !== undefined) {
      await this.getMinQualityScoreInput().fill(params.minQualityScore.toString());
    }
  }

  /**
   * Submit generate form
   */
  async submitGenerateForm() {
    await this.getFormGenerateButton().click();
  }

  // ==================== Filters ====================

  /**
   * Get min score filter slider
   */
  getMinScoreFilter(): Locator {
    return this.page.locator('label:has-text("Min Score")').locator('..').locator('input[type="range"]').first();
  }

  /**
   * Get use case filter select
   */
  getUseCaseFilter(): Locator {
    return this.page.locator('label:has-text("Use Case")').locator('..').locator('select').first();
  }

  /**
   * Get status filter select
   */
  getStatusFilter(): Locator {
    return this.page.locator('label:has-text("Status")').locator('..').locator('select');
  }

  /**
   * Get blueprint ID filter input
   */
  getBlueprintIdFilter(): Locator {
    return this.page.locator('label:has-text("Blueprint ID")').locator('..').locator('input[type="text"]');
  }

  /**
   * Set min score filter
   */
  async setMinScoreFilter(value: number) {
    await this.getMinScoreFilter().fill(value.toString());
    // Wait for filter to apply
    await this.page.waitForTimeout(500);
  }

  /**
   * Set use case filter
   */
  async setUseCaseFilter(useCase: 'convenience' | 'security' | 'energy' | 'comfort' | '') {
    await this.getUseCaseFilter().selectOption(useCase || '');
    await this.page.waitForTimeout(500);
  }

  /**
   * Set status filter
   */
  async setStatusFilter(status: 'pending' | 'accepted' | 'declined' | '') {
    await this.getStatusFilter().selectOption(status || '');
    await this.page.waitForTimeout(500);
  }

  /**
   * Set blueprint ID filter
   */
  async setBlueprintIdFilter(blueprintId: string) {
    await this.getBlueprintIdFilter().fill(blueprintId);
    await this.page.waitForTimeout(500);
  }

  // ==================== Suggestions List ====================

  /**
   * Get loading indicator
   */
  getLoadingIndicator(): Locator {
    return this.page.locator('text=Loading suggestions...');
  }

  /**
   * Get empty state message
   */
  getEmptyState(): Locator {
    return this.page.locator('text=No suggestions found');
  }

  /**
   * Get all suggestion cards
   */
  getSuggestionCards(): Locator {
    // Suggestions are in cards with blueprint name as heading
    return this.page.locator('div').filter({ has: this.page.locator('h3') }).filter({ 
      has: this.page.locator('button:has-text("Accept"), button:has-text("Decline")') 
    });
  }

  /**
   * Get suggestion count
   */
  async getSuggestionCount(): Promise<number> {
    return await this.getSuggestionCards().count();
  }

  /**
   * Get suggestion card by index
   */
  getSuggestionCard(index: number): Locator {
    return this.getSuggestionCards().nth(index);
  }

  /**
   * Get suggestion blueprint name
   */
  getSuggestionBlueprintName(card: Locator): Locator {
    return card.locator('h3').first();
  }

  /**
   * Get suggestion description
   */
  getSuggestionDescription(card: Locator): Locator {
    return card.locator('p').first();
  }

  /**
   * Get suggestion score
   */
  getSuggestionScore(card: Locator): Locator {
    return card.locator('text=/Score:.*\\d+%/').first();
  }

  /**
   * Get suggestion use case badge
   */
  getSuggestionUseCase(card: Locator): Locator {
    return card.locator('text=/convenience|security|energy|comfort/i');
  }

  /**
   * Get Accept button for a suggestion
   */
  getAcceptButton(card: Locator): Locator {
    return card.locator('button:has-text("Accept")');
  }

  /**
   * Get Decline button for a suggestion
   */
  getDeclineButton(card: Locator): Locator {
    return card.locator('button:has-text("Decline")');
  }

  /**
   * Get matched devices section
   */
  getMatchedDevices(card: Locator): Locator {
    return card.locator('text=/Matched Devices/').locator('..');
  }

  /**
   * Get matched device badges
   */
  getMatchedDeviceBadges(card: Locator): Locator {
    return card.locator('text=/Matched Devices/').locator('..').locator('div').filter({ 
      hasText: /\\w+.*\\(\\w+\\)/ 
    });
  }

  /**
   * Accept a suggestion by index
   */
  async acceptSuggestion(index: number) {
    const card = this.getSuggestionCard(index);
    const acceptButton = this.getAcceptButton(card);
    await acceptButton.click();
  }

  /**
   * Decline a suggestion by index
   */
  async declineSuggestion(index: number) {
    const card = this.getSuggestionCard(index);
    const declineButton = this.getDeclineButton(card);
    await declineButton.click();
  }

  // ==================== Pagination ====================

  /**
   * Get pagination container
   */
  getPaginationContainer(): Locator {
    return this.page.locator('button:has-text("Previous"), button:has-text("Next")').first().locator('..').locator('..');
  }

  /**
   * Get Previous button
   */
  getPreviousButton(): Locator {
    return this.page.getByRole('button', { name: /Previous/i });
  }

  /**
   * Get Next button
   */
  getNextButton(): Locator {
    return this.page.getByRole('button', { name: /Next/i });
  }

  /**
   * Get pagination info text
   */
  getPaginationInfo(): Locator {
    return this.page.locator('text=/\\d+-\\d+ of \\d+/');
  }

  /**
   * Go to next page
   */
  async goToNextPage() {
    await this.getNextButton().click();
    await this.waitForPageReady();
  }

  /**
   * Go to previous page
   */
  async goToPreviousPage() {
    await this.getPreviousButton().click();
    await this.waitForPageReady();
  }

  // ==================== Toast Notifications ====================

  /**
   * Wait for toast notification
   */
  async waitForToast(message: string | RegExp, timeout = 5000) {
    const toast = this.page.locator('[role="status"], [class*="toast"]').filter({
      hasText: typeof message === 'string' ? message : message
    });
    await expect(toast).toBeVisible({ timeout });
    return toast;
  }

  /**
   * Wait for success toast
   */
  async waitForSuccessToast(message?: string | RegExp) {
    const pattern = message || /success|accepted|declined|generated|deleted/i;
    return await this.waitForToast(pattern);
  }

  /**
   * Wait for error toast
   */
  async waitForErrorToast(message?: string | RegExp) {
    const pattern = message || /error|failed/i;
    return await this.waitForToast(pattern);
  }

  // ==================== Delete All ====================

  /**
   * Delete all suggestions (with confirmation)
   */
  async deleteAllSuggestions(confirm = true) {
    // Set up dialog handler before clicking
    if (confirm) {
      this.page.once('dialog', async dialog => {
        expect(dialog.type()).toBe('confirm');
        await dialog.accept();
      });
    } else {
      this.page.once('dialog', async dialog => {
        await dialog.dismiss();
      });
    }
    
    await this.getDeleteAllButton().click();
  }

  // ==================== Helpers ====================

  /**
   * Wait for API response
   */
  async waitForApiResponse(urlPattern: string | RegExp, timeout = 10000) {
    await this.page.waitForResponse(
      response => {
        const url = response.url();
        const matches = typeof urlPattern === 'string' 
          ? url.includes(urlPattern)
          : urlPattern.test(url);
        return matches && response.status() === 200;
      },
      { timeout }
    );
  }

  /**
   * Wait for suggestions to load
   */
  async waitForSuggestionsToLoad() {
    // Wait for either suggestions to appear or empty state
    await Promise.race([
      this.getSuggestionCards().first().waitFor({ state: 'visible', timeout: 10000 }).catch(() => null),
      this.getEmptyState().waitFor({ state: 'visible', timeout: 10000 }).catch(() => null),
    ]);
    // Ensure loading is complete
    await this.getLoadingIndicator().waitFor({ state: 'hidden', timeout: 5000 }).catch(() => null);
  }

  /**
   * Get suggestion data from card
   */
  async getSuggestionData(index: number) {
    const card = this.getSuggestionCard(index);
    const name = await this.getSuggestionBlueprintName(card).textContent();
    const description = await this.getSuggestionDescription(card).textContent().catch(() => null);
    const scoreText = await this.getSuggestionScore(card).textContent();
    const score = scoreText ? parseInt(scoreText.match(/\d+/)![0]) : null;
    const useCase = await this.getSuggestionUseCase(card).textContent().catch(() => null);
    const acceptButton = this.getAcceptButton(card);
    const declineButton = this.getDeclineButton(card);
    const isAcceptEnabled = await acceptButton.isEnabled();
    const isDeclineEnabled = await declineButton.isEnabled();
    const matchedDevicesCount = await this.getMatchedDeviceBadges(card).count();

    return {
      name,
      description,
      score,
      useCase,
      isAcceptEnabled,
      isDeclineEnabled,
      matchedDevicesCount,
    };
  }
}

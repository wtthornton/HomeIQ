/**
 * Page Object Model for AI Automation Settings Page
 * 
 * Configuration management interface
 * URL: http://localhost:3001/settings
 */

import { Page, Locator, expect } from '@playwright/test';

export class SettingsPage {
  constructor(private page: Page) {}

  /**
   * Navigate to Settings page
   */
  async goto() {
    await this.page.goto('http://localhost:3001/settings');
    await expect(this.page.getByTestId('settings-container')).toBeVisible();
  }

  /**
   * Update OpenAI API key
   * @param apiKey - API key
   */
  async updateOpenAIKey(apiKey: string): Promise<void> {
    await this.page.getByLabel('OpenAI API Key').fill(apiKey);
  }

  /**
   * Update Home Assistant URL
   * @param url - HA URL
   */
  async updateHomeAssistantURL(url: string): Promise<void> {
    await this.page.getByLabel('Home Assistant URL').fill(url);
  }

  /**
   * Update Home Assistant access token
   * @param token - Access token
   */
  async updateHomeAssistantToken(token: string): Promise<void> {
    await this.page.getByLabel('Access Token').fill(token);
  }

  /**
   * Update analysis schedule
   * @param schedule - Cron schedule
   */
  async updateAnalysisSchedule(schedule: string): Promise<void> {
    await this.page.getByLabel('Analysis Schedule').fill(schedule);
  }

  /**
   * Toggle auto-deploy setting
   */
  async toggleAutoDeploy(): Promise<void> {
    await this.page.getByRole('checkbox', { name: 'Auto Deploy' }).click();
  }

  /**
   * Save settings
   */
  async saveSettings(): Promise<void> {
    await this.page.getByRole('button', { name: 'Save Settings' }).click();
  }

  /**
   * Reset settings to defaults
   */
  async resetSettings(): Promise<void> {
    await this.page.getByRole('button', { name: 'Reset to Defaults' }).click();
    
    // Confirm reset if modal appears
    const confirmButton = this.page.getByRole('button', { name: 'Confirm' });
    if (await confirmButton.isVisible()) {
      await confirmButton.click();
    }
  }

  /**
   * Get settings form
   * @returns Locator for settings form
   */
  async getSettingsForm(): Promise<Locator> {
    return this.page.getByTestId('settings-form');
  }

  /**
   * Expect success toast
   * @param message - Expected message
   */
  async expectSuccessToast(message: string): Promise<void> {
    const toast = this.page.getByTestId('toast-success');
    await expect(toast).toBeVisible();
    await expect(toast).toContainText(message);
  }

  /**
   * Expect error toast
   * @param message - Expected message
   */
  async expectErrorToast(message: string): Promise<void> {
    const toast = this.page.getByTestId('toast-error');
    await expect(toast).toBeVisible();
    await expect(toast).toContainText(message);
  }

  /**
   * Expect field value
   * @param label - Field label
   * @param value - Expected value
   */
  async expectFieldValue(label: string, value: string): Promise<void> {
    const field = this.page.getByLabel(label);
    await expect(field).toHaveValue(value);
  }
}


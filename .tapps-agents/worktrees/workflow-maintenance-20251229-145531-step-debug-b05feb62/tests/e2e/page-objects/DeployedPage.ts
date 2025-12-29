/**
 * Page Object Model for AI Automation Deployed Page
 * 
 * Deployed automations management interface
 * URL: http://localhost:3001/deployed
 */

import { Page, Locator, expect } from '@playwright/test';

export class DeployedPage {
  constructor(private page: Page) {}

  /**
   * Navigate to Deployed page
   */
  async goto() {
    await this.page.goto('http://localhost:3001/deployed');
    await expect(this.page.getByTestId('deployed-container')).toBeVisible();
  }

  /**
   * Get all deployed automation items
   * @returns Locator for deployed automations
   */
  async getDeployedAutomations(): Promise<Locator> {
    return this.page.getByTestId('deployed-automation');
  }

  /**
   * Get count of deployed automations
   * @returns Number of deployed automations
   */
  async getDeployedCount(): Promise<number> {
    const automations = await this.getDeployedAutomations();
    return await automations.count();
  }

  /**
   * Get deployed automation by ID
   * @param id - Automation ID
   * @returns Locator for specific automation
   */
  async getDeployedAutomationById(id: string): Promise<Locator> {
    return this.page.getByTestId(`deployed-automation-${id}`);
  }

  /**
   * Disable a deployed automation
   * @param index - Index of automation (0-based)
   */
  async disableAutomation(index: number): Promise<void> {
    const automation = (await this.getDeployedAutomations()).nth(index);
    await automation.getByRole('button', { name: 'Disable' }).click();
  }

  /**
   * Enable a deployed automation
   * @param index - Index of automation (0-based)
   */
  async enableAutomation(index: number): Promise<void> {
    const automation = (await this.getDeployedAutomations()).nth(index);
    await automation.getByRole('button', { name: 'Enable' }).click();
  }

  /**
   * Delete a deployed automation
   * @param index - Index of automation (0-based)
   */
  async deleteAutomation(index: number): Promise<void> {
    const automation = (await this.getDeployedAutomations()).nth(index);
    await automation.getByRole('button', { name: 'Delete' }).click();
    
    // Confirm deletion if modal appears
    const confirmButton = this.page.getByRole('button', { name: 'Confirm' });
    if (await confirmButton.isVisible()) {
      await confirmButton.click();
    }
  }

  /**
   * Expect automation count
   * @param count - Expected count
   */
  async expectAutomationCount(count: number): Promise<void> {
    const automations = await this.getDeployedAutomations();
    await expect(automations).toHaveCount(count);
  }

  /**
   * Expect no deployed automations
   */
  async expectNoAutomations(): Promise<void> {
    await expect(this.page.getByText('No deployed automations')).toBeVisible();
  }

  /**
   * Expect automation is visible
   * @param id - Automation ID
   */
  async expectAutomationVisible(id: string): Promise<void> {
    const automation = await this.getDeployedAutomationById(id);
    await expect(automation).toBeVisible();
  }
}


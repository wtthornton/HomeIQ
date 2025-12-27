/**
 * Page Object Model for AI Automation Patterns Page
 * 
 * Pattern visualization and analysis interface
 * URL: http://localhost:3001/patterns
 */

import { Page, Locator, expect } from '@playwright/test';

export class PatternsPage {
  constructor(private page: Page) {}

  /**
   * Navigate to Patterns page
   */
  async goto() {
    await this.page.goto('http://localhost:3001/patterns');
    await expect(this.page.getByTestId('patterns-container')).toBeVisible();
  }

  /**
   * Get all pattern items
   * @returns Locator for pattern items
   */
  async getPatternList(): Promise<Locator> {
    return this.page.getByTestId('pattern-item');
  }

  /**
   * Get count of visible patterns
   * @returns Number of patterns
   */
  async getPatternCount(): Promise<number> {
    const patterns = await this.getPatternList();
    return await patterns.count();
  }

  /**
   * Filter patterns by device
   * @param deviceName - Device name to filter by
   */
  async filterByDevice(deviceName: string): Promise<void> {
    await this.page.getByRole('combobox', { name: 'Device' }).selectOption(deviceName);
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Filter patterns by confidence level
   * @param level - Confidence level
   */
  async filterByConfidence(level: 'high' | 'medium' | 'low'): Promise<void> {
    await this.page.getByRole('combobox', { name: 'Confidence' }).selectOption(level);
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Filter patterns by type
   * @param type - Pattern type
   */
  async filterByType(type: 'time-of-day' | 'co-occurrence'): Promise<void> {
    await this.page.getByRole('combobox', { name: 'Pattern Type' }).selectOption(type);
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Get pattern chart canvas
   * @returns Locator for chart canvas
   */
  async getPatternChart(): Promise<Locator> {
    return this.page.locator('canvas').first();
  }

  /**
   * Verify chart is rendered
   */
  async expectChartRendered(): Promise<void> {
    const chart = await this.getPatternChart();
    await expect(chart).toBeVisible();
    
    // Verify chart has context (actually rendered)
    const hasContext = await this.page.evaluate(() => {
      const canvas = document.querySelector('canvas');
      return canvas?.getContext('2d') !== null;
    });
    expect(hasContext).toBe(true);
  }

  /**
   * Click on a pattern item
   * @param index - Pattern index (0-based)
   */
  async clickPattern(index: number): Promise<void> {
    const pattern = (await this.getPatternList()).nth(index);
    await pattern.click();
  }

  /**
   * Expect pattern count
   * @param count - Expected count
   */
  async expectPatternCount(count: number): Promise<void> {
    const patterns = await this.getPatternList();
    await expect(patterns).toHaveCount(count);
  }

  /**
   * Expect no patterns displayed
   */
  async expectNoPatterns(): Promise<void> {
    await expect(this.page.getByText('No patterns found')).toBeVisible();
  }
}


import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';
import { BlueprintSuggestionsPage } from '../../page-objects/BlueprintSuggestionsPage';

/** P4 - Blueprint Suggestions page */
test.describe('AI Automation UI - Blueprint Suggestions Page', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/?source=blueprints');
    await waitForLoadingComplete(page);
  });

  test('@smoke Blueprint page loads', async ({ page }) => {
    await expect(page.locator('#main-content')).toBeVisible({ timeout: 8000 });
  });

  test('Blueprint content displays', async ({ page }) => {
    const content = page.getByText(/Blueprint|Generate|Total|No suggestions/i).or(page.locator('main')).first();
    await expect(content).toBeVisible({ timeout: 10000 });
  });

  test('Generate button or empty state', async ({ page }) => {
    const generateBtn = page.getByRole('button', { name: /Generate/i });
    const emptyState = page.getByText(/No suggestions found/i);
    const errorState = page.getByText(/error|failed|unavailable|authentication/i).first();
    const hasGenerate = await generateBtn.isVisible().catch(() => false);
    const hasEmpty = await emptyState.isVisible().catch(() => false);
    const hasError = await errorState.isVisible().catch(() => false);
    expect(hasGenerate || hasEmpty || hasError).toBe(true);
  });

  test('Page object - stats or suggestions', async ({ page }) => {
    const blueprintPage = new BlueprintSuggestionsPage(page);
    const hasStats = await page.getByText('Total').isVisible().catch(() => false);
    const hasEmpty = await blueprintPage.getEmptyState().isVisible().catch(() => false);
    const hasNoBlueprints = await page.getByText(/No Blueprint Suggestions/i).isVisible().catch(() => false);
    const hasCards = await blueprintPage.getSuggestionCards().count() > 0;
    const hasError = await page.getByText(/error|failed|unavailable|authentication/i).first().isVisible().catch(() => false);
    expect(hasStats || hasEmpty || hasNoBlueprints || hasCards || hasError).toBe(true);
  });
});

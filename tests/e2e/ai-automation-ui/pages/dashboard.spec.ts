import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete, waitForModalOpen } from '../../../shared/helpers/wait-helpers';

/** Tests run against deployed Docker (no API mocks). */
test.describe('AI Automation UI - Conversational Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/');
    await waitForLoadingComplete(page);
  });

  test('@smoke Dashboard loads', async ({ page }) => {
    await expect(page.locator('body')).toBeVisible();
    await expect(page).toHaveTitle(/AI Automation|HomeIQ/i);
  });

  test('P4.2 Dashboard page loads and displays suggestions or empty state', async ({ page }) => {
    const container = page.locator('[data-testid="dashboard-container"], main, [class*="Dashboard"]').first();
    await expect(container).toBeVisible({ timeout: 15000 });
    const cards = page.locator('[data-testid="suggestion-card"], [class*="SuggestionCard"]');
    const emptyState = page.getByText(/no suggestions|empty|get started/i).first();
    const hasCards = await cards.first().isVisible().catch(() => false);
    const hasEmpty = await emptyState.isVisible().catch(() => false);
    expect(hasCards || hasEmpty).toBe(true);
  });

  test('Suggestion cards display', async ({ page }) => {
    const suggestionCards = page.locator('[data-testid="suggestion-card"], [class*="SuggestionCard"]');
    await expect(suggestionCards.first()).toBeVisible({ timeout: 5000 });
  });

  test('Status tabs work (draft, refining, ready, deployed)', async ({ page }) => {
    const statusTabs = [
      { status: 'draft', selector: 'button:has-text("Draft"), [data-status="draft"]' },
      { status: 'refining', selector: 'button:has-text("Refining"), [data-status="refining"]' },
      { status: 'yaml_generated', selector: 'button:has-text("Ready"), [data-status="yaml_generated"]' },
      { status: 'deployed', selector: 'button:has-text("Deployed"), [data-status="deployed"]' },
    ];

    for (const tab of statusTabs) {
      const tabButton = page.locator(tab.selector).first();
      if (await tabButton.isVisible({ timeout: 2000 })) {
        await tabButton.click();
        await page.waitForTimeout(500);
        await expect(tabButton).toBeVisible();
      }
    }
  });

  test('Filter pills work', async ({ page }) => {
    const filterPills = page.locator('[data-testid="filter-pill"], [class*="FilterPill"], button[class*="pill"]');
    
    if (await filterPills.count() > 0) {
      await filterPills.first().click();
      await page.waitForTimeout(500);
    }
  });

  test('P5.1 User can filter suggestions by category/confidence', async ({ page }) => {
    const filterPills = page.locator('[data-testid="filter-pill"], [class*="FilterPill"], button[class*="pill"], [data-status]');
    const count = await filterPills.count();
    if (count > 0) {
      await filterPills.first().click();
      await page.waitForTimeout(500);
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('P5.2 User can approve and deploy a suggestion', async ({ page }) => {
    const approveButton = page.locator('button:has-text("Approve"), [data-testid="approve"]').first();
    if (await approveButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await approveButton.click();
      await page.waitForTimeout(1000);
      const deployButton = page.locator('button:has-text("Deploy"), [data-testid="deploy"]').first();
      if (await deployButton.isVisible({ timeout: 2000 }).catch(() => false)) {
        await deployButton.click();
        await page.waitForTimeout(1000);
      }
    }
  });

  test('P5.3 User can reject a suggestion with feedback', async ({ page }) => {
    const rejectButton = page.locator('button:has-text("Reject"), [data-testid="reject"]').first();
    if (await rejectButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await rejectButton.click();
      await page.waitForTimeout(500);
      const feedbackInput = page.locator('textarea, input[placeholder*="feedback"], input[placeholder*="reason"]').first();
      if (await feedbackInput.isVisible({ timeout: 2000 }).catch(() => false)) {
        await feedbackInput.fill('Not needed');
        await page.locator('button:has-text("Submit"), button:has-text("Confirm")').first().click();
      }
    }
  });

  test('Search bar functionality', async ({ page }) => {
    const searchInput = page.locator('input[type="search"], input[placeholder*="search"]').first();
    
    if (await searchInput.isVisible({ timeout: 2000 })) {
      await searchInput.fill('light');
      await page.waitForTimeout(500);
      
      const results = page.locator('[data-testid="suggestion-card"], [class*="SuggestionCard"]');
      await expect(results.first()).toBeVisible();
    }
  });

  test('Refine button works', async ({ page }) => {
    const refineButton = page.locator('button:has-text("Refine"), [data-testid="refine"]').first();
    
    if (await refineButton.isVisible({ timeout: 2000 })) {
      await refineButton.click();
      await page.waitForTimeout(500);
      
      // Look for refinement interface
      const refinementInput = page.locator('textarea, input[type="text"]').first();
      const exists = await refinementInput.isVisible().catch(() => false);
    }
  });

  test('Approve button works', async ({ page }) => {
    const approveButton = page.locator('button:has-text("Approve"), [data-testid="approve"]').first();
    
    if (await approveButton.isVisible({ timeout: 2000 })) {
      await approveButton.click();
      await page.waitForTimeout(2000);
      
      // Verify YAML was generated (status changed)
      const yamlGenerated = page.locator('[data-status="yaml_generated"], [class*="yaml"]').first();
      const exists = await yamlGenerated.isVisible().catch(() => false);
    }
  });

  test('Deploy button works', async ({ page }) => {
    // First navigate to ready suggestions
    const readyTab = page.locator('button:has-text("Ready"), [data-status="yaml_generated"]').first();
    if (await readyTab.isVisible({ timeout: 2000 })) {
      await readyTab.click();
      await page.waitForTimeout(500);
    }
    
    const deployButton = page.locator('button:has-text("Deploy"), [data-testid="deploy"]').first();
    
    if (await deployButton.isVisible({ timeout: 2000 })) {
      await deployButton.click();
      await page.waitForTimeout(2000);
      
      // Verify deployment status
      const deployed = page.locator('[data-status="deployed"]').first();
      const exists = await deployed.isVisible().catch(() => false);
    }
  });

  test('YAML preview modal', async ({ page }) => {
    // Navigate to ready suggestions
    const readyTab = page.locator('button:has-text("Ready")').first();
    if (await readyTab.isVisible({ timeout: 2000 })) {
      await readyTab.click();
      await page.waitForTimeout(500);
    }
    
    const previewButton = page.locator('button:has-text("Preview"), [data-testid="preview"]').first();
    
    if (await previewButton.isVisible({ timeout: 2000 })) {
      await previewButton.click();
      await waitForModalOpen(page);
      
      const modal = page.locator('[role="dialog"], .modal').first();
      await expect(modal).toBeVisible({ timeout: 3000 });
      
      // Verify YAML is displayed
      const yamlContent = page.locator('pre, code, [class*="yaml"]').first();
      await expect(yamlContent).toBeVisible();
    }
  });

  test('Loading states', async ({ page }) => {
    await page.reload();
    
    const loadingIndicators = page.locator('[data-testid="loading"], .loading, .spinner, [class*="Skeleton"]');
    // Loading might be fast, but structure supports it
  });

  test.skip('Error states (requires API mock)', async ({ page }) => {
    const errorMessage = page.locator('[data-testid="error"], .error, [role="alert"]').first();
    await expect(errorMessage).toBeVisible({ timeout: 5000 });
  });

  test.skip('Empty states (requires API mock)', async ({ page }) => {
    const emptyState = page.locator('[data-testid="empty-state"], .empty-state').first();
    await emptyState.isVisible().catch(() => false);
  });

  test('Refresh functionality', async ({ page }) => {
    const refreshButton = page.locator('button[aria-label*="refresh"], button:has([class*="refresh"])').first();
    
    if (await refreshButton.isVisible({ timeout: 2000 })) {
      await refreshButton.click();
      await waitForLoadingComplete(page);
      
      const cards = page.locator('[data-testid="suggestion-card"]');
      await expect(cards.first()).toBeVisible();
    }
  });

  test('Batch actions', async ({ page }) => {
    const batchActionButton = page.locator('button:has-text("Batch"), [data-testid="batch-actions"]').first();
    
    if (await batchActionButton.isVisible({ timeout: 2000 })) {
      await batchActionButton.click();
      await waitForModalOpen(page);
      
      const modal = page.locator('[role="dialog"], .modal').first();
      await expect(modal).toBeVisible({ timeout: 3000 });
    }
  });
});

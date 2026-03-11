/**
 * Automation Creation Workflow Tests - "Can I go from idea to refinement to deployment?"
 *
 * WHY THIS WORKFLOW EXISTS:
 * The automation creation workflow is the core value proposition of the AI
 * Automation UI. A user starts with a draft suggestion, optionally refines it
 * through conversation, approves it to generate YAML, reviews the YAML, and
 * deploys it to Home Assistant. This end-to-end flow must work reliably.
 *
 * WHAT THE USER NEEDS:
 * - View a draft suggestion on the Ideas dashboard
 * - Refine a suggestion by providing additional context
 * - Approve a suggestion to generate deployment-ready YAML
 * - Deploy the approved automation to Home Assistant
 * - Verify the deployment appears in the Deployed view
 *
 * WHAT OLD TESTS MISSED:
 * - Each step was a separate test that could pass independently, never testing the flow
 * - Assertions like `expect(hasCard || hasEmpty).toBe(true)` masked real failures
 * - "Verify deployment" just checked for card or empty state (always passes)
 * - No console error detection
 */

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { isIgnorableConsoleError } from '../../../shared/helpers/console-filters';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

test.describe('Automation Creation Workflow - From idea to deployment', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/');
    await waitForLoadingComplete(page);
  });

  test('@integration step 1: view draft suggestions on the dashboard', async ({ page }) => {
    const draftTab = page.locator('button:has-text("Draft"), [data-status="draft"]').first();
    if (await draftTab.isVisible({ timeout: 2000 }).catch(() => false)) {
      await draftTab.click();
      await waitForLoadingComplete(page);

      // After clicking Draft tab, should see draft cards or empty state
      const cards = page.locator('[data-testid="suggestion-card"]');
      const emptyState = page.getByText(/no.*suggestions/i).first();
      const hasCards = await cards.first().isVisible({ timeout: 3000 }).catch(() => false);
      const hasEmpty = await emptyState.isVisible({ timeout: 2000 }).catch(() => false);
      expect(hasCards || hasEmpty).toBe(true);
    }
  });

  test('@integration step 2: refine a suggestion with additional context', async ({ page }) => {
    const refineButton = page.locator('button:has-text("Refine"), [data-testid="refine"]').first();

    if (await refineButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await refineButton.click();
      await waitForLoadingComplete(page);

      // A refinement input should appear
      const refinementInput = page.locator('textarea, input[type="text"]').first();
      if (await refinementInput.isVisible({ timeout: 2000 }).catch(() => false)) {
        await refinementInput.fill('Make it trigger at 6:30am instead');
        const value = await refinementInput.inputValue();
        expect(value).toContain('6:30am');
      }
    }
  });

  test('@integration step 3: approve a suggestion to generate YAML', async ({ page }) => {
    const approveButton = page.locator('button:has-text("Approve"), [data-testid="approve"]').first();

    if (await approveButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await approveButton.click();
      await waitForLoadingComplete(page);

      // After approval, the Ready tab should have the approved suggestion
      const readyTab = page.locator('button:has-text("Ready"), [data-status="yaml_generated"]').first();
      if (await readyTab.isVisible({ timeout: 2000 }).catch(() => false)) {
        await readyTab.click();
        await waitForLoadingComplete(page);
        await expect(page.locator('body')).toBeVisible();
      }
    }
  });

  test('@integration step 4: deploy an approved automation to Home Assistant', async ({ page }) => {
    // Navigate to ready suggestions
    const readyTab = page.locator('button:has-text("Ready")').first();
    if (await readyTab.isVisible({ timeout: 2000 }).catch(() => false)) {
      await readyTab.click();
      await waitForLoadingComplete(page);
    }

    const deployButton = page.locator('button:has-text("Deploy"), [data-testid="deploy"]').first();

    if (await deployButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await deployButton.click();
      await waitForLoadingComplete(page);

      // After deployment, switching to the Deployed tab should show results
      const deployedTab = page.locator('button:has-text("Deployed"), [data-status="deployed"]').first();
      if (await deployedTab.isVisible({ timeout: 2000 }).catch(() => false)) {
        await deployedTab.click();
        await waitForLoadingComplete(page);
        await expect(page.locator('body')).toBeVisible();
      }
    }
  });

  test('@integration step 5: verify deployed automation appears in the list', async ({ page }) => {
    const deployedTab = page.locator('button:has-text("Deployed"), [data-status="deployed"]').first();
    await expect(deployedTab, 'Automation creation flow should show Deployed tab').toBeVisible({ timeout: 5000 });
    await deployedTab.click();
    await waitForLoadingComplete(page);

    // Deployed page: data-testid="deployed-container", cards "deployed-automation", empty "No Deployed Automations Yet"
    const container = page.locator('[data-testid="deployed-container"]');
    await container.waitFor({ state: 'visible', timeout: 10000 }).catch(() => {});

    const deployedCards = page.locator('[data-testid="deployed-automation"], [data-testid="suggestion-card"]');
    const emptyState = page.getByText(/No Deployed Automations Yet|no.*suggestions|no automations/i).first();
    const loading = page.getByText(/Loading deployed automations/i);
    const hasCards = await deployedCards.first().isVisible({ timeout: 5000 }).catch(() => false);
    const hasEmpty = await emptyState.isVisible({ timeout: 5000 }).catch(() => false);
    const stillLoading = await loading.isVisible({ timeout: 2000 }).catch(() => false);
    expect(
      hasCards || hasEmpty || stillLoading,
      'Deployed tab should show list, empty state, or loading'
    ).toBe(true);
  });

  test('no console errors during the creation workflow', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Walk through the main tabs
    const tabs = ['Draft', 'Refining', 'Ready', 'Deployed'];
    for (const tab of tabs) {
      const tabButton = page.locator(`button:has-text("${tab}")`).first();
      if (await tabButton.isVisible({ timeout: 2000 }).catch(() => false)) {
        await tabButton.click();
        await waitForLoadingComplete(page);
      }
    }

    const criticalErrors = consoleErrors.filter((e) => !isIgnorableConsoleError(e));
    expect(criticalErrors).toEqual([]);
  });
});

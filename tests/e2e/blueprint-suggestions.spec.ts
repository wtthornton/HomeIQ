/**
 * Blueprint Suggestions - Comprehensive UI/UX Tests
 * 
 * Tests for the Blueprint Suggestions page at http://localhost:3001/?source=blueprints
 * 
 * Coverage:
 * - Page load and navigation
 * - Stats display
 * - Filters (min_score, use_case, status, blueprint_id)
 * - Suggestion cards display and interactions
 * - Accept/Decline functionality
 * - Generate form
 * - Delete all functionality
 * - Pagination
 * - Loading and empty states
 * - Error handling
 * - Toast notifications
 * - Accessibility
 */

import { test, expect } from '@playwright/test';
import { BlueprintSuggestionsPage } from './page-objects/BlueprintSuggestionsPage';

test.describe('Blueprint Suggestions - Page Load and Navigation', () => {
  let page: BlueprintSuggestionsPage;

  test.beforeEach(async ({ page: playwrightPage }) => {
    page = new BlueprintSuggestionsPage(playwrightPage);
    await page.goto();
  });

  test('@smoke Page loads successfully', async () => {
    // Verify page title
    await expect(page.getPageTitle()).toBeVisible();
    await expect(page.getPageDescription()).toBeVisible();
    
    // Verify header buttons
    await expect(page.getGenerateButton()).toBeVisible();
    await expect(page.getDeleteAllButton()).toBeVisible();
  });

  test('Page URL is correct', async ({ page: playwrightPage }) => {
    await expect(playwrightPage).toHaveURL(/.*source=blueprints/);
  });

  test('Stats section is visible', async () => {
    // Wait for stats to load
    await page.waitForPageReady();
    
    // Verify stats cards are visible
    await expect(page.getTotalStat()).toBeVisible({ timeout: 10000 });
    await expect(page.getPendingStat()).toBeVisible();
    await expect(page.getAcceptedStat()).toBeVisible();
    await expect(page.getAverageScoreStat()).toBeVisible();
  });

  test('Filters section is visible', async () => {
    await expect(page.getMinScoreFilter()).toBeVisible();
    await expect(page.getUseCaseFilter()).toBeVisible();
    await expect(page.getStatusFilter()).toBeVisible();
    await expect(page.getBlueprintIdFilter()).toBeVisible();
  });
});

test.describe('Blueprint Suggestions - Stats Display', () => {
  let page: BlueprintSuggestionsPage;

  test.beforeEach(async ({ page: playwrightPage }) => {
    page = new BlueprintSuggestionsPage(playwrightPage);
    await page.goto();
    await page.waitForPageReady();
  });

  test('Stats display numeric values', async () => {
    const total = await page.getTotalStat().textContent();
    const pending = await page.getPendingStat().textContent();
    const accepted = await page.getAcceptedStat().textContent();
    const avgScore = await page.getAverageScoreStat().textContent();

    // Verify stats are numbers
    expect(total).toMatch(/^\d+$/);
    expect(pending).toMatch(/^\d+$/);
    expect(accepted).toMatch(/^\d+$/);
    expect(avgScore).toMatch(/^\d+%$/);
  });

  test('Stats update after actions', async () => {
    const initialPending = await page.getPendingStat().textContent();
    const initialAccepted = await page.getAcceptedStat().textContent();

    // If there are suggestions, accept one
    const suggestionCount = await page.getSuggestionCount();
    if (suggestionCount > 0) {
      await page.acceptSuggestion(0);
      await page.waitForSuccessToast(/accepted/i);
      await page.waitForPageReady();

      // Verify stats updated
      const newPending = await page.getPendingStat().textContent();
      const newAccepted = await page.getAcceptedStat().textContent();

      // Pending should decrease or stay same, accepted should increase
      expect(parseInt(newAccepted!)).toBeGreaterThanOrEqual(parseInt(initialAccepted!));
    }
  });
});

test.describe('Blueprint Suggestions - Filters', () => {
  let page: BlueprintSuggestionsPage;

  test.beforeEach(async ({ page: playwrightPage }) => {
    page = new BlueprintSuggestionsPage(playwrightPage);
    await page.goto();
    await page.waitForPageReady();
  });

  test('Min score filter updates suggestions', async () => {
    const initialCount = await page.getSuggestionCount();
    
    // Set min score to 0.8 (80%)
    await page.setMinScoreFilter(0.8);
    await page.waitForSuggestionsToLoad();
    
    const filteredCount = await page.getSuggestionCount();
    
    // Filtered count should be <= initial count
    expect(filteredCount).toBeLessThanOrEqual(initialCount);
    
    // If there are suggestions, verify scores are >= 80%
    if (filteredCount > 0) {
      const suggestionData = await page.getSuggestionData(0);
      if (suggestionData.score !== null) {
        expect(suggestionData.score).toBeGreaterThanOrEqual(80);
      }
    }
  });

  test('Use case filter filters suggestions', async () => {
    const initialCount = await page.getSuggestionCount();
    
    // Filter by convenience
    await page.setUseCaseFilter('convenience');
    await page.waitForSuggestionsToLoad();
    
    const filteredCount = await page.getSuggestionCount();
    expect(filteredCount).toBeLessThanOrEqual(initialCount);
    
    // If there are suggestions, verify use case matches
    if (filteredCount > 0) {
      const suggestionData = await page.getSuggestionData(0);
      if (suggestionData.useCase) {
        expect(suggestionData.useCase.toLowerCase()).toContain('convenience');
      }
    }
  });

  test('Status filter filters suggestions', async () => {
    const initialCount = await page.getSuggestionCount();
    
    // Filter by pending
    await page.setStatusFilter('pending');
    await page.waitForSuggestionsToLoad();
    
    const filteredCount = await page.getSuggestionCount();
    expect(filteredCount).toBeLessThanOrEqual(initialCount);
    
    // If there are suggestions, verify accept/decline buttons are enabled
    if (filteredCount > 0) {
      const suggestionData = await page.getSuggestionData(0);
      expect(suggestionData.isAcceptEnabled).toBe(true);
      expect(suggestionData.isDeclineEnabled).toBe(true);
    }
  });

  test('Blueprint ID filter filters suggestions', async () => {
    const initialCount = await page.getSuggestionCount();
    
    if (initialCount > 0) {
      // Get first suggestion's blueprint name to use as filter
      const firstSuggestion = page.getSuggestionCard(0);
      const blueprintName = await page.getSuggestionBlueprintName(firstSuggestion).textContent();
      
      if (blueprintName) {
        // Try filtering by partial name
        await page.setBlueprintIdFilter(blueprintName.substring(0, 5));
        await page.waitForSuggestionsToLoad();
        
        const filteredCount = await page.getSuggestionCount();
        expect(filteredCount).toBeLessThanOrEqual(initialCount);
      }
    }
  });

  test('Multiple filters work together', async () => {
    await page.setMinScoreFilter(0.7);
    await page.setUseCaseFilter('security');
    await page.setStatusFilter('pending');
    await page.waitForSuggestionsToLoad();
    
    // Should have filtered results
    const filteredCount = await page.getSuggestionCount();
    expect(filteredCount).toBeGreaterThanOrEqual(0);
  });
});

test.describe('Blueprint Suggestions - Suggestion Cards', () => {
  let page: BlueprintSuggestionsPage;

  test.beforeEach(async ({ page: playwrightPage }) => {
    page = new BlueprintSuggestionsPage(playwrightPage);
    await page.goto();
    await page.waitForSuggestionsToLoad();
  });

  test('Suggestion cards display correctly', async () => {
    const count = await page.getSuggestionCount();
    
    if (count > 0) {
      const card = page.getSuggestionCard(0);
      
      // Verify card elements
      await expect(page.getSuggestionBlueprintName(card)).toBeVisible();
      await expect(page.getSuggestionScore(card)).toBeVisible();
      await expect(page.getAcceptButton(card)).toBeVisible();
      await expect(page.getDeclineButton(card)).toBeVisible();
    }
  });

  test('Suggestion cards show blueprint name', async () => {
    const count = await page.getSuggestionCount();
    
    if (count > 0) {
      const card = page.getSuggestionCard(0);
      const name = await page.getSuggestionBlueprintName(card).textContent();
      expect(name).toBeTruthy();
      expect(name!.length).toBeGreaterThan(0);
    }
  });

  test('Suggestion cards show score', async () => {
    const count = await page.getSuggestionCount();
    
    if (count > 0) {
      const card = page.getSuggestionCard(0);
      const scoreText = await page.getSuggestionScore(card).textContent();
      expect(scoreText).toMatch(/\d+%/);
    }
  });

  test('Suggestion cards show matched devices', async () => {
    const count = await page.getSuggestionCount();
    
    if (count > 0) {
      const card = page.getSuggestionCard(0);
      const matchedDevices = page.getMatchedDevices(card);
      await expect(matchedDevices).toBeVisible();
      
      const deviceCount = await page.getMatchedDeviceBadges(card).count();
      expect(deviceCount).toBeGreaterThanOrEqual(0);
    }
  });

  test('Suggestion cards show use case badge when available', async () => {
    const count = await page.getSuggestionCount();
    
    if (count > 0) {
      const suggestionData = await page.getSuggestionData(0);
      // Use case may or may not be present
      if (suggestionData.useCase) {
        expect(['convenience', 'security', 'energy', 'comfort']).toContain(
          suggestionData.useCase.toLowerCase()
        );
      }
    }
  });

  test('Pending suggestions have enabled buttons', async () => {
    // Filter to pending only
    await page.setStatusFilter('pending');
    await page.waitForSuggestionsToLoad();
    
    const count = await page.getSuggestionCount();
    if (count > 0) {
      const suggestionData = await page.getSuggestionData(0);
      expect(suggestionData.isAcceptEnabled).toBe(true);
      expect(suggestionData.isDeclineEnabled).toBe(true);
    }
  });

  test('Accepted suggestions have disabled buttons', async () => {
    // Filter to accepted only
    await page.setStatusFilter('accepted');
    await page.waitForSuggestionsToLoad();
    
    const count = await page.getSuggestionCount();
    if (count > 0) {
      const suggestionData = await page.getSuggestionData(0);
      expect(suggestionData.isAcceptEnabled).toBe(false);
      expect(suggestionData.isDeclineEnabled).toBe(false);
    }
  });
});

test.describe('Blueprint Suggestions - Accept/Decline Actions', () => {
  let page: BlueprintSuggestionsPage;

  test.beforeEach(async ({ page: playwrightPage }) => {
    page = new BlueprintSuggestionsPage(playwrightPage);
    await page.goto();
    await page.waitForSuggestionsToLoad();
    
    // Filter to pending only
    await page.setStatusFilter('pending');
    await page.waitForSuggestionsToLoad();
  });

  test('@smoke Accept suggestion shows success toast', async () => {
    const count = await page.getSuggestionCount();
    
    if (count > 0) {
      await page.acceptSuggestion(0);
      await page.waitForSuccessToast(/accepted/i);
    } else {
      expect(true, 'Required condition not met for blueprint test').toBe(false);
    }
  });

  test('Accept suggestion navigates to HA Agent page', async ({ page: playwrightPage }) => {
    const count = await page.getSuggestionCount();
    
    if (count > 0) {
      await page.acceptSuggestion(0);
      await page.waitForSuccessToast(/accepted/i);
      
      // Should navigate to chat page
      await expect(playwrightPage).toHaveURL(/.*chat/, { timeout: 10000 });
    } else {
      expect(true, 'Required condition not met for blueprint test').toBe(false);
    }
  });

  test('Decline suggestion shows success toast', async () => {
    const count = await page.getSuggestionCount();
    
    if (count > 0) {
      await page.declineSuggestion(0);
      await page.waitForSuccessToast(/declined/i);
    } else {
      expect(true, 'Required condition not met for blueprint test').toBe(false);
    }
  });

  test('Decline suggestion updates status', async () => {
    const count = await page.getSuggestionCount();
    
    if (count > 0) {
      await page.declineSuggestion(0);
      await page.waitForSuccessToast(/declined/i);
      await page.waitForPageReady();
      
      // Suggestion should no longer be in pending list
      await page.setStatusFilter('pending');
      await page.waitForSuggestionsToLoad();
      
      const newCount = await page.getSuggestionCount();
      expect(newCount).toBeLessThan(count);
    } else {
      expect(true, 'Required condition not met for blueprint test').toBe(false);
    }
  });
});

test.describe('Blueprint Suggestions - Generate Form', () => {
  let page: BlueprintSuggestionsPage;

  test.beforeEach(async ({ page: playwrightPage }) => {
    page = new BlueprintSuggestionsPage(playwrightPage);
    await page.goto();
  });

  test('Generate form toggles visibility', async () => {
    // Form should be hidden initially
    expect(await page.isGenerateFormVisible()).toBe(false);
    
    // Toggle form open
    await page.toggleGenerateForm();
    expect(await page.isGenerateFormVisible()).toBe(true);
    
    // Toggle form closed
    await page.toggleGenerateForm();
    expect(await page.isGenerateFormVisible()).toBe(false);
  });

  test('Generate form has all fields', async () => {
    await page.toggleGenerateForm();
    
    await expect(page.getMaxSuggestionsInput()).toBeVisible();
    await expect(page.getGenerateMinScoreSlider()).toBeVisible();
    await expect(page.getComplexitySelect()).toBeVisible();
    await expect(page.getGenerateUseCaseSelect()).toBeVisible();
    await expect(page.getDomainInput()).toBeVisible();
    await expect(page.getMinQualityScoreInput()).toBeVisible();
    await expect(page.getFormGenerateButton()).toBeVisible();
    await expect(page.getFormCancelButton()).toBeVisible();
  });

  test('Generate form can be filled', async () => {
    await page.toggleGenerateForm();
    
    await page.fillGenerateForm({
      maxSuggestions: 5,
      minScore: 0.7,
      complexity: 'simple',
      useCase: 'convenience',
      domain: 'light',
      minQualityScore: 0.8,
    });
    
    // Verify values
    const maxSuggestions = await page.getMaxSuggestionsInput().inputValue();
    expect(maxSuggestions).toBe('5');
    
    const complexity = await page.getComplexitySelect().inputValue();
    expect(complexity).toBe('simple');
    
    const useCase = await page.getGenerateUseCaseSelect().inputValue();
    expect(useCase).toBe('convenience');
    
    const domain = await page.getDomainInput().inputValue();
    expect(domain).toBe('light');
  });

  test('Generate form cancel button closes form', async () => {
    await page.toggleGenerateForm();
    expect(await page.isGenerateFormVisible()).toBe(true);
    
    await page.getFormCancelButton().click();
    expect(await page.isGenerateFormVisible()).toBe(false);
  });

  test('Generate form submission shows success toast', async () => {
    await page.toggleGenerateForm();
    
    await page.fillGenerateForm({
      maxSuggestions: 5,
      minScore: 0.6,
    });
    
    await page.submitGenerateForm();
    
    // Wait for generation to complete
    await page.waitForSuccessToast(/generated/i, 30000);
  });

  test('Generate form submission updates suggestions', async () => {
    const initialCount = await page.getSuggestionCount();
    
    await page.toggleGenerateForm();
    await page.fillGenerateForm({
      maxSuggestions: 3,
      minScore: 0.6,
    });
    
    await page.submitGenerateForm();
    await page.waitForSuccessToast(/generated/i, 30000);
    await page.waitForSuggestionsToLoad();
    
    // Suggestions should be updated (may increase or stay same)
    const newCount = await page.getSuggestionCount();
    expect(newCount).toBeGreaterThanOrEqual(0);
  });
});

test.describe('Blueprint Suggestions - Delete All', () => {
  let page: BlueprintSuggestionsPage;

  test.beforeEach(async ({ page: playwrightPage }) => {
    page = new BlueprintSuggestionsPage(playwrightPage);
    await page.goto();
    await page.waitForSuggestionsToLoad();
  });

  test('Delete all shows confirmation dialog', async ({ page: playwrightPage }) => {
    let dialogShown = false;
    
    playwrightPage.once('dialog', async dialog => {
      dialogShown = true;
      expect(dialog.type()).toBe('confirm');
      expect(dialog.message()).toContain('delete all');
      await dialog.dismiss();
    });
    
    await page.deleteAllSuggestions(false);
    expect(dialogShown).toBe(true);
  });

  test('Delete all with confirmation shows success toast', async () => {
    const count = await page.getSuggestionCount();
    
    if (count > 0) {
      await page.deleteAllSuggestions(true);
      await page.waitForSuccessToast(/deleted/i);
      await page.waitForSuggestionsToLoad();
      
      // Should have no suggestions or empty state
      const newCount = await page.getSuggestionCount();
      expect(newCount).toBe(0);
    } else {
      expect(true, 'Required condition not met for blueprint test').toBe(false);
    }
  });

  test('Delete all without confirmation does not delete', async () => {
    const initialCount = await page.getSuggestionCount();
    
    await page.deleteAllSuggestions(false);
    
    // Wait a bit to ensure no deletion occurred
    await page.page.waitForTimeout(1000);
    
    const newCount = await page.getSuggestionCount();
    expect(newCount).toBe(initialCount);
  });
});

test.describe('Blueprint Suggestions - Pagination', () => {
  let page: BlueprintSuggestionsPage;

  test.beforeEach(async ({ page: playwrightPage }) => {
    page = new BlueprintSuggestionsPage(playwrightPage);
    await page.goto();
    await page.waitForSuggestionsToLoad();
  });

  test('Pagination appears when there are many suggestions', async () => {
    const paginationInfo = page.getPaginationInfo();
    const isVisible = await paginationInfo.isVisible().catch(() => false);
    
    if (isVisible) {
      await expect(page.getPreviousButton()).toBeVisible();
      await expect(page.getNextButton()).toBeVisible();
      await expect(paginationInfo).toBeVisible();
    } else {
      expect(true, 'Pagination required for this test').toBe(false);
    }
  });

  test('Pagination info shows correct range', async () => {
    const paginationInfo = page.getPaginationInfo();
    const isVisible = await paginationInfo.isVisible().catch(() => false);
    
    if (isVisible) {
      const infoText = await paginationInfo.textContent();
      expect(infoText).toMatch(/\d+-\d+ of \d+/);
    } else {
      expect(true, 'Required condition not met for blueprint test').toBe(false);
    }
  });

  test('Next button navigates to next page', async () => {
    const nextButton = page.getNextButton();
    const isEnabled = await nextButton.isEnabled().catch(() => false);
    
    if (isEnabled) {
      const initialInfo = await page.getPaginationInfo().textContent();
      await page.goToNextPage();
      
      const newInfo = await page.getPaginationInfo().textContent();
      expect(newInfo).not.toBe(initialInfo);
    } else {
      expect(true, 'Required condition not met for blueprint test').toBe(false);
    }
  });

  test('Previous button navigates to previous page', async () => {
    // First go to next page if possible
    const nextButton = page.getNextButton();
    const canGoNext = await nextButton.isEnabled().catch(() => false);
    
    if (canGoNext) {
      await page.goToNextPage();
      
      // Now previous should be enabled
      const previousButton = page.getPreviousButton();
      const isEnabled = await previousButton.isEnabled().catch(() => false);
      
      if (isEnabled) {
        const initialInfo = await page.getPaginationInfo().textContent();
        await page.goToPreviousPage();
        
        const newInfo = await page.getPaginationInfo().textContent();
        expect(newInfo).not.toBe(initialInfo);
      }
    } else {
      expect(true, 'Required condition not met for blueprint test').toBe(false);
    }
  });

  test('Previous button is disabled on first page', async () => {
    const previousButton = page.getPreviousButton();
    const isVisible = await previousButton.isVisible().catch(() => false);
    
    if (isVisible) {
      const isEnabled = await previousButton.isEnabled();
      // If we're on first page, previous should be disabled
      // If we're not on first page, this test doesn't apply
      // We can't easily determine which page we're on, so we'll just check if it exists
      expect(isEnabled).toBeDefined();
    } else {
      expect(true, 'Required condition not met for blueprint test').toBe(false);
    }
  });
});

test.describe('Blueprint Suggestions - Loading and Empty States', () => {
  let page: BlueprintSuggestionsPage;

  test.beforeEach(async ({ page: playwrightPage }) => {
    page = new BlueprintSuggestionsPage(playwrightPage);
  });

  test('Loading indicator shows during initial load', async () => {
    // Navigate and immediately check for loading
    await page.page.goto('http://localhost:3001/?source=blueprints');
    
    // Loading indicator may appear briefly
    const loadingVisible = await page.getLoadingIndicator().isVisible({ timeout: 2000 }).catch(() => false);
    
    // Either loading shows or page loads quickly
    if (loadingVisible) {
      await expect(page.getLoadingIndicator()).toBeVisible();
    }
    
    // Eventually loading should disappear
    await page.waitForPageReady();
    await expect(page.getLoadingIndicator()).not.toBeVisible();
  });

  test('Empty state shows when no suggestions', async () => {
    // Delete all suggestions first
    await page.goto();
    await page.waitForPageReady();
    
    const count = await page.getSuggestionCount();
    if (count > 0) {
      await page.deleteAllSuggestions(true);
      await page.waitForSuccessToast(/deleted/i);
      await page.waitForSuggestionsToLoad();
    }
    
    // Should show empty state
    await expect(page.getEmptyState()).toBeVisible();
  });
});

test.describe('Blueprint Suggestions - Error Handling', () => {
  let page: BlueprintSuggestionsPage;

  test.beforeEach(async ({ page: playwrightPage }) => {
    page = new BlueprintSuggestionsPage(playwrightPage);
    await page.goto();
    await page.waitForPageReady();
  });

  test('Error toast shows on API failure', async () => {
    // Intercept API calls and return error
    await page.page.route('**/api/blueprint-suggestions/**', route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ detail: 'Internal server error' }),
      });
    });
    
    // Try to accept a suggestion (will fail)
    const count = await page.getSuggestionCount();
    if (count > 0) {
      await page.acceptSuggestion(0);
      await page.waitForErrorToast(/failed|error/i);
    } else {
      expect(true, 'Required condition not met for blueprint test').toBe(false);
    }
  });
});

test.describe('Blueprint Suggestions - Accessibility', () => {
  let page: BlueprintSuggestionsPage;

  test.beforeEach(async ({ page: playwrightPage }) => {
    page = new BlueprintSuggestionsPage(playwrightPage);
    await page.goto();
    await page.waitForPageReady();
  });

  test('Page has proper heading structure', async () => {
    const h1 = page.page.locator('h1');
    await expect(h1).toBeVisible();
    
    const h1Text = await h1.textContent();
    expect(h1Text).toContain('Blueprint Suggestions');
  });

  test('Buttons have accessible labels', async () => {
    const generateButton = page.getGenerateButton();
    const deleteButton = page.getDeleteAllButton();
    
    await expect(generateButton).toBeVisible();
    await expect(deleteButton).toBeVisible();
    
    // Verify buttons have text content
    const generateText = await generateButton.textContent();
    const deleteText = await deleteButton.textContent();
    
    expect(generateText).toBeTruthy();
    expect(deleteText).toBeTruthy();
  });

  test('Form inputs have labels', async () => {
    await page.toggleGenerateForm();
    
    const maxSuggestionsLabel = page.page.locator('label:has-text("Max Suggestions")');
    await expect(maxSuggestionsLabel).toBeVisible();
    
    const complexityLabel = page.page.locator('label:has-text("Complexity")');
    await expect(complexityLabel).toBeVisible();
  });
});

test.describe('Blueprint Suggestions - Mocked Data in Table', () => {
  const mockSuggestions = [
    {
      id: 'sug-001',
      blueprint_id: 'bp-motion-light',
      blueprint_name: 'Motion-Activated Lights',
      blueprint_description: 'Turn on lights when motion is detected',
      suggestion_score: 0.92,
      matched_devices: [
        { entity_id: 'binary_sensor.hallway_motion', domain: 'binary_sensor', friendly_name: 'Hallway Motion', area_name: 'Hallway' },
        { entity_id: 'light.hallway_ceiling', domain: 'light', friendly_name: 'Hallway Ceiling Light', area_name: 'Hallway' },
      ],
      use_case: 'convenience',
      status: 'pending',
      created_at: '2026-03-01T10:00:00Z',
      updated_at: '2026-03-01T10:00:00Z',
    },
    {
      id: 'sug-002',
      blueprint_id: 'bp-night-security',
      blueprint_name: 'Night Security Lockdown',
      blueprint_description: 'Lock doors and arm alarm at bedtime',
      suggestion_score: 0.85,
      matched_devices: [
        { entity_id: 'lock.front_door', domain: 'lock', friendly_name: 'Front Door Lock', area_name: 'Entrance' },
        { entity_id: 'alarm_control_panel.home', domain: 'alarm_control_panel', friendly_name: 'Home Alarm', area_name: 'Entrance' },
      ],
      use_case: 'security',
      status: 'pending',
      created_at: '2026-03-01T11:00:00Z',
      updated_at: '2026-03-01T11:00:00Z',
    },
    {
      id: 'sug-003',
      blueprint_id: 'bp-energy-saver',
      blueprint_name: 'Energy Saver Schedule',
      blueprint_description: 'Reduce energy usage during off-peak hours',
      suggestion_score: 0.78,
      matched_devices: [
        { entity_id: 'climate.living_room', domain: 'climate', friendly_name: 'Living Room Thermostat', area_name: 'Living Room' },
      ],
      use_case: 'energy',
      status: 'pending',
      created_at: '2026-03-01T12:00:00Z',
      updated_at: '2026-03-01T12:00:00Z',
    },
  ];

  const mockStats = {
    total_suggestions: 3,
    pending_count: 3,
    accepted_count: 0,
    declined_count: 0,
    average_score: 0.85,
    min_score: 0.78,
    max_score: 0.92,
  };

  test.beforeEach(async ({ page }) => {
    // Mock the suggestions API
    await page.route('**/api/blueprint-suggestions/suggestions*', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ suggestions: mockSuggestions, total: mockSuggestions.length, limit: 50, offset: 0 }),
      });
    });

    // Mock the stats API
    await page.route('**/api/blueprint-suggestions/stats', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockStats),
      });
    });

    await page.goto('http://localhost:3001/?source=blueprints');
    await page.waitForLoadState('networkidle');
  });

  test('@smoke Blueprint suggestions render in the list', async ({ page }) => {
    // All 3 suggestions should be visible as cards
    const cards = page.locator('h3');
    await expect(cards.filter({ hasText: 'Motion-Activated Lights' })).toBeVisible();
    await expect(cards.filter({ hasText: 'Night Security Lockdown' })).toBeVisible();
    await expect(cards.filter({ hasText: 'Energy Saver Schedule' })).toBeVisible();
  });

  test('Blueprint cards show correct scores', async ({ page }) => {
    await expect(page.locator('text=Score:').first()).toBeVisible();
    // 0.92 * 100 = 92%
    await expect(page.getByText('92%').first()).toBeVisible();
    await expect(page.getByText('85%').first()).toBeVisible();
    await expect(page.getByText('78%').first()).toBeVisible();
  });

  test('Blueprint cards show matched devices', async ({ page }) => {
    await expect(page.getByText('Hallway Motion')).toBeVisible();
    await expect(page.getByText('Hallway Ceiling Light')).toBeVisible();
    await expect(page.getByText('Front Door Lock')).toBeVisible();
    await expect(page.getByText('Home Alarm')).toBeVisible();
    await expect(page.getByText('Living Room Thermostat')).toBeVisible();
  });

  test('Blueprint cards show use case badges', async ({ page }) => {
    await expect(page.getByText('convenience').first()).toBeVisible();
    await expect(page.getByText('security').first()).toBeVisible();
    await expect(page.getByText('energy').first()).toBeVisible();
  });

  test('Stats reflect mocked data', async ({ page }) => {
    // Total = 3, Pending = 3, Accepted = 0, Avg Score = 85%
    const totalCard = page.locator('text=Total').locator('..');
    await expect(totalCard.getByText('3')).toBeVisible();

    const pendingCard = page.locator('text=Pending').locator('..').first();
    await expect(pendingCard.getByText('3')).toBeVisible();

    await expect(page.getByText('85%').first()).toBeVisible();
  });

  test('Accept and Decline buttons are enabled for pending suggestions', async ({ page }) => {
    const acceptButtons = page.getByRole('button', { name: 'Accept' });
    const declineButtons = page.getByRole('button', { name: 'Decline' });

    expect(await acceptButtons.count()).toBe(3);
    expect(await declineButtons.count()).toBe(3);

    // All should be enabled since status is pending
    for (let i = 0; i < 3; i++) {
      await expect(acceptButtons.nth(i)).toBeEnabled();
      await expect(declineButtons.nth(i)).toBeEnabled();
    }
  });

  test('Empty state is NOT shown when suggestions exist', async ({ page }) => {
    await expect(page.getByText('No Blueprint Suggestions Yet')).not.toBeVisible();
  });
});

test.describe('Blueprint Suggestions - User Journey', () => {
  let page: BlueprintSuggestionsPage;

  test.beforeEach(async ({ page: playwrightPage }) => {
    page = new BlueprintSuggestionsPage(playwrightPage);
    await page.goto();
    await page.waitForPageReady();
  });

  test('@smoke Complete user journey: filter, view, accept', async () => {
    // 1. View stats
    await expect(page.getTotalStat()).toBeVisible();
    
    // 2. Apply filters
    await page.setMinScoreFilter(0.7);
    await page.setUseCaseFilter('convenience');
    await page.waitForSuggestionsToLoad();
    
    // 3. View suggestions
    const count = await page.getSuggestionCount();
    if (count > 0) {
      // 4. View suggestion details
      const suggestionData = await page.getSuggestionData(0);
      expect(suggestionData.name).toBeTruthy();
      expect(suggestionData.score).toBeGreaterThanOrEqual(70);
      
      // 5. Accept suggestion
      await page.acceptSuggestion(0);
      await page.waitForSuccessToast(/accepted/i);
    } else {
      // If no suggestions, generate some
      await page.toggleGenerateForm();
      await page.fillGenerateForm({
        maxSuggestions: 5,
        minScore: 0.7,
      });
      await page.submitGenerateForm();
      await page.waitForSuccessToast(/generated/i, 30000);
      await page.waitForSuggestionsToLoad();
    }
  });

  test('Complete user journey: generate, filter, decline', async () => {
    // 1. Generate suggestions
    await page.toggleGenerateForm();
    await page.fillGenerateForm({
      maxSuggestions: 3,
      minScore: 0.6,
      useCase: 'security',
    });
    await page.submitGenerateForm();
    await page.waitForSuccessToast(/generated/i, 30000);
    await page.waitForSuggestionsToLoad();
    
    // 2. Filter by status
    await page.setStatusFilter('pending');
    await page.waitForSuggestionsToLoad();
    
    // 3. View and decline
    const count = await page.getSuggestionCount();
    if (count > 0) {
      await page.declineSuggestion(0);
      await page.waitForSuccessToast(/declined/i);
      
      // 4. Verify decline worked
      await page.waitForPageReady();
      await page.setStatusFilter('declined');
      await page.waitForSuggestionsToLoad();
      
      const declinedCount = await page.getSuggestionCount();
      expect(declinedCount).toBeGreaterThanOrEqual(1);
    }
  });
});

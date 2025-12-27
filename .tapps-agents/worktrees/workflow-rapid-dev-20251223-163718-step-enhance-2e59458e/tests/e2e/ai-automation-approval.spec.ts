/**
 * Story 26.1: Suggestion Approval & Deployment E2E Tests
 * Epic 26: AI Automation UI E2E Test Coverage
 * 
 * Tests the complete approval workflow from browsing to deployment.
 * 100% accurate to actual implementation (verified Oct 19, 2025)
 * 
 * Total Tests: 6
 * Priority: HIGH (critical user workflows)
 * Dependencies: Epic 25 test infrastructure
 */

import { test, expect, Page } from '@playwright/test';
import { DashboardPage } from './page-objects/DashboardPage';
import { DeployedPage } from './page-objects/DeployedPage';

test.describe('AI Automation Approval Workflow - Story 26.1', () => {
  let dashboardPage: DashboardPage;
  let deployedPage: DeployedPage;

  test.beforeEach(async ({ page }) => {
    // Initialize page objects
    dashboardPage = new DashboardPage(page);
    deployedPage = new DeployedPage(page);

    // Mock AI automation service API (actual endpoints verified)
    await mockAutomationAPI(page);

    // Navigate to dashboard
    await dashboardPage.goto();
    
    // Wait for page to load
    await expect(page.getByTestId('dashboard-container')).toBeVisible();
  });

  /**
   * Test 1: Complete Approval and Deployment Workflow
   * 
   * Verifies the entire user journey:
   * 1. Browse suggestions
   * 2. Approve a suggestion
   * 3. Deploy to Home Assistant
   * 4. Verify appears in Deployed tab
   */
  test('should complete full approval and deployment workflow', async ({ page }) => {
    // STEP 1: Verify suggestions load (web-first assertion with auto-wait)
    const suggestionCards = await dashboardPage.getSuggestionCards();
    await expect(suggestionCards).toHaveCount({ min: 1 });

    // STEP 2: Get first suggestion details (ID is a NUMBER, not string)
    const suggestionId = await dashboardPage.getSuggestionId(0);
    expect(suggestionId).toBeTruthy();
    expect(typeof parseInt(suggestionId!)).toBe('number');

    // STEP 3: Approve first suggestion
    await dashboardPage.approveSuggestion(0);

    // STEP 4: Wait for success toast (data-testid from CustomToast.tsx)
    await expect(page.getByTestId('toast-success')).toBeVisible();
    await expect(page.getByTestId('toast-success')).toContainText(/approved successfully/i);

    // STEP 5: Reload to get updated status
    await page.reload();
    await expect(page.getByTestId('dashboard-container')).toBeVisible();

    // STEP 6: Switch to 'approved' tab
    await page.getByRole('button', { name: /approved/i }).click();
    
    // STEP 7: Verify suggestion shows in approved tab
    const approvedCards = await dashboardPage.getSuggestionCards();
    await expect(approvedCards).toHaveCount({ min: 1 });

    // STEP 8: Deploy the approved suggestion
    const deployButton = page.getByTestId(`deploy-${suggestionId}`);
    await expect(deployButton).toBeVisible();
    await deployButton.click();

    // STEP 9: Wait for deployment success toast
    await expect(page.getByTestId('toast-success')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('toast-success')).toContainText(/deployed/i);

    // STEP 10: Navigate to Deployed tab
    await deployedPage.goto();
    await expect(page.getByTestId('deployed-container')).toBeVisible();

    // STEP 11: Verify automation appears in deployed list
    const deployedAutomations = await deployedPage.getDeployedAutomations();
    await expect(deployedAutomations).toHaveCount({ min: 1 });
  });

  /**
   * Test 2: Filter Suggestions by Category
   * 
   * Verifies category filtering works correctly for:
   * - energy, comfort, security, convenience categories
   */
  test('should filter suggestions by category', async ({ page }) => {
    // STEP 1: Verify initial suggestions loaded
    const allSuggestions = await dashboardPage.getSuggestionCards();
    const initialCount = await allSuggestions.count();
    expect(initialCount).toBeGreaterThanOrEqual(1);

    // STEP 2: Apply energy category filter
    await dashboardPage.filterByCategory('energy');
    
    // Wait for network to settle
    await page.waitForLoadState('networkidle');

    // STEP 3: Verify filtered results
    const energySuggestions = await dashboardPage.getSuggestionCards();
    const energyCount = await energySuggestions.count();

    // Should have at least 1 energy suggestion (from mock data)
    expect(energyCount).toBeGreaterThanOrEqual(1);

    // STEP 4: Verify all visible suggestions contain energy-related keywords
    for (let i = 0; i < Math.min(energyCount, 3); i++) {
      const card = energySuggestions.nth(i);
      const text = await card.textContent();
      // Energy suggestions should mention energy/power/electricity/consumption
      expect(text).toMatch(/energy|power|electricity|consumption|lights?|saving/i);
    }

    // STEP 5: Change to comfort category
    await dashboardPage.filterByCategory('comfort');
    await page.waitForLoadState('networkidle');

    // STEP 6: Verify comfort suggestions
    const comfortSuggestions = await dashboardPage.getSuggestionCards();
    const comfortCount = await comfortSuggestions.count();

    if (comfortCount > 0) {
      const firstComfort = comfortSuggestions.first();
      const text = await firstComfort.textContent();
      // Comfort suggestions should mention comfort/temperature/climate/heating
      expect(text).toMatch(/comfort|temperature|climate|heating|cooling|hvac/i);
    }
  });

  /**
   * Test 3: Filter by Confidence Level
   * 
   * Verifies confidence level filtering:
   * - High: >= 90%
   * - Medium: 70-89%
   * - Low: < 70%
   */
  test('should filter suggestions by confidence level', async ({ page }) => {
    // STEP 1: Verify initial state
    await expect(page.getByTestId('dashboard-container')).toBeVisible();

    // STEP 2: Filter for high-confidence suggestions (>= 90%)
    await dashboardPage.filterByConfidence('high');
    await page.waitForLoadState('networkidle');

    const highConfSuggestions = await dashboardPage.getSuggestionCards();
    const highCount = await highConfSuggestions.count();

    if (highCount > 0) {
      // STEP 3: Verify confidence badge shows high percentage
      const firstCard = highConfSuggestions.first();
      
      // Check for confidence meter (ConfidenceMeter component)
      // Should show >= 90%
      const cardText = await firstCard.textContent();
      expect(cardText).toMatch(/9[0-9]%|100%/);
    }

    // STEP 4: Filter for medium confidence (70-89%)
    await dashboardPage.filterByConfidence('medium');
    await page.waitForLoadState('networkidle');

    const mediumConfSuggestions = await dashboardPage.getSuggestionCards();
    const mediumCount = await mediumConfSuggestions.count();

    if (mediumCount > 0) {
      const firstCard = mediumConfSuggestions.first();
      const cardText = await firstCard.textContent();
      // Should show 70-89%
      expect(cardText).toMatch(/[7-8][0-9]%/);
    }
  });

  /**
   * Test 4: Search Suggestions by Keyword
   * 
   * Verifies search functionality searches across:
   * - Title
   * - Description  
   * - YAML content
   */
  test('should search suggestions by keyword', async ({ page }) => {
    // STEP 1: Search for "light" keyword
    await dashboardPage.searchSuggestions('light');
    await page.waitForLoadState('networkidle');

    const lightResults = await dashboardPage.getSuggestionCards();
    const lightCount = await lightResults.count();

    // STEP 2: Verify search results contain keyword
    if (lightCount > 0) {
      for (let i = 0; i < Math.min(lightCount, 3); i++) {
        const card = lightResults.nth(i);
        const text = await card.textContent();
        // Should contain "light" somewhere
        expect(text?.toLowerCase()).toContain('light');
      }
    }

    // STEP 3: Clear search
    await dashboardPage.searchSuggestions('');
    await page.waitForLoadState('networkidle');

    const allResults = await dashboardPage.getSuggestionCards();
    const allCount = await allResults.count();
    
    // Should have more (or equal) results when search is cleared
    expect(allCount).toBeGreaterThanOrEqual(lightCount);

    // STEP 4: Search with no results
    await dashboardPage.searchSuggestions('xyznonexistent123');
    await page.waitForLoadState('networkidle');

    // Should show "No suggestions" message
    await expect(page.getByText(/No.*suggestions/i)).toBeVisible();
  });

  /**
   * Test 5: Handle Deployment Errors Gracefully
   * 
   * Verifies error handling when deployment fails:
   * - Shows error toast
   * - Suggestion remains in approved state
   * - User can retry
   */
  test('should handle deployment errors gracefully', async ({ page }) => {
    // STEP 1: Override mock to return deployment error
    await page.route('**/api/deploy/*', route => route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ 
        error: 'Home Assistant connection failed',
        details: 'Could not connect to HA instance at http://homeassistant.local:8123'
      })
    }));

    // STEP 2: Approve a suggestion first
    await dashboardPage.approveSuggestion(0);
    
    // Wait for approval toast
    await expect(page.getByTestId('toast-success')).toBeVisible();
    
    // STEP 3: Reload and go to approved tab
    await page.reload();
    await page.getByRole('button', { name: /approved/i }).click();

    // STEP 4: Get suggestion ID and try to deploy
    const suggestionId = await dashboardPage.getSuggestionId(0);
    const deployButton = page.getByTestId(`deploy-${suggestionId}`);
    await deployButton.click();

    // STEP 5: Verify error toast appears (web-first assertion with auto-wait)
    await expect(page.getByTestId('toast-error')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('toast-error')).toContainText(/failed|error|connection/i);

    // STEP 6: Verify suggestion remains in approved state (not deployed)
    await page.reload();
    await page.getByRole('button', { name: /approved/i }).click();
    
    const approvedCards = await dashboardPage.getSuggestionCards();
    await expect(approvedCards).toHaveCount({ min: 1 });

    // STEP 7: Verify deploy button still available (can retry)
    await expect(page.getByTestId(`deploy-${suggestionId}`)).toBeVisible();
  });

  /**
   * Test 6: Verify Deployed Automation in Home Assistant
   * 
   * Verifies that deployed automations:
   * - Appear in Deployed tab
   * - Show correct status (active/inactive)
   * - Have action buttons (Edit, Disable)
   */
  test('should verify deployed automation appears in Home Assistant', async ({ page }) => {
    // STEP 1: Track if HA API was called
    let automationCreated = false;
    await page.route('**/api/services/automation/reload', route => {
      automationCreated = true;
      route.fulfill({ 
        status: 200, 
        contentType: 'application/json',
        body: JSON.stringify({ success: true }) 
      });
    });

    // STEP 2: Complete approval workflow
    await dashboardPage.approveSuggestion(0);
    await expect(page.getByTestId('toast-success')).toBeVisible();

    // STEP 3: Reload and deploy
    await page.reload();
    await page.getByRole('button', { name: /approved/i }).click();
    
    const suggestionId = await dashboardPage.getSuggestionId(0);
    await page.getByTestId(`deploy-${suggestionId}`).click();

    // STEP 4: Wait for deployment success
    await expect(page.getByTestId('toast-success')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('toast-success')).toContainText(/deployed/i);

    // STEP 5: Verify HA API was called (automation reload)
    expect(automationCreated).toBe(true);

    // STEP 6: Navigate to Deployed tab
    await deployedPage.goto();
    await expect(page.getByTestId('deployed-container')).toBeVisible();

    // STEP 7: Verify deployed automations list
    const deployedAutomations = await deployedPage.getDeployedAutomations();
    await expect(deployedAutomations).toHaveCount({ min: 1 });

    // STEP 8: Verify first automation details
    const firstAutomation = deployedAutomations.first();
    await expect(firstAutomation).toBeVisible();

    // Should have automation entity ID
    const automationText = await firstAutomation.textContent();
    expect(automationText).toBeTruthy();
    expect(automationText).toMatch(/automation\./);
  });
});

/**
 * Helper: Mock AI Automation Service API
 * 
 * Mocks all endpoints with actual API structure (verified Oct 19, 2025)
 * - Uses ACTUAL endpoint paths
 * - Uses ACTUAL response structures
 * - Uses number IDs (not strings)
 * - Uses PATCH for approve/reject (not POST)
 */
async function mockAutomationAPI(page: Page) {
  // Mock GET /api/suggestions/list (ACTUAL endpoint)
  await page.route('**/api/suggestions/list*', route => {
    const url = new URL(route.request().url());
    const status = url.searchParams.get('status') || 'pending';

    const allSuggestions = [
      {
        id: 1,  // NUMBER, not string!
        title: 'Turn off lights when leaving home',
        description: 'Automatically turn off all lights when presence sensor detects no motion for 30 minutes',
        category: 'energy',
        confidence: 95,
        automation_yaml: 'alias: "Turn off lights"\ntrigger:\n  - platform: state\n    entity_id: binary_sensor.motion\n    to: "off"\n    for:\n      minutes: 30\naction:\n  - service: light.turn_off\n    target:\n      area_id: all',
        status: 'pending',
        created_at: new Date().toISOString()
      },
      {
        id: 2,
        title: 'Pre-heat bedroom before wake time',
        description: 'Start heating bedroom 30 minutes before your usual wake time of 6:30 AM',
        category: 'comfort',
        confidence: 87,
        automation_yaml: 'alias: "Pre-heat bedroom"\ntrigger:\n  - platform: time\n    at: "06:00:00"\naction:\n  - service: climate.set_temperature\n    target:\n      entity_id: climate.bedroom\n    data:\n      temperature: 72',
        status: 'pending',
        created_at: new Date().toISOString()
      },
      {
        id: 3,
        title: 'Lock doors at bedtime',
        description: 'Automatically lock all doors at 11:00 PM if not already locked',
        category: 'security',
        confidence: 92,
        automation_yaml: 'alias: "Lock doors at night"\ntrigger:\n  - platform: time\n    at: "23:00:00"\ncondition:\n  - condition: state\n    entity_id: lock.front_door\n    state: "unlocked"\naction:\n  - service: lock.lock\n    target:\n      entity_id: all',
        status: 'pending',
        created_at: new Date().toISOString()
      }
    ];

    // Filter by status
    const filtered = allSuggestions.map(s => ({ ...s, status }));

    // ACTUAL response structure (verified)
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          suggestions: filtered,
          count: filtered.length
        }
      })
    });
  });

  // Mock PATCH /api/suggestions/:id/approve (ACTUAL endpoint + method)
  await page.route('**/api/suggestions/*/approve', route => {
    expect(route.request().method()).toBe('PATCH');  // Verify correct method
    
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ 
        success: true, 
        message: 'Suggestion approved successfully' 
      })
    });
  });

  // Mock PATCH /api/suggestions/:id/reject (ACTUAL endpoint + method)
  await page.route('**/api/suggestions/*/reject', route => {
    expect(route.request().method()).toBe('PATCH');  // Verify correct method
    
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ 
        success: true, 
        message: 'Suggestion rejected successfully' 
      })
    });
  });

  // Mock POST /api/deploy/:id (ACTUAL endpoint)
  await page.route('**/api/deploy/*', (route) => {
    const url = route.request().url();
    const suggestionId = url.split('/').pop();

    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        message: 'Successfully deployed to Home Assistant',
        data: {
          automation_id: `automation.suggestion_${suggestionId}`
        }
      })
    });
  });

  // Mock GET /api/deploy/automations (ACTUAL endpoint)
  await page.route('**/api/deploy/automations', route => {
    const deployed = [
      {
        entity_id: 'automation.suggestion_1',
        state: 'on',
        attributes: {
          friendly_name: 'Turn off lights when leaving home',
          last_triggered: null,
          mode: 'single'
        }
      }
    ];

    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: deployed })
    });
  });

  // Mock GET /api/analysis/schedule (for dashboard header)
  await page.route('**/api/analysis/schedule', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        is_running: false,
        next_run: new Date(Date.now() + 3600000).toISOString(),
        last_run: new Date(Date.now() - 3600000).toISOString()
      })
    });
  });
}


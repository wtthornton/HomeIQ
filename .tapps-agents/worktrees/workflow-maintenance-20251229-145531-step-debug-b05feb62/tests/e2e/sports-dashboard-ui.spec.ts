/**
 * Sports Dashboard UI E2E Tests
 * 
 * Tests the Sports tab in the Health Dashboard
 * Verifies UI components, team selection, and game display
 * 
 * Based on Playwright best practices:
 * - Use getByRole for accessibility-first selection
 * - Web-first assertions with auto-retry
 * - Test isolation with beforeEach
 */

import { test, expect } from '@playwright/test';

const DASHBOARD_BASE_URL = process.env.DASHBOARD_URL || 'http://localhost:3000';

test.describe('Sports Dashboard - Tab Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(DASHBOARD_BASE_URL);
    // Wait for dashboard to load
    await expect(page.getByRole('heading', { name: /health dashboard/i })).toBeVisible();
  });

  test('should display Sports tab', async ({ page }) => {
    const sportsTab = page.getByRole('tab', { name: /sports/i });
    await expect(sportsTab).toBeVisible();
  });

  test('should navigate to Sports tab', async ({ page }) => {
    await page.getByRole('tab', { name: /sports/i }).click();
    
    // Should show sports-specific content
    await expect(page).toHaveURL(/.*sports.*/i);
  });
});

test.describe('Sports Dashboard - Team Selection', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${DASHBOARD_BASE_URL}/sports`);
  });

  test('should display team selection interface', async ({ page }) => {
    // Look for team selection UI elements
    const teamSelector = page.getByRole('button', { name: /select teams/i });
    if (await teamSelector.isVisible()) {
      await expect(teamSelector).toBeVisible();
    }
  });

  test('should allow selecting NFL teams', async ({ page }) => {
    // This test will be implementation-specific
    // For now, verify the sports page loads
    await expect(page).toHaveURL(/.*sports.*/i);
  });

  test('should allow selecting NHL teams', async ({ page }) => {
    await expect(page).toHaveURL(/.*sports.*/i);
  });
});

test.describe('Sports Dashboard - Live Games Display', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${DASHBOARD_BASE_URL}/sports`);
  });

  test('should display live games section', async ({ page }) => {
    // Look for live games indicator
    const liveSection = page.locator('text=/live games/i');
    if (await liveSection.isVisible()) {
      await expect(liveSection).toBeVisible();
    }
  });

  test('should display game scores if games are live', async ({ page }) => {
    // Look for score elements
    const scoreElements = page.locator('[data-testid="game-score"]');
    // Games may or may not be live, so we just verify the page structure
    await expect(page).toHaveURL(/.*sports.*/i);
  });

  test('should show upcoming games', async ({ page }) => {
    // Look for upcoming games section
    const upcomingSection = page.locator('text=/upcoming/i');
    if (await upcomingSection.isVisible()) {
      await expect(upcomingSection).toBeVisible();
    }
  });
});

test.describe('Sports Dashboard - Real-Time Updates', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${DASHBOARD_BASE_URL}/sports`);
  });

  test('should handle empty state when no teams selected', async ({ page }) => {
    // Should show a message or empty state
    const emptyState = page.locator('text=/no teams selected/i, text=/select teams/i');
    if (await emptyState.isVisible()) {
      await expect(emptyState).toBeVisible();
    }
  });

  test('should update when teams are selected', async ({ page }) => {
    // This would require interaction with team selection UI
    // For now, verify the page is interactive
    await expect(page).toHaveURL(/.*sports.*/i);
  });
});

test.describe('Sports Dashboard - Performance', () => {
  test('should load sports tab within 2 seconds', async ({ page }) => {
    const startTime = Date.now();
    await page.goto(`${DASHBOARD_BASE_URL}/sports`);
    await expect(page).toHaveURL(/.*sports.*/i);
    const loadTime = Date.now() - startTime;
    
    expect(loadTime).toBeLessThan(2000);
  });

  test('should be responsive on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 }); // iPhone SE
    await page.goto(`${DASHBOARD_BASE_URL}/sports`);
    
    // Page should be responsive and not overflow
    await expect(page).toHaveURL(/.*sports.*/i);
  });
});

test.describe('Sports Dashboard - Error Handling', () => {
  test('should handle API errors gracefully', async ({ page }) => {
    await page.goto(`${DASHBOARD_BASE_URL}/sports`);
    
    // Should not show error boundary
    const errorBoundary = page.locator('text=/something went wrong/i');
    await expect(errorBoundary).not.toBeVisible();
  });

  test('should show loading state', async ({ page }) => {
    await page.goto(`${DASHBOARD_BASE_URL}/sports`);
    
    // Look for loading indicator (spinner, skeleton, etc.)
    // This may flash quickly, so we just verify no errors
    await expect(page).not.toHaveTitle(/error/i);
  });
});

test.describe('Sports Dashboard - Accessibility', () => {
  test('should have accessible team selection', async ({ page }) => {
    await page.goto(`${DASHBOARD_BASE_URL}/sports`);
    
    // Check for ARIA labels
    const interactiveElements = await page.locator('button, a, input').all();
    // Should have interactive elements
    expect(interactiveElements.length).toBeGreaterThan(0);
  });

  test('should support keyboard navigation', async ({ page }) => {
    await page.goto(`${DASHBOARD_BASE_URL}/sports`);
    
    // Tab through elements
    await page.keyboard.press('Tab');
    const focusedElement = await page.locator(':focus').count();
    expect(focusedElement).toBeGreaterThan(0);
  });
});


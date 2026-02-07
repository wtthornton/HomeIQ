import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForModalOpen } from '../../../shared/helpers/wait-helpers';

/**
 * RAG Details Modal Tests
 * Tests run against deployed Docker (no API mocks).
 * Validates that the RAG Details Modal shows RAG metrics and does not display non-RAG sections.
 */

test.describe('RAG Details Modal - RAG Metrics Only', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/#overview');
    await page.waitForLoadState('networkidle');
  });

  test('@smoke RAG Details Modal opens from RAG Status Card', async ({ page }) => {
    // Wait for overview tab to load
    // Wait for RAG Status Card to be visible
    const ragStatusSection = page.locator('[data-testid="rag-status-section"]');
    await expect(ragStatusSection).toBeVisible({ timeout: 10000 });
    
    const ragStatusCard = page.locator('[data-testid="rag-status-card"]');
    await expect(ragStatusCard).toBeVisible({ timeout: 5000 });
    
    // Click on RAG Status Card to open modal
    await ragStatusCard.click();
    
    // Wait for modal to open
    await waitForModalOpen(page);
    
    // Verify modal is visible
    const modal = page.locator('[role="dialog"]').filter({ hasText: 'RAG Status Details' });
    await expect(modal).toBeVisible({ timeout: 3000 });
    
    // Verify modal title
    await expect(modal.locator('h2:has-text("RAG Status Details")')).toBeVisible();
    
    // Verify modal content is populated (title already verified above)
    const modalContent = modal.locator('h2, p, span').first();
    await expect(modalContent).toBeVisible({ timeout: 3000 });
  });

  test('RAG Operations section displays RAG metric labels', async ({ page }) => {
    const ragStatusCard = page.locator('[data-testid="rag-status-card"]');
    await expect(ragStatusCard).toBeVisible({ timeout: 15000 });
    await ragStatusCard.click();
    await waitForModalOpen(page);
    const modal = page.locator('[role="dialog"]').filter({ hasText: 'RAG Status Details' });
    const ragOperationsSection = modal.locator('text=RAG Operations').locator('..');
    await expect(ragOperationsSection).toBeVisible({ timeout: 5000 });
    const expectedMetrics = [
      'Total RAG Calls',
      'Store Operations',
      'Retrieve Operations',
      'Search Operations',
      'Cache Hit Rate',
      'Avg Latency',
      'Error Rate',
      'Avg Success Score',
    ];
    for (const metric of expectedMetrics) {
      await expect(modal.locator(`text=${metric}`).first()).toBeVisible({ timeout: 2000 });
    }
    // Real data: at least one numeric value visible in modal
    const hasNumbers = await modal.locator('text=/\\d+(\\.\\d+)?%?/').first().isVisible().catch(() => false);
    expect(hasNumbers).toBe(true);
  });

  test('Non-RAG sections are NOT displayed', async ({ page }) => {
    // Open modal
    const ragStatusCard = page.locator('[data-testid="rag-status-card"]');
    await ragStatusCard.click();
    await waitForModalOpen(page);
    
    const modal = page.locator('[role="dialog"]').filter({ hasText: 'RAG Status Details' });
    
    // Verify non-RAG sections are NOT present
    const nonRAGSections = [
      'Data Metrics',
      'Data Breakdown',
      'Events Processed',
      'Unique Entities',
      'Events per Entity',
      'Events/Minute',
      'Total Events',
      'Throughput',
      'Connection Attempts',
      'WebSocket Connection',
      'Event Processing',
      'Data Storage',
      'Component Health Breakdown',
    ];
    
    for (const section of nonRAGSections) {
      const sectionElement = modal.locator(`text=${section}`);
      await expect(sectionElement).not.toBeVisible({ timeout: 1000 });
    }
  });

  test('Overall Status section is NOT displayed', async ({ page }) => {
    // Open modal
    const ragStatusCard = page.locator('[data-testid="rag-status-card"]');
    await expect(ragStatusCard).toBeVisible({ timeout: 10000 });
    await ragStatusCard.click();
    await waitForModalOpen(page);
    
    const modal = page.locator('[role="dialog"]').filter({ hasText: 'RAG Status Details' });
    await expect(modal).toBeVisible({ timeout: 3000 });
    
    // Verify Overall Status section is NOT present in the modal content area
    // (It might exist in the card, but not in the modal details)
    const modalContent = modal.locator('.p-6'); // Content area
    const overallStatus = modalContent.locator('text=Overall Status');
    const count = await overallStatus.count();
    expect(count).toBe(0);
  });

  test.skip('Modal displays loading state (requires API mock with delay)', async ({ page }) => {
    const ragStatusCard = page.locator('[data-testid="rag-status-card"]');
    await ragStatusCard.click();
    await waitForModalOpen(page);
    const modal = page.locator('[role="dialog"]').filter({ hasText: 'RAG Status Details' });
    const loadingSpinner = modal.locator('text=Loading RAG metrics');
    await expect(loadingSpinner).toBeVisible({ timeout: 1000 });
  });

  test.skip('Modal displays error state when RAG service is unavailable (requires API mock)', async ({ page }) => {
    const ragStatusCard = page.locator('[data-testid="rag-status-card"]');
    await ragStatusCard.click();
    await waitForModalOpen(page);
    const modal = page.locator('[role="dialog"]').filter({ hasText: 'RAG Status Details' });
    await expect(modal.locator('text=RAG Service Metrics Unavailable')).toBeVisible({ timeout: 3000 });
  });

  test('Modal closes on close button click', async ({ page }) => {
    // Open modal
    const ragStatusCard = page.locator('[data-testid="rag-status-card"]');
    await ragStatusCard.click();
    await waitForModalOpen(page);
    
    const modal = page.locator('[role="dialog"]').filter({ hasText: 'RAG Status Details' });
    await expect(modal).toBeVisible();
    
    // Click close button
    const closeButton = modal.locator('button[aria-label="Close modal"], button:has-text("Close")').first();
    await closeButton.click();
    await expect(modal).not.toBeVisible({ timeout: 3000 });
  });

  test('Modal closes on ESC key', async ({ page }) => {
    // Open modal
    const ragStatusCard = page.locator('[data-testid="rag-status-card"]');
    await ragStatusCard.click();
    await waitForModalOpen(page);
    
    const modal = page.locator('[role="dialog"]').filter({ hasText: 'RAG Status Details' });
    await expect(modal).toBeVisible();
    
    // Press ESC key
    await page.keyboard.press('Escape');
    await expect(modal).not.toBeVisible({ timeout: 3000 });
  });

  test('Modal closes on backdrop click', async ({ page }) => {
    // Open modal
    const ragStatusCard = page.locator('[data-testid="rag-status-card"]');
    await ragStatusCard.click();
    await waitForModalOpen(page);
    
    const modal = page.locator('[role="dialog"]').filter({ hasText: 'RAG Status Details' });
    await expect(modal).toBeVisible();
    
    // Click on backdrop (outside modal content)
    const backdrop = page.locator('.fixed.inset-0').first();
    await backdrop.click({ position: { x: 10, y: 10 } });
    await expect(modal).not.toBeVisible({ timeout: 3000 });
  });

  test('RAG metrics show formatted values (real data)', async ({ page }) => {
    const ragStatusCard = page.locator('[data-testid="rag-status-card"]');
    await expect(ragStatusCard).toBeVisible({ timeout: 15000 });
    await ragStatusCard.click();
    await waitForModalOpen(page);
    const modal = page.locator('[role="dialog"]').filter({ hasText: 'RAG Status Details' });
    await expect(modal.locator('text=Total RAG Calls').first()).toBeVisible({ timeout: 5000 });
    const hasNumericOrPercent = await modal.locator('text=/\\d+(\\.\\d+)?%?|\\d+\\.?\\d*[Kk]?/').first().isVisible().catch(() => false);
    expect(hasNumericOrPercent).toBe(true);
  });

  test.skip('RAG metrics display cache hits and misses (asserts mock values)', async ({ page }) => {
    const ragStatusCard = page.locator('[data-testid="rag-status-card"]');
    await ragStatusCard.click();
    await waitForModalOpen(page);
    const modal = page.locator('[role="dialog"]').filter({ hasText: 'RAG Status Details' });
    const cacheSection = modal.locator('text=Cache Hit Rate').locator('..');
    await expect(cacheSection.locator('text=/\\d+.*hits/')).toBeVisible();
  });

  test.skip('RAG metrics display latency range (asserts mock values)', async ({ page }) => {
    const ragStatusCard = page.locator('[data-testid="rag-status-card"]');
    await ragStatusCard.click();
    await waitForModalOpen(page);
    const modal = page.locator('[role="dialog"]').filter({ hasText: 'RAG Status Details' });
    const latencySection = modal.locator('text=Avg Latency').locator('..');
    await expect(latencySection.locator('text=/\\d+\\.?\\d*-\\d+\\.?\\d*ms/')).toBeVisible();
  });

  test('Modal is accessible (keyboard navigation)', async ({ page }) => {
    // Open modal
    const ragStatusCard = page.locator('[data-testid="rag-status-card"]');
    await ragStatusCard.click();
    await waitForModalOpen(page);
    
    const modal = page.locator('[role="dialog"]').filter({ hasText: 'RAG Status Details' });
    await expect(modal).toBeVisible();
    
    // Verify modal has proper ARIA attributes
    await expect(modal).toHaveAttribute('role', 'dialog');
    await expect(modal).toHaveAttribute('aria-modal', 'true');
    await expect(modal).toHaveAttribute('aria-labelledby', 'rag-modal-title');
    
    // Verify title has proper ID
    const title = modal.locator('#rag-modal-title');
    await expect(title).toBeVisible();
    await expect(title).toHaveText('RAG Status Details');
    
    // Verify close button has aria-label
    const closeButton = modal.locator('button[aria-label="Close modal"]');
    await expect(closeButton).toBeVisible();
  });

  test('Modal works in both light and dark modes', async ({ page }) => {
    // Test in light mode (default)
    const ragStatusCard = page.locator('[data-testid="rag-status-card"]');
    await ragStatusCard.click();
    await waitForModalOpen(page);
    
    let modal = page.locator('[role="dialog"]').filter({ hasText: 'RAG Status Details' });
    await expect(modal).toBeVisible();
    
    // Verify light mode styling (white background)
    const modalContent = modal.locator('.bg-white, .bg-gray-800').first();
    await expect(modalContent).toBeVisible();
    
    // Close modal
    await page.keyboard.press('Escape');
    await expect(modal).not.toBeVisible({ timeout: 3000 });

    // Toggle dark mode (if theme toggle exists)
    const themeToggle = page.locator('[data-testid="theme-toggle"], button[aria-label*="theme"], button[aria-label*="dark"]').first();
    if (await themeToggle.isVisible({ timeout: 2000 })) {
      await themeToggle.click();
      
      // Reopen modal
      await ragStatusCard.click();
      await waitForModalOpen(page);
      
      modal = page.locator('[role="dialog"]').filter({ hasText: 'RAG Status Details' });
      await expect(modal).toBeVisible();
      
      // Verify dark mode styling (dark background)
      const darkModalContent = modal.locator('.bg-gray-800').first();
      await expect(darkModalContent).toBeVisible();
    }
  });
});

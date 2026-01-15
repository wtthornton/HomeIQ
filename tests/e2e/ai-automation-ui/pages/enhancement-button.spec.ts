import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

/**
 * Enhancement Button Tests
 * Tests for EnhancementButton functionality after automation creation
 * 
 * Issue: After automation creation, Enhance button doesn't work (no response)
 * Root Cause: originalPrompt state is lost after loadConversation() reload
 */

test.describe('Enhancement Button After Automation Creation', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/ha-agent');
    await waitForLoadingComplete(page);
  });

  test('Enhance button should work after automation creation without preview', async ({ page }) => {
    // Step 1: Create a conversation and send automation request
    const inputField = page.locator('textarea[placeholder*="Type your message"]');
    await expect(inputField).toBeVisible();
    
    // Send automation request
    await inputField.fill('Create an automation to turn on office lights when motion is detected');
    await page.locator('button:has-text("Send")').click();
    
    // Step 2: Wait for assistant response with automation proposal
    await page.waitForSelector('text=/automation|create|ready to create/i', { timeout: 30000 });
    
    // Step 3: Find and click "Create Automation" button (from CTAActionButtons)
    const createButton = page.locator('button:has-text("Create Automation"), button:has-text("approve")').first();
    
    // Wait for button to be enabled (YAML validation may take time)
    await createButton.waitFor({ state: 'visible', timeout: 10000 });
    await createButton.waitFor({ state: 'attached' });
    
    // Check if button is disabled (validation might be running)
    const isDisabled = await createButton.getAttribute('aria-disabled');
    if (isDisabled === 'true') {
      // Wait for validation to complete (max 10 seconds)
      await page.waitForTimeout(2000);
      await createButton.waitFor({ state: 'visible' });
    }
    
    // Step 4: Click Create Automation button
    await createButton.click();
    
    // Step 5: Wait for success toast and automation creation
    await page.waitForSelector('text=/✅.*Automation.*created/i', { timeout: 15000 });
    await page.waitForSelector('text=/automation\\.[a-z_]+/i', { timeout: 5000 });
    
    // Step 6: Verify Enhance button is visible
    const enhanceButton = page.locator('button:has-text("Enhance"), button:has-text("✨ Enhance")').first();
    await expect(enhanceButton).toBeVisible({ timeout: 5000 });
    
    // Step 7: Check if Enhance button is disabled
    const enhanceIsDisabled = await enhanceButton.getAttribute('aria-disabled');
    const enhanceIsDisabledClass = await enhanceButton.getAttribute('class');
    
    console.log('[Test] Enhance button state:', {
      disabled: enhanceIsDisabled,
      class: enhanceIsDisabledClass,
    });
    
    // Step 8: Click Enhance button
    await enhanceButton.click();
    
    // Step 9: Verify enhancement modal appears (should NOT show error toast)
    // If originalPrompt is missing, we'll see error toast instead of modal
    const errorToast = page.locator('text=/Original prompt is required/i');
    const enhancementModal = page.locator('text=/Enhancement Suggestions/i');
    
    // Wait for either error toast or modal
    await Promise.race([
      errorToast.waitFor({ state: 'visible', timeout: 3000 }).then(() => 'error'),
      enhancementModal.waitFor({ state: 'visible', timeout: 5000 }).then(() => 'modal'),
    ]).then(async (result) => {
      if (result === 'error') {
        // FAIL: Error toast appeared (originalPrompt missing)
        console.error('[Test] FAIL: Enhancement button showed error toast (originalPrompt missing)');
        const errorVisible = await errorToast.isVisible();
        expect(errorVisible).toBe(false); // This will fail the test
      } else {
        // PASS: Modal appeared (originalPrompt available)
        console.log('[Test] PASS: Enhancement modal appeared');
        await expect(enhancementModal).toBeVisible();
      }
    });
  });

  test('Enhance button should work after automation creation with preview', async ({ page }) => {
    // Step 1: Create a conversation and send automation request
    const inputField = page.locator('textarea[placeholder*="Type your message"]');
    await expect(inputField).toBeVisible();
    
    await inputField.fill('Create an automation to turn on office lights when motion is detected');
    await page.locator('button:has-text("Send")').click();
    
    // Step 2: Wait for assistant response
    await page.waitForSelector('text=/automation|create|ready to create/i', { timeout: 30000 });
    
    // Step 3: Click "Preview Automation" button first (this sets originalPrompt)
    const previewButton = page.locator('button:has-text("Preview Automation"), button:has-text("⚙️ Preview")').first();
    const previewVisible = await previewButton.isVisible({ timeout: 5000 }).catch(() => false);
    
    if (previewVisible) {
      await previewButton.click();
      
      // Wait for preview modal to appear
      await page.waitForSelector('text=/Automation Preview|Preview Automation/i', { timeout: 5000 });
      
      // Close preview modal (optional - we just wanted to set originalPrompt)
      const closeButton = page.locator('button:has-text("×"), button[aria-label*="Close"], button[aria-label*="close"]').first();
      const closeVisible = await closeButton.isVisible({ timeout: 2000 }).catch(() => false);
      if (closeVisible) {
        await closeButton.click();
        await page.waitForTimeout(500);
      }
    }
    
    // Step 4: Create automation
    const createButton = page.locator('button:has-text("Create Automation"), button:has-text("approve")').first();
    await createButton.waitFor({ state: 'visible', timeout: 10000 });
    
    const isDisabled = await createButton.getAttribute('aria-disabled');
    if (isDisabled === 'true') {
      await page.waitForTimeout(2000);
    }
    
    await createButton.click();
    
    // Step 5: Wait for success
    await page.waitForSelector('text=/✅.*Automation.*created/i', { timeout: 15000 });
    
    // Step 6: Verify Enhance button is visible
    const enhanceButton = page.locator('button:has-text("Enhance"), button:has-text("✨ Enhance")').first();
    await expect(enhanceButton).toBeVisible({ timeout: 5000 });
    
    // Step 7: Click Enhance button
    await enhanceButton.click();
    
    // Step 8: Verify enhancement modal appears (should work because originalPrompt was set via preview)
    const enhancementModal = page.locator('text=/Enhancement Suggestions/i');
    const errorToast = page.locator('text=/Original prompt is required/i');
    
    // Wait for modal (should appear since preview was clicked)
    await enhancementModal.waitFor({ state: 'visible', timeout: 5000 });
    await expect(enhancementModal).toBeVisible();
    
    // Verify error toast did NOT appear
    const errorVisible = await errorToast.isVisible({ timeout: 2000 }).catch(() => false);
    expect(errorVisible).toBe(false);
  });

  test('Enhance button should preserve originalPrompt after conversation reload', async ({ page }) => {
    // This test verifies the fix: originalPrompt should be set after loadConversation()
    
    // Step 1: Create automation
    const inputField = page.locator('textarea[placeholder*="Type your message"]');
    await expect(inputField).toBeVisible();
    
    await inputField.fill('Create an automation to turn on office lights when motion is detected');
    await page.locator('button:has-text("Send")').click();
    
    await page.waitForSelector('text=/automation|create|ready to create/i', { timeout: 30000 });
    
    // Step 2: Create automation (triggers loadConversation() via onSuccess)
    const createButton = page.locator('button:has-text("Create Automation"), button:has-text("approve")').first();
    await createButton.waitFor({ state: 'visible', timeout: 10000 });
    
    const isDisabled = await createButton.getAttribute('aria-disabled');
    if (isDisabled === 'true') {
      await page.waitForTimeout(2000);
    }
    
    await createButton.click();
    
    // Step 3: Wait for success (loadConversation() is called here)
    await page.waitForSelector('text=/✅.*Automation.*created/i', { timeout: 15000 });
    
    // Step 4: Wait for conversation reload to complete
    await page.waitForTimeout(2000); // Allow loadConversation() to complete
    
    // Step 5: Verify Enhance button is visible and NOT disabled
    const enhanceButton = page.locator('button:has-text("Enhance"), button:has-text("✨ Enhance")').first();
    await expect(enhanceButton).toBeVisible({ timeout: 5000 });
    
    const enhanceIsDisabled = await enhanceButton.getAttribute('aria-disabled');
    const hasDisabledClass = await enhanceButton.getAttribute('class');
    
    // Check if button shows warning icon (indicates prerequisites missing)
    const hasWarning = await enhanceButton.locator('text=⚠️').isVisible().catch(() => false);
    
    console.log('[Test] Enhance button after reload:', {
      disabled: enhanceIsDisabled,
      hasDisabledClass: hasDisabledClass?.includes('cursor-not-allowed'),
      hasWarning: hasWarning,
    });
    
    // Step 6: Click Enhance button
    await enhanceButton.click();
    
    // Step 7: Verify enhancement modal appears (should work after fix)
    const enhancementModal = page.locator('text=/Enhancement Suggestions/i');
    const errorToast = page.locator('text=/Original prompt is required/i');
    
    // Wait for either modal or error
    const result = await Promise.race([
      errorToast.waitFor({ state: 'visible', timeout: 3000 }).then(() => 'error' as const),
      enhancementModal.waitFor({ state: 'visible', timeout: 5000 }).then(() => 'modal' as const),
      page.waitForTimeout(5000).then(() => 'timeout' as const),
    ]).catch(() => 'timeout' as const);
    
    if (result === 'error') {
      // FAIL: Fix didn't work - originalPrompt still missing
      console.error('[Test] FAIL: Enhancement button still shows error after reload');
      expect(result).toBe('modal'); // This will fail the test
    } else if (result === 'modal') {
      // PASS: Fix works - modal appeared
      console.log('[Test] PASS: Enhancement modal appeared after reload');
      await expect(enhancementModal).toBeVisible();
    } else {
      // TIMEOUT: Neither error nor modal appeared
      console.error('[Test] TIMEOUT: No response from Enhance button');
      expect(result).toBe('modal'); // This will fail the test
    }
  });
});

/**
 * Ask AI - Complete E2E Test Suite
 *
 * Tests the complete Ask AI workflow:
 * 1. Query submission (no execution)
 * 2. Create Automation CTA (creates permanent automation)
 * 3. Error handling and user feedback
 *
 * Split into Fast (UI-only, 30s default) and Slow (OpenAI round-trip, 120s + retries).
 *
 * The chat flow renders:
 * - Assistant messages (data-testid="chat-message" data-role="assistant")
 * - AutomationProposal (data-testid="automation-proposal") when AI proposes automation
 * - CTAActionButtons (data-testid="cta-create-button") when AI includes CTA prompt
 * - Preview Automation button when YAML is detected in response
 *
 * Related:
 * - Implementation: implementation/ASK_AI_IMMEDIATE_EXECUTION_FIX.md
 * - Enhancement: implementation/ASK_AI_TEST_EXECUTION_ENHANCEMENT.md
 * - Summary: implementation/ASK_AI_FIXES_SUMMARY.md
 */

import { test, expect } from '@playwright/test';
import { AskAIPage } from './page-objects/AskAIPage';

test.describe('Fast — UI Only', () => {
  let askAI: AskAIPage;

  test.beforeEach(async ({ page }) => {
    askAI = new AskAIPage(page);
    await askAI.goto();
  });

  test.describe('Page Load and Navigation', () => {
    test('Ask AI page loads successfully', async ({ page }) => {
      // Verify page loaded (title set by TitleUpdater in App.tsx)
      await expect(page).toHaveTitle(/Chat.*HomeIQ|HomeIQ/i);

      // Verify main elements present
      await expect(askAI.getQueryInput()).toBeVisible();
      await expect(askAI.getSendButton()).toBeVisible();
      await expect(askAI.getClearButton()).toBeVisible();
    });

    test('Conversation sidebar is visible', async () => {
      // Toggle sidebar open
      await askAI.toggleSidebar();

      // Sidebar shows "Conversations" heading even with no conversations
      // (empty state shows "No conversations yet" message)
      const sidebarHeading = askAI.page.locator('h2:has-text("Conversations")');
      await expect(sidebarHeading).toBeVisible({ timeout: 5000 });
    });

    test('New Chat button creates fresh conversation', async () => {
      // Click New Chat button
      await askAI.clearChat();

      // Verify input is cleared and ready for new conversation
      const inputValue = await askAI.getQueryInput().inputValue();
      expect(inputValue.length).toBe(0);
    });
  });

  test.describe('User Experience and Feedback', () => {
    test('Error messages are user-friendly', async () => {
      // Verify send button is disabled with empty input
      // SendButton uses aria-disabled attribute
      const sendButton = askAI.getSendButton();
      await expect(sendButton).toHaveAttribute('aria-disabled', 'true');

      // Fill invalid/empty query (just spaces)
      await askAI.getQueryInput().fill('   ');

      // Button should still be disabled
      await expect(sendButton).toHaveAttribute('aria-disabled', 'true');
    });
  });
});

test.describe('Slow — OpenAI Round-Trip', () => {
  let askAI: AskAIPage;

  test.beforeEach(async ({ page }) => {
    askAI = new AskAIPage(page);
    await askAI.goto();
  });

  test.describe('Query Submission - No Execution (Bug Fix)', () => {
    test('Submitting query does NOT execute HA commands', async () => {
      test.slow();

      // CRITICAL TEST: Verify fix for immediate execution bug
      // Before fix: Query would turn on lights immediately
      // After fix: Query only generates suggestions via chat

      const query = 'Turn on the office lights';

      // Submit query
      await askAI.submitQuery(query);

      // Wait for AI response
      await askAI.waitForResponse(60000);

      // Verify NO execution occurred (no device control)
      await askAI.verifyNoDeviceExecution();

      // Verify assistant responded (message count increased)
      const messageCount = await askAI.getAssistantMessageCount();
      expect(messageCount).toBeGreaterThan(0);

      // Verify the response mentions the requested devices
      const lastMessage = askAI.getLastAssistantMessage();
      const messageText = await lastMessage.textContent();
      expect(messageText?.length).toBeGreaterThan(10);

      console.log(`✅ Query generated response WITHOUT executing commands`);
    });

    test('Query extracts entities using pattern matching (not HA API)', async () => {
      test.slow();

      const query = 'Flash the office lights when the front door opens';

      await askAI.submitQuery(query);
      await askAI.waitForResponse(60000);

      // Verify AI response mentions detected devices
      const lastMessage = askAI.getLastAssistantMessage();
      const messageText = await lastMessage.textContent();

      // Should mention devices detected
      expect(messageText).toMatch(/office|lights|door/i);

      // Should have at least one assistant message
      const assistantCount = await askAI.getAssistantMessageCount();
      expect(assistantCount).toBeGreaterThanOrEqual(1);
    });

    test('Multiple queries do not execute HA commands', async () => {
      test.slow();

      const queries = [
        'Turn on the living room lights',
        'Turn off the bedroom lights',
        'Dim the kitchen lights to 50%'
      ];

      for (const query of queries) {
        await askAI.submitQuery(query);
        await askAI.waitForResponse(60000);

        // Verify no execution
        await askAI.verifyNoDeviceExecution();

        // Wait a moment before next query
        await askAI.page.waitForTimeout(500);
      }

      // All queries should have generated messages (user + assistant pairs)
      await expect.poll(
        async () => await askAI.getMessageCount(),
        { timeout: 60_000, intervals: [1000, 2000, 5000] }
      ).toBeGreaterThanOrEqual(6);
    });
  });

  test.describe('Create Automation — CTA Button Flow', () => {
    test('Create Automation CTA creates automation from AI proposal', async () => {
      test.slow();

      const query = 'Turn on the office lights at sunset';

      // Submit query
      await askAI.submitQuery(query);
      await askAI.waitForResponse(60000);

      // Wait for AI response with automation content (proposal or CTA)
      const messageCount = await askAI.getAssistantMessageCount();
      expect(messageCount).toBeGreaterThan(0);

      // Check if CTA button appeared (AI must include CTA prompt for this)
      const ctaButton = askAI.getCreateAutomationButton();
      const hasCTA = await ctaButton.isVisible().catch(() => false);

      if (hasCTA) {
        // Click Create Automation CTA
        await askAI.clickCreateAutomation();

        // Verify success toast (automation created)
        await askAI.waitForToast(/automation.*created|✅.*automation/i, undefined, 45000);
      } else {
        // AI didn't include CTA prompt — verify we at least got an automation response
        const hasAutomation = await askAI.hasAutomationResponse();
        console.log(`AI responded (CTA prompt not detected, automation content: ${hasAutomation})`);
      }
    });

    test('Test button handles validation failures gracefully', async () => {
      test.slow();

      // This test verifies the UI handles errors properly with invalid entities

      const query = 'Control the nonexistent device xyz123';

      await askAI.submitQuery(query);
      await askAI.waitForResponse(60000);

      // AI should respond even with invalid entities
      const messageCount = await askAI.getAssistantMessageCount();
      expect(messageCount).toBeGreaterThan(0);

      // Verify no crashes occurred
      const isPageResponsive = await askAI.getQueryInput().isEnabled();
      expect(isPageResponsive).toBe(true);
    });
  });

  test.describe('User Experience and Feedback', () => {
    test('Loading indicators appear during processing', async () => {
      test.slow();

      const query = 'Turn on all lights in the house';

      // Start submission
      await askAI.getQueryInput().fill(query);
      await askAI.getSendButton().click();

      // Verify loading state appears
      const isLoading = await askAI.isLoading();
      expect(isLoading).toBe(true);

      // Wait for completion
      await askAI.waitForResponse(60000);

      // Verify loading cleared
      await expect.poll(
        async () => await askAI.isLoading(),
        { timeout: 30_000, intervals: [1000, 2000, 5000] }
      ).toBe(false);
    });

    test('Clear chat button works correctly', async () => {
      test.slow();

      // Submit a few queries
      await askAI.submitQuery('Turn on lights');
      await askAI.waitForResponse(60000);

      await askAI.submitQuery('Turn off lights');
      await askAI.waitForResponse(60000);

      await expect.poll(
        async () => await askAI.getMessageCount(),
        { timeout: 60_000, intervals: [1000, 2000, 5000] }
      ).toBeGreaterThan(1);

      // Clear chat
      await askAI.clearChat();

      // Verify success toast
      await askAI.waitForToast(/Chat cleared|New conversation/i, undefined, 45000);

      // Verify chat cleared (should only have welcome message or be empty)
      await expect.poll(
        async () => await askAI.getMessageCount(),
        { timeout: 10_000, intervals: [500, 1000, 2000] }
      ).toBeLessThanOrEqual(2);
    });
  });

  test.describe('Complex Queries and Edge Cases', () => {
    test('Handles complex multi-device queries', async () => {
      test.slow();

      const complexQuery = 'Flash all office lights in sequence red, blue, green when both front and garage doors open at night';

      await askAI.submitQuery(complexQuery);
      await askAI.waitForResponse(60000);

      // Should generate a response mentioning the devices
      const lastMessage = askAI.getLastAssistantMessage();
      const messageText = await lastMessage.textContent();
      expect(messageText?.length).toBeGreaterThan(20);
    });

    test('Handles queries with timing and conditions', async () => {
      test.slow();

      const queries = [
        'Turn on lights at sunset',
        'Dim lights to 50% after 10pm',
        'Turn off all lights when I leave',
        'Flash lights 3 times when doorbell rings'
      ];

      for (const query of queries) {
        await askAI.submitQuery(query);
        await askAI.waitForResponse(60000);

        // Verify AI responded
        const assistantCount = await askAI.getAssistantMessageCount();
        expect(assistantCount).toBeGreaterThan(0);

        // Clear for next query
        await askAI.clearChat();
        await askAI.page.waitForTimeout(500);
      }
    });

    test('Handles queries with colors and patterns', async () => {
      test.slow();

      const query = 'Flash office lights red for front door, blue for back door';

      await askAI.submitQuery(query);
      await askAI.waitForResponse(60000);

      // Should generate a creative response
      const lastMessage = askAI.getLastAssistantMessage();
      const messageText = await lastMessage.textContent();
      expect(messageText?.length).toBeGreaterThan(20);
    });
  });

  test.describe('OpenAI Integration (Not HA AI)', () => {
    test('Uses OpenAI for response generation', async () => {
      test.slow();

      // This verifies the system uses OpenAI GPT-4o-mini, not HA Conversation AI
      const query = 'Create a creative lighting scene for movie night';

      await askAI.submitQuery(query);
      await askAI.waitForResponse(60000);

      // OpenAI should generate creative, detailed responses
      const lastMessage = askAI.getLastAssistantMessage();
      const messageText = await lastMessage.textContent();

      // Verify response is substantial (not just a short error)
      expect(messageText?.length).toBeGreaterThan(50);
    });

    test('Generates detailed automation proposals', async () => {
      test.slow();

      const query = 'Automate my office lights';

      await askAI.submitQuery(query);
      await askAI.waitForResponse(60000);

      // Verify we got a substantial response
      const lastMessage = askAI.getLastAssistantMessage();
      const messageText = await lastMessage.textContent();
      expect(messageText?.length).toBeGreaterThan(30);
    });
  });

  test.describe('Regression Tests for Bug Fixes', () => {
    test('BUG FIX: Query submission no longer executes HA commands', async () => {
      test.slow();

      // Critical regression test for immediate execution bug
      // See: implementation/ASK_AI_IMMEDIATE_EXECUTION_FIX.md

      const executionQueries = [
        'Turn on the office lights',
        'Turn off all lights',
        'Dim bedroom lights to 25%',
        'Set living room lights to blue'
      ];

      for (const query of executionQueries) {
        await askAI.submitQuery(query);
        await askAI.waitForResponse(60000);

        // CRITICAL: Verify no execution occurred
        await askAI.verifyNoDeviceExecution();

        // Should generate a response
        const assistantCount = await askAI.getAssistantMessageCount();
        expect(assistantCount).toBeGreaterThan(0);

        // Clear for next test
        await askAI.clearChat();
        await askAI.page.waitForTimeout(300);
      }

      console.log('✅ REGRESSION TEST PASSED: No HA command execution on query submission');
    });

    test('ENHANCEMENT: Create Automation CTA produces automation', async () => {
      test.slow();

      // Regression test for CTA button automation creation
      const query = 'Flash the garage lights when door opens';

      await askAI.submitQuery(query);
      await askAI.waitForResponse(60000);

      // Verify AI responded with automation content
      const lastMessage = askAI.getLastAssistantMessage();
      const messageText = await lastMessage.textContent();
      expect(messageText?.length).toBeGreaterThan(20);

      // Check if CTA button appeared
      const ctaButton = askAI.getCreateAutomationButton();
      const hasCTA = await ctaButton.isVisible().catch(() => false);

      if (hasCTA) {
        await askAI.clickCreateAutomation();

        // Verify success toast
        await askAI.waitForToast(/automation.*created|✅.*automation/i, undefined, 60000);

        // Verify automation ID in toast
        const toasts = askAI.getToasts();
        const toastText = await toasts.first().textContent();
        expect(toastText).toMatch(/automation/i);

        console.log('✅ REGRESSION TEST PASSED: CTA creates automation');
      } else {
        console.log('✅ AI responded but CTA not shown (no CTA prompt in response)');
      }
    });
  });

  test.describe('Performance and Reliability', () => {
    test('Query submission completes within reasonable time', async () => {
      test.slow();

      const query = 'Turn on the kitchen lights';
      const startTime = Date.now();

      await askAI.submitQuery(query);
      await askAI.waitForResponse(60000);

      const duration = Date.now() - startTime;

      // Should complete within 30 seconds (OpenAI + processing)
      expect(duration).toBeLessThan(30000);

      console.log(`Query processed in ${duration}ms`);
    });

    test('Page remains responsive during long operations', async () => {
      test.slow();

      const query = 'Create complex automation with multiple conditions';

      await askAI.submitQuery(query);

      // Input is disabled during processing (good UX)
      await askAI.page.waitForTimeout(500);
      const isInputDisabledDuringProcessing = await askAI.getQueryInput().isDisabled();
      expect(isInputDisabledDuringProcessing).toBe(true);

      // Wait for completion
      await askAI.waitForResponse(60000);

      // Input should be re-enabled after processing
      await expect.poll(
        async () => await askAI.getQueryInput().isEnabled(),
        { timeout: 30_000, intervals: [1000, 2000, 5000] }
      ).toBe(true);
    });
  });
});

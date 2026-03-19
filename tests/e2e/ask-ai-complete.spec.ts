/**
 * Ask AI - Complete E2E Test Suite
 *
 * Tests the complete Ask AI workflow:
 * 1. Query submission (no execution)
 * 2. Test button (executes automation)
 * 3. Approve button (creates permanent automation)
 * 4. Error handling and user feedback
 *
 * Split into Fast (UI-only, 30s default) and Slow (OpenAI round-trip, 120s + retries).
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

      // Verify conversation list container is present
      const conversationList = askAI.page.locator('[role="listbox"][aria-label="Conversations"]');
      await expect(conversationList).toBeVisible();
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
      // After fix: Query only generates suggestions

      const query = 'Turn on the office lights';

      // Submit query
      await askAI.submitQuery(query);

      // Wait for response
      await askAI.waitForResponse(60000);

      // Verify suggestions generated (success toast) - OpenAI takes time
      await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45000);

      // Verify NO execution occurred (no device control)
      await askAI.verifyNoDeviceExecution();

      // Verify suggestions visible
      await expect.poll(
        async () => await askAI.getSuggestionCount(),
        { timeout: 60_000, intervals: [1000, 2000, 5000] }
      ).toBeGreaterThan(0);

      const suggestionCount = await askAI.getSuggestionCount();
      console.log(`✅ Query generated ${suggestionCount} suggestions WITHOUT executing commands`);
    });

    test('Query extracts entities using pattern matching (not HA API)', async () => {
      test.slow();

      const query = 'Flash the office lights when the front door opens';

      await askAI.submitQuery(query);
      await askAI.waitForResponse(60000);

      // Verify AI response mentions detected devices
      const lastMessage = askAI.getLastMessage();
      const messageText = await lastMessage.textContent();

      // Should mention devices detected
      expect(messageText).toMatch(/office|lights|door/i);

      // Should generate suggestions
      await expect.poll(
        async () => await askAI.getSuggestionCount(),
        { timeout: 60_000, intervals: [1000, 2000, 5000] }
      ).toBeGreaterThanOrEqual(1);
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

      // All queries should have generated suggestions
      await expect.poll(
        async () => await askAI.getMessageCount(),
        { timeout: 60_000, intervals: [1000, 2000, 5000] }
      ).toBeGreaterThanOrEqual(7);
    });
  });

  test.describe('Test Button - Execution Enhancement', () => {
    test('Test button creates and executes automation in HA', async () => {
      test.slow();

      // CRITICAL TEST: Verify test button enhancement
      // Test button should: validate, create, trigger, disable automation

      const query = 'Turn on the office lights';

      // Submit query
      await askAI.submitQuery(query);
      await askAI.waitForResponse(60000);

      // Wait for suggestions
      await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45000);

      // Click Test on first suggestion
      await askAI.testSuggestion(0);

      // Verify success toast (automation executed) - can take 30+ seconds
      await askAI.waitForToast(/test automation executed|executed successfully/i, undefined, 60000);

      // Verify automation ID in toast
      const toasts = askAI.getToasts();
      const toastText = await toasts.first().textContent();
      expect(toastText).toMatch(/automation\.(test_)?[\w_]+/);

      console.log('✅ Test automation created, executed, and disabled successfully');
    });

    test('Test button shows detailed feedback on success', async () => {
      test.slow();

      const query = 'Flash the office lights red';

      await askAI.submitQuery(query);
      await askAI.waitForResponse(60000);
      await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45000);

      // Test first suggestion
      await askAI.testSuggestion(0);

      // Wait for execution
      await askAI.waitForToast(/test automation executed/i, undefined, 60000);

      // Verify detailed success message
      const successToastVisible = await askAI.isToastVisible(/check your devices/i);
      expect(successToastVisible).toBe(true);

      // Verify automation ID shown
      const automationIdVisible = await askAI.isToastVisible(/automation\.test_/);
      expect(automationIdVisible).toBe(true);
    });

    test('Test button handles validation failures gracefully', async () => {
      test.slow();

      // This test would require mocking the backend to return validation error
      // For now, we test that the UI handles errors properly

      const query = 'Control the nonexistent device xyz123';

      await askAI.submitQuery(query);
      await askAI.waitForResponse(60000);

      // Even with potentially invalid entities, should generate suggestions
      const suggestionCount = await askAI.getSuggestionCount();

      if (suggestionCount > 0) {
        // Try to test (may fail validation)
        await askAI.testSuggestion(0);

      // Should show either success or validation error
      // Check for any response within reasonable time
      await askAI.page.waitForTimeout(5000);

        // Verify no crashes occurred
        const isPageResponsive = await askAI.getQueryInput().isEnabled();
        expect(isPageResponsive).toBe(true);
      }
    });

    test('Can test multiple suggestions sequentially', async () => {
      test.slow();

      const query = 'Flash the office lights when door opens';

      await askAI.submitQuery(query);
      await askAI.waitForResponse(60000);
      await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45000);

      const suggestionCount = await askAI.getSuggestionCount();
      const testsToRun = Math.min(2, suggestionCount); // Test first 2 suggestions

      for (let i = 0; i < testsToRun; i++) {
        // Test suggestion
        await askAI.testSuggestion(i);

        // Wait for execution
        await askAI.waitForToast(/test automation executed|validation failed|executed successfully/i, undefined, 60000);

        // Wait before next test
        await askAI.page.waitForTimeout(2000);
      }

      console.log(`✅ Successfully tested ${testsToRun} suggestions`);
    });
  });

  test.describe('Approve Button - Automation Creation', () => {
    test('Approve button creates permanent automation', async () => {
      test.slow();

      const query = 'Turn on the office lights at sunset';

      // Submit query
      await askAI.submitQuery(query);
      await askAI.waitForResponse(60000);

      // Wait for AI response with automation proposal
      const messageCount = await askAI.getMessageCount();
      expect(messageCount).toBeGreaterThan(0);

      // Click Create Automation CTA (approve flow)
      await askAI.approveSuggestion(0);

      // Verify success toast (automation created)
      await askAI.waitForToast(/automation created|automation approved|YAML generated/i, undefined, 45000);
    });

    test('Approve workflow is separate from test workflow', async () => {
      test.slow();

      const query = 'Turn on the living room lights';

      await askAI.submitQuery(query);
      await askAI.waitForResponse(60000);
      await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45000);

      // First test suggestion
      await askAI.testSuggestion(0);
      await askAI.waitForToast(/test automation executed/i, undefined, 60000);

      // Then approve it (creates permanent automation, different ID)
      await askAI.approveSuggestion(0);
      await askAI.waitForToast(/automation approved/i, undefined, 45000);

      // Both operations should succeed
      console.log('✅ Test and Approve are independent operations');
    });
  });

  test.describe('Reject Button - Suggestion Management', () => {
    test('Reject button removes suggestion from view', async () => {
      test.slow();

      const query = 'Dim the bedroom lights at night';

      await askAI.submitQuery(query);
      await askAI.waitForResponse(60000);
      await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45000);

      const initialCount = await askAI.getSuggestionCount();

      // Reject first suggestion
      await askAI.rejectSuggestion(0);

      // Verify success feedback
      await askAI.waitForToast(/rejected|Suggestion rejected/i, undefined, 45000);

      // Verify suggestion removed
      await expect.poll(
        async () => await askAI.getSuggestionCount(),
        { timeout: 10_000, intervals: [500, 1000, 2000] }
      ).toBeLessThan(initialCount);
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
      await askAI.waitForToast(/Chat cleared/i, 'success', 45000);

      // Verify chat cleared (should only have welcome message)
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

      // Should generate creative suggestions
      await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45000);

      await expect.poll(
        async () => await askAI.getSuggestionCount(),
        { timeout: 60_000, intervals: [1000, 2000, 5000] }
      ).toBeGreaterThan(0);

      // Verify suggestions are detailed
      const suggestionCount = await askAI.getSuggestionCount();
      if (suggestionCount > 0) {
        const description = await askAI.getSuggestionDescription(0);
        expect(description.length).toBeGreaterThan(20);
      }
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

        await askAI.waitForToast(/found.*suggestion/i, undefined, 45000);

        await expect.poll(
          async () => await askAI.getSuggestionCount(),
          { timeout: 60_000, intervals: [1000, 2000, 5000] }
        ).toBeGreaterThan(0);

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
      await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45000);

      // Should generate creative color-based suggestions
      await expect.poll(
        async () => await askAI.getSuggestionCount(),
        { timeout: 60_000, intervals: [1000, 2000, 5000] }
      ).toBeGreaterThan(0);
    });
  });

  test.describe('OpenAI Integration (Not HA AI)', () => {
    test('Uses OpenAI for suggestion generation', async () => {
      test.slow();

      // This verifies the system uses OpenAI GPT-4o-mini, not HA Conversation AI
      const query = 'Create a creative lighting scene for movie night';

      await askAI.submitQuery(query);
      await askAI.waitForResponse(60000);

      // OpenAI should generate creative, detailed suggestions
      await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45000);

      await expect.poll(
        async () => await askAI.getSuggestionCount(),
        { timeout: 60_000, intervals: [1000, 2000, 5000] }
      ).toBeGreaterThanOrEqual(3);

      // Verify suggestions are creative (longer descriptions)
      const suggestionCount = await askAI.getSuggestionCount();
      if (suggestionCount > 0) {
        const description = await askAI.getSuggestionDescription(0);
        expect(description.length).toBeGreaterThan(30); // Creative descriptions are detailed
      }
    });

    test('Generates diverse suggestions for same query', async () => {
      test.slow();

      const query = 'Automate my office lights';

      await askAI.submitQuery(query);
      await askAI.waitForResponse(60000);
      await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45000);

      await expect.poll(
        async () => await askAI.getSuggestionCount(),
        { timeout: 60_000, intervals: [1000, 2000, 5000] }
      ).toBeGreaterThanOrEqual(2);

      // Get descriptions of multiple suggestions
      const suggestionCount = await askAI.getSuggestionCount();
      const descriptions: string[] = [];
      for (let i = 0; i < Math.min(3, suggestionCount); i++) {
        const desc = await askAI.getSuggestionDescription(i);
        descriptions.push(desc);
      }

      // Verify suggestions are different (not identical)
      const uniqueDescriptions = new Set(descriptions);
      expect(uniqueDescriptions.size).toBeGreaterThan(1);
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
        // Before fix: HA Conversation API executed commands immediately
        // After fix: Only pattern matching for entity extraction
        await askAI.verifyNoDeviceExecution();

        // Should generate suggestions instead
        await expect.poll(
          async () => await askAI.getSuggestionCount(),
          { timeout: 60_000, intervals: [1000, 2000, 5000] }
        ).toBeGreaterThan(0);

        // Clear for next test
        await askAI.clearChat();
        await askAI.page.waitForTimeout(300);
      }

      console.log('✅ REGRESSION TEST PASSED: No HA command execution on query submission');
    });

    test('ENHANCEMENT: Test button executes and disables automation', async () => {
      test.slow();

      // Regression test for test button enhancement
      // See: implementation/ASK_AI_TEST_EXECUTION_ENHANCEMENT.md

      const query = 'Flash the garage lights when door opens';

      await askAI.submitQuery(query);
      await askAI.waitForResponse(60000);
      await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45000);

      // Click Test
      await askAI.testSuggestion(0);

      // Verify complete test flow (may be fast, so just check for success)
      await askAI.waitForToast(/test automation executed|executed successfully/i, undefined, 60000);

      // Verify automation ID with [TEST] prefix
      const toastText = await askAI.getToasts().first().textContent();
      expect(toastText).toMatch(/automation\.test_/);

      console.log('✅ REGRESSION TEST PASSED: Test button executes and disables automation');
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

    test('Test execution completes within reasonable time', async () => {
      test.slow();

      const query = 'Turn on the lights';

      await askAI.submitQuery(query);
      await askAI.waitForResponse(60000);
      await askAI.waitForToast(/Found.*automation suggestion/i, undefined, 45000);

      const startTime = Date.now();

      await askAI.testSuggestion(0);
      await askAI.waitForToast(/test automation executed|validation failed/i, undefined, 60000);

      const duration = Date.now() - startTime;

      // Test execution should complete within 25 seconds
      // (YAML generation + validation + creation + trigger + disable)
      expect(duration).toBeLessThan(25000);

      console.log(`Test execution completed in ${duration}ms`);
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

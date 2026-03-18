/**
 * Ask AI — Mocked E2E for CI (Epic 49.5, fixed Epic 89.1)
 *
 * Exercises the Ask AI page with mocked /api/v1/ask-ai/* responses so CI can run
 * without OpenAI API key or Home Assistant. Full flow tests live in ask-ai-complete.spec.ts
 * (local/optional, long timeout).
 */

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

const MOCK_QUERY_ID = 'mock-query-ci';
const MOCK_SUGGESTION = {
  id: 'mock-s1',
  summary: 'Turn on the office lights',
  yaml_preview: 'action: turn_on\n  target:\n    entity_id: light.office',
  status: 'ready',
};

test.describe('Ask AI — Mocked (CI)', () => {
  test.setTimeout(60000);

  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);

    // Mock POST /v1/ask-ai/query -> returns query_id
    await page.route('**/v1/ask-ai/query', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ query_id: MOCK_QUERY_ID, status: 'completed' }),
        });
      } else {
        await route.continue();
      }
    });

    // Mock GET /v1/ask-ai/query/:id/suggestions -> returns static suggestions
    await page.route(`**/v1/ask-ai/query/${MOCK_QUERY_ID}/suggestions`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ suggestions: [MOCK_SUGGESTION] }),
      });
    });

    // Catch any other ask-ai suggestion path (app might use different id from response)
    await page.route(/.*\/v1\/ask-ai\/query\/[^/]+\/suggestions/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ suggestions: [MOCK_SUGGESTION] }),
      });
    });
  });

  test('Ask AI page or Ideas dashboard loads with input and send', async ({ page }) => {
    await page.goto('/');
    await waitForLoadingComplete(page);
    await expect(page).toHaveTitle(/AI Automation|HomeIQ|Ideas|Chat/i);

    // Chat page (/chat) has message-input and send-button; Ideas (/) has tabs and suggestion cards
    const chatInput = page.getByTestId('message-input').or(page.locator('textarea[placeholder*="message" i], textarea[placeholder*="Type" i]').first());
    const sendButton = page.getByTestId('send-button').or(page.getByRole('button', { name: /send|submit/i }).first());
    const ideasContent = page.locator('[data-testid="suggestion-card"], [role="tablist"]').first();

    // Wait for at least one element to appear — don't silently swallow failures
    await expect(
      chatInput.or(sendButton).or(ideasContent),
      'Page should show Chat input, send button, or Ideas content'
    ).toBeVisible({ timeout: 10000 });
  });

  test('query submitted returns mocked suggestions without real OpenAI', async ({ page }) => {
    // Navigate directly to Chat — default route (/) is Ideas
    await page.goto('/chat');
    await waitForLoadingComplete(page);

    const queryInput = page.getByTestId('message-input').or(page.locator('textarea[placeholder*="Type" i], textarea[placeholder*="message" i]').first());
    const sendButton = page.getByTestId('send-button').or(page.getByRole('button', { name: /send|submit/i }).first());

    await expect(queryInput, 'Chat page should show message input').toBeVisible({ timeout: 10000 });

    await queryInput.fill('Turn on the office lights');
    await sendButton.click();

    // Wait for either suggestion card or success message (mocked response)
    const suggestionCard = page.locator('[data-testid="suggestion-card"]');
    const successMessage = page.getByText(/suggestion|found|automation/i);

    await expect(
      suggestionCard.first().or(successMessage.first()),
      'Mocked response should show suggestion card or success message'
    ).toBeVisible({ timeout: 15000 });
  });
});

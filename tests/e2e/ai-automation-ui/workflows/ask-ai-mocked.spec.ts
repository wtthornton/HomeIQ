/**
 * Ask AI — Mocked E2E for CI (Epic 49.5)
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
  test.setTimeout(30000);

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

    await page.goto('/');
    await waitForLoadingComplete(page);
  });

  test('Ask AI page or Ideas dashboard loads with input and send', async ({ page }) => {
    await expect(page).toHaveTitle(/AI Automation|HomeIQ|Ideas|Chat/i);

    // Chat page (/chat) has message-input and send-button; Ideas (/) has tabs and suggestion cards
    const chatInput = page.getByTestId('message-input').or(page.locator('textarea[placeholder*="message" i], textarea[placeholder*="Type" i]').first());
    const sendButton = page.getByTestId('send-button').or(page.getByRole('button', { name: /send|submit/i }).first());
    const ideasContent = page.locator('[data-testid="suggestion-card"], [role="tablist"]').first();

    const hasChatInput = await chatInput.isVisible({ timeout: 6000 }).catch(() => false);
    const hasSend = await sendButton.isVisible({ timeout: 4000 }).catch(() => false);
    const hasIdeas = await ideasContent.isVisible({ timeout: 4000 }).catch(() => false);

    expect(hasChatInput || hasSend || hasIdeas, 'Page should show Chat input/send or Ideas content').toBe(true);
  });

  test('query submitted returns mocked suggestions without real OpenAI', async ({ page }) => {
    // Chat view has message-input; default route (/) is Ideas — ensure we're on Chat
    await page.goto('/chat');
    await waitForLoadingComplete(page);

    const queryInput = page.getByTestId('message-input').or(page.locator('textarea[placeholder*="Type" i], textarea[placeholder*="message" i]').first());
    const sendButton = page.getByTestId('send-button').or(page.getByRole('button', { name: /send|submit/i }).first());

    await expect(queryInput, 'Chat page should show message input').toBeVisible({ timeout: 10000 });

    await queryInput.fill('Turn on the office lights');
    await sendButton.click();

    // Wait for either suggestion card or success toast (mocked response)
    const suggestionCard = page.locator('[data-testid="suggestion-card"]');
    const successToast = page.getByText(/suggestion|found|automation/i);
    await Promise.race([
      suggestionCard.first().waitFor({ state: 'visible', timeout: 15000 }),
      successToast.first().waitFor({ state: 'visible', timeout: 15000 }),
    ]).catch(() => {});

    const hasSuggestion = await suggestionCard.first().isVisible({ timeout: 3000 }).catch(() => false);
    const hasToast = await successToast.first().isVisible({ timeout: 2000 }).catch(() => false);

    expect(hasSuggestion || hasToast, 'Mocked response should show suggestion or success message').toBe(true);
  });
});

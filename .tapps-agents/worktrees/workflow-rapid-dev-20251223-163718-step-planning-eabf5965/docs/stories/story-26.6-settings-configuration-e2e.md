# Story 26.6: Settings & Configuration E2E Tests

## Status
Draft

## Story

**As a** QA engineer,
**I want** comprehensive E2E tests for settings and configuration management,
**so that** we can ensure users can reliably configure API keys, Home Assistant connection, and analysis preferences with proper validation and persistence.

## Acceptance Criteria

1. **Test Coverage:** 3 E2E tests for settings, <30 seconds execution
2. **Configuration Management:** Update OpenAI API key, configure Home Assistant connection (URL, token), set analysis schedule preferences, save configuration successfully
3. **Validation:** API key format validation, HA URL format validation, invalid token detection, required field validation, helpful error messages
4. **Persistence:** Settings persist after page refresh, settings persist after browser restart, can reset to defaults, export/import configuration (if applicable)

## Tasks / Subtasks

- [ ] **Task 1:** Create test file `ai-automation-settings.spec.ts`
- [ ] **Task 2:** Implement configuration tests (API key, HA connection, schedule, save)
- [ ] **Task 3:** Implement validation tests (formats, invalid values, required fields, errors)
- [ ] **Task 4:** Implement persistence tests (refresh, restart, reset, export/import)

## Dev Notes

**Settings Data:**
```typescript
interface Settings {
  openai_api_key: string;
  ha_url: string;
  ha_token: string;
  analysis_schedule: string;  // cron format
  auto_deploy: boolean;
}
```

**Key Test Example:**
```typescript
test('update and save configuration', async ({ page }) => {
  await page.goto('http://localhost:3001/settings');
  
  // Update OpenAI API key
  await page.getByLabel('OpenAI API Key').fill('sk-test-1234567890');
  
  // Update HA URL
  await page.getByLabel('Home Assistant URL').fill('http://192.168.1.86:8123');
  
  // Update HA token
  await page.getByLabel('Access Token').fill('test-token-abc');
  
  // Save
  await page.getByRole('button', { name: 'Save Settings' }).click();
  
  // Verify success toast
  await expect(page.getByTestId('toast-success')).toBeVisible();
  await expect(page.getByTestId('toast-success')).toContainText('saved');
});

test('validate API key format', async ({ page }) => {
  await page.goto('http://localhost:3001/settings');
  
  // Enter invalid API key
  await page.getByLabel('OpenAI API Key').fill('invalid-key');
  
  // Try to save
  await page.getByRole('button', { name: 'Save Settings' }).click();
  
  // Verify error message
  await expect(page.getByText('Invalid API key format')).toBeVisible();
  
  // Save button should be disabled or error shown
  await expect(page.getByTestId('toast-error')).toBeVisible();
});

test('settings persist after refresh', async ({ page }) => {
  await page.goto('http://localhost:3001/settings');
  
  const testApiKey = 'sk-test-9876543210';
  
  // Update and save
  await page.getByLabel('OpenAI API Key').fill(testApiKey);
  await page.getByRole('button', { name: 'Save Settings' }).click();
  await expect(page.getByTestId('toast-success')).toBeVisible();
  
  // Reload page
  await page.reload();
  
  // Verify value persisted
  const apiKeyInput = page.getByLabel('OpenAI API Key');
  await expect(apiKeyInput).toHaveValue(testApiKey);
});
```

**Required data-testid Attributes:**
- `settings-form`
- `openai-api-key-input`
- `ha-url-input`
- `ha-token-input`
- `save-settings-button`
- `reset-settings-button`

## Change Log
| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-18 | 1.0 | Initial story creation | BMad Master |

## Dev Agent Record
(To be filled by dev agent)

## File List
**New Files:**
- `tests/e2e/ai-automation-settings.spec.ts`

**Modified Files:**
- `services/ai-automation-ui/src/pages/Settings.tsx` (add data-testid)

## QA Results
(To be filled by QA agent)


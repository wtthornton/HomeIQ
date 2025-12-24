# Story AI1.18: End-to-End Testing and Documentation

**Epic:** Epic-AI-1 - AI Automation Suggestion System  
**Story ID:** AI1.18  
**Priority:** High  
**Estimated Effort:** 12-14 hours  
**Dependencies:** Story AI1.17 (All features complete)

---

## User Story

**As a** developer  
**I want** comprehensive E2E tests and documentation  
**so that** the system is reliable and maintainable

---

## Business Value

- Ensures system reliability before deployment
- Provides documentation for future developers
- Validates all acceptance criteria met
- Enables confident deployment to production

---

## Acceptance Criteria

1. ✅ E2E test: Full suggestion approval flow (browse → approve → deploy → verify in HA)
2. ✅ E2E test: Pattern viewing and filtering works
3. ✅ E2E test: Automation management (view → remove → verify)
4. ✅ E2E tests run in CI/CD pipeline (GitHub Actions)
5. ✅ README.md documents setup, configuration, and deployment
6. ✅ API documentation complete and accessible at /docs
7. ✅ Troubleshooting guide covers common issues
8. ✅ Code coverage >70% (unit + integration tests combined)

---

## Technical Implementation Notes

### Playwright E2E Tests

**Create: tests/e2e/ai-automation.spec.ts**

```typescript
import { test, expect } from '@playwright/test';

test.describe('AI Automation Suggestion Flow', () => {
  
  test('complete suggestion approval workflow', async ({ page }) => {
    // 1. Navigate to AI Automation dashboard
    await page.goto('http://localhost:3002');
    
    // 2. Verify dashboard loads
    await expect(page.locator('h1')).toContainText('AI Automation');
    
    // 3. Navigate to Suggestions tab
    await page.click('text=Suggestions');
    
    // 4. Wait for suggestions to load
    await page.waitForSelector('[data-testid="suggestion-card"]');
    
    // 5. Click first suggestion
    await page.click('[data-testid="suggestion-card"]:first-child');
    
    // 6. Modal should open
    await expect(page.locator('[data-testid="suggestion-modal"]')).toBeVisible();
    
    // 7. Click Approve button
    await page.click('button:text("Approve")');
    
    // 8. Should show success message
    await expect(page.locator('text=Approved successfully')).toBeVisible();
    
    // 9. Navigate to Automations tab
    await page.click('text=Automations');
    
    // 10. Verify automation appears with AI badge
    await expect(page.locator('text=🤖 AI')).toBeVisible();
  });
  
  test('pattern visualization works', async ({ page }) => {
    await page.goto('http://localhost:3002');
    await page.click('text=Patterns');
    
    // Should show pattern stats
    await expect(page.locator('text=Patterns Detected')).toBeVisible();
    
    // Should show chart
    await expect(page.locator('[data-testid="pattern-chart"]')).toBeVisible();
  });
  
  test('dark mode persists across refresh', async ({ page }) => {
    await page.goto('http://localhost:3002');
    
    // Toggle dark mode
    await page.click('[aria-label="Switch to Dark Mode"]');
    
    // Verify dark mode applied
    await expect(page.locator('html')).toHaveClass(/dark/);
    
    // Refresh page
    await page.reload();
    
    // Dark mode should persist
    await expect(page.locator('html')).toHaveClass(/dark/);
  });
});
```

### README.md

**Create: services/ai-automation-service/README.md**

```markdown
# AI Automation Suggestion System

AI-powered Home Assistant automation discovery and recommendation system.

## Features

- 🔍 **Pattern Detection**: Analyzes 30 days of HA data to find automation opportunities
- 💡 **Smart Suggestions**: Generates 5-10 automation suggestions weekly
- ✅ **User Approval**: Human-in-the-loop workflow for all deployments
- 🚀 **Auto-Deploy**: Approved automations pushed to Home Assistant
- 📊 **Insights**: Pattern visualization and system health monitoring

## Quick Start

### Prerequisites

- Home Assistant running and accessible
- Data API service running (port 8006)
- MQTT broker (Mosquitto) running
- OpenAI API key

### Installation

1. Configure environment:
```bash
cp infrastructure/env.example .env.ai-automation
# Edit .env.ai-automation with your values
```

2. Start services:
```bash
docker-compose up -d mosquitto
docker-compose up -d ai-automation-service
docker-compose up -d ai-automation-frontend
```

3. Access dashboard:
http://localhost:3002

### Configuration

See `.env.ai-automation` for all configuration options.

## Architecture

See PRD: `docs/prd/ai-automation/index.md`

## Development

See PRD Section 7 for implementation guide.

## Troubleshooting

See `docs/troubleshooting/ai-automation.md`
```

---

## Definition of Done (All 4 Stories)

**AI1.15:**
- [ ] PatternsTab implemented
- [ ] Pattern charts working
- [ ] Filter by type functional

**AI1.16:**
- [ ] AutomationsTab implemented  
- [ ] HA automations displayed
- [ ] Remove automation working

**AI1.17:**
- [ ] InsightsTab implemented
- [ ] System status showing
- [ ] Cost tracking displaying

**AI1.18:**
- [ ] E2E tests passing
- [ ] README complete
- [ ] API docs at /docs
- [ ] Code coverage >70%

---

## Combined Effort

**Total:** 42-50 hours (1-1.5 weeks)  
**Can parallelize:** Yes (different tabs)

---

**Story Status:** Not Started  
**Created:** 2025-10-15


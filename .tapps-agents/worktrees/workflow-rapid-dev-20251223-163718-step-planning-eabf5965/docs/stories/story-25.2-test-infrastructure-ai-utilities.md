# Story 25.2: Enhance Test Infrastructure with AI-Specific Utilities

## Status
Draft

## Story

**As a** QA engineer,
**I want** specialized test utilities and mock data generators for AI automation testing,
**so that** E2E tests are maintainable, deterministic, and can reliably simulate AI automation scenarios without external API dependencies.

## Acceptance Criteria

1. **Mock Data Generators:**
   - Suggestion mock data generator (10+ realistic suggestions)
   - Pattern mock data generator (time-of-day, co-occurrence)
   - Deployed automation mock data generator
   - Device capability mock data generator
   - All generators support customizable options (count, category, confidence)

2. **Custom Assertions:**
   - `expectSuggestionVisible(id)` - Assert suggestion is displayed
   - `expectToastMessage(type, message)` - Assert toast notifications
   - `expectPatternCount(count)` - Assert pattern list count
   - `expectDeploymentSuccess(id)` - Assert automation deployed
   - All assertions use web-first pattern with auto-wait

3. **API Mocking Utilities:**
   - Mock handler for `/api/suggestions` endpoint
   - Mock handler for `/api/deploy/{id}` endpoint
   - Mock handler for `/api/patterns` endpoint
   - Mock handler for `/api/analysis/trigger` endpoint
   - Support success and error scenarios
   - Configurable response delays for testing loading states

4. **Test Data Factories:**
   - Factory pattern for creating test fixtures
   - Realistic AI-generated suggestion descriptions
   - Device names matching actual Home Assistant entities
   - Confidence scores with realistic distributions
   - Pattern data with temporal relationships

5. **Documentation:**
   - Code examples for each utility
   - JSDoc comments on all functions
   - Usage guide in test utilities README
   - Integration examples with Page Object Models

## Tasks / Subtasks

- [ ] **Task 1: Create Mock Data Generators** (AC: 1, 4)
  - [ ] Create `tests/e2e/utils/mock-data-generators.ts`
  - [ ] Implement `MockDataGenerator.generateSuggestions(options)`
  - [ ] Implement `MockDataGenerator.generatePatterns(options)`
  - [ ] Implement `MockDataGenerator.generateDeployedAutomations(options)`
  - [ ] Implement `MockDataGenerator.generateDeviceCapabilities(options)`
  - [ ] Add TypeScript interfaces for all data types
  - [ ] Create 10+ realistic suggestion templates

- [ ] **Task 2: Implement Custom Assertions** (AC: 2)
  - [ ] Create `tests/e2e/utils/custom-assertions.ts`
  - [ ] Implement `expectSuggestionVisible(page, id)`
  - [ ] Implement `expectToastMessage(page, type, message)`
  - [ ] Implement `expectPatternCount(page, count)`
  - [ ] Implement `expectDeploymentSuccess(page, id)`
  - [ ] Use Playwright web-first assertions internally
  - [ ] Add JSDoc comments with examples

- [ ] **Task 3: Create API Mocking Utilities** (AC: 3)
  - [ ] Create `tests/e2e/utils/api-mocks.ts`
  - [ ] Implement `mockSuggestionsEndpoint(page, data, delay?)`
  - [ ] Implement `mockDeployEndpoint(page, success, delay?)`
  - [ ] Implement `mockPatternsEndpoint(page, data, delay?)`
  - [ ] Implement `mockAnalysisTriggerEndpoint(page, delay?)`
  - [ ] Support error responses (500, 404, timeout)
  - [ ] Add configurable delay for loading state testing

- [ ] **Task 4: Create Test Data Factories** (AC: 4)
  - [ ] Create `tests/e2e/fixtures/ai-automation.ts`
  - [ ] Define TypeScript interfaces (Suggestion, Pattern, Automation)
  - [ ] Create factory functions for each type
  - [ ] Add realistic AI-generated descriptions
  - [ ] Add Home Assistant entity naming conventions
  - [ ] Add confidence score distributions

- [ ] **Task 5: Documentation and Examples** (AC: 5)
  - [ ] Create `tests/e2e/utils/README.md`
  - [ ] Document each utility with code examples
  - [ ] Add integration examples with Page Object Models
  - [ ] Create quick reference guide
  - [ ] Add troubleshooting section

## Dev Notes

### Project Context

**Existing Test Utilities:**
- Location: `tests/e2e/utils/docker-test-helpers.ts`
- Existing patterns: Helper functions for Docker health checks
- Integration: Used in global setup/teardown

**AI Automation System:**
- Backend: ai-automation-service (Port 8018)
- Frontend: ai-automation-ui (Port 3001)
- Data structure: SQLite database with suggestions, patterns, automations
- External dependencies: OpenAI API, MQTT, Home Assistant

**Data Models (from backend):**
- **Suggestion:** `id, title, description, category, confidence, pattern_type, approved, created_at`
- **Pattern:** `id, pattern_type, devices, time_range, confidence, occurrences`
- **Automation:** `id, suggestion_id, ha_automation_id, deployed_at, status`

### Mock Data Generator Implementation

**Pattern from Context7 Research:**
```typescript
// tests/e2e/utils/mock-data-generators.ts

export interface MockDataOptions {
  count?: number;
  category?: 'energy' | 'comfort' | 'security' | 'convenience';
  confidence?: 'high' | 'medium' | 'low';
  approved?: boolean;
}

export interface Suggestion {
  id: string;
  title: string;
  description: string;
  category: 'energy' | 'comfort' | 'security' | 'convenience';
  confidence: 'high' | 'medium' | 'low';
  pattern_type: 'time-of-day' | 'co-occurrence';
  approved: boolean;
  created_at: string;
}

export class MockDataGenerator {
  /**
   * Generate realistic AI automation suggestions
   * @param options - Configuration options
   * @returns Array of mock suggestions
   */
  static generateSuggestions(options: MockDataOptions = {}): Suggestion[] {
    const {
      count = 5,
      category,
      confidence,
      approved = false
    } = options;

    const templates = [
      {
        title: 'Turn off lights at bedtime',
        description: 'Detected consistent manual light shutdown at 11 PM every night for the past 30 days',
        category: 'energy' as const,
        pattern_type: 'time-of-day' as const,
      },
      {
        title: 'Morning coffee automation',
        description: 'Coffee maker and kitchen lights are turned on together 95% of mornings at 7 AM',
        category: 'convenience' as const,
        pattern_type: 'co-occurrence' as const,
      },
      // Add 8+ more realistic templates
    ];

    return Array.from({ length: count }, (_, i) => {
      const template = templates[i % templates.length];
      return {
        id: `sug-${Date.now()}-${i}`,
        title: template.title,
        description: template.description,
        category: category || template.category,
        confidence: confidence || this.randomConfidence(),
        pattern_type: template.pattern_type,
        approved,
        created_at: new Date(Date.now() - i * 86400000).toISOString(),
      };
    });
  }

  /**
   * Generate realistic pattern data
   */
  static generatePatterns(options: MockDataOptions = {}): Pattern[] {
    // Implementation similar to suggestions
  }

  private static randomConfidence(): 'high' | 'medium' | 'low' {
    const rand = Math.random();
    if (rand > 0.7) return 'high';
    if (rand > 0.4) return 'medium';
    return 'low';
  }
}
```

### Custom Assertions Implementation

**Playwright Best Practice Pattern:**
```typescript
// tests/e2e/utils/custom-assertions.ts
import { Page, expect } from '@playwright/test';

/**
 * Assert that a suggestion with given ID is visible
 * Uses web-first assertion with auto-wait
 */
export async function expectSuggestionVisible(page: Page, id: string) {
  const suggestion = page.getByTestId(`suggestion-${id}`);
  await expect(suggestion).toBeVisible();
  await expect(suggestion).toContainText(id);
}

/**
 * Assert toast notification appears with message
 * @param type - 'success' | 'error' | 'warning' | 'info'
 * @param message - Expected message (partial match)
 */
export async function expectToastMessage(
  page: Page,
  type: 'success' | 'error' | 'warning' | 'info',
  message: string
) {
  const toast = page.getByTestId(`toast-${type}`);
  await expect(toast).toBeVisible({ timeout: 5000 });
  await expect(toast).toContainText(message);
}

/**
 * Assert pattern list has expected count
 */
export async function expectPatternCount(page: Page, count: number) {
  const patterns = page.getByTestId('pattern-item');
  await expect(patterns).toHaveCount(count);
}

/**
 * Assert automation deployed successfully
 */
export async function expectDeploymentSuccess(page: Page, id: string) {
  // Check success toast
  await expectToastMessage(page, 'success', 'deployed');
  
  // Navigate to deployed tab and verify
  await page.goto('http://localhost:3001/deployed');
  const automation = page.getByTestId(`deployed-automation-${id}`);
  await expect(automation).toBeVisible();
}
```

### API Mocking Utilities

**Pattern from Context7 Research:**
```typescript
// tests/e2e/utils/api-mocks.ts
import { Page, Route } from '@playwright/test';
import { MockDataGenerator, Suggestion } from './mock-data-generators';

/**
 * Mock the suggestions API endpoint
 * @param page - Playwright page
 * @param data - Mock suggestions (or generate if not provided)
 * @param delay - Optional delay in ms for loading state testing
 */
export async function mockSuggestionsEndpoint(
  page: Page,
  data?: Suggestion[],
  delay: number = 0
) {
  const suggestions = data || MockDataGenerator.generateSuggestions({ count: 10 });
  
  await page.route('**/api/suggestions', async (route: Route) => {
    await new Promise(resolve => setTimeout(resolve, delay));
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(suggestions),
    });
  });
}

/**
 * Mock the deployment endpoint
 * @param page - Playwright page
 * @param success - Whether deployment should succeed
 * @param delay - Optional delay in ms
 */
export async function mockDeployEndpoint(
  page: Page,
  success: boolean = true,
  delay: number = 0
) {
  await page.route('**/api/deploy/*', async (route: Route) => {
    await new Promise(resolve => setTimeout(resolve, delay));
    
    if (success) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          automation_id: 'automation.test_123',
          message: 'Successfully deployed to Home Assistant',
        }),
      });
    } else {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Home Assistant connection failed',
          details: 'MQTT broker unavailable',
        }),
      });
    }
  });
}

/**
 * Mock patterns endpoint
 */
export async function mockPatternsEndpoint(
  page: Page,
  data?: Pattern[],
  delay: number = 0
) {
  // Similar implementation
}

/**
 * Mock analysis trigger endpoint
 */
export async function mockAnalysisTriggerEndpoint(
  page: Page,
  delay: number = 5000
) {
  await page.route('**/api/analysis/trigger', async (route: Route) => {
    await new Promise(resolve => setTimeout(resolve, delay));
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'started',
        job_id: 'job-' + Date.now(),
        estimated_duration: 120,
      }),
    });
  });
}
```

### Realistic AI-Generated Suggestion Templates

```typescript
const SUGGESTION_TEMPLATES = [
  {
    title: 'Turn off bedroom lights at bedtime',
    description: 'Detected consistent manual light shutdown at 11 PM every night for the past 30 days. Average bedtime is 11:05 PM with 95% consistency.',
    category: 'energy',
    pattern_type: 'time-of-day',
    confidence: 'high',
  },
  {
    title: 'Morning coffee automation',
    description: 'Coffee maker and kitchen lights are turned on together 95% of mornings at 7 AM. Strong co-occurrence pattern detected.',
    category: 'convenience',
    pattern_type: 'co-occurrence',
    confidence: 'high',
  },
  {
    title: 'Lower thermostat when away',
    description: 'Temperature is manually lowered when leaving home. Detected 18 times in last 30 days. Could save ~15% on heating costs.',
    category: 'energy',
    pattern_type: 'co-occurrence',
    confidence: 'medium',
  },
  {
    title: 'Lock doors at night',
    description: 'Front door is manually locked at 10:30 PM every night. Detected consistent pattern for 45 consecutive days.',
    category: 'security',
    pattern_type: 'time-of-day',
    confidence: 'high',
  },
  {
    title: 'Dim living room lights at sunset',
    description: 'Living room lights are dimmed to 40% at sunset 85% of the time. Detected seasonal adjustment pattern.',
    category: 'comfort',
    pattern_type: 'time-of-day',
    confidence: 'medium',
  },
  // Add 5+ more templates
];
```

### Integration with Page Object Models

**Usage Example:**
```typescript
// tests/e2e/ai-automation-approval-workflow.spec.ts
import { test, expect } from '@playwright/test';
import { DashboardPage } from './page-objects/DashboardPage';
import { mockSuggestionsEndpoint, mockDeployEndpoint } from './utils/api-mocks';
import { MockDataGenerator } from './utils/mock-data-generators';
import { expectToastMessage, expectDeploymentSuccess } from './utils/custom-assertions';

test.describe('AI Automation Approval Workflow', () => {
  let dashboardPage: DashboardPage;

  test.beforeEach(async ({ page }) => {
    dashboardPage = new DashboardPage(page);
    
    // Mock API with realistic data
    const suggestions = MockDataGenerator.generateSuggestions({
      count: 5,
      category: 'energy',
      confidence: 'high',
    });
    await mockSuggestionsEndpoint(page, suggestions);
    await mockDeployEndpoint(page, true);
    
    await dashboardPage.goto();
  });

  test('approve and deploy suggestion', async ({ page }) => {
    await dashboardPage.approveSuggestion(0);
    const suggestionId = 'sug-1';
    await dashboardPage.deploySuggestion(suggestionId);
    
    // Use custom assertion
    await expectDeploymentSuccess(page, suggestionId);
  });
});
```

### Testing

**Test File Location:** `tests/e2e/utils/`

**Test Standards:**
- TypeScript for all utilities
- JSDoc comments required
- Unit tests for generators (optional but recommended)
- Integration tests with actual Page Object Models

**Testing Framework:** Playwright 1.56.0

**Validation:**
- All utilities work with existing Page Object Models
- Mock data matches backend schema
- Custom assertions use web-first pattern
- API mocks handle success and error cases

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-18 | 1.0 | Initial story creation | BMad Master |

## Dev Agent Record

### Agent Model Used
(To be filled by dev agent)

### Debug Log References
(To be filled by dev agent)

### Completion Notes List
(To be filled by dev agent)

### File List
**Expected Files Created/Modified:**

**New Files:**
- `tests/e2e/utils/mock-data-generators.ts`
- `tests/e2e/utils/custom-assertions.ts`
- `tests/e2e/utils/api-mocks.ts`
- `tests/e2e/fixtures/ai-automation.ts` (enhanced)
- `tests/e2e/utils/README.md`

**No Changes:**
- Existing test files remain unchanged
- Page Object Models (will integrate utilities later)

## QA Results
(To be filled by QA agent)


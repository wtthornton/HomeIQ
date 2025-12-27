# Epic 25: E2E Test Infrastructure Enhancement - Brownfield Enhancement

## Epic Goal

Enhance the existing Playwright E2E test infrastructure to support comprehensive testing of the AI Automation UI (localhost:3001), establishing best practices and test patterns that enable reliable end-to-end workflow validation across the entire system.

## Epic Description

### Existing System Context

**Current E2E Testing:**
- Technology stack: Playwright 1.56.0, TypeScript
- Test location: `tests/e2e/`
- Coverage: Health Dashboard (localhost:3000) with 17 test files
- Configuration: `docker-deployment.config.ts` for Docker environment
- Test types: System health, dashboard functionality, monitoring, settings, visual regression, integration, performance
- **Gap**: Zero coverage for AI Automation UI (localhost:3001)

**AI Automation UI:**
- Service: ai-automation-ui (Port 3001)
- Technology: React 18.2.0 + TypeScript + Vite
- Pages: Dashboard, Patterns, Deployed, Settings
- Current testing: Puppeteer visual tests only (no workflow testing)
- Integration: ai-automation-service (Port 8018 backend)

### Enhancement Details

**What's being added/changed:**

Based on Context7 Playwright best practices research, we will:

1. **Test Configuration Enhancement**
   - Add AI Automation UI base URL (localhost:3001) to test config
   - Create dedicated test fixtures for AI automation workflows
   - Implement Page Object Models for reusable component interactions
   - Configure parallel execution for independent tests

2. **Test Infrastructure**
   - Extend `docker-deployment.config.ts` with AI automation service health checks
   - Create helper utilities for AI automation-specific assertions
   - Implement mock data generators for suggestions and patterns
   - Add custom assertions for AI-specific UI states

3. **Test Organization**
   - New test files following existing naming conventions
   - Reuse proven patterns from health-dashboard tests
   - Apply web-first assertions (`toBeVisible()`, `toHaveText()`)
   - Use `data-testid` attributes for reliable element selection

**How it integrates:**
- Extends existing Playwright test suite infrastructure
- Reuses Docker test helpers and global setup/teardown
- Follows same test configuration patterns
- Integrates with existing CI/CD test runner scripts

**Success criteria:**
1. AI Automation UI test infrastructure configured and validated
2. Page Object Models created for all 4 UI pages
3. Test helpers and fixtures ready for workflow tests
4. At least 2 example tests passing (smoke tests)
5. Documentation updated with AI automation testing guide
6. Zero disruption to existing health dashboard tests

### Stories

1. **Story 25.1:** Configure Playwright for AI Automation UI Testing
   - Add localhost:3001 to test configuration
   - Create Page Object Models for Dashboard, Patterns, Deployed, Settings pages
   - Implement test fixtures and helper utilities
   - Write 2 smoke tests to validate setup

2. **Story 25.2:** Enhance Test Infrastructure with AI-Specific Utilities
   - Create mock data generators for suggestions, patterns, automations
   - Implement custom assertions for AI automation UI states
   - Add reusable test helpers for API mocking
   - Create test data factories following Playwright best practices

3. **Story 25.3:** Test Runner Enhancement and Documentation
   - Update `run-docker-tests.sh` to include AI automation tests
   - Add AI automation test section to `tests/e2e/README.md`
   - Create testing guide with examples and best practices
   - Implement test health checks for ai-automation-service

### Compatibility Requirements

- [x] Existing E2E test infrastructure remains unchanged
- [x] Health Dashboard tests (17 files) continue to pass
- [x] Docker deployment config backward compatible
- [x] Test runner scripts support both UI services
- [x] No changes to existing Page Object Models

### Risk Mitigation

**Primary Risk:** Test infrastructure changes break existing health dashboard tests

**Mitigation:**
- Add AI automation config as separate section in test config
- Create dedicated test files (no modifications to existing tests)
- Run full regression suite after each change
- Use feature flags for new test helpers

**Rollback Plan:**
- Remove new test files (isolated from existing tests)
- Revert config changes (separate sections)
- Existing tests unaffected due to zero modifications

### Definition of Done

- [x] All 3 stories completed with acceptance criteria met
- [x] AI Automation UI test infrastructure fully configured
- [x] Page Object Models created and documented
- [x] At least 2 smoke tests passing
- [x] Existing 17 health dashboard test files still passing
- [x] Documentation updated with examples
- [x] Test runner includes AI automation tests
- [x] No regression in existing test functionality

---

## Technical Context (from Context7 Research)

### Playwright Best Practices Applied

**1. Web-First Assertions:**
```typescript
// ✅ Recommended - auto-wait and retry
await expect(page.getByText('welcome')).toBeVisible();

// ❌ Avoid - no waiting
expect(await page.getByText('welcome').isVisible()).toBe(true);
```

**2. Test Isolation with beforeEach:**
```typescript
test.beforeEach(async ({ page }) => {
  await page.goto('http://localhost:3001');
  // Setup code runs before each test
});
```

**3. User-Facing Locators:**
```typescript
// ✅ Preferred - role-based selectors
page.getByRole('button', { name: 'Approve' });

// Use data-testid for unique identification
page.getByTestId('suggestion-card');
```

**4. Parallel Execution:**
```typescript
test.describe.configure({ mode: 'parallel' });
```

**5. Page Object Model Pattern:**
```typescript
class PatternsPage {
  constructor(private page: Page) {}
  
  async goto() {
    await this.page.goto('http://localhost:3001/patterns');
  }
  
  async getPatternList() {
    return this.page.getByTestId('pattern-list');
  }
}
```

---

**Epic Owner:** QA Team  
**Epic Priority:** High  
**Estimated Duration:** 3-5 days  
**Dependencies:** Playwright 1.56.0, ai-automation-ui running on port 3001

---

**Related Epics:**
- Epic 9: Optimization & Testing (foundation)
- Epic 26: AI Automation UI E2E Test Coverage (uses this infrastructure)

**Last Updated:** October 18, 2025


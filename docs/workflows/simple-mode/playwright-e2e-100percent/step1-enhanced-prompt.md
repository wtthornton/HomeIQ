# Playwright E2E Test Suite - Enhanced Prompt

**Date:** February 7, 2026  
**Workflow:** Review, Plan, Enhance, Implement  
**Goal:** HomeIQ frontends and UI 100% test pass rate

## Enhanced Requirements

### Scope
- **Frontends:** health-dashboard (port 3000), ai-automation-ui (port 3001)
- **Existing suite:** tests/e2e/ with 50+ spec files
- **Current state:** 7/26 Ask AI tests pass; timing issues in 19 tests

### Requirements

1. **Smoke Test Suite (100% Pass)**
   - Run in <2 minutes with Docker stack up
   - No OpenAI/async dependencies for core smoke
   - Include: system-health, dashboard load, health-dashboard navigation

2. **Fix Async Timing (AI Tests)**
   - Increase waitForToast to 45s for OpenAI responses
   - Increase test timeout to 90s for AI workflow tests
   - Add retry logic (retries: 2) for flaky AI tests

3. **Configuration**
   - Smoke config: chromium-only, minimal testMatch
   - Full config: all projects, extended testMatch including health-dashboard/ and ai-automation-ui/
   - Epic 31: Remove enrichment-pipeline references from README

4. **Test Organization**
   - Fast tests: Page load, navigation, UI interactions (<5s)
   - Slow tests: AI integration, full workflow (>20s)
   - Tag tests: @smoke, @ai-integration, @visual

5. **Coverage**
   - health-dashboard: Overview, tabs, components
   - ai-automation-ui: Ask AI, Dashboard, Deployed, Settings, Patterns

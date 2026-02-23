**Title:** [P0] Add AI Automation UI Test Suite (Vitest + React Testing Library)

**Labels:** `testing`, `P0`, `enhancement`

---

**Priority:** 🔴 P0 - Critical
**Effort:** 8-12 hours
**Dependencies:** None

## Description

Implement comprehensive test suite for the AI Automation UI (Port 3001) using modern 2025 frontend testing patterns with Vitest (4× faster than Jest) and React Testing Library.

**Current Status:** 0% test coverage (47 TypeScript/React files untested)

**Risk:** Primary user interface for AI automation has no automated tests. Regressions could break critical user workflows.

## Modern 2025 Patterns

✅ **Vitest** (replaces Jest) - Native ESM, 4× faster
✅ **Playwright Component Testing** - Component-level isolation
✅ **MSW 2.0** - Modern API mocking
✅ **Testing Library** - User-centric testing

## Acceptance Criteria

- [ ] Vitest configuration setup (`vitest.config.ts`)
- [ ] Test coverage >70% for components
- [ ] Test coverage >80% for hooks
- [ ] Test coverage >60% for stores/state management
- [ ] MSW 2.0 API mocking configured
- [ ] All tests pass in CI/CD pipeline
- [ ] Test execution time <30 seconds

## File Structure

```
domains/frontends/ai-automation-ui/
├── vitest.config.ts (new)
├── src/
│   ├── test/
│   │   └── setup.ts (new)
│   ├── __tests__/
│   │   ├── components/
│   │   │   ├── AutomationApproval.test.tsx
│   │   │   ├── PatternAnalysis.test.tsx
│   │   │   ├── ConversationFlow.test.tsx
│   │   │   └── SettingsPanel.test.tsx
│   │   ├── hooks/
│   │   │   ├── useAutomationState.test.ts
│   │   │   ├── usePatternDetection.test.ts
│   │   │   ├── useWebSocket.test.ts
│   │   │   └── useDeviceIntelligence.test.ts
│   │   ├── store/
│   │   │   ├── automationSlice.test.ts
│   │   │   └── conversationSlice.test.ts
│   │   └── integration/
│   │       ├── automationWorkflow.test.tsx
│   │       └── patternToApproval.test.tsx
│   └── mocks/
│       └── handlers.ts (MSW 2.0)
```

## Code Templates

See [GITHUB_ISSUES.md](https://github.com/wtthornton/HomeIQ/blob/main/GITHUB_ISSUES.md#issue-1-p0-add-ai-automation-ui-test-suite-vitest--react-testing-library) for complete code templates.

## Dependencies

```json
{
  "devDependencies": {
    "vitest": "^2.0.0",
    "@vitest/ui": "^2.0.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.5.0",
    "@testing-library/jest-dom": "^6.1.0",
    "jsdom": "^23.0.0",
    "msw": "^2.4.0",
    "@playwright/experimental-ct-react": "^1.47.0"
  }
}
```

## Success Metrics

- ✅ All components have unit tests
- ✅ All hooks have unit tests
- ✅ Integration tests cover main user flows
- ✅ Coverage thresholds met (70/60/70/70)
- ✅ Tests run in <30 seconds
- ✅ No flaky tests

## References

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [MSW 2.0 Documentation](https://mswjs.io/)
- [HomeIQ CLAUDE.md](/CLAUDE.md)

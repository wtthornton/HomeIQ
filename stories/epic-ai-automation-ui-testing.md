# Epic 44: AI Automation UI — Critical Path Testing

**Sprint:** 10
**Priority:** P0 (Critical)
**Status:** Open
**Created:** 2026-03-09
**Effort:** 2 weeks
**Dependencies:** Epic 42 complete
**Source:** `docs/planning/frontend-testing-epics.md` (Epic 52 mapping)

## Objective

Achieve 40%+ file coverage for ai-automation-ui by testing the chat system, API clients, and core page components. Currently at 7% file coverage (7 test files / 105 source files).

## Stories

### Story 44.1: API Client Unit Tests (P0)
- Create `src/services/__tests__/api-v2.test.ts` (conversation CRUD, message sending, error handling, auth)
- Create `src/services/__tests__/haAiAgentApi.test.ts` (chat API, tool execution, response parsing)
- **Target:** 30-40 tests
- **Effort:** 4 hours

### Story 44.2: HAAgentChat Page Tests (P0)
- Create `src/pages/__tests__/HAAgentChat.test.tsx`
- Test: conversation loading, message rendering, input handling, send flow, error states, conversation switching
- **Target:** 20-30 tests
- **Effort:** 4 hours

### Story 44.3: Chat Component Tests (P0)
- Test MessageContent, ConversationSidebar, AutomationProposal, MarkdownErrorBoundary
- **Target:** 60-80 tests
- **Effort:** 6 hours

### Story 44.4: Device Picker & Suggestions Tests (P0)
- Test DevicePicker (list loading, filtering, multi-select) and DeviceSuggestions
- **Target:** 15-20 tests
- **Effort:** 3 hours

### Story 44.5: useConversationV2 Hook Tests (P1)
- Test conversation lifecycle, async operations, loading states, error handling, history management
- **Target:** 15-20 tests
- **Effort:** 3 hours

### Story 44.6: Page Component Tests (P1)
- Test Suggestions, Deployed, Patterns, Synergies pages
- **Target:** 40-48 tests
- **Effort:** 5 hours

### Story 44.7: Modal & Action Tests (P1)
- Test BatchActionModal, DeviceMappingModal, SuggestionCard, ConversationalSuggestionCard
- **Target:** 32-40 tests
- **Effort:** 4 hours

### Story 44.8: Service Layer Tests (P2)
- Test deviceApi, proactiveApi, blueprintSuggestionsApi
- **Target:** 24-30 tests
- **Effort:** 3 hours

## Acceptance Criteria
- [ ] 40%+ file coverage for ai-automation-ui
- [ ] Chat system fully tested (API, page, components, hook)
- [ ] All page components have at least basic tests
- [ ] CI green

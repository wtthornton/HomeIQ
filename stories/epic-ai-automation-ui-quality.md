---
epic: ai-automation-ui-quality
priority: high
status: open
estimated_duration: 2-3 weeks
risk_level: medium
source: REVIEW_AND_FIXES.md (2026-02-06), TAPPS expert consultation
---

# Epic: AI Automation UI Quality & Performance

**Status:** Open
**Priority:** High (P1)
**Duration:** 2-3 weeks
**Risk Level:** Medium
**Predecessor:** Epic frontend-security-hardening (Stories 1, 2)
**Affects:** domains/frontends/ai-automation-ui

## Context

The AI Automation UI code review (Feb 6, 2026) identified massive code duplication
across 10 API modules, monolithic components (Patterns.tsx at 1427 lines), inconsistent
state management (3 competing patterns), and only 7 test files for 60+ source files.
The frontend redesign (Phase 4b) consolidated navigation but did not address these
structural issues.

## Stories

### Story 1: Consolidate API Layer (DRY)

**Priority:** High | **Estimate:** 8h | **Risk:** Medium

**Problem:** `withAuthHeaders` / `fetchJSON` / `APIError` duplicated verbatim across
10 separate API modules in `src/services/` and `src/api/`. Bug fixes must be applied
10 times. Auth patterns already inconsistent (`credentials: 'include'` in some, not others).

**Files:** 10 files across `src/services/` and `src/api/`

**Acceptance Criteria:**
- [ ] Single `ApiClient` class in `src/lib/api-client.ts` with `fetchJSON`, auth headers, error handling
- [ ] All 10 API modules refactored to use shared `ApiClient`
- [ ] Consistent auth pattern across all endpoints
- [ ] `src/services/` and `src/api/` consolidated into single `src/api/` directory
- [ ] Centralized `src/config/api.ts` used by all modules (not just 2)
- [ ] Hardcoded `http://localhost:7242` fallback URL removed (API-03)

---

### Story 2: Break Down Monolithic Components

**Priority:** High | **Estimate:** 2 days | **Risk:** Medium

**Problem:** 4 components exceed maintainability limits:
- `Patterns.tsx` — 1427 lines
- `HAAgentChat.tsx` — 1139 lines, 25+ useState
- `ConversationalDashboard.tsx` — 883 lines
- `Settings.tsx` — 797 lines (4x duplicated model selector JSX)

**Acceptance Criteria:**
- [ ] Each component < 300 lines
- [ ] `Patterns.tsx` split into: `PatternList`, `PatternDetail`, `PatternFilters`, `PatternChart`
- [ ] `HAAgentChat.tsx` state extracted into `useChatState()` custom hook
- [ ] `Settings.tsx` model selector extracted into reusable `ModelSelector` component (eliminates 4x duplication)
- [ ] `ConversationalDashboard.tsx` split with custom hooks for polling and state
- [ ] Hardcoded device hash→name map removed (CQ-07)

---

### Story 3: Unify State Management

**Priority:** Medium | **Estimate:** 6h | **Risk:** Medium

**Problem:** Three competing state patterns: Zustand (global), React Query (some pages),
raw useState+useEffect (ConversationalDashboard, Synergies, Patterns, Deployed).

**Acceptance Criteria:**
- [ ] React Query as primary data-fetching layer for all server state
- [ ] `QueryClient` configured with sensible defaults (staleTime, retry, refetchOnWindowFocus)
- [ ] Zustand reserved for client-only UI state (sidebar collapse, theme, etc.)
- [ ] Zero raw `useState` + `useEffect` + `setInterval` fetch patterns remaining
- [ ] `Synergies.tsx` 19 useState declarations reduced via custom hooks or React Query

---

### Story 4: Fix Dead Code and Stub Functions

**Priority:** Medium | **Estimate:** 3h | **Risk:** Low

**Problem:**
- Pattern delete button shows success toast without making API call (CQ-03)
- `handleTestAutomation` / `handleScheduleAutomation` show "coming soon" but appear functional (CQ-04)
- Dead files: `App-simple.tsx`, `Navigation-fixed.tsx` (CQ-05)
- Duplicate `parseDeviceIds` / `parseDeviceIdsForSearch` functions (CQ-08)
- Duplicate `downloadFile` in `exportUtils.ts` and `synergyExportUtils.ts` (CQ-09)
- AFRAME global stub defined in 3 places (ARCH-04)

**Acceptance Criteria:**
- [ ] Pattern delete either makes real API call or button removed/disabled
- [ ] Stub "coming soon" handlers either implemented or buttons hidden
- [ ] Dead files deleted
- [ ] Duplicate functions consolidated
- [ ] AFRAME stub defined in exactly one place

---

### Story 5: Fix Accessibility Gaps

**Priority:** Medium | **Estimate:** 4h | **Risk:** Low

**Problem:**
- Settings.tsx checkboxes missing `id`/`htmlFor`
- Admin.tsx delete buttons emoji-only (no text/aria-label)
- Synergies.tsx filter buttons missing `aria-label`
- ConversationalDashboard tabs missing `role="tablist"`
- Icon-only buttons use `title` only (screen readers miss this)
- `onKeyPress` deprecated (should be `onKeyDown`)

**Acceptance Criteria:**
- [ ] All form inputs have proper `id`/`htmlFor` pairs
- [ ] All icon-only buttons have `aria-label`
- [ ] Tab components use `role="tablist"` / `role="tab"` / `role="tabpanel"`
- [ ] `onKeyPress` replaced with `onKeyDown`
- [ ] Keyboard navigation tested for all interactive elements

---

### Story 6: Clean Up Console Logging & Dependencies

**Priority:** Low | **Estimate:** 2h | **Risk:** Low

**Problem:**
- ~55 debug `console.log` statements in production code
- `@types/canvas-confetti` and `@types/react-syntax-highlighter` in `dependencies` instead of `devDependencies`
- `window.confirm` / `window.prompt` in 4 locations
- Two competing dark mode systems (Tailwind ternaries vs CSS custom properties)

**Acceptance Criteria:**
- [ ] Production console statements removed or behind feature flag
- [ ] `@types/*` packages moved to `devDependencies`
- [ ] `window.confirm` replaced with themed dialog for destructive actions
- [ ] Single consistent styling approach documented

---

### Story 7: Add nginx Rate Limiting & Security

**Priority:** Medium | **Estimate:** 2h | **Risk:** Low

**Problem:** No rate limiting — single client can overwhelm all backend services.
Static asset `add_header` overrides security headers from parent context.

**Files:** `domains/frontends/ai-automation-ui/nginx.conf`

**Acceptance Criteria:**
- [ ] `limit_req_zone` configured (e.g., 10 req/s per IP for API routes)
- [ ] Static asset location inherits parent security headers
- [ ] Health check URL path traversal (`..`) removed (SEC-06)

---

### Story 8: Establish Test Coverage Foundation

**Priority:** High | **Estimate:** 2-3 days | **Risk:** Low

**Problem:** Only 7 test files for 60+ source files. Zero tests for API modules, most
page components, all hooks, all utilities except 2.

**Acceptance Criteria:**
- [ ] Vitest + React Testing Library configured
- [ ] Global test setup with mocks for `fetch`, `localStorage`, `IntersectionObserver`
- [ ] Tests for consolidated `ApiClient` (from Story 1)
- [ ] Tests for 5 highest-traffic page components (smoke + interaction tests)
- [ ] Coverage threshold set at 30% (baseline) in CI
- [ ] `test_LoadingSpinner.py` deleted (wrong language — Python testing React TSX)

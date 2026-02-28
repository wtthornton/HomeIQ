---
epic: browser-review-ai-automation-ui
priority: high
status: in-progress
estimated_duration: 2-3 weeks
risk_level: medium
source: implementation/analysis/browser-review/*.md (2026-02-28)
---

# Epic: Browser Review – AI Automation UI Fixes (Port 3001)

**Status:** In Progress (Stories 1-2 Complete)
**Priority:** High (P1)
**Duration:** 2-3 weeks
**Risk Level:** Medium
**Source:** Playwright MCP browser review, Feb 2026
**Affects:** domains/frontends/ai-automation-ui

## Context

A Playwright MCP review of http://localhost:3001/ documented issues and enhancements for every page (Ideas, Chat, Explore, Insights, Automations, Settings). Per-page details live in `implementation/analysis/browser-review/3001-*.md`.

## Stories

### Story 1: Fix Ideas Page – Suggestions API Failure (Critical)

**Priority:** Critical | **Estimate:** 8h | **Risk:** Medium

**Problem:** "Failed to load suggestions" error; 0 suggestions across all filters. Core feature is broken; backend/API or connectivity to suggestion service (proactive/agent) is likely failing.

**Files:** Ideas page, ProactiveSuggestions, proactive API layer

**Acceptance Criteria:**
- [x] Suggestions load successfully when backend is available
- [x] Clear error message with retry or "Check connection" when API fails; auth errors (401/403) show specific guidance
- [x] Link to Settings or docs if API key/config may be wrong (auth error card includes env var guidance)
- [x] Empty state when count is 0 and no error: "No suggestions yet – we'll suggest automations based on your data"
- [x] Refresh Suggestions shows loading state and success/error feedback (already had spinner + toast)

---

### Story 2: Fix Explore Page – Devices API & Mobile Nav

**Priority:** High | **Estimate:** 6h | **Risk:** Low

**Problem:** "Failed to load devices. Using demo mode." Explore is not in mobile bottom nav; device dropdown gives no demo/error feedback.

**Files:** DiscoveryPage, DeviceExplorer, Sidebar (MOBILE_TABS)

**Acceptance Criteria:**
- [x] Devices/entities load from `/api/entities` when backend is available
- [x] When in demo mode: "Showing demo devices. Connect your home to see your devices." with amber banner
- [x] Retry button + link to Settings in demo mode banner when load fails
- [x] Explore added to mobile bottom nav (replaced Settings, kept 5-tab limit)
- [x] Loading skeleton (2 pulse cards) while devices load; dropdown disabled with spinner until loaded or error

---

### Story 3: Chat, Insights, Automations, Settings – UX & Accessibility

**Priority:** Medium | **Estimate:** 12h | **Risk:** Low

**Problem:** Various UX gaps: Chat agent description verify, empty states, Automations card layout and confirmation dialogs, Settings persistence and help text.

**Files:** HAAgentChat, Insights, Deployed, Settings

**Acceptance Criteria:**
- [ ] Chat: Verify agent description copy; add empty-state hint in conversations sidebar
- [ ] Insights: Empty state when no patterns ("No patterns yet – we need at least 30 days of events"); differentiate Device Connections vs Room View content
- [ ] Automations: Clear Disabled vs Enable state; optional confirmation for Trigger/Re-deploy; truncation with tooltip for long names
- [ ] Settings: Confirm all settings persist; add help text for Confidence/Max Suggestions; validation for numeric inputs (min/max)

---

### Story 4: Accessibility & Empty States

**Priority:** Medium | **Estimate:** 6h | **Risk:** Low

**Problem:** Source tabs, status filters, sub-tabs need aria-current/aria-selected; keyboard navigation and screen-reader support.

**Acceptance Criteria:**
- [ ] Ideas: Source tabs and status filters have aria-current/aria-selected
- [ ] Insights: Sub-tab strip is tablist with proper roles and focus
- [ ] All interactive elements have clear focus styles
- [ ] Skip-to-content and heading hierarchy correct

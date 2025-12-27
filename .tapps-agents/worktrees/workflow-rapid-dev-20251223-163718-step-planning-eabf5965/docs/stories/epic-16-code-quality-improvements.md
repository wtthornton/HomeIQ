# Epic 16: Code Quality & Maintainability Improvements - Brownfield Enhancement

## Status
Draft

## Overview
Improve code maintainability and quality for the HA Ingestor personal home automation project. Focus on simplifying the large Dashboard component, adding basic test coverage for critical workflows, and improving initial setup documentation.

**Context:** This is a single-user local application, not an enterprise SaaS product. Improvements should be simple, practical, and appropriate for a personal home automation system.

## Business Value
- **Maintainability:** Easier to modify and extend dashboard features
- **Reliability:** Basic test coverage prevents regressions
- **Usability:** Clear setup instructions reduce deployment friction
- **Time Savings:** Faster debugging with modular components

## Goals
1. Simplify Dashboard.tsx by extracting tab components
2. Add basic test coverage for main user workflows
3. Improve first-time setup documentation with security best practices

## Stories

### Story 16.1: Refactor Dashboard Component into Modular Tab Components
**Priority:** High  
**Estimated Effort:** 2-3 hours

Split the 597-line Dashboard.tsx into separate, focused tab components to improve code maintainability and readability.

**Acceptance Criteria:**
1. Each dashboard tab (Overview, Services, Sports, Configuration, etc.) is extracted into its own component file
2. Dashboard.tsx acts as a layout/router component (~100 lines max)
3. All existing functionality works identically after refactor
4. Dark mode prop is passed cleanly to tab components
5. No duplicate code between tab components

### Story 16.2: Add Basic Test Coverage for Critical User Workflows
**Priority:** High  
**Estimated Effort:** 3-4 hours

Add focused tests for main dashboard workflows and critical hooks. Target: 5-10 meaningful tests, not comprehensive coverage.

**Acceptance Criteria:**
1. Dashboard component renders and displays health status
2. Tab navigation works correctly
3. useHealth hook fetches and returns health data
4. useStatistics hook fetches and returns statistics data
5. Error states display user-friendly messages
6. All tests pass in CI/CD pipeline

### Story 16.3: Improve Security Documentation for Initial Setup
**Priority:** Medium  
**Estimated Effort:** 30-60 minutes

Update README and setup guides to emphasize password changes and basic security for local deployment.

**Acceptance Criteria:**
1. README has clear "Security Setup" section
2. Deployment wizard prompts for password changes
3. `.env.example` includes security comments
4. Setup guide warns about default passwords
5. Quick checklist for securing local deployment

## Technical Notes

### Technology Stack
- **Frontend:** React 18.2 + TypeScript 5.2 + TailwindCSS
- **Testing:** Vitest 3.2 + Testing Library
- **Backend:** Python 3.11 + FastAPI + pytest

### Architecture Context
- Single-user local application
- Docker Compose deployment
- Microservices architecture (WebSocket, Enrichment, Admin API, Dashboard)
- InfluxDB for time-series storage

### Constraints
- Keep it simple - this is a personal project
- Don't over-engineer solutions
- Maintain existing functionality
- No breaking changes to API contracts

## Success Metrics
- Dashboard.tsx reduced from 597 lines to ~100 lines
- 5-10 tests added covering main workflows
- Zero test failures after refactor
- Setup documentation includes security checklist
- No change in user-facing functionality

## Dependencies
- None - this is a standalone quality improvement epic

## Risks & Mitigation
- **Risk:** Refactor breaks existing functionality
  - **Mitigation:** Add tests first, test thoroughly after refactor
- **Risk:** Tests take too long to write
  - **Mitigation:** Focus on main workflows only, not comprehensive coverage

## Timeline
- **Story 16.1:** 2-3 hours
- **Story 16.2:** 3-4 hours
- **Story 16.3:** 30-60 minutes
- **Total:** ~1 day of focused work

## Notes
- This epic focuses on practical improvements for a single-user application
- No need for enterprise-scale solutions (monitoring, complex CI/CD, etc.)
- Keep testing simple and focused on preventing regressions
- Security docs are about local network best practices, not multi-tenant security

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-01-12 | 1.0 | Created epic based on code review findings | BMad Master |


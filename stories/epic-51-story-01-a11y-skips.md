# Story 51.1 — Health-dashboard a11y skips (headings, landmarks, form labels, focus)

<!-- docsmcp:start:user-story -->

> **As a** developer, **I want** to fix or remove conditional skips in health-dashboard a11y E2E tests, **so that** a11y spec runs without skips and pass/fail reflects real assertions

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:description -->
## Description

Fix or delete conditional skips in tests/e2e/health-dashboard/accessibility/a11y.spec.ts when no visible headings, no landmarks, no form inputs, or no visible focus. Align selectors to dashboard-root/main/nav and heading/landmark expectations; add waits or remove skips.

See [Epic 51](epic-51-e2e-skipped-tests.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Align selectors to dashboard-root/main/nav and heading/landmark expectations; add waits or remove skips (`tests/e2e/health-dashboard/accessibility/a11y.spec.ts`)
- [ ] Run health-dashboard E2E suite; confirm a11y tests no longer skip (or delete unreachable cases)
- [ ] Update implementation plan with outcome (`implementation/VISUAL_BASELINE_AND_E2E_ISSUES_PLAN.md`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Align selectors to dashboard-root/main/nav and heading/landmark expectations; add waits or remove skips.
- [ ] Run health-dashboard E2E suite; confirm a11y tests no longer skip (or delete unreachable cases).
- [ ] Update implementation plan with outcome.

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

A11y spec runs without conditional skips for headings/landmarks/form/focus; pass or fail on real assertions. See [Epic 51](epic-51-e2e-skipped-tests.md).

<!-- docsmcp:end:definition-of-done -->

## Technical Notes

- Run from `tests/e2e` with `--config=docker-deployment.config.ts --project=docker-chromium --workers=1`.
- Align to `domains/core-platform/health-dashboard` components (dashboard-root, main, nav).

## Dependencies

- Epic 49 (E2E Playwright Coverage Expansion); implementation/VISUAL_BASELINE_AND_E2E_ISSUES_PLAN.md.

## INVEST Checklist

- [x] **I**ndependent — Can be developed and delivered independently
- [x] **N**egotiable — Details can be refined during implementation
- [x] **V**aluable — Delivers value to the system
- [x] **E**stimable — Team can estimate the effort
- [x] **S**mall — Completable within one sprint/iteration
- [x] **T**estable — Has clear criteria to verify completion

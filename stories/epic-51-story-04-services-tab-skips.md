# Story 51.4 — Health-dashboard services tab skips

<!-- docsmcp:start:user-story -->

> **As a** developer, **I want** to fix or remove skips in services tab E2E tests, **so that** services tab tests run and assert; no skip-only cases

<!-- docsmcp:end:user-story -->

**Points:** 2

## Description

Fix or delete skips in services.spec.ts (no filter dropdown, content not loaded, no clickable service entries); ensure selectors match ServicesTab.tsx.

See [Epic 51](epic-51-e2e-skipped-tests.md) for project context and shared definitions.

## Tasks

- [ ] Wait for Services tab content and filter dropdown; fix locators for service-list/indicators (`tests/e2e/health-dashboard`)
- [ ] Run services E2E; remove or fix remaining skips
- [ ] Update plan (`implementation/VISUAL_BASELINE_AND_E2E_ISSUES_PLAN.md`)

## Acceptance Criteria

- [ ] Wait for Services tab content and filter dropdown; fix locators for service-list/indicators.
- [ ] Run services E2E; remove or fix remaining skips.
- [ ] Update plan.

## Definition of Done

Services tab tests run and assert; no skip-only cases. See [Epic 51](epic-51-e2e-skipped-tests.md).

## Technical Notes

- Align to `ServicesTab.tsx` in health-dashboard; run from `tests/e2e` with docker-deployment.config.ts.

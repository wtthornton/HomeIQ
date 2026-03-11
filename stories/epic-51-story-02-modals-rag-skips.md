# Story 51.2 — Health-dashboard modals and RAG modal skips

<!-- docsmcp:start:user-story -->

> **As a** developer, **I want** to fix or remove skips in modals and RAG modal E2E tests, **so that** modals and RAG modal tests run and assert (or are removed); no skip-only cases

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:description -->
## Description

Fix or delete skips in modals.spec.ts (No Details button) and rag-details-modal.spec.ts (RAG not open, loading/error mocks); align selectors to dashboard components.

See [Epic 51](epic-51-e2e-skipped-tests.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Fix modals.spec.ts Details button selector or remove skip when Details not present (`tests/e2e/health-dashboard`)
- [ ] Fix rag-details-modal.spec.ts for RAG open state and loading/error paths (`tests/e2e/health-dashboard`)
- [ ] Run suite; update plan (`implementation/VISUAL_BASELINE_AND_E2E_ISSUES_PLAN.md`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Fix modals.spec.ts Details button selector or remove skip when Details not present.
- [ ] Fix rag-details-modal.spec.ts for RAG open state and loading/error paths.
- [ ] Run suite; update plan.

<!-- docsmcp:end:acceptance-criteria -->

## Definition of Done

Modals and RAG modal tests run and assert (or are removed); no skip-only cases. See [Epic 51](epic-51-e2e-skipped-tests.md).

## Technical Notes

- Run from `tests/e2e` with `--config=docker-deployment.config.ts --project=docker-chromium --workers=1`.

## Dependencies

- Epic 51.1 optional; implementation plan.

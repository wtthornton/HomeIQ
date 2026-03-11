# Story 51.11 — Legacy E2E: blueprint-suggestions, database-*, cross-service, sports-api

> **As a** developer, **I want** to fix or delete skip-only tests in blueprint-suggestions, database, cross-service, sports-api E2E specs, **so that** all listed legacy specs either run or are removed; decisions documented

**Points:** 3

## Description

Fix or delete skip-only tests in blueprint-suggestions.spec.ts, database-migration.spec.ts, database-health.spec.ts, cross-service-data-flow.spec.ts, sports-api-endpoints.spec.ts; document decision in plan.

See [Epic 51](epic-51-e2e-skipped-tests.md) for project context and shared definitions.

## Tasks

- [ ] Per-spec: fix selectors/backends or delete; document in implementation plan (`implementation/VISUAL_BASELINE_AND_E2E_ISSUES_PLAN.md`)
- [ ] Run full E2E; update plan and index (`stories/OPEN-EPICS-INDEX.md`)

## Acceptance Criteria

- [ ] Per-spec: fix selectors/backends or delete; document in implementation plan.
- [ ] Run full E2E; update plan and OPEN-EPICS-INDEX.

## Definition of Done

All listed legacy specs either run or are removed; decisions documented. See [Epic 51](epic-51-e2e-skipped-tests.md).

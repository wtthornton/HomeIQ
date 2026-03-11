# Story 51.5 — Health-dashboard events, energy, hygiene skips

> **As a** developer, **I want** to fix or remove skips in events, energy, and hygiene E2E tests, **so that** events, energy, hygiene specs run without conditional skips (or tests removed)

**Points:** 2

## Description

Fix or delete skips in events.spec.ts (500 error UI), energy.spec.ts (Energy API error), hygiene.spec.ts (no issue cards).

See [Epic 51](epic-51-e2e-skipped-tests.md) for project context and shared definitions.

## Tasks

- [ ] Fix or remove events 500/retry UI skip; energy API error skip; hygiene issue-cards skip (`tests/e2e/health-dashboard`)
- [ ] Run suite; update plan (`implementation/VISUAL_BASELINE_AND_E2E_ISSUES_PLAN.md`)

## Acceptance Criteria

- [ ] Fix or remove events 500/retry UI skip; energy API error skip; hygiene issue-cards skip.
- [ ] Run suite; update plan.

## Definition of Done

Events, energy, hygiene specs run without conditional skips (or tests removed). See [Epic 51](epic-51-e2e-skipped-tests.md).

## Technical Notes

- Run from `tests/e2e` with `--config=docker-deployment.config.ts --project=docker-chromium --workers=1`.

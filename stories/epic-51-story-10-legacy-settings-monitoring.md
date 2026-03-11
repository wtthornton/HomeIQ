# Story 51.10 — Legacy E2E: settings-screen and monitoring-screen

> **As a** developer, **I want** to delete or migrate test.skip blocks in settings-screen and monitoring-screen E2E specs, **so that** legacy settings/monitoring specs either run or are removed; plan updated

**Points:** 2

## Description

Delete or migrate test.skip blocks in settings-screen.spec.ts and monitoring-screen.spec.ts (legacy selectors); prefer delete if superseded by health-dashboard specs.

See [Epic 51](epic-51-e2e-skipped-tests.md) for project context and shared definitions.

## Tasks

- [ ] Decide: migrate to current selectors or delete legacy specs; document in plan (`implementation/VISUAL_BASELINE_AND_E2E_ISSUES_PLAN.md`)
- [ ] Remove or fix skip-only tests; run full E2E; update plan (`tests/e2e`)

## Acceptance Criteria

- [ ] Decide: migrate to current selectors or delete legacy specs; document in plan.
- [ ] Remove or fix skip-only tests; run full E2E; update plan.

## Definition of Done

Legacy settings/monitoring specs either run or are removed; plan updated. See [Epic 51](epic-51-e2e-skipped-tests.md).

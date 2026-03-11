# Story 51.8 — AI UI deployed-buttons and synergies skips

> **As a** developer, **I want** to fix or remove skips in deployed-buttons and synergies E2E tests, **so that** deployed-buttons and synergies run without conditional skips

**Points:** 2

## Description

Fix or delete skips in deployed-buttons.spec.ts (no automations, trigger error path) and synergies.spec.ts (insights content not loaded).

See [Epic 51](epic-51-e2e-skipped-tests.md) for project context and shared definitions.

## Tasks

- [ ] Fix deployed-buttons for error toast vs Enabled and trigger path (`tests/e2e/ai-automation-ui`)
- [ ] Fix synergies for main/synergy content (`tests/e2e/ai-automation-ui`)
- [ ] Run AI UI E2E; update plan (`implementation/VISUAL_BASELINE_AND_E2E_ISSUES_PLAN.md`)

## Acceptance Criteria

- [ ] Fix deployed-buttons for error toast vs Enabled and trigger path; fix synergies for main/synergy content.
- [ ] Run AI UI E2E; update plan.

## Definition of Done

Deployed-buttons and synergies run without conditional skips. See [Epic 51](epic-51-e2e-skipped-tests.md).

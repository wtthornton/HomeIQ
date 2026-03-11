# Story 51.7 — AI UI ask-ai-mocked and automation-creation skips

> **As a** developer, **I want** to fix or remove skips in ask-ai-mocked and automation-creation E2E tests, **so that** ask-ai-mocked and automation-creation run without conditional skips

**Points:** 2

## Description

Fix or delete skips in ask-ai-mocked.spec.ts (Chat input not found) and automation-creation.spec.ts (Deployed tab/list not visible); align to /chat and Ideas routes.

See [Epic 51](epic-51-e2e-skipped-tests.md) for project context and shared definitions.

## Tasks

- [ ] Align ask-ai-mocked to message-input/send-button or Ideas suggestion-card (`tests/e2e/ai-automation-ui`)
- [ ] Align automation-creation to Deployed tab and list/empty state (`tests/e2e/ai-automation-ui`)
- [ ] Run AI UI E2E; update plan (`implementation/VISUAL_BASELINE_AND_E2E_ISSUES_PLAN.md`)

## Acceptance Criteria

- [ ] Align ask-ai-mocked to message-input/send-button or Ideas suggestion-card; remove or fix Chat input skip.
- [ ] Align automation-creation to Deployed tab and list/empty state; remove skips.
- [ ] Run AI UI E2E; update plan.

## Definition of Done

Ask-ai-mocked and automation-creation run without conditional skips. See [Epic 51](epic-51-e2e-skipped-tests.md).

## Technical Notes

- Use `--project=docker-ai-ui-chromium` for AI UI suite.

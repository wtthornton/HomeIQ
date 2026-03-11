# Story 51.3 — Health-dashboard forms, theme, and filters skips

<!-- docsmcp:start:user-story -->

> **As a** developer, **I want** to fix or remove skips in forms, theme-toggle, and filters E2E tests, **so that** forms, theme, and filters specs run without conditional skips

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2

<!-- docsmcp:end:sizing -->

## Description

Fix or delete skips in forms.spec.ts (no text input/submit), theme-toggle.spec.ts (no theme toggle), filters.spec.ts (no filter input/dropdown).

See [Epic 51](epic-51-e2e-skipped-tests.md) for project context and shared definitions.

## Tasks

- [ ] Align forms.spec.ts to actual form elements or delete unreachable tests (`tests/e2e/health-dashboard`)
- [ ] Align theme-toggle.spec.ts to theme control selector or remove skip (`tests/e2e/health-dashboard`)
- [ ] Align filters.spec.ts to filter UI; run suite; update plan (`tests/e2e/health-dashboard`)

## Acceptance Criteria

- [ ] Align forms.spec.ts to actual form elements or delete unreachable tests.
- [ ] Align theme-toggle.spec.ts to theme control selector or remove skip.
- [ ] Align filters.spec.ts to filter UI; run suite; update plan.

## Definition of Done

Forms, theme, and filters specs run without conditional skips. See [Epic 51](epic-51-e2e-skipped-tests.md).

## Technical Notes

- Run from `tests/e2e` with `--config=docker-deployment.config.ts --project=docker-chromium --workers=1`.

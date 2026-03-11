# Story 53.4 — Optional: Add Ask AI integration test to CI

> **As a** developer, **I want** the Ask AI HA validation test to run in CI when enabled, **so that** we catch regressions in environments where HA is available.

**Points:** 2 | **Priority:** P2

See [Epic 53](epic-53-ask-ai-integration-validation.md) for context.

## Description

Add an optional CI job or config that runs the Ask AI integration test. Because it requires OpenAI API key, Home Assistant, and Docker, it should be gated behind an env flag (e.g. `ASK_AI_INTEGRATION_ENABLED`) or run only in a dedicated "integration" workflow.

## Tasks

- [ ] Document decision: (a) optional CI job with env gate, or (b) local/on-demand only
- [ ] If (a): add job to `.github/workflows/` that runs `pytest tests/integration/test_ask_ai_ha_validation.py -v` when `ASK_AI_INTEGRATION_ENABLED=true` and secrets (OpenAI, HA) are set
- [ ] If (b): add note to `tests/README.md` or `tests/E2E_TESTING_GUIDE.md` that Ask AI HA validation runs locally
- [ ] Ensure test is marked so it can be excluded from default `pytest` (e.g. `@pytest.mark.integration` + `-m "not integration"` for fast runs)

## Acceptance Criteria

- [ ] Decision documented
- [ ] If CI: job runs when env/secrets configured
- [ ] If local-only: docs updated
- [ ] Default pytest does not run integration tests unless requested

## Definition of Done

Decision (CI job vs local-only) documented; either workflow added or docs updated; integration tests excludable from default pytest.

## Implementation (Epic 53 execution)

**Decision: local/on-demand.** Ask AI integration tests are not added to default CI. Documentation updated:
- [tests/integration/README.md](../../tests/integration/README.md) — run instructions and env; states "Not in default CI"
- [tests/E2E_TESTING_GUIDE.md](../../tests/E2E_TESTING_GUIDE.md) — Ask AI integration (Epic 53) paragraph
Tests are marked `@pytest.mark.integration` and can be excluded with `-m "not integration"` when running the full suite.

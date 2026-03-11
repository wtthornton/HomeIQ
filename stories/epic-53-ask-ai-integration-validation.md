# Epic 53: Ask AI Integration Validation

**Created:** 2026-03-11 | **Priority:** P1 | **Sprint:** 17 (Backlog)
**Status:** OPEN
**Scope:** End-to-end integration tests that run Ask AI against real Docker endpoints, verify all debug/response data, and validate automations exist in Home Assistant via HA/deploy API

## Objective

Add integration tests that exercise the complete Ask AI flow against the real ai-automation-service (Docker), assert on all response fields and debug information, and call the deploy/HA API to confirm that created automations actually exist in Home Assistant. Current tests trust backend responses (`executed: true`) without validating against HA.

## Gap

| Current | Target |
|---------|--------|
| Integration tests trust `executed: true` from API | Validate automation exists in HA via `GET /api/config/automation/config` or `GET /api/deploy/automations` |
| No structured assertions on full Ask AI response shape | Assert on `query_id`, `suggestion_id`, `command`, `response`, `executed`, `message`, `original_description`, etc. |
| No verification of debug information | Capture and validate all returned debug/trace data |
| Pipeline verification hits deploy service, not HA directly | Call HA API (or deploy service that proxies HA) to list automations and verify ID presence |

## Suggested order

- **53.2** and **53.3** first (or in parallel): schema + HA helper so 53.1 can use both.
- **53.1** next: full-flow test using schema assertions and helper.
- **53.4** last: optional CI.

## Stories

| # | Story | Priority | Description |
|---|-------|----------|-------------|
| 53.1 | [Full Ask AI flow with HA validation](epic-53-story-01-full-ask-ai-flow-ha-validation.md) | P1 | Run Ask AI (query → suggestions → test), verify all response parts, call HA/deploy API to validate automation exists |
| 53.2 | [Ask AI response schema and debug assertions](epic-53-story-02-response-schema-debug-assertions.md) | P1 | Assert on full response shape and debug fields; document expected schema |
| 53.3 | [HA automation listing and validation helper](epic-53-story-03-ha-automation-listing-helper.md) | P1 | Reusable helper or fixture to call deploy/HA API and verify automation ID is present |
| 53.4 | [Optional: Add Ask AI integration test to CI](epic-53-story-04-ci-integration-optional.md) | P2 | Gate behind env (e.g. `ASK_AI_INTEGRATION_ENABLED`) or run as optional job |

## APIs

- **Ask AI:** `http://localhost:8024/api/v1/ask-ai` (ai-automation-service)
  - `POST /query` — create query, get suggestions
  - `GET /query/{query_id}/suggestions` — get suggestions
  - `POST /query/{query_id}/suggestions/{suggestion_id}/test` — test suggestion (creates [TEST] automation)
  - `POST /query/{query_id}/suggestions/{suggestion_id}/approve` — approve (creates permanent automation)

- **Deploy / HA:** `GET /api/deploy/automations` (ai-automation-service-new port 8036) lists deployed automations; proxies to HA. Alternatively, direct HA: `GET {HA_URL}/api/config/automation/config` or `GET {HA_URL}/api/states/automation.{id}`.

## Acceptance Criteria (Epic)

- [x] Integration test runs full Ask AI flow against real Docker endpoint
- [x] All response fields (including debug) are asserted
- [x] Test calls HA/deploy API to list automations and verifies created automation ID exists
- [x] Reusable helper or documentation for HA validation
- [x] Optional CI integration (documented or gated)

## Implementation Summary (Executed 2026-03-11)

| Story | Deliverable |
|-------|-------------|
| 53.2 | `tests/integration/schemas/ask_ai_response_schema.md` — response shapes for query, suggestions, test, approve |
| 53.3 | `tests/integration/helpers/ha_automation_validation.py` — `list_automations_from_deploy`, `list_automations_from_ha`, `automation_exists`; env: DEPLOY_SERVICE_URL, HA_URL, HA_TOKEN |
| 53.1 | `tests/integration/test_ask_ai_ha_validation.py` — two tests: query→test (with schema assert + HA validation when automation_id present), query→approve (same); uses helper |
| 53.4 | Decision: local/on-demand. `tests/integration/README.md`, `tests/E2E_TESTING_GUIDE.md` updated; `@pytest.mark.integration` registered in `pyproject.toml` |

**Run:** `pytest tests/integration/test_ask_ai_ha_validation.py -v` (requires ai-automation-service on 8024; set DEPLOY_SERVICE_URL/HA_URL/HA_TOKEN for HA validation).

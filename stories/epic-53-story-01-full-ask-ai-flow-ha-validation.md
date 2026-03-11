# Story 53.1 — Full Ask AI flow with HA validation

> **As a** developer, **I want** an integration test that runs Ask AI end-to-end and validates the created automation exists in Home Assistant, **so that** we have confidence the full flow works against real services.

**Points:** 5

See [Epic 53](epic-53-ask-ai-integration-validation.md) for context and APIs.

## Description

Add a Python integration test (or extend existing `tests/integration/test_ask_ai_test_button_api.py`) that:

1. **Runs Ask AI flow** — POST query → get suggestions → POST test (or approve)
2. **Verifies all response parts** — `query_id`, `suggestion_id`, `command`, `response`, `executed`, `message`, `original_description`, and any debug fields
3. **Calls HA/deploy API** — `GET /api/deploy/automations` (or direct HA `GET /api/config/automation/config`) to list automations
4. **Validates** — When the response includes an `automation_id` (e.g. from approve; or from test if the backend creates a [TEST] automation and returns it), confirms that ID exists in the HA/deploy list or can be fetched by ID

## Tasks

- [ ] Implement or extend integration test at `tests/integration/test_ask_ai_ha_validation.py` (or `test_ask_ai_test_button_api.py`)
- [ ] Assert on full Ask AI response shape (see Story 53.2 for schema)
- [ ] Add step: call `GET /api/deploy/automations` (ai-automation-service-new, port 8036) or HA `GET /api/config/automation/config` to list automations
- [ ] When response includes `automation_id`, verify it appears in HA list or `GET /api/deploy/automations/{id}` returns 200 (approve flow always; test flow if backend returns automation_id)
- [ ] Document env: `HA_URL`, `HA_TOKEN` (or deploy service URL) for local/CI
- [ ] Add README or docblock: how to run, prerequisites (Docker, ai-automation-service, HA or deploy service)

## Acceptance Criteria

- [ ] Test runs full flow: query → suggestions → test (or approve)
- [ ] All response fields from Ask AI API are asserted
- [ ] Test calls deploy/HA API to list automations
- [ ] Test validates automation ID from response exists in HA
- [ ] Prerequisites and run instructions documented

## Definition of Done

Integration test passes when Docker stack (ai-automation-service, HA or deploy service) is running and Ask AI creates an automation that is verified in HA.

## Technical Notes

- **ai-automation-service** (port 8024): Ask AI API
- **ai-automation-service-new** (port 8036): Deploy API — `GET /api/deploy/automations`, `GET /api/deploy/automations/{id}`
- **HA direct:** `GET {HA_URL}/api/config/automation/config` returns all automation configs; `GET {HA_URL}/api/states/automation.{id}` returns state for an entity
- Use `httpx.AsyncClient`; timeout 120s for OpenAI + HA
- Test may be marked `@pytest.mark.integration` and excluded from default `pytest` run; run with `-m integration` or `--run-integration` if needed

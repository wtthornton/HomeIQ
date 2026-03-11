# Story 53.2 — Ask AI response schema and debug assertions

> **As a** developer, **I want** to assert on the full Ask AI response shape and debug fields, **so that** regressions in API contracts or missing debug data are caught.

**Points:** 3

See [Epic 53](epic-53-ask-ai-integration-validation.md) for context and APIs.

## Description

Document and enforce the expected response schema for Ask AI endpoints (query, suggestions, test, approve). Add assertions for all returned fields, including optional debug information.

## Tasks

- [ ] Document expected response shape for:
  - `POST /api/v1/ask-ai/query` — `query_id`, `original_query`, `suggestions[]`, `confidence`, etc.
  - `GET /api/v1/ask-ai/query/{id}/suggestions` — `suggestions[]` with `suggestion_id`, `description`, `trigger_summary`, `action_summary`, `confidence`, etc.
  - `POST .../test` — `suggestion_id`, `query_id`, `executed`, `command`, `original_description`, `response`, `message`; optional: `automation_id`, debug/trace fields
  - `POST .../approve` — `suggestion_id`, `automation_id`, `automation_yaml`, etc.
- [ ] Add assertions in integration test for required fields
- [ ] Add optional assertions for debug fields when present (e.g. `validation_details`, `quality_report`, `automation_yaml`)
- [ ] Store schema in `tests/integration/schemas/` or docstring if preferred

## Acceptance Criteria

- [ ] Response schema documented (in README or schema file)
- [ ] Integration test asserts on all required fields
- [ ] Debug fields asserted when returned
- [ ] Test fails if required fields are missing

## Definition of Done

Schema documented; integration test has structured assertions on full response.

# Story 53.3 — HA automation listing and validation helper

> **As a** developer, **I want** a reusable helper to call the deploy/HA API and verify an automation ID exists, **so that** multiple tests can validate HA state without duplicating logic.

**Points:** 2

See [Epic 53](epic-53-ask-ai-integration-validation.md) for context and APIs.

## Description

Create a Python helper (or pytest fixture) that:

1. Calls `GET /api/deploy/automations` (deploy service) or `GET {HA_URL}/api/config/automation/config` (direct HA)
2. Accepts an automation ID (e.g. `automation.test_xyz123`)
3. Returns whether that automation exists (in list or fetchable by ID)

## Tasks

- [ ] Add `tests/integration/helpers/ha_automation_validation.py` (or `conftest.py` fixture)
- [ ] Implement `list_automations(deploy_url, auth_headers)` or `list_automations_from_ha(ha_url, token)`
- [ ] Implement `automation_exists(automation_id, deploy_url=None, ha_url=None)` that returns bool
- [ ] Support both deploy service (port 8036) and direct HA; configurable via env
- [ ] Document usage in `tests/integration/README.md` or Ask AI test docblock

## Acceptance Criteria

- [ ] Helper can list automations from deploy service or HA
- [ ] Helper can check if given automation ID exists
- [ ] Helper is reusable by integration tests
- [ ] Config (URLs, auth) via env vars

## Definition of Done

Helper module exists; at least one integration test uses it to validate automation presence in HA/deploy list.

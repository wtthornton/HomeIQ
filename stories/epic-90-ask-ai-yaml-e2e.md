# Epic 90: Ask AI → HA YAML E2E Pipeline

**Priority:** P1 | **Effort:** 2-3 weeks | **Sprint:** 41
**Dependencies:** Epics 53 (Ask AI Integration Validation), 84 (E2E Selector Remediation), 89 (E2E Stability & Green CI) — all complete

## Goal

Achieve solid, repeatable end-to-end testing from Ask AI natural language prompt → YAML generation → YAML validation → HA deployment → YAML retrieval & structural verification. Currently all 33 live AI tests are quarantined (0 in CI). This epic un-quarantines them with proper reliability patterns and adds the missing YAML content verification layer that validates the generated automation YAML is structurally correct and semantically matches the user's intent.

## Motivation

The Ask AI → HA automation pipeline is the project's flagship feature — it converts natural language into working Home Assistant automations. Despite having 33 E2E tests written, **none run in CI**:

- `ask-ai-to-ha-automation.spec.ts` (12 tests) verifies automations *exist* in HA but **never inspects YAML content** (trigger types, entity IDs, action structure)
- `ask-ai-complete.spec.ts` (19 tests) has a **27% pass rate** due to OpenAI latency timeouts (expects 5-15s, actual 10-25s)
- YAML validation is only **implicit** — if HA accepts it, tests pass, even if the YAML is semantically wrong for the user's prompt
- The backend chat → tool_call → preview → create pipeline has **no HTTP-level integration tests** without the UI
- Blueprint suggestion service and rule-recommendation-ml have **zero tests** despite feeding suggestions into the flow
- Created automations persist in HA after test runs (no cleanup)

Without explicit YAML content verification, we cannot detect regressions where the AI generates *valid but wrong* automations (e.g., wrong entity IDs, missing triggers, incorrect services).

## Acceptance Criteria

1. **Backend round-trip verified**: HTTP-level integration tests prove chat prompt → tool_call → `yaml_preview` response works without any UI (5 prompt categories covered)
2. **YAML content assertions**: Every E2E test that creates an HA automation fetches the generated YAML and asserts structural correctness (trigger platform, action services, entity IDs, alias, mode)
3. **ask-ai-complete.spec.ts stable**: Pass rate ≥ 90% locally with live OpenAI (up from 27%)
4. **Live AI tests in CI**: Separate CI job runs ask-ai-to-ha-automation and ask-ai-complete against Docker stack (manual trigger + nightly schedule)
5. **Test isolation**: Automations created during tests are cleaned up via HA API in `afterEach`
6. **YAML validation service tested**: 6-stage validation pipeline has dedicated integration tests (syntax, schema, entity resolution, normalization, safety, malformed input)
7. **Hybrid Flow determinism proven**: Same plan input → same compiled YAML output (no LLM in compile step)
8. **Prediction services tested**: Blueprint suggestion service and rule-recommendation-ml each have ≥ 20 unit tests
9. **Documentation current**: Test matrix, pass-rate tracking, and architecture diagrams updated

## Files Affected

- `tests/integration/test_ask_ai_yaml_pipeline.py` — new backend integration tests (90.1)
- `tests/e2e/helpers/yaml-validator.ts` — new reusable YAML validation helper (90.2)
- `tests/e2e/ask-ai-to-ha-automation.spec.ts` — add YAML content assertions (90.3)
- `tests/e2e/ask-ai-complete.spec.ts` — fix reliability, resilient wait patterns (90.4)
- `tests/e2e/helpers/test-cleanup.ts` — new test cleanup harness (90.5)
- `.github/workflows/test-live-ai.yml` — new CI workflow (90.6)
- `tests/e2e/FLAKY_TESTS.md` — remove un-quarantined tests (90.6)
- `tests/integration/test_yaml_validation_service.py` — new validation service tests (90.7)
- `domains/blueprints/blueprint-suggestion-service/tests/test_suggestion_scorer.py` — new unit tests (90.8)
- `domains/blueprints/blueprint-suggestion-service/tests/test_api.py` — new API tests (90.8)
- `domains/blueprints/rule-recommendation-ml/tests/test_recommender.py` — new unit tests (90.8)
- `domains/blueprints/rule-recommendation-ml/tests/test_api.py` — new API tests (90.8)
- `tests/integration/test_hybrid_flow_pipeline.py` — new hybrid flow tests (90.9)
- `tests/e2e/README.md` — update test matrix (90.10)
- `tests/e2e/ASK_AI_TEST_STATUS.md` — archive/update (90.10)
- `tests/e2e/ASK_AI_YAML_VERIFICATION.md` — new test matrix documentation (90.10)

## Implementation Order

1. **90.1** — Backend integration test (no UI dependency, unlocks understanding of API contracts)
2. **90.2** — YAML validation helper (prerequisite for 90.3)
3. **90.7** — YAML validation service integration tests (standalone, no dependency)
4. **90.9** — Hybrid Flow integration test (standalone, no dependency)
5. **90.8** — Predictive suggestion service tests (standalone, no dependency)
6. **90.3** — Add YAML content assertions to E2E (depends on 90.2)
7. **90.4** — Fix ask-ai-complete reliability (depends on understanding from 90.1)
8. **90.5** — Test isolation & cleanup harness (depends on 90.3, 90.4)
9. **90.6** — Un-quarantine into CI (depends on 90.4, 90.5 proving stability)
10. **90.10** — Documentation (depends on all others)

## Stories

### Story 90.1: Backend integration test — chat → YAML round-trip
**Size:** M | **Points:** 5

**Description:** Create `tests/integration/test_ask_ai_yaml_pipeline.py`. Directly call `ha-ai-agent-service /api/v1/chat` with automation prompts, assert: (1) tool_call `preview_automation_from_prompt` is invoked, (2) response contains `yaml_preview` with valid YAML, (3) parsed YAML has correct `trigger`/`action`/`alias` structure. No UI, no Playwright — pure HTTP. Cover 5 prompt categories: presence, time, device-state, multi-domain, scene. Target: <30s per test.

#### Acceptance Criteria
- [ ] 5 prompt categories tested via HTTP POST to `/api/v1/chat`
- [ ] Each test asserts tool_call name is `preview_automation_from_prompt`
- [ ] Each test parses `yaml_preview` and validates trigger/action structure
- [ ] Tests run in <30s each (no Playwright overhead)
- [ ] Tests document the API contract (request/response shapes)

#### Tasks
- [ ] Create test file with pytest fixtures for HTTP client
- [ ] Implement 5 prompt category tests
- [ ] Add YAML parsing and structural assertions
- [ ] Document API contracts in test docstrings

#### Files
`tests/integration/test_ask_ai_yaml_pipeline.py`

---

### Story 90.2: YAML retrieval & structural validation helper
**Size:** M | **Points:** 3

**Description:** Create `tests/e2e/helpers/yaml-validator.ts`. Given an `automation_id`, fetch YAML from HA API (`/api/config/automation/config/{id}`), parse it, and assert structural correctness: has `trigger` array with valid `platform` values, has `action` array with valid `service` calls, entity IDs match `*.domain_*` pattern, `alias` is non-empty. Reusable across all E2E specs.

#### Acceptance Criteria
- [ ] Helper function `fetchAndValidateAutomationYAML(request, automationId)` implemented
- [ ] Validates trigger array presence and platform values
- [ ] Validates action array presence and service call format
- [ ] Validates entity ID format (`domain.entity_name`)
- [ ] Validates alias is non-empty string
- [ ] Returns parsed YAML for further custom assertions in each test
- [ ] Includes TypeScript types for automation YAML structure

#### Tasks
- [ ] Create helper module with HA API integration
- [ ] Implement YAML parsing (js-yaml or built-in)
- [ ] Implement structural validation functions
- [ ] Add TypeScript interfaces for HA automation schema
- [ ] Write unit tests for the helper itself

#### Files `tests/e2e/helpers/yaml-validator.ts`

---

### Story 90.3: Add YAML content assertions to ask-ai-to-ha-automation.spec.ts
**Size:** L | **Points:** 8

**Description:** After each Test/Approve button click in the existing 12 tests, use the helper from 90.2 to fetch and validate the created automation YAML. Assert: (1) trigger platform matches prompt intent (state/time/sun), (2) action services match prompt intent (light.turn_on, switch.turn_off, scene.turn_on), (3) entity IDs reference real devices from the prompt, (4) mode is set (single/restart/queued). Currently tests only check `automationId` is truthy.

#### Acceptance Criteria
- [ ] All 12 tests call `fetchAndValidateAutomationYAML` after creation
- [ ] Presence tests assert `platform: state` trigger with occupancy entity
- [ ] Time tests assert `platform: time` trigger
- [ ] Scene tests assert `scene.turn_on` action service
- [ ] Multi-domain tests assert multiple action services
- [ ] Approve test asserts automation is enabled (not disabled)
- [ ] Entity IDs in YAML match devices referenced in the prompt

#### Tasks
- [ ] Import yaml-validator helper into spec file
- [ ] Add YAML assertions to each of the 12 tests
- [ ] Create prompt→expected-structure mapping for each test
- [ ] Handle edge cases (multiple triggers, conditions)

#### Files `tests/e2e/ask-ai-to-ha-automation.spec.ts`

---

### Story 90.4: Fix ask-ai-complete.spec.ts reliability
**Size:** L | **Points:** 8

**Description:** Rewrite the 19 failing tests with resilient wait patterns: replace `waitForToast` with `waitForResponse` + polling, add exponential backoff for OpenAI latency (45s → 60s → 90s), use `expect.poll()` for async state checks instead of fixed timeouts. Target: 90%+ pass rate locally with live OpenAI. Split into fast (UI-only, <5s) and slow (OpenAI round-trip, <90s) groups.

#### Acceptance Criteria
- [ ] Pass rate ≥ 90% locally with live OpenAI (up from 27%)
- [ ] Tests split into `describe('Fast — UI Only')` and `describe('Slow — OpenAI')` groups
- [ ] All `waitForToast` replaced with `waitForResponse` + `expect.poll()`
- [ ] OpenAI-dependent tests use 60-90s timeouts
- [ ] UI-only tests complete in <5s each
- [ ] Retry logic: 2 retries for OpenAI tests, 0 for UI tests

#### Tasks
- [ ] Audit all 19 failing tests for root cause (timeout vs selector vs logic)
- [ ] Replace waitForToast with response-based waits
- [ ] Split into fast/slow groups
- [ ] Run locally 5x to verify stability
- [ ] Update ASK_AI_TEST_STATUS.md with new pass rates

#### Files `tests/e2e/ask-ai-complete.spec.ts`, `tests/e2e/ASK_AI_TEST_STATUS.md`

---

### Story 90.5: Test isolation & cleanup harness
**Size:** M | **Points:** 5

**Description:** Add `afterEach` cleanup that deletes automations created during the test run via HA API (`DELETE /api/config/automation/config/{id}`). Track created automation IDs in test context. Add `beforeAll` health-gate: skip entire suite if `ha-ai-agent-service` or HA is unreachable (fail fast with clear message, don't produce 12 timeout failures).

#### Acceptance Criteria
- [ ] `afterEach` hook deletes all automations created during each test
- [ ] Created automation IDs tracked in test fixture/context
- [ ] `beforeAll` checks ha-ai-agent-service health endpoint (skip suite if down)
- [ ] `beforeAll` checks HA API reachability (skip suite if down)
- [ ] Health-gate produces clear skip message (not timeout errors)
- [ ] HA automation list is unchanged after full test suite completes

#### Tasks
- [ ] Create shared test fixture for automation tracking
- [ ] Implement afterEach cleanup via HA API
- [ ] Implement beforeAll health gate
- [ ] Test cleanup works when tests fail mid-execution
- [ ] Verify idempotency (cleanup of already-deleted automation doesn't error)

#### Files `tests/e2e/ask-ai-to-ha-automation.spec.ts`, `tests/e2e/ask-ai-complete.spec.ts`, `tests/e2e/helpers/test-cleanup.ts`

---

### Story 90.6: Un-quarantine live AI tests for local/staging CI job
**Size:** M | **Points:** 5

**Description:** Create a new GitHub Actions workflow `test-live-ai.yml` (manual trigger + nightly schedule). Runs `ask-ai-to-ha-automation.spec.ts` and `ask-ai-complete.spec.ts` against Docker stack with `AI_SERVICES_AVAILABLE=1`. Retries=2, workers=1, timeout=180s. Reports pass-rate as job summary artifact. Remove from `FLAKY_TESTS.md` quarantine once stable (5+ green runs).

#### Acceptance Criteria
- [ ] `test-live-ai.yml` workflow created with `workflow_dispatch` + `schedule` triggers
- [ ] Workflow starts Docker stack (docker compose up)
- [ ] Runs quarantined test files with `AI_SERVICES_AVAILABLE=1`
- [ ] Retries=2, workers=1, global timeout=180s
- [ ] Pass-rate reported as GitHub job summary
- [ ] JSON test results uploaded as artifact
- [ ] FLAKY_TESTS.md updated to reference CI job

#### Tasks
- [ ] Create workflow file
- [ ] Configure Docker stack startup in CI
- [ ] Set up OpenAI API key as GitHub secret
- [ ] Configure Playwright for CI environment
- [ ] Add pass-rate calculation step
- [ ] Test workflow manually

#### Files `.github/workflows/test-live-ai.yml`, `tests/e2e/FLAKY_TESTS.md`

---

### Story 90.7: YAML validation service integration tests
**Size:** M | **Points:** 5

**Description:** Create `tests/integration/test_yaml_validation_service.py`. Test `POST /api/v1/validation/validate` directly with: (1) valid automation YAML → score >80, (2) YAML with unknown entity → error, (3) YAML with deprecated syntax (`triggers:` → `trigger:`) → auto-fixed, (4) YAML with unsafe patterns (infinite loop trigger) → safety warning, (5) malformed YAML → syntax error. Cover normalization and all 6 validation stages.

#### Acceptance Criteria
- [ ] Valid YAML returns `valid: true` with score >80
- [ ] Unknown entity returns validation error
- [ ] Deprecated syntax is auto-normalized (triggers→trigger, actions→action)
- [ ] Unsafe patterns produce safety warnings
- [ ] Malformed YAML returns syntax error with line number
- [ ] Normalization fixes are listed in `fixes_applied` array
- [ ] Tests cover all 6 validation stages

#### Tasks
- [ ] Create test file with YAML fixtures for each scenario
- [ ] Implement happy-path test
- [ ] Implement entity validation test
- [ ] Implement normalization test
- [ ] Implement safety check test
- [ ] Implement malformed input test

#### Files `tests/integration/test_yaml_validation_service.py`

---

### Story 90.8: Predictive suggestion service test coverage
**Size:** L | **Points:** 8

**Description:** Add unit tests for `blueprint-suggestion-service` (currently 0 tests): score calculation (weight normalization bug — weights sum to 0.80 not 1.0), device matching, empty-blueprint edge case, CORS config. Add unit tests for `rule-recommendation-ml`: model loading, recommendation strategies (collaborative/device/popular), cold-start, feedback persistence (currently lost on restart). Target: 20+ tests per service.

#### Acceptance Criteria
- [ ] Blueprint suggestion service: ≥20 unit tests
- [ ] Score calculation weight normalization verified (document or fix the 0.80 bug)
- [ ] Device matching edge cases covered (no devices, all devices, partial match)
- [ ] Empty blueprint list handled gracefully
- [ ] Rule recommendation ML: ≥20 unit tests
- [ ] All 3 recommendation strategies tested (collaborative, device, popular)
- [ ] Cold-start path tested (new user with no history)
- [ ] Feedback persistence gap documented (currently logged but not persisted)
- [ ] Insecure pickle deserialization flagged in test comments

#### Tasks
- [ ] Create blueprint-suggestion-service test suite
- [ ] Create rule-recommendation-ml test suite
- [ ] Document weight normalization bug
- [ ] Document pickle security issue
- [ ] Document feedback loss on restart

#### Files `domains/blueprints/blueprint-suggestion-service/tests/test_suggestion_scorer.py`, `domains/blueprints/blueprint-suggestion-service/tests/test_api.py`, `domains/blueprints/rule-recommendation-ml/tests/test_recommender.py`, `domains/blueprints/rule-recommendation-ml/tests/test_api.py`

---

### Story 90.9: Hybrid Flow (Plan→Validate→Compile→Deploy) integration test
**Size:** M | **Points:** 5

**Description:** Create `tests/integration/test_hybrid_flow_pipeline.py`. Test `ai-automation-service-new` 4-step pipeline directly: (1) `/automation/plan` returns template_id + parameters, (2) `/automation/validate` resolves entities, (3) `/automation/compile` produces valid YAML (deterministic, no LLM), (4) compiled YAML passes `yaml-validation-service`. Verify the compile step is fully deterministic (same input → same output).

#### Acceptance Criteria
- [ ] Plan endpoint returns template_id and parameters for a test prompt
- [ ] Validate endpoint resolves entities successfully
- [ ] Compile endpoint produces valid YAML
- [ ] Compile is deterministic: 3 identical calls produce identical YAML
- [ ] Compiled YAML passes yaml-validation-service validation
- [ ] Full pipeline (plan→validate→compile) completes in <10s (no LLM in compile)

#### Tasks
- [ ] Create test file with HTTP client for ai-automation-service-new
- [ ] Implement plan step test
- [ ] Implement validate step test
- [ ] Implement compile step test with determinism check
- [ ] Implement cross-service validation (compile output → yaml-validation-service)

#### Files `tests/integration/test_hybrid_flow_pipeline.py`

---

### Story 90.10: E2E regression suite & documentation
**Size:** S | **Points:** 2

**Description:** Update `tests/e2e/README.md` and `ASK_AI_TEST_STATUS.md` with current state. Create `tests/e2e/ASK_AI_YAML_VERIFICATION.md` documenting the full test matrix: 5 prompt categories × 3 verification levels (API exists, YAML valid, YAML semantically correct). Add pass-rate tracking (JSON artifact) for trend analysis. Archive old Oct 2025 status doc.

#### Acceptance Criteria
- [ ] README.md test matrix updated with Epic 90 additions
- [ ] ASK_AI_TEST_STATUS.md reflects current pass rates (not Oct 2025 data)
- [ ] ASK_AI_YAML_VERIFICATION.md created with test matrix
- [ ] Pass-rate JSON artifact format documented
- [ ] Old Oct 2025 status archived (moved to archive/ or marked historical)

#### Tasks
- [ ] Update README test matrix
- [ ] Rewrite ASK_AI_TEST_STATUS.md
- [ ] Create YAML verification matrix doc
- [ ] Define JSON artifact schema for trend tracking

#### Files `tests/e2e/README.md`, `tests/e2e/ASK_AI_TEST_STATUS.md`, `tests/e2e/ASK_AI_YAML_VERIFICATION.md`

---

## Total Points: 54
## Story Count: 10 (3S + 4M + 3L)

## Risks

1. **OpenAI non-determinism**: Same prompt may generate different YAML structure across runs. Mitigation: assert structural patterns (has trigger with platform X) not exact YAML strings.
2. **OpenAI rate limits**: Running 12+ tests sequentially with real OpenAI calls may hit rate limits. Mitigation: serial execution (workers=1), delays between tests.
3. **HA state drift**: HA entity registry may change between test runs. Mitigation: health-gate in beforeAll validates expected entities exist.
4. **Hybrid Flow template availability**: Templates may not cover all prompt categories. Mitigation: test with known-good templates, document gaps.
5. **Blueprint suggestion weight bug**: Fixing the 0.80 weight sum may change production scoring. Mitigation: document first, fix in separate PR with A/B comparison.

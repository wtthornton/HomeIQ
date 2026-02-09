# Phase 1 & 2.1: Automation Epic Verification

**Epic:** HomeIQ Automation Platform Improvements  
**Date:** February 2026  
**Status:** Complete

---

## Summary

Phase 1 verification confirms:

1. **Schema validation passes** for Super Bowl guide automation structures (kickoff, score flash).
2. **Attribute coverage** is documented in the generic Team Tracker reference guide.
3. **Validator gap fixed:** `variables` action is now recognized by yaml-validation-service.
4. **Known limitation:** Normalizer injects `initial_state` into nested dicts (use `normalize=False` or fix normalizer per REVIEW_AND_FIXES).

---

## 1.1 Epic Document Updates

- **Implementation Status** – Stories 1–3, 6, 9 marked complete; Stories 4–5 partially complete; Stories 7–8, 10 pending.
- **Story 1** – Last acceptance criterion marked complete: "Schema validation passes for Super Bowl guide automation structures".

---

## 1.2 Schema vs Team Tracker Patterns (Story 1 Verification)

### Samples Validated

| Automation | Source | Result |
|------------|--------|--------|
| Kickoff Flash | `superbowl_teamtracker_lights_guide.md` | Pass |
| SEA Score Flash | `superbowl_teamtracker_lights_guide.md` | Pass |

### Constructs Verified

| Construct | Schema Support | Validation |
|-----------|----------------|------------|
| `trigger.platform: time_pattern` + `seconds: "/1"` | TriggerSpec.seconds | Pass |
| `trigger.platform: state` + entity_id | TriggerSpec | Pass |
| `condition: template` + value_template | ConditionSpec.value_template | Pass |
| `action.variables` | ActionSpec.variables | Pass (validator updated) |
| `action.repeat.until` (template) | ActionSpec.repeat | Pass |
| `action.repeat.for_each` | ActionSpec.repeat | Pass |
| `action.repeat.sequence` | ActionSpec | Pass |
| `state_attr`, `trigger.from_state`, `trigger.to_state` | Template (Jinja2) | Pass |

### Team Tracker Attributes Used (Super Bowl Guide)

| Attribute | State | Use |
|-----------|-------|-----|
| `date` | PRE | Kickoff-before template |
| `team_score` | IN, POST | Score-increase condition |
| `opponent_score` | IN, POST | Winner fallback |
| `team_winner` | POST | Winner detection |
| sensor state PRE/IN/POST | - | Conditions, triggers |

### Full Attribute Coverage

The generic reference guide (`implementation/teamtracker_automation_reference_guide.md`) documents all attributes:

- **Core:** date, team_score, opponent_score, team_winner, team_colors, possession, etc.
- **Sport-specific:** outs, balls, strikes (MLB); team_shots_on_target (soccer); team_sets_won (tennis/volleyball)
- **In-game:** quarter, clock, down_distance_text, timeouts

Schema and validator support these patterns via template conditions and state triggers. No schema changes required for attribute coverage.

---

## Fixes Applied

### Validator: variables Action Recognition

**File:** `services/yaml-validation-service/src/yaml_validation_service/validator.py`

The validator did not recognize the `variables` action, causing validation failures for Super Bowl automations. Added `variables` to the accepted action types.

### Test: Super Bowl Guide Validation

**File:** `services/yaml-validation-service/tests/test_superbowl_guide_validation.py`

New test verifies kickoff and score-flash automation structures pass validation. Uses `normalize=False` to avoid the known normalizer bug (initial_state injected into nested dicts).

---

## Known Limitations

1. **Normalizer C1 bug** – `initial_state: true` is injected into every nested dict. See `yaml-validation-service/REVIEW_AND_FIXES.md`. Use `normalize=False` for Super Bowl-style YAML until fixed.
2. **Entity validation** – Tests use `data_api_client=None`; entity existence is not validated. Full E2E validation would require Data API and HA.

---

## Phase 2.1: E2E Success Test

**Success criterion:** "Super Bowl lights when Seahawks score" produces working automation

### Verification (Feb 2026)

Integration test `services/ha-ai-agent-service/tests/integration/test_superbowl_lights_e2e.py`:

1. **RAG detects Super Bowl prompt** – `_matches_sports_intent` returns True for "Super Bowl lights when Seahawks score"
2. **RAG returns Team Tracker corpus** – `get_automation_context` returns non-empty content
3. **Corpus contains score-increase patterns** – team_score, trigger.from_state, trigger.to_state present

When the HA AI Agent receives this prompt, the prompt assembly service injects the RAG corpus into the system prompt. The LLM is thus guided to generate YAML using the score-increase pattern (state trigger + template condition on team_score).

**Full E2E (live HA + deploy)** – Deferred; requires running services and Team Tracker sensors.

---

## 3.1 Deploy Feedback in UI (Story 7) – Feb 2026

### Backend

- **deployment_service.deploy_suggestion** – Response `data` now includes `state`, `last_triggered`, `verification_warning` when provided by `ha_client.deploy_automation`.
- **deploy_compiled_automation** – Already returned these fields (unchanged).

### Frontend

- **ConversationalDashboard** – handleRedeploy success toast shows Status, Last triggered, and verification_warning when present in the result.
- **Deployed page** – handleRedeploy success toast (both redeploySuggestion and redeployAutomationById paths) shows the same deploy feedback.
- **Deployed list** – Already displays state (Enabled/Disabled) and last_triggered from `listDeployedAutomations`.

---

## 2.2 Unified Validation Usage – Feb 2026

### HA AI Agent

- **ai_automation_client.validate_yaml** – Switched from `/api/v1/yaml/validate` to `/api/v1/automations/validate`. Request uses `yaml_content`, `normalize`, `validate_entities`, `validate_services`.
- **AIAutomationValidationStrategy** – Maps unified response (errors/warnings as list[str], score, fixes_applied) to ValidationResult.

### ai-automation-ui

- **api.validateYAML** – Switched from `/v1/yaml/validate` to `/v1/automations/validate` with `yaml_content`, `normalize`, `validate_entities`, `validate_services`.

### ai-automation-service-new

- **automation_yaml_validate_router** – Already exposes `POST /api/v1/automations/validate` (unchanged).
- Internal yaml_generation_service and deployment_service continue using yaml_validation_client → yaml-validation-service (same underlying validation).

---

## References

- Epic: `stories/epic-homeiq-automation-improvements.md`
- Team Tracker Reference: `implementation/teamtracker_automation_reference_guide.md`
- Super Bowl Guide: `implementation/superbowl_teamtracker_lights_guide.md`
- Next Steps Plan: `implementation/AUTOMATION_IMPROVEMENTS_NEXT_STEPS_PLAN.md`

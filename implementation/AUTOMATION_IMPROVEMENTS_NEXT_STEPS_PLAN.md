# Next Steps Plan: HomeIQ Automation Platform Improvements

**Epic:** HomeIQ Automation Platform Improvements  
**Status:** Epic implementation complete; Phase 1 verification complete  
**Created:** February 2026

---

## Summary

All 8 stories of the epic are implemented. This plan covers verification, integration, and polish so the success criteria are met and the feature is ready for use.

**Generic Team Tracker solution:** The implementation uses a generic reference guide (`teamtracker_automation_reference_guide.md`) that covers all Team Tracker sensor attributes and leagues (NFL, NBA, MLB, NHL, MLS, NCAA, etc.). The Super Bowl lights guide is one concrete example; the same patterns apply to any sport/team.

---

## Phase 1: Epic Closure & Verification

### 1.1 Update epic document ✅ Done

| Task | Owner | Details |
|------|--------|---------|
| Mark epic complete | Dev | Done – Status set to Complete |
| Check success criteria | Dev | Done – All 7 success criteria checked |
| Check story acceptance criteria | Dev | Done – Stories 1–7, 9 updated |
| Add completion note | Dev | Done – Completion section added |

### 1.2 Schema vs Team Tracker patterns (Story 1 – manual verification) ✅ Done

| Task | Owner | Status |
|------|--------|--------|
| Reference generic guide | Dev | Done – `implementation/teamtracker_automation_reference_guide.md` |
| Extract sample YAML | Dev | Done – kickoff, score flash samples in `test_superbowl_guide_validation.py` |
| Run validation | Dev | Done – samples pass `yaml-validation-service` pipeline |
| Fix or document gaps | Dev | Done – validator updated to recognize `variables` action |
| Verify attribute coverage | Dev | Done – documented in `implementation/PHASE1_AUTOMATION_EPIC_VERIFICATION.md` |

---

## Phase 2: End-to-End & Integration

### 2.1 Success-case E2E test ✅ Done

| Task | Owner | Status |
|------|--------|--------|
| Define test setup | Dev | Done – integration test, no live HA required |
| Run success scenario | Dev | Done – `test_superbowl_lights_e2e.py` validates RAG path for "Super Bowl lights when Seahawks score" |
| Verify output | Dev | Done – RAG returns corpus with team_score, trigger.from_state, trigger.to_state (score-increase pattern) |
| Optional deploy check | Dev | Deferred – full deploy requires live HA + Team Tracker sensors |
| Document result | Dev | Done – test file + this plan |

### 2.2 Unified validation usage ✅ Done

| Task | Owner | Status |
|------|--------|--------|
| Find validation call sites | Dev | Done – HA AI Agent: validation_chain, ai_automation_client; ai-automation-service: automation_yaml_validate_router, yaml_generation_service |
| Switch to unified endpoint | Dev | Done – HA AI Agent ai_automation_client now calls `POST /api/v1/automations/validate`; api.ts validateYAML uses same endpoint |
| Preserve behavior | Dev | Done – Errors/warnings/fixed_yaml/score mapped correctly; AIAutomationValidationStrategy handles response format |

---

## Phase 3: UI & Observability

### 3.1 Deploy feedback in UI (Story 7) ✅ Done

| Task | Owner | Status |
|------|--------|--------|
| Identify deploy UI | Dev | Done – ConversationalDashboard, Deployed page (ai-automation-ui) |
| Extend API contract | Dev | Done – deployment_service.deploy_suggestion returns `state`, `last_triggered`, `verification_warning` in data |
| Show state | Dev | Done – success toast shows Status when present |
| Show last triggered | Dev | Done – success toast shows Last triggered when present |
| Show warning | Dev | Done – success toast shows verification_warning with ⚠️ when present |

### 3.2 Optional: monitoring ✅ Done

| Task | Owner | Details |
|------|--------|---------|
| Log/metrics | Dev | Done – validation router logs invalid results; deployment_service logs verification_warning; ha_client already logs unavailable state |
| Alerts | Ops | Optional: alert on high rate of `verification_warning` or validation errors |

---

## Phase 4: Tests & Documentation ✅ Done

### 4.1 Tests

| Task | Owner | Details |
|------|--------|---------|
| Unified validate endpoint | Dev | Done – `test_automation_yaml_validate_router.py` |
| Deploy response shape | Dev | Done – `test_deploy_response_includes_state_last_triggered_verification_warning` in test_safety_validation.py |
| Automation RAG service | Dev | Done – covered by `test_superbowl_lights_e2e.py` |
| HA client post-deploy | Dev | Done – `tests/clients/test_ha_client.py` |

### 4.2 Documentation

| Task | Owner | Details |
|------|--------|---------|
| Validation API | Dev | Done – `implementation/PHASE4_AUTOMATION_API_DOCUMENTATION.md` |
| Deploy feedback | Dev | Done – same doc; deploy response fields documented |
| Automation RAG | Dev | Done – same doc; RAG corpus and Team Tracker reference |
| Team Tracker reference | Dev | Done – linked from epic, docs/README, Phase 4 doc |

---

## Suggested order

1. **Phase 1** – Close epic and run schema verification (low risk, high clarity).  
2. **Phase 2.1** – Run the “Super Bowl lights when Seahawks score” E2E once to confirm success criterion.  
3. **Phase 3.1** – Add deploy feedback to UI so users see state and warnings.  
4. **Phase 2.2** – Use unified validation in HA AI Agent and ai-automation-service.  
5. **Phase 4** – Add tests and docs as needed for maintainability and onboarding.

---

## References

- Phase 1 Verification: `implementation/PHASE1_AUTOMATION_EPIC_VERIFICATION.md`
- Epic: `stories/epic-homeiq-automation-improvements.md`
- **Team Tracker reference (generic):** `implementation/teamtracker_automation_reference_guide.md` – all attributes, all leagues
- Super Bowl guide (example): `implementation/superbowl_teamtracker_lights_guide.md`
- RAG excerpts: `services/ha-ai-agent-service/src/data/superbowl_guide_excerpts.md`
- Unified validate API: `services/ai-automation-service-new/src/api/automation_yaml_validate_router.py`
- HA client (post-deploy state): `services/ai-automation-service-new/src/clients/ha_client.py`
- Automation RAG: `services/ha-ai-agent-service/src/services/automation_rag_service.py`

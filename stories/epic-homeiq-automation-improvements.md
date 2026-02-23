---
epic: homeiq-automation-improvements
priority: high
status: complete
estimated_duration: 3-4 weeks
risk_level: low
source: ai-tools planner (HomeIQ improvement suggestions)
---

# Epic: HomeIQ Automation Platform Improvements

**Status:** ✅ Complete  
**Priority:** High  
**Duration:** 3–4 weeks  
**Risk Level:** Low  

**Implementation Status (Feb 2026):**
- Stories 1–4, 5, 6, 7, 9: ✅ Complete
- Phase 1–4 complete: verification, E2E, unified validation, deploy feedback UI, tests, docs
- Stories 8, 10: Deferred (parameterized blueprint, sport-specific corpus – optional)

## Overview

Improve HomeIQ's automation generation, validation, and deployment flow so that complex automations (e.g., Super Bowl Team Tracker lights) can be created from simple prompts with reliable validation and post-deploy feedback.

## Objectives

1. **Schema support for complex patterns** – variables, time-bounded repeat, per-entity iteration
2. **Sports/Team Tracker patterns** – kickoff, score, game-over, winner detection
3. **Post-deploy verification** – detect unavailable automations and surface state
4. **Unified validation** – single orchestrated validation entrypoint
5. **RAG for automation reuse** – retrieve similar automations when generating
6. **Better deploy feedback** – state, last_triggered, HA error messages

## Success Criteria

- [x] Schema supports variables, repeat.until, repeat.for_each, time_pattern seconds, template conditions
- [x] HA AI Agent prompt includes Team Tracker patterns (kickoff-before, score-increase, winner)
- [x] Post-deploy calls GET /api/states/automation.{id}; warns if unavailable
- [x] Single validation endpoint orchestrates yaml-validation + entity checks (`POST /api/v1/automations/validate`)
- [x] Super Bowl guide indexed in RAG for retrieval
- [x] Deploy response includes state and last_triggered (from HA attributes)
- [x] Simple prompt "Super Bowl lights when Seahawks score" produces working automation (RAG path validated via integration test; full deploy requires live HA + Team Tracker sensors)

---

## User Stories

### Story 1: Extend Automation Schema for Complex Patterns

**As a** automation developer  
**I want** the canonical schema to support variables, repeat.until, repeat.for_each, time_pattern seconds, and template conditions  
**So that** the system can generate time-bounded loops and per-entity iteration (e.g., Hue lights flashing independently)

**Acceptance Criteria:**
- [x] `TriggerSpec` has `seconds` field for `time_pattern`
- [x] `ConditionSpec` has `value_template` for `condition: template`
- [x] `ActionSpec` supports `variables` action
- [x] `ActionSpec.repeat` supports `until` (template-based) and `for_each`
- [x] YAML renderer outputs valid HA 2025.10+ YAML for these constructs
- [x] Schema validation passes for Super Bowl guide automation structures (Phase 1 verification; see implementation/PHASE1_AUTOMATION_EPIC_VERIFICATION.md)

**Story Points:** 5  
**Dependencies:** None  

---

### Story 2: Add Team Tracker Patterns to HA AI Agent Prompt

**As a** user creating sports automations  
**I want** the HA AI Agent to understand Team Tracker triggers (kickoff-before, score-increase, game-over, winner)  
**So that** prompts like "flash lights when Seahawks score" produce correct YAML without manual edits

**Acceptance Criteria:**
- [x] Section 5B extended with kickoff X seconds before (template using `date` + `timedelta`)
- [x] Score-increase pattern documented (trigger.from_state vs trigger.to_state team_score)
- [x] Winner detection pattern (team_winner, score fallback)
- [x] Helper creation guidance (input_boolean for kickoff/game-over)
- [x] Examples in system prompt for each pattern

**Story Points:** 3  
**Dependencies:** None  

---

### Story 3: Post-Deploy Verification via Automation State

**As a** user deploying automations  
**I want** the system to verify the automation loaded successfully after deploy  
**So that** I know immediately if HA rejected it (e.g., state = unavailable)

**Acceptance Criteria:**
- [x] After POST to HA config API, call GET /api/states/automation.{id}
- [x] If state === "unavailable", return warning to user
- [x] Consider optional rollback or "deploy failed" signal
- [x] HA AI Agent / ai-automation-service surfaces this in deploy response

**Story Points:** 2  
**Dependencies:** None  

---

### Story 4: Unified Validation API

**As a** frontend or automation service  
**I want** a single validation endpoint that orchestrates schema, entities, and services  
**So that** I don't need to call multiple services for pre-deploy validation

**Acceptance Criteria:**
- [x] Single endpoint (e.g., `/api/v1/automations/validate`) accepts YAML
- [x] Orchestrates yaml-validation-service, entity checks (DataAPIClient/HA GET states), service checks
- [x] Returns unified result: valid, errors, warnings, entity_validation, service_validation
- [x] HA AI Agent and ai-automation-service use this endpoint

**Story Points:** 3  
**Dependencies:** None  

---

### Story 5: RAG Over Past Automations

**As a** user creating new automations  
**I want** the system to retrieve similar deployed automations when generating  
**So that** new automations follow proven patterns (e.g., score flash, scene restore)

**Acceptance Criteria:**
- [x] Deployed automations indexed (config + metadata)
- [x] Retrieval by pattern keywords (e.g., "score flash", "scene create", "repeat until")
- [x] RAG context included in automation generation prompts
- [x] Super Bowl guide (implementation/superbowl_teamtracker_lights_guide.md) in RAG corpus

**Story Points:** 5  
**Dependencies:** Story 2 (patterns help define retrieval keys)  

---

### Story 6: WLED vs Hue Device Resolution Rules

**As a** user controlling lights  
**I want** the system to correctly choose WLED entities (effect support) vs Hue entities (individual flashing)  
**So that** automations use the right device type for each pattern

**Acceptance Criteria:**
- [x] Prompt guidance: when to use WLED (effect + color) vs Hue (per-entity)
- [x] Entity resolution considers device capabilities (effect_list, etc.)
- [x] Area vs explicit entity_id rules documented
- [x] Hue group vs individual light handling clarified

**Story Points:** 2  
**Dependencies:** None  

---

### Story 7: Deploy Feedback with State and last_triggered

**As a** user who just deployed an automation  
**I want** to see automation state (on/off) and last_triggered in the deploy response  
**So that** I know it’s active and when it last ran

**Acceptance Criteria:**
- [x] Deploy response includes state (on/off) and attributes.last_triggered
- [x] UI shows "Enabled" / "Disabled" and "Last triggered: ..." after deploy
- [x] If unavailable, show clear warning (verification_warning in success toast)

**Story Points:** 2  
**Dependencies:** Story 3 (post-deploy verification)  

---

### Story 8: Parameterized Sports-Lights Blueprint (Optional)

**As a** user setting up game-day lights  
**I want** a single parameterized pattern that generates kickoff, score, game-over, and reset automations  
**So that** I don’t have to create each automation separately

**Acceptance Criteria:**
- [ ] Blueprint parameters: team_sensors, wled_entities, hue_entities, team_a/team_b colors, helper_prefix
- [ ] Generates 5 automations: kickoff, team A score, team B score, game over, reset helpers
- [ ] Documented in prompt guidance and RAG

**Story Points:** 5  
**Dependencies:** Story 1, Story 2  

---

### Story 9: Comprehensive Sports Keyword Coverage for RAG

**As a** user creating automations for any sport (NFL, NBA, MLB, NHL, MLS, golf, tennis, etc.)  
**I want** the RAG service to detect sports intent for all ha-teamtracker supported leagues  
**So that** prompts like "lights when Lakers score" or "notify on PGA birdie" retrieve Team Tracker patterns

**Acceptance Criteria:**
- [x] SPORTS_KEYWORDS covers all ha-teamtracker leagues: NFL, NBA, MLB, NHL, MLS, NCAA, WNBA, NCAAM, NCAAW, NCAAF, XFL, PGA, UFC, NWSL, EPL, F1, IRL, ATP, WTA, AFL
- [x] Sport-specific scoring terms: touchdown, goal, home run, run, basket, inning, strikeout, birdie, etc.
- [x] Event terms: world cup, premier league, march madness, championship, finals
- [x] Unit test verifies key phrases (e.g., "Lakers score lights", "PGA birdie automation") match sports intent

**Story Points:** 1  
**Dependencies:** Story 5 (RAG)

---

### Story 10: Sport-Specific RAG Corpus (Optional Future)

**As a** user creating MLB, soccer, or tennis automations  
**I want** sport-specific pattern excerpts (inning, outs, shots on target, sets won)  
**So that** generated automations use correct attributes for each sport

**Acceptance Criteria:**
- [ ] RAG excerpts include MLB patterns (outs, balls, strikes, on_first, etc.)
- [ ] RAG excerpts include MLS/soccer patterns (team_shots_on_target, etc.)
- [ ] RAG excerpts include tennis/volleyball patterns (team_sets_won, opponent_sets_won)
- [ ] Generic Team Tracker reference guide remains single source of truth

**Story Points:** 2  
**Dependencies:** Story 9  

---

## Dependencies

```
Story 1 (Schema) ──┬──> Story 8 (Blueprint)
Story 2 (Patterns)─┴──> Story 5 (RAG), Story 8
Story 3 (Post-deploy) ──> Story 7 (Deploy feedback)
Story 5 (RAG) ────────> Story 9 (Sports keywords)
Story 9 ──────────────> Story 10 (Sport-specific corpus, optional)
```

## Suggested Execution Order

1. **Story 1** – Schema extensions (enables complex YAML generation)
2. **Story 2** – Team Tracker patterns (prompt guidance)
3. **Story 3** – Post-deploy verification
4. **Story 7** – Deploy feedback (builds on Story 3)
5. **Story 4** – Unified validation API
6. **Story 6** – WLED vs Hue resolution
7. **Story 5** – RAG over past automations
8. **Story 9** – Comprehensive sports keyword coverage for RAG
9. **Story 8** – Parameterized blueprint (optional)
10. **Story 10** – Sport-specific RAG corpus (optional future)

## Completion

**Date:** February 2026

**Deliverables:**
- Schema supports variables, repeat.until, time_pattern, template conditions; Super Bowl samples pass validation
- HA AI Agent prompt includes Team Tracker patterns; RAG corpus with Super Bowl guide and sports keywords
- Post-deploy verification (GET state, verification_warning when unavailable); deploy response includes state, last_triggered
- Unified validation API `POST /api/v1/automations/validate`; HA AI Agent and ai-automation-service use it
- Deploy feedback UI (ConversationalDashboard, Deployed toast shows state, last triggered, warning)
- Phase 4 tests and docs: `implementation/PHASE4_AUTOMATION_API_DOCUMENTATION.md`

**Deferred:** Story 8 (parameterized blueprint), Story 10 (sport-specific RAG corpus) – optional future enhancements.

---

## References

- [Phase 1 Verification](../implementation/PHASE1_AUTOMATION_EPIC_VERIFICATION.md) – schema validation, attribute coverage
- [Phase 4 API Documentation](../implementation/PHASE4_AUTOMATION_API_DOCUMENTATION.md) – validation API, deploy response, RAG
- [Team Tracker Reference Guide](../implementation/teamtracker_automation_reference_guide.md) – all leagues, all attributes
- [Super Bowl Team Tracker Guide](../implementation/superbowl_teamtracker_lights_guide.md)
- [HA AI Agent System Prompt](../domains/automation-core/ha-ai-agent-service/src/prompts/system_prompt.py)
- [Automation Schema](../libs/homeiq-ha/src/homeiq_ha/yaml_validation_service/schema.py)
- [HA Client](../domains/automation-core/ai-automation-service-new/src/clients/ha_client.py)

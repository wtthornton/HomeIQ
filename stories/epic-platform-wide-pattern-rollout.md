---
epic: platform-wide-pattern-rollout
priority: medium
status: complete
estimated_duration: 4-6 weeks
risk_level: medium
source: PRD – Automation Architecture & Reusable Patterns (Phase 4)
---

# Epic: Platform-Wide Pattern Rollout

**Status:** Complete
**Priority:** Medium
**Duration:** 4–6 weeks
**Risk Level:** Medium
**PRD Reference:** `docs/planning/automation-architecture-reusable-patterns-prd.md` (Phase 4)

## Overview

Extend the reusable patterns to remaining HomeIQ domains: **Security**, **Comfort**, **Proactive Agent**, **Scenes/Scripts**, **Device Intelligence**, and **API Automation Edge**. This epic also picks up the two deferred stories from the original Automation Improvements epic (parameterized sports blueprint and sport-specific RAG corpus). By completion, all three patterns are applied platform-wide.

## Objectives

1. Security and Comfort RAG context services for specialized automation generation
2. Proactive Agent RAG corpuses for domain-specific proactive suggestions
3. Scene and script validation endpoint with unified response shape
4. API Automation Edge post-execution verification
5. Device Intelligence RAG for capability-aware feature suggestions
6. Complete deferred automation stories (parameterized blueprint, sport-specific corpus)

## Success Criteria

- [x] Security prompts ("motion alert", "lock when away") inject security corpus
- [x] Comfort prompts ("thermostat schedule", "HVAC away mode") inject comfort corpus
- [x] Proactive agent uses domain RAG for contextual suggestions
- [x] `POST /api/v1/scenes/validate` and `POST /api/v1/scripts/validate` endpoints operational
- [x] API Automation Edge verifies task execution results and surfaces failures
- [x] Parameterized sports-lights blueprint generates 5 automations from parameters
- [x] At least 3 sport-specific RAG corpuses (MLB, soccer, tennis) available

---

## User Stories

### Story 1: Security RAG Context Service

**As a** user creating security-related automations
**I want** the AI agent to understand security patterns (motion alerts, lock management, camera triggers, presence detection)
**So that** prompts like "alert me when motion detected and nobody home" produce accurate automations

**Acceptance Criteria:**
- [x] `SecurityRAGService` extends `RAGContextService` interface
- [x] Security keyword set: camera, alarm, motion, lock, presence, geofence, intrusion, alert, notify, arm, disarm, siren, doorbell, occupancy, away mode
- [x] Security corpus: motion-triggered notifications, lock management patterns, camera-action automations, presence-based arming/disarming, geofencing patterns
- [x] All examples use valid HA YAML with real entity patterns (binary_sensor.motion_*, lock.*, alarm_control_panel.*)
- [x] Registered in `RAGContextRegistry`
- [x] Integration test: security prompt triggers corpus injection

**Story Points:** 5
**Dependencies:** Epic: Reusable Pattern Framework (Story 1, Story 2)
**Affected Services:** ha-ai-agent-service (8030)

---

### Story 2: Comfort RAG Context Service

**As a** user creating comfort/climate automations
**I want** the AI agent to understand HVAC and comfort patterns
**So that** prompts like "set thermostat schedule for winter" produce optimized comfort automations

**Acceptance Criteria:**
- [x] `ComfortRAGService` extends `RAGContextService` interface
- [x] Comfort keyword set: thermostat, HVAC, schedule, away, heat, cool, temperature, humidity, fan, climate, setpoint, eco mode, comfort, occupied, vacation
- [x] Comfort corpus: thermostat scheduling, away-mode detection, seasonal presets, humidity management, multi-zone coordination, adaptive comfort
- [x] All examples use valid HA YAML with real entity patterns (climate.*, sensor.temperature_*, sensor.humidity_*)
- [x] Registered in `RAGContextRegistry`
- [x] Integration test: comfort prompt triggers corpus injection

**Story Points:** 3
**Dependencies:** Epic: Reusable Pattern Framework (Story 1, Story 2)
**Affected Services:** ha-ai-agent-service (8030)

---

### Story 3: Proactive Agent Domain RAG Corpuses

**As a** the proactive agent service generating suggestions
**I want** domain-specific RAG corpuses (energy savings, security best practices, comfort optimization) injected based on detected home context
**So that** proactive suggestions are relevant, actionable, and specific to the user's setup

**Acceptance Criteria:**
- [x] Proactive agent integrates with `RAGContextRegistry`
- [x] Energy savings corpus: peak avoidance tips, solar optimization, battery scheduling advice
- [x] Security best practices corpus: common automation gaps, notification improvements, presence patterns
- [x] Comfort optimization corpus: schedule optimization, seasonal adjustment, occupancy-based tips
- [x] Context detection based on: home type, installed devices, recent events, time of year
- [x] Corpus selection is additive (multiple corpuses can be injected)
- [x] Unit tests for context detection and corpus selection

**Story Points:** 5
**Dependencies:** Epic: Reusable Pattern Framework (Story 1, Story 2); Stories 1-2 (can reuse security/comfort corpuses)
**Affected Services:** proactive-agent-service

---

### Story 4: Scene Validation Endpoint

**As a** the AI automation UI or scene management service
**I want** a `POST /api/v1/scenes/validate` endpoint that validates scene definitions
**So that** users get pre-creation validation feedback for scenes

**Acceptance Criteria:**
- [x] `SceneValidationRouter` extends `UnifiedValidationRouter` template
- [x] Validates scene entity targets exist and are available
- [x] Validates state values are valid for target entity domains (e.g., light brightness 0-255, color valid hex)
- [x] Validates service calls in scene are valid HA services
- [x] Returns standardized response: `valid`, `errors`, `warnings`, `entity_validation`, `service_validation`
- [x] Unit and integration tests

**Story Points:** 3
**Dependencies:** Epic: Reusable Pattern Framework (Story 3)
**Affected Services:** ai-automation-service-new (8024)

---

### Story 5: Script Validation Endpoint

**As a** the AI automation UI or script management service
**I want** a `POST /api/v1/scripts/validate` endpoint that validates script definitions
**So that** users get pre-creation validation feedback for scripts

**Acceptance Criteria:**
- [x] `ScriptValidationRouter` extends `UnifiedValidationRouter` template
- [x] Validates script YAML structure (sequence of actions, conditions, delays)
- [x] Validates entities and services referenced in script actions
- [x] Validates template syntax in script conditions and data templates
- [x] Returns standardized response: `valid`, `errors`, `warnings`, `entity_validation`, `service_validation`
- [x] Unit and integration tests

**Story Points:** 3
**Dependencies:** Epic: Reusable Pattern Framework (Story 3)
**Affected Services:** ai-automation-service-new (8024)

---

### Story 6: Scene/Script RAG Context Service

**As a** user creating scenes or scripts via the AI agent
**I want** the AI agent to inject scene/script patterns when I mention scenes or scripts
**So that** prompts like "create a movie night scene" produce correct, HA-compatible definitions

**Acceptance Criteria:**
- [x] `SceneScriptRAGService` extends `RAGContextService` interface
- [x] Keyword set: scene, script, turn_on, turn_off, activate, movie night, morning routine, bedtime, sequence, workflow
- [x] Corpus: scene creation patterns, script sequencing, delay/wait patterns, condition branching, common scene archetypes (movie, morning, sleep, away, party)
- [x] Registered in `RAGContextRegistry`
- [x] Integration test: scene/script prompt triggers corpus injection

**Story Points:** 3
**Dependencies:** Epic: Reusable Pattern Framework (Story 1, Story 2)
**Affected Services:** ha-ai-agent-service (8030)

---

### Story 7: Post-Scene/Script Creation Verification

**As a** user who just created a scene or script
**I want** the system to verify it was created successfully
**So that** I know immediately if HA rejected the definition

**Acceptance Criteria:**
- [x] `SceneVerifier` and `ScriptVerifier` extend `PostActionVerifier` interface
- [x] After scene creation, verify scene entity exists and is not `unavailable`
- [x] After script creation, verify script entity exists and is not `unavailable`
- [x] Return `verification_warning` if creation failed or entity is unavailable
- [x] UI shows verification feedback in creation success toast
- [x] Unit and integration tests

**Story Points:** 2
**Dependencies:** Epic: Reusable Pattern Framework (Story 4), Stories 4-5
**Affected Services:** ai-automation-service-new (8024), ai-automation-ui (3001)

---

### Story 8: API Automation Edge Post-Execution Verification

**As a** the API automation edge service executing tasks
**I want** to verify task execution results after completion
**So that** failed or partially failed executions are detected and surfaced to the task status

**Acceptance Criteria:**
- [x] `TaskExecutionVerifier` extends `PostActionVerifier` interface
- [x] After task execution, check automation state or execution log
- [x] Detect failed executions (error in trace, entity still in wrong state)
- [x] Map failures to actionable warnings in task status
- [x] Surface `verification_warning` in task queue UI
- [x] Support retry recommendation for transient failures
- [x] Unit and integration tests

**Story Points:** 3
**Dependencies:** Epic: Reusable Pattern Framework (Story 4)
**Affected Services:** api-automation-edge

---

### Story 9: Device Intelligence Capability RAG

**As a** the device intelligence service suggesting features
**I want** to inject device capability patterns when suggesting features for specific device types
**So that** suggestions for WLED include effect_list patterns, Hue includes scene/group patterns, etc.

**Acceptance Criteria:**
- [x] `DeviceCapabilityRAGService` extends `RAGContextService` interface
- [x] Keyword detection based on device type context (WLED, Hue, Sonoff, Shelly, etc.)
- [x] Corpus per device category: WLED effects and segments, Hue scenes and groups, smart plug power monitoring, sensor automation patterns
- [x] Registered in `RAGContextRegistry` (or equivalent in device-intelligence-service)
- [x] Integration test: device-type context triggers correct corpus
- [x] Unit tests

**Story Points:** 5
**Dependencies:** Epic: Reusable Pattern Framework (Story 1)
**Affected Services:** device-intelligence-service

---

### Story 10: Parameterized Sports-Lights Blueprint (Deferred from Automation Epic)

**As a** user setting up game-day lights
**I want** a single parameterized pattern that generates kickoff, score, game-over, and reset automations
**So that** I don't have to create each automation separately

**Acceptance Criteria:**
- [x] Blueprint parameters: team_sensors, wled_entities, hue_entities, team_a/team_b colors, helper_prefix
- [x] Generates 5 automations: kickoff, team A score, team B score, game over, reset helpers
- [x] Documented in prompt guidance and RAG
- [x] Uses blueprint validation endpoint (Story 3 from Phase 3 epic) for pre-deploy validation
- [x] Post-deploy verification for all generated automations

**Story Points:** 5
**Dependencies:** Epic: High-Value Domain Extensions (Story 3 – Blueprint Validation)
**Affected Services:** ai-automation-service-new (8024), ha-ai-agent-service (8030)

*Originally: Automation Improvements Epic – Story 8 (deferred)*

---

### Story 11: Sport-Specific RAG Corpus (Deferred from Automation Epic)

**As a** user creating MLB, soccer, or tennis automations
**I want** sport-specific pattern excerpts (inning, outs, shots on target, sets won)
**So that** generated automations use correct attributes for each sport

**Acceptance Criteria:**
- [x] RAG excerpts include MLB patterns (outs, balls, strikes, on_first, on_second, on_third, etc.)
- [x] RAG excerpts include MLS/soccer patterns (team_shots_on_target, team_total_shots, etc.)
- [x] RAG excerpts include tennis/volleyball patterns (team_sets_won, opponent_sets_won)
- [x] RAG excerpts include NHL patterns (team_shots_on_goal, power_play, etc.)
- [x] Generic Team Tracker reference guide remains single source of truth
- [x] Sport-specific corpuses registered in `AutomationRAGService` (or extend it)
- [x] Unit tests verify sport-specific keyword matching

**Story Points:** 3
**Dependencies:** None (AutomationRAGService already exists)
**Affected Services:** ha-ai-agent-service (8030)

*Originally: Automation Improvements Epic – Story 10 (deferred)*

---

## Dependencies

```
Epic: Reusable Pattern Framework (prerequisite for most stories)
Epic: High-Value Domain Extensions (prerequisite for Story 10)

Story 1 (Security RAG)           ──┐
Story 2 (Comfort RAG)            ──├──> Story 3 (Proactive Agent RAG)
                                   │
Story 4 (Scene Validation)       ──┤
Story 5 (Script Validation)      ──├──> Story 7 (Post-Scene/Script Verification)
Story 6 (Scene/Script RAG)        │
                                   │
Story 8 (API Edge Verification)    │   (independent)
Story 9 (Device Intelligence RAG)  │   (independent)
Story 10 (Sports Blueprint)        │   (depends on Phase 3 Blueprint Validation)
Story 11 (Sport-Specific Corpus)       (independent)
```

## Suggested Execution Order

**Sprint 1 – RAG Services (parallelizable):**
1. **Story 1** – Security RAG
2. **Story 2** – Comfort RAG
3. **Story 6** – Scene/Script RAG
4. **Story 11** – Sport-Specific Corpus (independent, can start anytime)

**Sprint 2 – Validation & Proactive (parallelizable):**
5. **Story 4** – Scene Validation
6. **Story 5** – Script Validation
7. **Story 3** – Proactive Agent RAG (uses security/comfort corpuses)
8. **Story 9** – Device Intelligence Capability RAG

**Sprint 3 – Verification & Deferred:**
9. **Story 7** – Post-Scene/Script Verification
10. **Story 8** – API Edge Post-Execution Verification
11. **Story 10** – Parameterized Sports-Lights Blueprint

## Implementation Artifacts

### RAG Services Created

| Service | File | Keywords (count) |
|---------|------|-----------------|
| SecurityRAGService | `domains/automation-core/ha-ai-agent-service/src/services/security_rag_service.py` | 15 |
| ComfortRAGService | `domains/automation-core/ha-ai-agent-service/src/services/comfort_rag_service.py` | 15 |
| SceneScriptRAGService | `domains/automation-core/ha-ai-agent-service/src/services/scene_script_rag_service.py` | 10 |
| DeviceCapabilityRAGService | `domains/automation-core/ha-ai-agent-service/src/services/device_capability_rag_service.py` | 12+ |

### Corpus Files Created

| Corpus | File |
|--------|------|
| Security patterns | `domains/automation-core/ha-ai-agent-service/src/data/security_automation_patterns.md` |
| Comfort patterns | `domains/automation-core/ha-ai-agent-service/src/data/comfort_automation_patterns.md` |
| Scene/script patterns | `domains/automation-core/ha-ai-agent-service/src/data/scene_script_patterns.md` |
| Device capability patterns | `domains/automation-core/ha-ai-agent-service/src/data/device_capability_patterns.md` |
| Sport-specific patterns | `domains/automation-core/ha-ai-agent-service/src/data/sport_specific_patterns.md` |

### Validation Routers Created

| Endpoint | File |
|----------|------|
| `POST /api/v1/scenes/validate` | `domains/automation-core/ai-automation-service-new/src/api/scene_validate_router.py` |
| `POST /api/v1/scripts/validate` | `domains/automation-core/ai-automation-service-new/src/api/script_validate_router.py` |

### Verifiers Created

| Verifier | File |
|----------|------|
| SceneVerifier | `domains/automation-core/ai-automation-service-new/src/services/scene_verifier.py` |
| ScriptVerifier | `domains/automation-core/ai-automation-service-new/src/services/script_verifier.py` |
| TaskExecutionVerifier | `domains/automation-core/ai-automation-service-new/src/services/task_execution_verifier.py` |

### Other Artifacts

| Artifact | File |
|----------|------|
| Sports blueprint generator | `domains/automation-core/ai-automation-service-new/src/services/sports_blueprint_generator.py` |

### Tests

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `libs/homeiq-patterns/tests/test_epic3_rag_services.py` | 30 | Security, Comfort, SceneScript, DeviceCapability RAG + registry |
| `libs/homeiq-patterns/tests/test_epic3_validation_verifiers.py` | 24 | Scene/Script validation, verifiers, task execution, sports blueprint |
| **Total Phase 4** | **54** | |

### Registry Integration

All 4 new RAG services registered in `domains/automation-core/ha-ai-agent-service/src/services/context_builder.py` via `ContextBuilder.initialize()`.

---

## References

- [PRD: Automation Architecture & Reusable Patterns](../docs/planning/automation-architecture-reusable-patterns-prd.md)
- [Epic: Reusable Pattern Framework](epic-reusable-pattern-framework.md) (prerequisite)
- [Epic: High-Value Domain Extensions](epic-high-value-domain-extensions.md) (prerequisite for Story 10)
- [Epic: Automation Improvements](epic-homeiq-automation-improvements.md) (deferred Stories 8, 10)
- [Team Tracker Reference Guide](../implementation/teamtracker_automation_reference_guide.md) (Story 11)
- [Services Ranked by Importance](../docs/architecture/SERVICES_RANKED_BY_IMPORTANCE.md)
- [Shared Patterns README](../libs/homeiq-patterns/README.md) (pattern documentation and file map)

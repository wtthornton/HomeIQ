---
epic: high-value-domain-extensions
priority: high
status: complete
estimated_duration: 4-5 weeks
risk_level: medium
source: PRD – Automation Architecture & Reusable Patterns (Phase 3)
---

# Epic: High-Value Domain Extensions

**Status:** Complete
**Priority:** High
**Duration:** 4–5 weeks
**Risk Level:** Medium
**PRD Reference:** `docs/planning/automation-architecture-reusable-patterns-prd.md` (Phase 3)

## Overview

Apply the three reusable patterns (RAG Context Injection, Unified Validation, Post-Action Verification) to the highest-value domains beyond automation: **Energy**, **Blueprint Suggestion & Deployment**, and **Device Setup**. This delivers immediate user-facing improvements and validates the shared abstractions from Epic: Reusable Pattern Framework.

## Objectives

1. Energy RAG context injection for better energy-related automation generation
2. Blueprint validation endpoint with unified response shape
3. Post-blueprint-deploy verification with user-facing warnings
4. Device setup RAG for common integration setup assistance (Zigbee, Hue, Z-Wave)
5. Validate that the shared abstractions work cleanly for non-automation domains

## Success Criteria

- [x] Energy-related prompts ("solar battery automation", "TOU load shifting") produce better automations via RAG
- [x] `POST /api/v1/blueprints/validate` validates schema, entities, and device compatibility
- [x] Blueprint deploy surfaces `verification_warning` when automation state is unavailable
- [x] Device setup prompts ("add Zigbee devices", "pair Hue lights") inject relevant corpus
- [x] All new implementations extend the shared pattern abstractions (no duplication)

---

## User Stories

### Story 1: Energy RAG Context Service

**As a** user creating energy-related automations
**I want** the AI agent to understand energy patterns (TOU rates, load shifting, battery management, solar production)
**So that** prompts like "shift laundry to off-peak hours" produce correct, optimized automations

**Acceptance Criteria:**
- [x] `EnergyRAGService` extends `RAGContextService` interface
- [x] Energy keyword set: electricity, solar, battery, TOU, time-of-use, demand, kWh, peak, off-peak, load shift, tariff, grid, export, net metering, EV charging
- [x] Energy corpus file created: TOU scheduling patterns, battery charge/discharge, solar production triggers, load shifting strategies, EV charging schedules
- [x] Registered in `RAGContextRegistry` within `ContextBuilder`
- [x] Integration test: energy prompt triggers corpus injection
- [x] Unit tests for keyword matching edge cases

**Story Points:** 5
**Dependencies:** Epic: Reusable Pattern Framework (Story 1, Story 2)
**Affected Services:** ha-ai-agent-service (8030)

---

### Story 2: Energy Automation Corpus Creation

**As a** the EnergyRAGService
**I want** a comprehensive energy automation corpus covering common patterns
**So that** RAG-injected context produces accurate, HA-compatible energy automations

**Acceptance Criteria:**
- [x] Corpus covers TOU/rate-based scheduling (peak avoidance, off-peak shifting)
- [x] Corpus covers solar production triggers (battery priority, export management)
- [x] Corpus covers EV charging patterns (scheduled, solar-surplus, rate-optimized)
- [x] Corpus covers battery management (charge thresholds, discharge schedules, grid fallback)
- [x] Corpus covers demand response patterns (load shedding, priority ordering)
- [x] All examples use valid HA 2025.10+ YAML with real entity patterns (sensor.electricity_*, sensor.solar_*, sensor.battery_*)
- [x] Corpus validated against automation schema

**Story Points:** 3
**Dependencies:** Story 1 (energy keywords define what patterns to include)
**Affected Services:** ha-ai-agent-service (8030)

---

### Story 3: Blueprint Validation Endpoint

**As a** the AI automation UI or blueprint service
**I want** a `POST /api/v1/blueprints/validate` endpoint that validates blueprint schema, required entities, and device compatibility
**So that** users get pre-deploy validation feedback before applying a blueprint

**Acceptance Criteria:**
- [x] `BlueprintValidationRouter` extends `UnifiedValidationRouter` template
- [x] Validates blueprint YAML schema (inputs, triggers, conditions, actions)
- [x] Validates required entities exist (via DataAPIClient or HA states)
- [x] Validates device compatibility (required capabilities vs available devices)
- [x] Returns standardized response: `valid`, `errors`, `warnings`, `entity_validation`, `device_validation`
- [x] Handles blueprint input substitution during validation
- [x] Unit and integration tests

**Story Points:** 5
**Dependencies:** Epic: Reusable Pattern Framework (Story 3)
**Affected Services:** ai-automation-service-new (8024), blueprint-index

---

### Story 4: Post-Blueprint-Deploy Verification

**As a** user deploying a blueprint
**I want** the system to verify the resulting automation(s) loaded successfully
**So that** I know immediately if any automation from the blueprint failed

**Acceptance Criteria:**
- [x] `BlueprintDeployVerifier` extends `PostActionVerifier` interface
- [x] After blueprint deploy, GET state for each created automation entity
- [x] If any automation state is `unavailable`, return `verification_warning` per entity
- [x] Aggregate verification: overall success if all automations are on, partial if some unavailable
- [x] Deploy response includes per-automation `state`, `last_triggered`, `verification_warning`
- [x] UI shows per-automation verification feedback in deploy success toast

**Story Points:** 3
**Dependencies:** Epic: Reusable Pattern Framework (Story 4), Story 3
**Affected Services:** ai-automation-service-new (8024), ai-automation-ui (3001)

---

### Story 5: Blueprint RAG Context Service

**As a** user asking for blueprint suggestions
**I want** the AI agent to inject blueprint selection patterns when I ask about blueprints
**So that** prompts like "suggest blueprints for my Hue lights" return relevant, compatible blueprints

**Acceptance Criteria:**
- [x] `BlueprintRAGService` extends `RAGContextService` interface
- [x] Blueprint keyword set: blueprint, template, prebuilt, pre-built, pre-made, starter, ready-made
- [x] Corpus includes blueprint selection criteria: device compatibility, input requirements, category matching
- [x] Corpus includes common blueprint categories and their typical inputs
- [x] Registered in `RAGContextRegistry`
- [x] Integration test: blueprint prompt triggers corpus injection

**Story Points:** 3
**Dependencies:** Epic: Reusable Pattern Framework (Story 1, Story 2)
**Affected Services:** ha-ai-agent-service (8030)

---

### Story 6: Device Setup RAG Context Service

**As a** user setting up new devices or integrations
**I want** the AI agent to inject setup guides when I ask about device configuration
**So that** prompts like "how do I add Zigbee devices" return accurate setup instructions

**Acceptance Criteria:**
- [x] `DeviceSetupRAGService` extends `RAGContextService` interface
- [x] Device setup keyword set: Zigbee, Z-Wave, Hue, MQTT, Zigbee2MQTT, pairing, setup, configure, integration, add device, discover, commissioning, Matter, Thread
- [x] Corpus covers: Zigbee pairing flows, Hue bridge setup, Z-Wave inclusion, MQTT configuration, Matter/Thread commissioning
- [x] Corpus includes troubleshooting patterns (device not found, pairing failed, integration offline)
- [x] Registered in `RAGContextRegistry`
- [x] Integration test: device setup prompt triggers corpus injection

**Story Points:** 5
**Dependencies:** Epic: Reusable Pattern Framework (Story 1, Story 2)
**Affected Services:** ha-ai-agent-service (8030)

---

### Story 7: Device Setup Corpus Creation

**As a** the DeviceSetupRAGService
**I want** a comprehensive device setup corpus covering popular integration types
**So that** RAG-injected context gives accurate, step-by-step setup guidance

**Acceptance Criteria:**
- [x] Corpus covers Zigbee2MQTT: pairing mode, permit join, device interview, entity creation
- [x] Corpus covers Hue bridge: bridge discovery, light pairing, room/zone assignment
- [x] Corpus covers Z-Wave: inclusion mode, secure inclusion, device interview
- [x] Corpus covers MQTT: broker setup, topic structure, auto-discovery
- [x] Corpus covers Matter/Thread: commissioning, border router, fabric joining
- [x] Each section includes common troubleshooting steps
- [x] Corpus validated by comparison with official HA integration docs

**Story Points:** 3
**Dependencies:** Story 6 (keywords define scope)
**Affected Services:** ha-ai-agent-service (8030)

---

### Story 8: Device Setup Validation Endpoint

**As a** the HA setup service or device setup wizard
**I want** a unified validation endpoint for setup step validation
**So that** each wizard step can be validated (config format, connectivity, integration health) before proceeding

**Acceptance Criteria:**
- [x] `SetupValidationRouter` extends `UnifiedValidationRouter` template
- [x] Validates configuration format for the target integration type
- [x] Validates connectivity (ping broker, check bridge reachable, verify coordinator)
- [x] Validates integration health after setup (HA integration check)
- [x] Returns standardized response: `valid`, `errors`, `warnings`, `connectivity_validation`, `health_validation`
- [x] Supports step-by-step validation (validate each wizard step independently)
- [x] Unit and integration tests

**Story Points:** 5
**Dependencies:** Epic: Reusable Pattern Framework (Story 3)
**Affected Services:** ha-setup-service, ai-automation-service-new (8024)

---

### Story 9: Post-Setup Verification for Device Integrations

**As a** user who just configured a new integration
**I want** the system to verify the integration is healthy after setup
**So that** I know immediately if the device/integration failed to connect

**Acceptance Criteria:**
- [x] `SetupVerifier` extends `PostActionVerifier` interface
- [x] After integration setup, check integration health via HA API
- [x] Verify device entities are created and not `unavailable`
- [x] If integration is unhealthy, return `verification_warning` with actionable guidance
- [x] Surface verification results in setup wizard UI
- [x] Unit and integration tests

**Story Points:** 3
**Dependencies:** Epic: Reusable Pattern Framework (Story 4), Story 8
**Affected Services:** ha-setup-service

---

## Dependencies

```
Epic: Reusable Pattern Framework
    ├──> Story 1 (Energy RAG) ──> Story 2 (Energy Corpus)
    ├──> Story 3 (Blueprint Validation) ──> Story 4 (Blueprint Post-Deploy)
    ├──> Story 5 (Blueprint RAG)
    ├──> Story 6 (Device Setup RAG) ──> Story 7 (Device Setup Corpus)
    └──> Story 8 (Setup Validation) ──> Story 9 (Post-Setup Verification)

External Dependencies:
    • blueprint-index service (Story 3, Story 5)
    • ha-setup-service (Story 8, Story 9)
    • HA API (all verification stories)
```

## Suggested Execution Order

**Sprint 1 – RAG Services (parallelizable):**
1. **Story 1** – Energy RAG Service
2. **Story 5** – Blueprint RAG Service
3. **Story 6** – Device Setup RAG Service

**Sprint 2 – Corpus & Validation (parallelizable):**
4. **Story 2** – Energy Corpus
5. **Story 7** – Device Setup Corpus
6. **Story 3** – Blueprint Validation Endpoint

**Sprint 3 – Post-Action & Setup Validation:**
7. **Story 4** – Post-Blueprint-Deploy Verification
8. **Story 8** – Device Setup Validation Endpoint
9. **Story 9** – Post-Setup Verification

## Implementation Artifacts

| Artifact | Path |
|----------|------|
| **RAG Services** | |
| EnergyRAGService | `domains/automation-core/ha-ai-agent-service/src/services/energy_rag_service.py` |
| BlueprintRAGService | `domains/automation-core/ha-ai-agent-service/src/services/blueprint_rag_service.py` |
| DeviceSetupRAGService | `domains/automation-core/ha-ai-agent-service/src/services/device_setup_rag_service.py` |
| **Corpus Files** | |
| Energy Automation Patterns | `domains/automation-core/ha-ai-agent-service/src/data/energy_automation_patterns.md` |
| Blueprint Patterns | `domains/automation-core/ha-ai-agent-service/src/data/blueprint_patterns.md` |
| Device Setup Patterns | `domains/automation-core/ha-ai-agent-service/src/data/device_setup_patterns.md` |
| **Validation Routers** | |
| BlueprintValidationRouter | `domains/automation-core/ai-automation-service-new/src/api/blueprint_validate_router.py` |
| SetupValidationRouter | `domains/automation-core/ai-automation-service-new/src/api/setup_validate_router.py` |
| **Verifiers** | |
| BlueprintDeployVerifier | `domains/automation-core/ai-automation-service-new/src/services/blueprint_deploy_verifier.py` |
| SetupVerifier | `domains/automation-core/ai-automation-service-new/src/services/setup_verifier.py` |
| **Modified Files** | |
| ContextBuilder (RAG registration) | `domains/automation-core/ha-ai-agent-service/src/services/context_builder.py` |
| **Tests (53 new)** | |
| RAG Service Tests (30) | `libs/homeiq-patterns/tests/test_epic2_rag_services.py` |
| Validation & Verifier Tests (23) | `libs/homeiq-patterns/tests/test_epic2_validation_verifiers.py` |

## References

- [PRD: Automation Architecture & Reusable Patterns](../docs/planning/automation-architecture-reusable-patterns-prd.md)
- [Epic: Reusable Pattern Framework](epic-reusable-pattern-framework.md) (prerequisite)
- [Epic: Automation Improvements](epic-homeiq-automation-improvements.md) (reference implementation)
- [Services Ranked by Importance](../docs/architecture/SERVICES_RANKED_BY_IMPORTANCE.md)

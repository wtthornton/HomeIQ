# PRD: Automation Architecture & Reusable Patterns

**Document Type:** Product Requirements Document
**Status:** Complete (All 4 Phases)
**Created:** February 2026
**Epic Reference:** HomeIQ Automation Platform Improvements (Complete)

---

## Executive Summary

The HomeIQ Automation Platform Improvements epic delivered three core architectural patterns that improve automation generation, validation, and deployment. This PRD captures the architecture in detail and defines how these patterns can be reused across other areas of HomeIQ to drive consistency, faster development, and better user experience.

**Key patterns:**
1. **Keyword RAG Context Injection** – Domain-specific corpus retrieval triggered by prompt keywords
2. **Unified Validation API** – Single orchestrated endpoint for schema, entity, and service validation
3. **Post-Action Verification** – Verify results after deploy/apply and surface warnings to users

---

## 1. Current Architecture (Automation Improvements)

### 1.1 High-Level Flow

```
User Prompt ("Super Bowl lights when Seahawks score")
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ HA AI Agent Service (Port 8030)                                         │
│ ├─ ContextBuilder                                                        │
│ │   └─ AutomationRAGService                                              │
│ │       • Keyword match: sports, score, Super Bowl, team tracker, etc.   │
│ │       • Load corpus: superbowl_guide_excerpts.md                       │
│ │       • Inject RAG context into prompt                                 │
│ ├─ PromptAssemblyService → assembles full prompt with context            │
│ └─ OpenAI → generates automation YAML                                    │
└─────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ ai-automation-service-new (Port 8024)                                    │
│ ├─ POST /api/v1/automations/validate                                     │
│ │   • Calls yaml-validation-service (schema, entities, services)         │
│ │   • Returns: valid, errors, entity_validation, service_validation      │
│ ├─ deploy_suggestion → HA Client                                         │
│ └─ HA Client                                                             │
│     • POST deploy → GET /api/states/{entity_id} (post-deploy)            │
│     • Adds state, last_triggered, verification_warning if unavailable    │
└─────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ ai-automation-ui (Port 3001)                                             │
│ • validateYAML → POST /api/v1/automations/validate                       │
│ • Deploy success toast: state, last triggered, verification_warning      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Components and Responsibilities

| Component | Service | Port | Responsibility |
|-----------|---------|------|----------------|
| **AutomationRAGService** | ha-ai-agent-service | 8030 | Keyword-based sports/Team Tracker detection; loads corpus; injects context |
| **ContextBuilder** | ha-ai-agent-service | 8030 | Orchestrates RAG and other context services for prompt assembly |
| **PromptAssemblyService** | ha-ai-agent-service | 8030 | Assembles messages with RAG context when sports intent detected |
| **AIAutomationClient** | ha-ai-agent-service | 8030 | Calls `POST /api/v1/automations/validate` for validation |
| **automation_yaml_validate_router** | ai-automation-service-new | 8024 | Unified validation endpoint; orchestrates yaml-validation-service |
| **DeploymentService** | ai-automation-service-new | 8024 | Deploy suggestions; passes state, last_triggered, verification_warning |
| **HA Client** | ai-automation-service-new | 8024 | Deploy to HA; GET state post-deploy; set verification_warning if unavailable |
| **yaml-validation-service** | yaml-validation-service | - | Schema validation, entity checks, service checks |

### 1.3 Data Artifacts

| Artifact | Path | Purpose |
|----------|------|---------|
| Schema | `shared/yaml_validation_service/schema.py` | TriggerSpec, ConditionSpec, ActionSpec (variables, repeat, time_pattern, value_template) |
| RAG Corpus | `services/ha-ai-agent-service/src/data/superbowl_guide_excerpts.md` | Sports/Team Tracker patterns |
| Team Tracker Reference | `implementation/teamtracker_automation_reference_guide.md` | All leagues, all attributes |
| Super Bowl Guide | `implementation/superbowl_teamtracker_lights_guide.md` | Example patterns |

### 1.4 API Contracts

**Unified Validation API**
- **Endpoint:** `POST /api/v1/automations/validate`
- **Request:** `yaml_content`, `normalize`, `validate_entities`, `validate_services`
- **Response:** `valid`, `errors`, `warnings`, `entity_validation`, `service_validation`, `score`, `fixed_yaml`, `fixes_applied`

**Deploy Response**
- **Fields:** `suggestion_id`, `automation_id`, `status`, `state`, `last_triggered`, `verification_warning`

---

## 2. Reusable Patterns (Detailed)

### 2.1 Pattern A: Keyword RAG Context Injection

**Description:** Detect domain intent from user prompt via keyword matching; load domain-specific corpus; inject into LLM prompt as context.

**Current Implementation:**
- `AutomationRAGService` in ha-ai-agent-service
- `SPORTS_KEYWORDS` tuple (team tracker, NFL, score, Super Bowl, etc.)
- `get_automation_context(user_prompt)` → returns corpus or empty string
- Wired into `PromptAssemblyService` via `ContextBuilder`

**Reusability:** High. Pattern is self-contained and requires only:
1. Keyword list (tuple or set)
2. Corpus file (markdown or text)
3. Integration into context assembly (e.g., `ContextBuilder` or equivalent)

**Extension points:**
- Add new `*RAGService` classes (e.g., `EnergyRAGService`, `SecurityRAGService`)
- Register with context builder; check intent before injection
- Corpus can be static file or dynamically assembled

### 2.2 Pattern B: Unified Validation API

**Description:** Single HTTP endpoint that orchestrates one or more validation backends (schema, entities, services) and returns a unified, structured response.

**Current Implementation:**
- `automation_yaml_validate_router` in ai-automation-service-new
- Calls `yaml-validation-service` via `YAMLValidationClient`
- Categorizes errors into `entity_validation` and `service_validation`
- Returns `ValidateYAMLResponse` with valid, errors, warnings, subsections

**Reusability:** High. Pattern requires:
1. Validation backend(s)
2. Orchestration router
3. Request/response models
4. Error categorization logic (if multiple validation types)

**Extension points:**
- New validation routers (e.g., `/api/v1/blueprints/validate`, `/api/v1/scenes/validate`)
- Shared validation client abstraction
- Common response shape: `valid`, `errors`, `warnings`, `{domain}_validation` subsections

### 2.3 Pattern C: Post-Action Verification

**Description:** After performing an action (deploy, apply, configure), verify the result (e.g., GET state) and surface warnings or errors to the user when verification fails.

**Current Implementation:**
- `ha_client.deploy_automation()`: POST deploy → GET `/api/states/{entity_id}` → set `verification_warning` if state is `unavailable`
- `deployment_service.deploy_suggestion()`: passes through state, last_triggered, verification_warning
- UI (ConversationalDashboard, Deployed toast): displays warning with ⚠️ when present

**Reusability:** High. Pattern requires:
1. Action (deploy, apply, configure)
2. Verification step (GET state, health check, status query)
3. Warning/error mapping
4. UI feedback (toast, banner, inline message)

**Extension points:**
- Post-blueprint-deploy verification
- Post-scene-creation verification
- Post-integration-setup health check
- Post-automation-execution result check

---

## 3. Application Areas Across HomeIQ

### 3.1 HA AI Agent Service (Tier 1 Context Injection)

**Current:** Automation RAG for sports/Team Tracker.

**Additional domains:**

| Domain | Keywords (examples) | Corpus | Benefit |
|--------|---------------------|--------|---------|
| **Energy** | electricity, solar, battery, TOU, demand, kWh | Energy automation patterns, load shifting, peak avoidance | Better energy-related prompts |
| **Security** | camera, alarm, motion, lock, presence | Security/notification patterns, geofencing | Better security automation prompts |
| **Device Setup** | Hue, Zigbee, Z-Wave, pairing, setup | Setup guides, pairing flows, troubleshooting | Better setup assistance |
| **Comfort** | thermostat, HVAC, schedule, away | Comfort patterns, schedule optimization | Better comfort automation prompts |
| **Scenes/Scripts** | scene, script, turn_on, turn_off | Scene/script patterns | Better scene/script generation |

**Implementation approach:** Add `EnergyRAGService`, `SecurityRAGService`, etc.; register in `ContextBuilder`; invoke from `PromptAssemblyService` based on keyword detection (can run multiple RAG services in parallel or sequence).

### 3.2 Blueprint Suggestion & Deployment

**Current:** Blueprint suggestions; device matching; accept/decline.

**Pattern applications:**

| Pattern | Application |
|---------|-------------|
| **Unified Validation** | `POST /api/v1/blueprints/validate` – validate blueprint schema, required entities, device compatibility before deploy |
| **Post-Action Verification** | After blueprint deploy, GET automation state; surface `verification_warning` if unavailable |
| **Keyword RAG** | When user asks "suggest blueprints for my Hue lights", inject blueprint selection patterns into agent prompt |

**Dependencies:** blueprint-index, ai-pattern-service, HA API.

### 3.3 Device Setup Assistant / HA Setup Service

**Current:** HA health monitoring, integration checks, setup wizards.

**Pattern applications:**

| Pattern | Application |
|---------|-------------|
| **Unified Validation** | Single endpoint for setup step validation – config format, connectivity, integration health |
| **Post-Action Verification** | After Zigbee/MQTT/HA config change, run integration check; surface status in wizard |
| **Keyword RAG** | "How do I add Zigbee devices?" → inject Zigbee setup corpus into assistant prompt |

**Dependencies:** HA, MQTT, Zigbee2MQTT, integration APIs.

### 3.4 API Automation Edge (Task Execution)

**Current:** Execute automations; task queue; kill switch.

**Pattern applications:**

| Pattern | Application |
|---------|-------------|
| **Post-Action Verification** | After task execution, verify result (e.g., check automation state or execution log); surface failure/warning in task status |
| **Unified Validation** | Validate automation spec before queuing (if not already validated upstream) |

**Dependencies:** HA API, task queue (Huey).

### 3.5 Device Intelligence Service

**Current:** 6,000+ device capability mapping; utilization analysis; feature suggestions.

**Pattern applications:**

| Pattern | Application |
|---------|-------------|
| **Keyword RAG** | When suggesting device features, inject capability patterns (e.g., "effect_list" for WLED) into suggestion context |
| **Unified Validation** | Validate device config or mapping before applying |

### 3.6 Proactive Agent Service

**Current:** Proactive suggestions based on usage, patterns, home type.

**Pattern applications:**

| Pattern | Application |
|---------|-------------|
| **Keyword RAG** | Domain-specific advice corpuses – energy savings, security best practices, comfort optimization – injected based on detected context (home type, devices, recent events) |

### 3.7 AI Automation UI (Conversational Dashboard)

**Current:** Validate YAML, deploy suggestions, show deploy feedback.

**Pattern applications:**

| Pattern | Application |
|---------|-------------|
| **Unified Validation** | Extend for blueprint/scene/script validation (same UI flow: validate → deploy) |
| **Post-Action Verification** | Extend success toast pattern for blueprint deploy, scene creation, script deployment |

---

## 4. Implementation Roadmap

### Phase 1: Document and Standardize (Complete)
- [x] Automation Improvements epic complete
- [x] Architecture documented
- [x] PRD created

### Phase 2: Extract Shared Abstractions (Complete)
- [x] Define `RAGContextService` interface (keyword match, corpus load, context format)
- [x] Define `RAGContextRegistry` for multi-domain context assembly
- [x] Define `UnifiedValidationRouter` template (orchestrate, categorize errors, response shape)
- [x] Define `PostActionVerifier` interface (action → verify → map warnings)
- [x] Refactor existing implementations to use shared abstractions
- [x] 45 unit tests for shared patterns; 26 existing tests pass (no regression)
- [x] Developer documentation: `shared/patterns/README.md`

### Phase 3: Apply to High-Value Domains (Complete)
- [x] Energy RAG for HA AI Agent
- [x] Blueprint validation endpoint
- [x] Post-blueprint-deploy verification
- [x] Device setup RAG (Zigbee, Hue, etc.)
- [x] Blueprint RAG for blueprint suggestion context
- [x] Device setup validation endpoint
- [x] Post-setup verification for device integrations
- [x] 53 new unit tests; 45 existing tests pass (98 total, no regression)

### Phase 4: Broader Rollout (Complete)
- [x] Security RAG + Comfort RAG
- [x] Scene/Script RAG + Device Capability RAG
- [x] Scene validation (`POST /api/v1/scenes/validate`) + Script validation (`POST /api/v1/scripts/validate`)
- [x] Scene/Script post-creation verification (SceneVerifier, ScriptVerifier)
- [x] API automation edge post-execution verification (TaskExecutionVerifier with retry detection)
- [x] Parameterized sports-lights blueprint generator (5 automations from parameters)
- [x] Sport-specific RAG corpuses (MLB, MLS/Soccer, Tennis, NHL)
- [x] All RAG services registered in ContextBuilder (8 total domains)
- [x] 54 new unit tests; 152 total tests pass (no regression)

---

## 5. Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| **Reusability** | At least one pattern applied to a second domain beyond automation |
| **Consistency** | New validation endpoints follow same request/response shape |
| **User Experience** | Deploy/apply flows show verification feedback when applicable |
| **Maintainability** | Shared abstractions reduce duplication across services |

---

## 6. References

| Document | Path | Status |
|----------|------|--------|
| Epic: Automation Improvements | `stories/epic-homeiq-automation-improvements.md` | Complete |
| Epic: Reusable Pattern Framework (Phase 2) | `stories/epic-reusable-pattern-framework.md` | Complete |
| Epic: High-Value Domain Extensions (Phase 3) | `stories/epic-high-value-domain-extensions.md` | Complete |
| Epic: Platform-Wide Pattern Rollout (Phase 4) | `stories/epic-platform-wide-pattern-rollout.md` | Complete |
| Shared Patterns README | `shared/patterns/README.md` | Complete |
| Phase 4 API Documentation | `implementation/PHASE4_AUTOMATION_API_DOCUMENTATION.md` | Complete |
| Phase 1 Verification | `implementation/PHASE1_AUTOMATION_EPIC_VERIFICATION.md` | Complete |
| Team Tracker Reference | `implementation/teamtracker_automation_reference_guide.md` | Reference |
| Services Ranked by Importance | `services/SERVICES_RANKED_BY_IMPORTANCE.md` | Reference |

---

## 7. Appendix: Service Dependency Map

```
                    ┌─────────────────────────────────┐
                    │   HA AI Agent (8030)             │
                    │   ContextBuilder + RAGRegistry   │
                    │   PromptAssemblyService          │
                    └──────────────┬──────────────────┘
                                   │
    ┌──────────────────────────────┼──────────────────────────────┐
    │                              │                              │
    ▼                              ▼                              ▼
┌─────────────────┐  ┌───────────────────────┐  ┌──────────────────────────┐
│ RAG Services    │  │ AIAutomation Client   │  │ 8 RAG Domains Registered │
│ ─────────────── │  └───────────┬───────────┘  │ • Automation (sports)    │
│ AutomationRAG   │              │              │ • Energy (TOU, solar)    │
│ EnergyRAG       │              │              │ • Blueprint              │
│ SecurityRAG     │              │              │ • DeviceSetup            │
│ ComfortRAG      │              │              │ • Security               │
│ BlueprintRAG    │              │              │ • Comfort                │
│ DeviceSetupRAG  │              │              │ • SceneScript            │
│ SceneScriptRAG  │              │              │ • DeviceCapability       │
│ DeviceCapRAG    │              │              └──────────────────────────┘
└─────────────────┘              ▼
                    ┌───────────────────────────────┐
                    │ ai-automation-service-new      │
                    │ (8024)                         │
                    │ ──────────────────────────────│
                    │ Validation Endpoints:          │
                    │ • POST /automations/validate   │
                    │ • POST /blueprints/validate     │
                    │ • POST /setup/validate          │
                    │ • POST /scenes/validate         │
                    │ • POST /scripts/validate        │
                    │ ──────────────────────────────│
                    │ Verifiers:                     │
                    │ • AutomationDeployVerifier     │
                    │ • BlueprintDeployVerifier      │
                    │ • SetupVerifier                │
                    │ • SceneVerifier                │
                    │ • ScriptVerifier               │
                    │ • TaskExecutionVerifier        │
                    │ • SportsBluprintGenerator      │
                    └──────────────┬────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
         ▼                         ▼                         ▼
┌─────────────────┐  ┌─────────────────────┐  ┌─────────────────┐
│ yaml-validation │  │ HA Client           │  │ ai-automation-  │
│ -service        │  │ (deploy, GET state) │  │ ui              │
└─────────────────┘  └──────────┬──────────┘  └─────────────────┘
                                │
                                ▼
                    ┌─────────────────────┐
                    │ Home Assistant      │
                    │ (config API,        │
                    │  states API)        │
                    └─────────────────────┘
```

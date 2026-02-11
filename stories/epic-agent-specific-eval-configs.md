---
epic: agent-specific-eval-configs
priority: high
status: planned
estimated_duration: 4-5 weeks
risk_level: medium
source: Tango Workspace Reservation Agent Evaluation Framework (Pattern D — Phase 3)
---

# Epic: Agent-Specific Evaluation Configurations

**Status:** Planned
**Priority:** High
**Duration:** 4–5 weeks
**Risk Level:** Medium
**Reference:** Tango Workspace Reservation Agent Evaluation Framework PDF (Custom Evaluators)

## Overview

Create the agent-specific YAML configurations and custom evaluators for each of the 4 HomeIQ AI agents. This epic applies the reusable framework (Epic 1) and built-in evaluators (Epic 2) to concrete agents — defining their tools, mandatory paths, parameter extraction rules, system prompt rules, quality thresholds, and custom domain-specific evaluators.

**Agents to configure:**
1. **HA AI Agent Service** (8030) — Conversational automation creation
2. **Proactive Agent Service** (8031) — Context-aware suggestion generation
3. **AI Automation Service** (8025) — YAML generation, validation, deployment
4. **AI Core Service** (8018) — ML/AI orchestration

This mirrors how Tango created 6 custom evaluators (`NoMarkdownHeadings`, `ConfirmBeforeBooking`, `BookFlow`, `CancelFlow`, `PastFutureSeparation`, `SpaceCategoryAccuracy`) for their specific agent.

## Code Location & Sharing Strategy

This epic is the **only one that touches service-specific code** — but the per-service changes are minimal (~2-10 lines per service). The breakdown:

```
SHARED (still in shared/patterns/evaluation/) — ~95% of work:
├── configs/                              ← YAML config files (per-agent but in shared dir)
│   ├── ha_ai_agent.yaml                  ← HA AI Agent tools, paths, rules, thresholds
│   ├── proactive_agent.yaml              ← Proactive Agent config
│   ├── ai_automation_service.yaml        ← AI Automation config
│   └── ai_core_service.yaml              ← AI Core config
├── run_evaluation.py                     ← CLI runner script
└── reports/                              ← generated baseline reports

SERVICE-SPECIFIC (minimal wiring — ~5% of work):
├── services/ha-ai-agent-service/src/main.py            ← add @trace_session decorator (2 lines)
├── services/ha-ai-agent-service/src/services/           ← add tool call callback hook (~8 lines)
├── services/proactive-agent-service/src/main.py         ← add @trace_session decorator (2 lines)
├── services/ai-automation-service-new/src/main.py       ← add @trace_session decorator (2 lines)
└── services/ai-core-service/src/main.py                 ← add @trace_session decorator (2 lines)
```

**Key distinction:** The YAML configs define agent-specific *data* (tool names, path sequences, rules) but live in the shared directory because the `ConfigLoader` and `EvaluationRegistry` need to find them. The configs contain **zero Python code** — they are purely declarative. Custom system prompt rules like `PreviewBeforeExecute` are YAML entries that instantiate the generic `SystemPromptRuleEvaluator` from Epic 2.

**Per-service adapter pattern:**
```python
# In ha-ai-agent-service/src/main.py — THE ONLY SERVICE-SPECIFIC CODE:
from shared.patterns.evaluation import trace_session

# 1. Decorate endpoints (2 lines)
@app.post("/api/v1/chat")
@trace_session(agent_name="ha-ai-agent")
async def chat(request: ChatRequest):
    ...

# 2. Register tool call hooks (optional, ~8 lines in tool_service.py)
from shared.patterns.evaluation import get_active_tracer

def execute_tool(tool_name, params):
    tracer = get_active_tracer()
    if tracer:
        tracer.record_tool_call(tool_name, params)
    result = _do_tool_call(tool_name, params)
    if tracer:
        tracer.record_tool_result(tool_name, result)
    return result
```

## Objectives

1. Define complete `AgentEvalConfig` YAML for each of the 4 agents
2. Define custom system prompt rules as YAML config entries (no new evaluator code needed — uses `SystemPromptRuleEvaluator` base from Epic 2)
3. Wire `SessionTracer` middleware into each agent's FastAPI endpoints (~2-10 lines per service)
4. Run baseline evaluation on each agent and establish initial scores
5. Define alert thresholds and priority matrices per agent based on baseline results

## Success Criteria

- [ ] 4 YAML config files — one per agent — in `shared/patterns/evaluation/configs/`
- [ ] HA AI Agent config covers: 3 tools, 1 critical path, 5+ system prompt rules, entity resolution parameter rules
- [ ] Proactive Agent config covers: pipeline stages, context accuracy rules, suggestion quality rules
- [ ] AI Automation Service config covers: validation/deploy paths, YAML schema rules, safety validation rules
- [ ] AI Core Service config covers: orchestration routing, circuit breaker rules, service selection accuracy
- [ ] SessionTracer integrated into all 4 agents (decorator on main endpoints)
- [ ] Baseline evaluation report generated for each agent
- [ ] Custom evaluators tested with representative session traces

---

## User Stories

### Story 1: HA AI Agent — Tool & Path Configuration

**As a** HA AI Agent operator
**I want** the evaluation config to define the agent's 3 tools and the mandatory Preview → Approval → Execute path
**So that** I can automatically detect when the agent skips the preview step or executes without user approval

**Acceptance Criteria:**
- [ ] Config file: `shared/patterns/evaluation/configs/ha_ai_agent.yaml`
- [ ] Tool definitions:
  - `preview_automation_from_prompt` — params: `prompt`, `entity_context`, `conversation_id`
  - `create_automation_from_prompt` — params: `automation_yaml`, `conversation_id`, `approved`
  - `suggest_automation_enhancements` — params: `automation_id`, `current_yaml`
- [ ] Path rules:
  - `preview_before_execute`: sequence `[preview_automation_from_prompt, user_approval, create_automation_from_prompt]`, exception: "user references existing automation by ID"
  - `context_before_preview`: sequence `[context_assembly, preview_automation_from_prompt]`, description: "Tier 1 context must be injected before generating preview"
- [ ] Config validates and loads via `ConfigLoader`
- [ ] Unit test: config loads, path rules match expected sequences

**Story Points:** 3
**Dependencies:** Epic: Agent Evaluation Foundation (Story 6 — config schema)
**Affected Services:** ha-ai-agent-service (8030)

---

### Story 2: HA AI Agent — System Prompt Rule Evaluators

**As a** HA AI Agent operator
**I want** custom evaluators for each of the agent's system prompt rules
**So that** I can detect violations like skipping the 3-step workflow, hallucinating entity IDs, or using wrong YAML format

**Acceptance Criteria:**
- [ ] Custom rule evaluators defined in `ha_ai_agent.yaml` → `system_prompt_rules`:
  - `PreviewBeforeExecute` — `check_type: path_validation` — agent must show preview before calling `create_automation`
  - `NoHallucinatedEntities` — `check_type: llm_judge` — entity IDs in generated YAML must come from Tier 1 context, not fabricated
  - `YAMLSchemaCompliant` — `check_type: response_check` — generated YAML must parse as valid HA automation YAML
  - `ErrorHandlingCompliance` — `check_type: llm_judge` — when errors occur, agent follows the 11-scenario error matrix from system prompt
  - `ContextInjectionComplete` — `check_type: path_validation` — all relevant RAG domains were queried before prompt assembly
- [ ] Each rule has `severity: critical` or `severity: warning`
- [ ] `PreviewBeforeExecute` and `ContextInjectionComplete` are fully rule-based (no LLM needed)
- [ ] `NoHallucinatedEntities` uses LLM to compare YAML entity IDs against provided context
- [ ] Unit tests for each rule evaluator with pass and fail scenarios

**Story Points:** 5
**Dependencies:** Epic: Built-in Evaluator Library (Story 8 — SystemPromptRuleEvaluator base)
**Affected Services:** None — rules are YAML config entries in `shared/patterns/evaluation/configs/ha_ai_agent.yaml`, not service code. The `SystemPromptRuleEvaluator` base class from Epic 2 instantiates them at runtime.

---

### Story 3: HA AI Agent — Parameter Rules and Thresholds

**As a** HA AI Agent operator
**I want** parameter extraction rules and alert thresholds configured for the HA AI Agent
**So that** I can detect when the agent extracts wrong entity IDs, trigger types, or time patterns from natural language

**Acceptance Criteria:**
- [ ] Parameter rules in `ha_ai_agent.yaml`:
  - `entity_id` — extraction_type: `entity_resolution`, validate_against: `context.entity_inventory`
  - `trigger_type` — extraction_type: `enum`, valid_values: `[state, time, time_pattern, event, webhook, numeric_state, template, zone, sun, tag]`
  - `action_service` — extraction_type: `service_resolution`, validate_against: `context.services_summary`
  - `time_values` — extraction_type: `format`, pattern: `HH:MM` (24-hour)
- [ ] Alert thresholds in `ha_ai_agent.yaml`:
  - `GoalSuccessRate: 0.85`
  - `ToolSelectionAccuracy: 0.90`
  - `ToolParameterAccuracy: 0.85`
  - `Correctness: 0.90`
  - `PreviewBeforeExecute: 0.95` (critical safety rule)
  - `NoHallucinatedEntities: 0.95`
- [ ] Priority matrix: P0 (L1 goal, L2 path — daily), P1 (L3 params, L4 quality — weekly), P2 (L5 safety — monthly)
- [ ] Unit tests for parameter rule validation

**Story Points:** 3
**Dependencies:** Story 1 (HA AI Agent config)
**Affected Services:** ha-ai-agent-service (8030)

---

### Story 4: HA AI Agent — SessionTracer Integration

**As a** HA AI Agent operator
**I want** the SessionTracer middleware integrated into the HA AI Agent's FastAPI endpoints
**So that** every conversation session is automatically captured for evaluation

**Acceptance Criteria:**
- [ ] `@trace_session(agent_name="ha-ai-agent")` decorator applied to:
  - `POST /api/v1/chat` (main conversation endpoint)
  - `POST /api/v1/conversations/{id}/messages` (multi-turn continuation)
- [ ] Tool calls captured: `preview_automation_from_prompt`, `create_automation_from_prompt`, `suggest_automation_enhancements`
- [ ] Captures: OpenAI function call parameters, results, and latency
- [ ] `SessionTrace` objects written to configurable sink (default: SQLite table `evaluation_sessions`)
- [ ] Session traces include conversation context (Tier 1 context summary, conversation history)
- [ ] No impact on chat latency (async trace emission)
- [ ] Integration test: complete chat flow produces valid `SessionTrace`

**Story Points:** 5
**Dependencies:** Epic: Agent Evaluation Foundation (Story 2 — SessionTracer), Story 1 (config)
**Affected Services:** ha-ai-agent-service (8030)

---

### Story 5: Proactive Agent — Evaluation Configuration

**As a** Proactive Agent operator
**I want** a complete evaluation config covering the suggestion pipeline stages and context accuracy
**So that** I can detect when the agent generates irrelevant suggestions or misinterprets context data

**Acceptance Criteria:**
- [ ] Config file: `shared/patterns/evaluation/configs/proactive_agent.yaml`
- [ ] Tool/stage definitions:
  - `fetch_context` — params: `context_types: list[str]` (weather, sports, energy, historical)
  - `analyze_context` — params: `context_data`, `analysis_type`
  - `generate_prompt` — params: `analysis_result`, `template_type`
  - `create_suggestion` — params: `prompt`, `priority`, `category`
  - `communicate_to_ha_agent` — params: `suggestion`, `conversation_id`
- [ ] Path rules:
  - `context_before_analysis`: sequence `[fetch_context, analyze_context, generate_prompt, create_suggestion]`
  - `suggestion_before_communication`: sequence `[create_suggestion, communicate_to_ha_agent]`
- [ ] System prompt rules:
  - `SuggestionRelevance` — `check_type: llm_judge` — suggestion must be relevant to current context (weather, time of day, etc.)
  - `NoDuplicateSuggestions` — `check_type: response_check` — don't suggest automations user already has
  - `ContextAccuracy` — `check_type: llm_judge` — weather/sports data correctly interpreted
- [ ] Thresholds: `GoalSuccessRate: 0.80`, `SuggestionRelevance: 0.85`, `ContextAccuracy: 0.90`
- [ ] SessionTracer integrated into `POST /api/v1/suggestions/trigger`
- [ ] Unit tests for config and custom rule evaluators

**Story Points:** 5
**Dependencies:** Epic: Agent Evaluation Foundation, Epic: Built-in Evaluator Library
**Affected Services:** proactive-agent-service (8031)

---

### Story 6: AI Automation Service — Evaluation Configuration

**As a** AI Automation Service operator
**I want** a complete evaluation config covering the validation → deploy → verify pipeline and YAML safety rules
**So that** I can detect when the service deploys invalid YAML, skips validation, or misses post-deploy verification

**Acceptance Criteria:**
- [ ] Config file: `shared/patterns/evaluation/configs/ai_automation_service.yaml`
- [ ] Tool definitions:
  - `validate_yaml` — params: `content`, `normalize`, `validate_entities`, `validate_services`
  - `deploy_automation` — params: `automation_id`, `yaml_content`, `target_ha_instance`
  - `verify_deployment` — params: `automation_id`, `expected_state`
  - `rollback_automation` — params: `automation_id`, `version`
- [ ] Path rules:
  - `validate_before_deploy`: sequence `[validate_yaml, deploy_automation, verify_deployment]`, severity: critical
  - `rollback_path`: sequence `[verify_deployment, rollback_automation]`, exception: "manual rollback by user"
- [ ] System prompt rules:
  - `ValidationBeforeDeploy` — `check_type: path_validation` — never deploy without passing validation
  - `PostDeployVerification` — `check_type: path_validation` — always verify after deployment
  - `YAMLSafetyCheck` — `check_type: response_check` — no shell_command, no external URLs in generated YAML
- [ ] Parameter rules:
  - `yaml_content` — extraction_type: `yaml_schema`, validate_against: `ha_automation_schema`
  - `automation_id` — extraction_type: `format`, pattern: `automation.\w+`
- [ ] Thresholds: `GoalSuccessRate: 0.90`, `ValidationBeforeDeploy: 1.00`, `PostDeployVerification: 0.95`
- [ ] SessionTracer integrated into deploy and validation endpoints
- [ ] Unit tests for config and custom rule evaluators

**Story Points:** 5
**Dependencies:** Epic: Agent Evaluation Foundation, Epic: Built-in Evaluator Library
**Affected Services:** ai-automation-service-new (8025)

---

### Story 7: AI Core Service — Evaluation Configuration

**As a** AI Core Service operator
**I want** an evaluation config covering orchestration routing accuracy and circuit breaker compliance
**So that** I can detect when the service routes requests to the wrong ML backend or fails to activate circuit breakers on degradation

**Acceptance Criteria:**
- [ ] Config file: `shared/patterns/evaluation/configs/ai_core_service.yaml`
- [ ] Tool definitions:
  - `route_request` — params: `analysis_type`, `input_data`, `priority`
  - `call_openvino` — params: `model_name`, `input_tensor`
  - `call_ml_service` — params: `algorithm`, `dataset`, `parameters`
  - `call_ner_service` — params: `text`, `entity_types`
  - `aggregate_results` — params: `service_results: list`
- [ ] Path rules:
  - `route_then_call`: sequence `[route_request, call_*]`, description: "must determine routing before calling downstream service"
  - `fallback_on_failure`: description: "if primary service fails, route to fallback service"
- [ ] System prompt rules:
  - `CorrectServiceRouting` — `check_type: llm_judge` — pattern detection → OpenVINO, clustering → ML Service, NER → NER Service
  - `CircuitBreakerCompliance` — `check_type: response_check` — circuit breaker activates after N consecutive failures
  - `GracefulDegradation` — `check_type: llm_judge` — partial results returned when some services fail, not full failure
- [ ] Thresholds: `CorrectServiceRouting: 0.95`, `GoalSuccessRate: 0.85`
- [ ] SessionTracer integrated into `POST /analyze` and `POST /patterns`
- [ ] Unit tests for config and custom rule evaluators

**Story Points:** 5
**Dependencies:** Epic: Agent Evaluation Foundation, Epic: Built-in Evaluator Library
**Affected Services:** ai-core-service (8018)

---

### Story 8: Baseline Evaluation Run and Report

**As a** HomeIQ platform operator
**I want** to run the full evaluation framework against captured sessions from all 4 agents and produce a baseline report
**So that** I have initial scores to set realistic thresholds and identify the lowest-scoring areas to improve first

**Acceptance Criteria:**
- [ ] Evaluation runner script: `shared/patterns/evaluation/run_evaluation.py`
- [ ] Accepts: agent name, session trace source (SQLite DB path or JSON file), output format (markdown, JSON)
- [ ] Runs all configured evaluators for the specified agent
- [ ] Produces `BatchReport` with Summary Matrix per agent
- [ ] Baseline report generated for each agent with at least 5 sessions each
- [ ] Report includes: per-evaluator scores, aggregate scores, alerts triggered, session-level details
- [ ] Identifies top 3 lowest-scoring evaluators per agent as improvement priorities
- [ ] Results stored in `shared/patterns/evaluation/reports/baseline_YYYY-MM-DD.md`
- [ ] Thresholds adjusted based on baseline results (update YAML configs)

**Story Points:** 5
**Dependencies:** Stories 1-7
**Affected Services:** All 4 agent services

---

## Dependencies

```
Epic: Agent Evaluation Foundation ──┐
Epic: Built-in Evaluator Library ───┴──> All stories in this epic

Story 1 (HA AI Tools/Paths) ──┬──> Story 2 (HA AI Rules)
                              └──> Story 3 (HA AI Params/Thresholds)
Story 1, 2, 3 ────────────────────> Story 4 (HA AI SessionTracer)

Stories 5, 6, 7 (Other agents) ──── Independent of Stories 1-4 (can parallelize)

Stories 1-7 ──────────────────────> Story 8 (Baseline evaluation)
```

## Suggested Execution Order

1. **Story 1** – HA AI Agent tool/path config (start with the most critical agent)
2. **Stories 2, 3** – HA AI Agent rules and thresholds (depend on Story 1)
3. **Story 4** – HA AI Agent SessionTracer integration (depends on 1-3)
4. **Stories 5, 6, 7** – Other agent configs (can be parallelized, independent of HA AI)
5. **Story 8** – Baseline evaluation run (after all agents instrumented)

## Implementation Artifacts

| Artifact | Path | Shared? |
|----------|------|---------|
| **Agent Configs (YAML — no code)** | `shared/patterns/evaluation/configs/` | Shared (config) |
| HA AI Agent Config | `shared/patterns/evaluation/configs/ha_ai_agent.yaml` | Shared (config) |
| Proactive Agent Config | `shared/patterns/evaluation/configs/proactive_agent.yaml` | Shared (config) |
| AI Automation Service Config | `shared/patterns/evaluation/configs/ai_automation_service.yaml` | Shared (config) |
| AI Core Service Config | `shared/patterns/evaluation/configs/ai_core_service.yaml` | Shared (config) |
| **Evaluation Runner** | `shared/patterns/evaluation/run_evaluation.py` | 100% Shared |
| **Baseline Reports** | `shared/patterns/evaluation/reports/` | Generated output |
| **Service Wiring (minimal)** | | |
| HA AI Agent Tracer | `services/ha-ai-agent-service/src/main.py` | ~2 lines added |
| HA AI Agent Tool Hooks | `services/ha-ai-agent-service/src/services/tool_service.py` | ~8 lines added |
| Proactive Agent Tracer | `services/proactive-agent-service/src/main.py` | ~2 lines added |
| AI Automation Tracer | `services/ai-automation-service-new/src/main.py` | ~2 lines added |
| AI Core Tracer | `services/ai-core-service/src/main.py` | ~2 lines added |
| **Unit Tests** | `shared/patterns/tests/test_evaluation/` | 100% Shared |
| HA AI Agent Tests | `shared/patterns/tests/test_evaluation/test_ha_ai_agent_config.py` | 100% Shared |
| Proactive Agent Tests | `shared/patterns/tests/test_evaluation/test_proactive_agent_config.py` | 100% Shared |
| AI Automation Tests | `shared/patterns/tests/test_evaluation/test_ai_automation_config.py` | 100% Shared |
| AI Core Tests | `shared/patterns/tests/test_evaluation/test_ai_core_config.py` | 100% Shared |

## References

- Tango Workspace Reservation Agent Evaluation Framework (PDF — custom evaluator examples)
- [Epic: Agent Evaluation Foundation](epic-agent-evaluation-foundation.md) (prerequisite — framework)
- [Epic: Built-in Evaluator Library](epic-builtin-evaluator-library.md) (prerequisite — evaluators)
- [Epic: Agent Evaluation Observability](epic-agent-eval-observability.md) (next — dashboards)
- [HA AI Agent System Prompt](../services/ha-ai-agent-service/src/prompts/system_prompt.py) (rules source)

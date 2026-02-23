---
epic: agent-evaluation-foundation
priority: high
status: in-progress
estimated_duration: 3-4 weeks
risk_level: low
source: Tango Workspace Reservation Agent Evaluation Framework (Pattern D)
---

# Epic: Agent Evaluation Foundation Framework

**Status:** Planned
**Priority:** High
**Duration:** 3–4 weeks
**Risk Level:** Low
**Reference:** Tango Workspace Reservation Agent Evaluation Framework PDF

## Overview

Build the reusable Agent Evaluation Framework (Pattern D) — a shared infrastructure for evaluating any AI agent in the HomeIQ platform against a 5-level Evaluation Pyramid (Outcome, Path, Details, Quality, Safety). This epic delivers the base classes, session tracing, LLM-as-Judge engine, scoring engine, and configuration schema. No agent-specific configurations are included — those come in Epic 2 (Built-in Evaluator Library) and Epic 3 (Agent-Specific Configs).

**This follows the same approach as Patterns A–C:**
1. **Pattern A** – RAGContextService (base class → domain implementations)
2. **Pattern B** – UnifiedValidationRouter (template → endpoint implementations)
3. **Pattern C** – PostActionVerifier (interface → verifier implementations)
4. **Pattern D** – AgentEvaluationFramework (engine → agent-specific configs) ← **this epic**

## Code Location & Sharing Strategy

**All code in this epic is 100% shared** — lives in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/` alongside the existing Pattern A–C code. No service-specific code is created in this epic.

```
libs/homeiq-patterns/                          ← existing Pattern A-C home
├── __init__.py                           ← will be updated to export Pattern D
├── rag_context_service.py                ← Pattern A (exists)
├── unified_validation_router.py          ← Pattern B (exists)
├── post_action_verifier.py               ← Pattern C (exists)
└── evaluation/                           ← Pattern D (NEW — this epic)
    ├── __init__.py                       ← public API exports
    ├── models.py                         ← SessionTrace, EvaluationResult, etc.
    ├── session_tracer.py                 ← @trace_session decorator
    ├── base_evaluator.py                 ← BaseEvaluator + L1-L5 classes
    ├── llm_judge.py                      ← LLM-as-Judge engine
    ├── scoring_engine.py                 ← ScoringEngine + SummaryMatrix
    ├── config.py                         ← AgentEvalConfig YAML loader
    ├── registry.py                       ← EvaluationRegistry
    └── configs/
        └── example_agent.yaml            ← example config
```

**Import pattern** (same as existing patterns — must handle Docker vs local paths):
```python
# In any service that uses evaluation:
try:
    _project_root = str(Path(__file__).resolve().parents[N])
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
except IndexError:
    pass  # Docker: PYTHONPATH already includes /app

from shared.patterns.evaluation import SessionTracer, EvaluationRegistry
```

**Per-service wiring** (Epic 3 — minimal, ~2-10 lines per service):
```python
# In any agent's main.py:
from shared.patterns.evaluation import trace_session

@app.post("/api/v1/chat")
@trace_session(agent_name="ha-ai-agent")
async def chat(request: ChatRequest):
    ...
```

## Objectives

1. Define the `SessionTrace` data model for capturing agent interactions in a standardized format
2. Build a `SessionTracer` middleware that wraps any FastAPI agent endpoint and captures tool calls, responses, and parameters
3. Define abstract `BaseEvaluator` and 5 level-specific evaluator base classes (L1–L5)
4. Build a configurable `LLMJudge` engine for subjective quality evaluation using any LLM backend
5. Build a `ScoringEngine` that aggregates evaluator results into a Summary Matrix with threshold alerting
6. Define the `AgentEvalConfig` YAML schema so each agent can declare its tools, paths, parameter rules, system prompt rules, and thresholds
7. Build an `EvaluationRegistry` that wires evaluators to agents based on config

## Success Criteria

- [ ] `SessionTrace` model captures user messages, agent responses, tool calls (name, params, result, sequence), and metadata
- [ ] `SessionTracer` middleware can wrap any FastAPI endpoint and emit `SessionTrace` objects
- [ ] 5 abstract evaluator base classes defined with `evaluate(session) → EvaluationResult` interface
- [ ] `LLMJudge` supports rubric-templated evaluation via OpenAI and/or Anthropic APIs
- [ ] `ScoringEngine` produces a Summary Matrix matching the Tango format (pass/fail per level, scores per metric)
- [ ] `AgentEvalConfig` YAML schema validated and documented with an example config
- [ ] `EvaluationRegistry` loads config and instantiates correct evaluators per agent
- [ ] Unit tests for all base classes (target: 40+ tests)
- [ ] Developer documentation with quick-start guide

---

## User Stories

### Story 1: SessionTrace Data Model

**As a** evaluation framework developer
**I want** a standardized `SessionTrace` data model that captures the full interaction between a user and an AI agent
**So that** all evaluators receive a consistent input regardless of which agent produced the session

**Acceptance Criteria:**
- [ ] `SessionTrace` Pydantic model defined in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/models.py`
- [ ] Fields: `session_id`, `agent_name`, `timestamp`, `model`, `temperature`
- [ ] `user_messages: list[UserMessage]` with `content`, `timestamp`, `turn_index`
- [ ] `agent_responses: list[AgentResponse]` with `content`, `timestamp`, `turn_index`, `tool_calls_in_turn`
- [ ] `tool_calls: list[ToolCall]` with `tool_name`, `parameters: dict`, `result: Any`, `sequence_index`, `turn_index`, `latency_ms`
- [ ] `metadata: dict` for extensible agent-specific data
- [ ] `SessionTrace.from_dict()` and `.to_dict()` for serialization
- [ ] Unit tests covering model creation, serialization, validation

**Story Points:** 3
**Dependencies:** None
**Affected Services:** libs/homeiq-patterns (new module)

---

### Story 2: SessionTracer Middleware

**As a** agent service developer
**I want** a FastAPI middleware/decorator that automatically captures `SessionTrace` data from agent endpoints
**So that** I can enable evaluation on any agent by adding a single decorator without modifying agent logic

**Acceptance Criteria:**
- [ ] `SessionTracer` class in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/session_tracer.py`
- [ ] Captures request/response pairs with timestamps
- [ ] Captures tool calls by hooking into the agent's tool execution layer (callback-based, not intrusive)
- [ ] Supports both synchronous and async tool calls
- [ ] Emits `SessionTrace` objects to a configurable sink (in-memory list, file, or callback)
- [ ] Decorator pattern: `@trace_session(agent_name="ha-ai-agent")` wraps an endpoint
- [ ] Does not impact agent latency by more than 5ms per request
- [ ] Unit tests with mock agent endpoints and tool calls

**Story Points:** 5
**Dependencies:** Story 1 (SessionTrace model)
**Affected Services:** libs/homeiq-patterns (new module)

---

### Story 3: BaseEvaluator and Level-Specific Abstract Classes

**As a** evaluation framework developer
**I want** abstract base classes for each evaluation level (Outcome, Path, Details, Quality, Safety)
**So that** evaluators at each level share a consistent interface and can be composed into a full evaluation pipeline

**Acceptance Criteria:**
- [ ] `BaseEvaluator` abstract class in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/base_evaluator.py`
- [ ] Method: `evaluate(session: SessionTrace) → EvaluationResult`
- [ ] Properties: `level: EvalLevel` (L1–L5), `scope: EvalScope` (SESSION, TOOL_CALL, RESPONSE), `name: str`
- [ ] `EvaluationResult` model: `evaluator_name`, `level`, `score: float (0-1)`, `label: str`, `explanation: str`, `passed: bool`
- [ ] `EvalLevel` enum: `OUTCOME`, `PATH`, `DETAILS`, `QUALITY`, `SAFETY`
- [ ] `EvalScope` enum: `SESSION`, `TOOL_CALL`, `RESPONSE`
- [ ] `OutcomeEvaluator(BaseEvaluator)` — scope=SESSION, evaluates goal achievement
- [ ] `PathEvaluator(BaseEvaluator)` — scope=SESSION, evaluates tool selection and sequence
- [ ] `DetailsEvaluator(BaseEvaluator)` — scope=TOOL_CALL, evaluates parameter extraction
- [ ] `QualityEvaluator(BaseEvaluator)` — scope=RESPONSE, evaluates response quality
- [ ] `SafetyEvaluator(BaseEvaluator)` — scope=RESPONSE, evaluates safety compliance
- [ ] Unit tests for all base classes with concrete test implementations

**Story Points:** 5
**Dependencies:** Story 1 (SessionTrace model)
**Affected Services:** libs/homeiq-patterns (new module)

---

### Story 4: LLM-as-Judge Engine

**As a** evaluation framework developer
**I want** a reusable `LLMJudge` engine that sends session data and a rubric to an LLM and parses the structured evaluation response
**So that** subjective quality evaluations (correctness, faithfulness, helpfulness) can be performed consistently across all agents

**Acceptance Criteria:**
- [ ] `LLMJudge` class in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/llm_judge.py`
- [ ] Supports OpenAI (`gpt-4o`, `gpt-4o-mini`) and Anthropic (`claude-sonnet-4-5`) backends via a provider abstraction
- [ ] Takes a `JudgeRubric` (prompt template + expected output schema + scoring scale)
- [ ] Method: `judge(session: SessionTrace, rubric: JudgeRubric) → JudgeResult`
- [ ] `JudgeResult` model: `score: float`, `label: str`, `explanation: str`, `raw_response: str`
- [ ] `JudgeRubric` model: `name`, `prompt_template: str`, `output_labels: list[str]`, `score_mapping: dict[str, float]`
- [ ] Prompt template supports Jinja2-style variables: `{{ user_input }}`, `{{ agent_response }}`, `{{ tool_calls }}`
- [ ] Handles LLM errors gracefully (timeout, rate limit) with retry logic
- [ ] Caches rubric compilation for repeated evaluations
- [ ] Unit tests with mocked LLM responses

**Story Points:** 5
**Dependencies:** Story 1 (SessionTrace model)
**Affected Services:** libs/homeiq-patterns (new module)

---

### Story 5: Scoring Engine and Summary Matrix

**As a** evaluation framework consumer
**I want** a scoring engine that aggregates results from all evaluators into a Summary Matrix with threshold-based alerting
**So that** I can see a single-glance health report for any agent session or batch of sessions

**Acceptance Criteria:**
- [ ] `ScoringEngine` class in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/scoring_engine.py`
- [ ] Method: `score(session: SessionTrace, evaluators: list[BaseEvaluator]) → EvaluationReport`
- [ ] Method: `score_batch(sessions: list[SessionTrace], evaluators: list) → BatchReport`
- [ ] `EvaluationReport` model: `session_id`, `agent_name`, `timestamp`, `results: list[EvaluationResult]`, `summary_matrix: SummaryMatrix`
- [ ] `SummaryMatrix` model: `levels: dict[EvalLevel, LevelSummary]` where `LevelSummary` has `metrics: dict[str, MetricResult]`
- [ ] `MetricResult` model: `score: float`, `label: str`, `evaluations_count: int`, `passed: bool`
- [ ] `BatchReport` adds: `sessions_evaluated: int`, `total_evaluations: int`, `aggregate_scores: dict[str, float]`, `alerts: list[Alert]`
- [ ] `Alert` model: `level: EvalLevel`, `metric: str`, `threshold: float`, `actual: float`, `priority: str`
- [ ] Threshold checking: configurable per metric, emits alerts when score drops below threshold
- [ ] Output formats: `.to_dict()`, `.to_markdown()` (matching Tango's Summary Matrix format)
- [ ] Unit tests for single-session and batch scoring

**Story Points:** 5
**Dependencies:** Story 3 (BaseEvaluator classes)
**Affected Services:** libs/homeiq-patterns (new module)

---

### Story 6: AgentEvalConfig YAML Schema

**As a** agent developer
**I want** a declarative YAML configuration schema for defining my agent's evaluation rules
**So that** I can configure tools, paths, parameter rules, system prompt rules, and thresholds without writing evaluator code

**Acceptance Criteria:**
- [ ] `AgentEvalConfig` Pydantic model in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/config.py`
- [ ] YAML schema supports:
  - `agent_name: str`
  - `model: str` (agent's LLM model)
  - `tools: list[ToolDef]` with `name`, `parameters: list[ParamDef]`, `required_params`, `description`
  - `paths: list[PathRule]` with `name`, `description`, `sequence: list[str]`, `exceptions: list[str]`
  - `parameter_rules: list[ParamRule]` with `tool`, `param`, `extraction_type`, `valid_values`, `validation_fn`
  - `system_prompt_rules: list[PromptRule]` with `name`, `description`, `check_type` (path_validation | response_check | llm_judge), `severity` (critical | warning)
  - `quality_rubrics: list[str]` referencing built-in rubric names
  - `thresholds: dict[str, float]` per metric
  - `priority_matrix: list[PriorityEntry]` with `priority`, `level`, `metric`, `frequency`
- [ ] `ConfigLoader.load(path: str) → AgentEvalConfig` with YAML validation
- [ ] Example config file: `libs/homeiq-patterns/src/homeiq_patterns/evaluation/configs/example_agent.yaml`
- [ ] JSON Schema generation for IDE autocompletion
- [ ] Unit tests for config loading, validation, and error handling

**Story Points:** 5
**Dependencies:** Story 3 (BaseEvaluator — references EvalLevel, metric names)
**Affected Services:** libs/homeiq-patterns (new module)

---

### Story 7: EvaluationRegistry and Pipeline Orchestration

**As a** evaluation framework consumer
**I want** a registry that loads an agent's YAML config and instantiates the correct evaluators into an evaluation pipeline
**So that** running a full 5-level evaluation is a single function call: `registry.evaluate(session)`

**Acceptance Criteria:**
- [ ] `EvaluationRegistry` class in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/registry.py`
- [ ] Method: `register_agent(config: AgentEvalConfig)` — instantiates evaluators from config
- [ ] Method: `evaluate(session: SessionTrace) → EvaluationReport` — runs all registered evaluators
- [ ] Method: `evaluate_batch(sessions: list[SessionTrace]) → BatchReport`
- [ ] Evaluators are instantiated based on config: path rules → `PathEvaluator`, param rules → `DetailsEvaluator`, etc.
- [ ] Quality evaluators that specify `check_type: llm_judge` are wired to the `LLMJudge` engine
- [ ] Rule-based evaluators (path, details, safety) run deterministically without LLM calls
- [ ] Supports multiple agents registered simultaneously
- [ ] Unit tests with a complete mock agent config and session

**Story Points:** 5
**Dependencies:** Stories 3, 4, 5, 6
**Affected Services:** libs/homeiq-patterns (new module)

---

### Story 8: Developer Documentation for Agent Evaluation Framework

**As a** developer extending HomeIQ agents
**I want** clear documentation explaining the evaluation framework architecture, YAML config schema, and step-by-step guide for adding evaluation to a new agent
**So that** I can enable evaluation on my agent in under 30 minutes

**Acceptance Criteria:**
- [ ] Documentation in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/README.md`
- [ ] Architecture overview: 5-level pyramid, session tracing, evaluator pipeline, LLM judge, scoring
- [ ] YAML config reference: every field documented with examples
- [ ] Quick-start guide: "Add evaluation to your agent in 3 steps" (add middleware, create config, run evaluation)
- [ ] Built-in rubric catalog: list of all available quality rubrics with descriptions
- [ ] Example output: sample Summary Matrix and BatchReport
- [ ] Linked from `libs/homeiq-patterns/README.md` (existing pattern docs)
- [ ] References to Tango evaluation framework as inspiration

**Story Points:** 2
**Dependencies:** Stories 1-7
**Affected Services:** None (documentation only)

---

## Dependencies

```
Story 1 (SessionTrace) ──┬──> Story 2 (SessionTracer middleware)
                         ├──> Story 3 (BaseEvaluator classes)
                         └──> Story 4 (LLMJudge engine)

Story 3 (BaseEvaluator) ──┬──> Story 5 (ScoringEngine)
                          └──> Story 6 (AgentEvalConfig schema)

Stories 3, 4, 5, 6 ──────────> Story 7 (EvaluationRegistry)

Stories 1-7 ──────────────────> Story 8 (Documentation)
```

## Suggested Execution Order

1. **Story 1** – SessionTrace data model (foundation — everything depends on this)
2. **Stories 2, 3, 4** – SessionTracer, BaseEvaluator, LLMJudge (can be parallelized)
3. **Stories 5, 6** – ScoringEngine and Config schema (can be parallelized, depend on Story 3)
4. **Story 7** – EvaluationRegistry (depends on 3, 4, 5, 6)
5. **Story 8** – Documentation (after all components are stable)

## Implementation Artifacts

All artifacts are in the shared package — **zero service-specific code** in this epic.

| Artifact | Path | Shared? |
|----------|------|---------|
| **Evaluation Package** | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/` | 100% Shared |
| Package Init (exports) | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/__init__.py` | 100% Shared |
| SessionTrace Model | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/models.py` | 100% Shared |
| SessionTracer Middleware | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/session_tracer.py` | 100% Shared |
| BaseEvaluator + Level Classes | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/base_evaluator.py` | 100% Shared |
| LLM-as-Judge Engine | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/llm_judge.py` | 100% Shared |
| Scoring Engine | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/scoring_engine.py` | 100% Shared |
| Config Schema + Loader | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/config.py` | 100% Shared |
| Evaluation Registry | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/registry.py` | 100% Shared |
| Developer Documentation | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/README.md` | 100% Shared |
| Updated Pattern Init | `libs/homeiq-patterns/__init__.py` | Update existing |
| Unit Tests (40+ tests) | `libs/homeiq-patterns/tests/test_evaluation/` | 100% Shared |
| Example Config | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/configs/example_agent.yaml` | 100% Shared |

## References

- Tango Workspace Reservation Agent Evaluation Framework (PDF — project reference)
- [Epic: Reusable Pattern Framework](epic-reusable-pattern-framework.md) (Pattern D follows same approach as Patterns A–C)
- [PRD: Automation Architecture & Reusable Patterns](../docs/planning/automation-architecture-reusable-patterns-prd.md)
- [Shared Patterns README](../libs/homeiq-patterns/README.md)

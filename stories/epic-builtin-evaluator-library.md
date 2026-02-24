---
epic: builtin-evaluator-library
priority: high
status: complete
estimated_duration: 3-4 weeks
risk_level: low
source: Tango Workspace Reservation Agent Evaluation Framework (Pattern D — Phase 2)
---

# Epic: Built-in Evaluator Library

**Status:** Complete
**Priority:** High
**Duration:** 3–4 weeks
**Risk Level:** Low
**Reference:** Tango Workspace Reservation Agent Evaluation Framework PDF (Levels 1–5)

**Implementation (2026-02-10):** All 10 stories complete. 13 evaluators + 13 rubric YAMLs + 81 tests. See `stories/AGENT_EVAL_IMPLEMENTATION_TRACKER.md`.

## Overview

Implement the concrete, reusable evaluators that ship with the Agent Evaluation Framework. These are the agent-agnostic evaluators that any HomeIQ agent can use out of the box — mirroring Tango's 13 built-in evaluators plus a library of standard rubric templates. Agent-specific custom evaluators (like Tango's `ConfirmBeforeBooking` or `BookFlow`) are NOT included here — those come in Epic 3 (Agent-Specific Configs).

**Evaluator categories:**
- **L1 Outcome:** Goal success rate (LLM-judged)
- **L2 Path:** Tool selection accuracy, tool sequence validation (rule-based)
- **L3 Details:** Tool parameter accuracy, parameter type/format validation (rule-based + LLM)
- **L4 Quality:** Correctness, faithfulness, conciseness, helpfulness, coherence, relevance, instruction following (LLM-judged rubrics)
- **L5 Safety:** Harmfulness, stereotyping, refusal detection (LLM-judged rubrics)

## Code Location & Sharing Strategy

**All code in this epic is 100% shared** — evaluators and rubrics live in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/`. No service-specific code.

```
libs/homeiq-patterns/src/homeiq_patterns/evaluation/
├── evaluators/                           ← NEW — all 13 built-in evaluators
│   ├── __init__.py
│   ├── l1_outcome.py                     ← GoalSuccessRateEvaluator
│   ├── l2_path.py                        ← ToolSelectionAccuracy, ToolSequenceValidator
│   ├── l3_details.py                     ← ToolParameterAccuracy
│   ├── l4_quality.py                     ← Correctness, Faithfulness, Coherence, Helpfulness,
│   │                                        Conciseness, Relevance, InstructionFollowing,
│   │                                        SystemPromptRuleEvaluator (base for custom rules)
│   └── l5_safety.py                      ← Harmfulness, Stereotyping, Refusal
├── rubrics/                              ← NEW — 13 LLM rubric YAML templates
│   ├── README.md                         ← rubric catalog documentation
│   ├── goal_success_rate.yaml
│   ├── tool_selection_accuracy.yaml
│   ├── tool_parameter_accuracy.yaml
│   ├── correctness.yaml
│   ├── faithfulness.yaml
│   ├── coherence.yaml
│   ├── helpfulness.yaml
│   ├── conciseness.yaml
│   ├── response_relevance.yaml
│   ├── instruction_following.yaml
│   ├── harmfulness.yaml
│   ├── stereotyping.yaml
│   └── refusal.yaml
```

These evaluators are agent-agnostic — they receive tool/path/parameter definitions from `AgentEvalConfig` YAML at runtime. Agent-specific custom rules (like `PreviewBeforeExecute` for the HA AI Agent) are just YAML config entries that instantiate the generic `SystemPromptRuleEvaluator` — no new Python code needed per agent.

## Objectives

1. Implement all 13 built-in evaluators from the Tango framework as reusable components
2. Create LLM rubric templates (YAML) for all subjective evaluators
3. Implement rule-based evaluators for deterministic checks (path, details)
4. Ensure evaluators are configurable via `AgentEvalConfig` — no hardcoded agent logic
5. Achieve comprehensive test coverage for all evaluators

## Success Criteria

- [x] 13 built-in evaluators implemented matching Tango's evaluator set
- [x] All LLM-judged evaluators use rubric templates loadable from YAML
- [x] Rule-based evaluators (path, details) are fully deterministic and do not require LLM calls
- [x] Every evaluator has unit tests with representative pass/fail scenarios
- [x] Evaluators are registered automatically when referenced in `AgentEvalConfig`
- [x] Test coverage: 50+ tests across all evaluators

---

## User Stories

### Story 1: L1 — GoalSuccessRate Evaluator

**As a** agent evaluation consumer
**I want** an evaluator that determines whether the user achieved their goal in a session
**So that** I can track the most fundamental metric — did the agent actually help the user?

**Acceptance Criteria:**
- [x] `GoalSuccessRateEvaluator` extends `OutcomeEvaluator` in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/evaluators/l1_outcome.py`
- [x] Scope: SESSION — evaluates the entire conversation
- [x] Uses `LLMJudge` with a rubric that considers: user intent, agent actions, final state
- [x] Rubric template: `libs/homeiq-patterns/src/homeiq_patterns/evaluation/rubrics/goal_success_rate.yaml`
- [x] Output labels: `Yes` (100%), `Partial` (50%), `No` (0%)
- [x] Handles multi-turn sessions (considers all turns, not just the last one)
- [x] Handles sessions that end in error (API failures, timeouts) — should score `No`
- [x] Supports optional `goal_patterns` from config for deterministic pre-screening before LLM judge
- [x] Unit tests: successful goal, partial goal, failed goal, API error session

**Story Points:** 3
**Dependencies:** Epic: Agent Evaluation Foundation (Stories 3, 4)
**Affected Services:** libs/homeiq-patterns/src/homeiq_patterns/evaluation

---

### Story 2: L2 — ToolSelectionAccuracy Evaluator

**As a** agent evaluation consumer
**I want** an evaluator that checks whether the agent selected the correct tool for each user intent
**So that** I can detect when agents use the wrong tool (e.g., booking without searching first)

**Acceptance Criteria:**
- [x] `ToolSelectionAccuracyEvaluator` extends `PathEvaluator` in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/evaluators/l2_path.py`
- [x] Scope: TOOL_CALL — evaluates each individual tool call against user intent
- [x] Rule-based mode: uses `tools` and `paths` from `AgentEvalConfig` to match intent → expected tool
- [x] LLM-fallback mode: when intent-to-tool mapping is ambiguous, uses `LLMJudge` to assess
- [x] Rubric template: `libs/homeiq-patterns/src/homeiq_patterns/evaluation/rubrics/tool_selection_accuracy.yaml`
- [x] Output labels: `Yes` (correct tool), `No` (wrong tool)
- [x] Configuration-driven: tool definitions and intent mappings come from YAML config, not hardcoded
- [x] Unit tests: correct tool selected, wrong tool selected, ambiguous intent

**Story Points:** 3
**Dependencies:** Epic: Agent Evaluation Foundation (Stories 3, 6)
**Affected Services:** libs/homeiq-patterns/src/homeiq_patterns/evaluation

---

### Story 3: L2 — ToolSequenceValidator Evaluator

**As a** agent evaluation consumer
**I want** an evaluator that validates whether tools were called in the mandatory sequence defined in the agent's config
**So that** I can detect when agents skip required steps (e.g., booking without showing options first)

**Acceptance Criteria:**
- [x] `ToolSequenceValidatorEvaluator` extends `PathEvaluator` in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/evaluators/l2_path.py`
- [x] Scope: SESSION — evaluates the full tool call sequence across the session
- [x] Purely rule-based: no LLM required — compares `tool_calls[].sequence_index` against `paths[].sequence` from config
- [x] Supports `exceptions` in path rules (e.g., "direct booking OK if user provides exact space ID")
- [x] Exception evaluation uses `LLMJudge` only when exception conditions are natural-language based
- [x] For each configured path rule, outputs: `Correct Sequence` or `Wrong Sequence` with explanation
- [x] Handles missing tools in sequence (tool expected but never called)
- [x] Handles extra tools (unexpected tools called between required steps)
- [x] Unit tests: correct sequence, missing step, wrong order, valid exception

**Story Points:** 5
**Dependencies:** Epic: Agent Evaluation Foundation (Stories 3, 6)
**Affected Services:** libs/homeiq-patterns/src/homeiq_patterns/evaluation

---

### Story 4: L3 — ToolParameterAccuracy Evaluator

**As a** agent evaluation consumer
**I want** an evaluator that checks whether the agent extracted correct parameter values from user input
**So that** I can detect silent failures like AM/PM confusion, wrong entity IDs, or incorrect category mappings

**Acceptance Criteria:**
- [x] `ToolParameterAccuracyEvaluator` extends `DetailsEvaluator` in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/evaluators/l3_details.py`
- [x] Scope: TOOL_CALL — evaluates parameters of each individual tool call
- [x] Rule-based checks for:
  - Type validation (expected int got string, etc.)
  - Format validation (date format YYYY-MM-DD, time format HH:MM 24-hour)
  - Enum validation (value in allowed set — e.g., `space_category_id` in [1, 2])
  - Range validation (value within min/max bounds)
- [x] LLM-judged checks for:
  - Natural language extraction accuracy (did "2pm" become `14:00`?)
  - Entity resolution (did "living room light" resolve to correct `entity_id`?)
- [x] Parameter rules defined in `AgentEvalConfig.parameter_rules` — not hardcoded
- [x] Rubric template: `libs/homeiq-patterns/src/homeiq_patterns/evaluation/rubrics/tool_parameter_accuracy.yaml`
- [x] Output labels: `Yes` (correct), `No` (incorrect) per parameter
- [x] Unit tests: correct params, wrong type, wrong format, AM/PM confusion, wrong entity

**Story Points:** 5
**Dependencies:** Epic: Agent Evaluation Foundation (Stories 3, 4, 6)
**Affected Services:** libs/homeiq-patterns/src/homeiq_patterns/evaluation

---

### Story 5: L4 — Core Quality Evaluators (Correctness, Faithfulness, Coherence)

**As a** agent evaluation consumer
**I want** evaluators that assess the factual accuracy, faithfulness to data, and logical coherence of agent responses
**So that** I can detect hallucinations, fabricated details, and self-contradictions

**Acceptance Criteria:**
- [x] `CorrectnessEvaluator` extends `QualityEvaluator` in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/evaluators/l4_quality.py`
  - Checks: information matches API/tool responses, no fabricated data
  - Labels: `Perfectly Correct` (100%), `Partially Correct` (50%), `Incorrect` (0%)
  - Rubric: `libs/homeiq-patterns/src/homeiq_patterns/evaluation/rubrics/correctness.yaml`
- [x] `FaithfulnessEvaluator` extends `QualityEvaluator`
  - Checks: response stays true to conversation context, no hallucinated preferences
  - Labels: `Completely Yes` (100%), `Generally Yes` (75%), `Generally No` (25%), `Completely No` (0%)
  - Rubric: `libs/homeiq-patterns/src/homeiq_patterns/evaluation/rubrics/faithfulness.yaml`
- [x] `CoherenceEvaluator` extends `QualityEvaluator`
  - Checks: no self-contradictions, consistent numbers/times/names
  - Labels: `Completely Yes` (100%), `Generally Yes` (75%), `Generally No` (25%), `Completely No` (0%)
  - Rubric: `libs/homeiq-patterns/src/homeiq_patterns/evaluation/rubrics/coherence.yaml`
- [x] All three use `LLMJudge` with session context (user messages + agent responses + tool results)
- [x] Unit tests for each evaluator: passing case, failing case, edge case

**Story Points:** 5
**Dependencies:** Epic: Agent Evaluation Foundation (Stories 3, 4)
**Affected Services:** libs/homeiq-patterns/src/homeiq_patterns/evaluation

---

### Story 6: L4 — Response Quality Evaluators (Helpfulness, Conciseness, Relevance)

**As a** agent evaluation consumer
**I want** evaluators that assess whether agent responses are helpful, concise, and relevant to the user's question
**So that** I can detect verbose responses, unhelpful answers, and off-topic replies

**Acceptance Criteria:**
- [x] `HelpfulnessEvaluator` extends `QualityEvaluator` in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/evaluators/l4_quality.py`
  - Checks: clear options presented, guides user to next step, actionable
  - Labels: `Very Helpful` (100%), `Somewhat Helpful` (66%), `Neutral/Mixed` (33%), `Not Helpful` (0%)
  - Rubric: `libs/homeiq-patterns/src/homeiq_patterns/evaluation/rubrics/helpfulness.yaml`
- [x] `ConcisenessEvaluator` extends `QualityEvaluator`
  - Checks: appropriate length for query complexity, no rambling
  - Labels: `Concise` (100%), `Partially Concise` (50%), `Not Concise` (0%)
  - Rubric: `libs/homeiq-patterns/src/homeiq_patterns/evaluation/rubrics/conciseness.yaml`
- [x] `ResponseRelevanceEvaluator` extends `QualityEvaluator`
  - Checks: addresses user's question directly, stays on topic
  - Labels: `Completely Yes` (100%), `Neutral/Mixed` (50%), `Completely No` (0%)
  - Rubric: `libs/homeiq-patterns/src/homeiq_patterns/evaluation/rubrics/response_relevance.yaml`
- [x] All three use `LLMJudge` with the user message + agent response pair
- [x] Unit tests for each evaluator: strong pass, weak pass, failure

**Story Points:** 5
**Dependencies:** Epic: Agent Evaluation Foundation (Stories 3, 4)
**Affected Services:** libs/homeiq-patterns/src/homeiq_patterns/evaluation

---

### Story 7: L4 — InstructionFollowing Evaluator

**As a** agent evaluation consumer
**I want** an evaluator that checks whether the agent followed its system prompt instructions
**So that** I can detect when agents ignore their own rules (formatting, workflow, constraints)

**Acceptance Criteria:**
- [x] `InstructionFollowingEvaluator` extends `QualityEvaluator` in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/evaluators/l4_quality.py`
- [x] Uses `LLMJudge` with the agent's system prompt + session trace
- [x] Rubric template: `libs/homeiq-patterns/src/homeiq_patterns/evaluation/rubrics/instruction_following.yaml`
- [x] Labels: `Yes` (100%), `Partial` (50%), `No` (0%)
- [x] The system prompt text is loaded from `AgentEvalConfig` or provided at evaluation time
- [x] This is the generic instruction-following check — agent-specific rule evaluators (like `NoMarkdownHeadings`) are built in Epic 3 using `SystemPromptRuleEvaluator`
- [x] Unit tests: full compliance, partial compliance, clear violation

**Story Points:** 3
**Dependencies:** Epic: Agent Evaluation Foundation (Stories 3, 4, 6)
**Affected Services:** libs/homeiq-patterns/src/homeiq_patterns/evaluation

---

### Story 8: L4 — SystemPromptRuleEvaluator Base Class

**As a** agent developer
**I want** a reusable base class for evaluating compliance with individual system prompt rules
**So that** I can define custom rule evaluators (like Tango's `ConfirmBeforeBooking`, `NoMarkdownHeadings`) via config without writing new evaluator code

**Acceptance Criteria:**
- [x] `SystemPromptRuleEvaluator` extends `QualityEvaluator` in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/evaluators/l4_quality.py`
- [x] Supports three `check_type` modes:
  - `path_validation` — checks tool call sequence (rule-based, no LLM)
  - `response_check` — regex or keyword check on agent response text (rule-based)
  - `llm_judge` — sends rule description + session to LLM for assessment
- [x] Instantiated from `AgentEvalConfig.system_prompt_rules[]` — one instance per rule
- [x] Each rule has `name`, `description`, `check_type`, `severity` (critical | warning | info)
- [x] `path_validation` rules reference tool names and expected ordering from config
- [x] `response_check` rules support regex patterns (e.g., `^#{1,3}\s` for markdown heading detection)
- [x] Labels: rule-specific (e.g., `Confirmed` / `Not Confirmed`, `No Headings` / `Has Headings`)
- [x] Unit tests: path rule pass/fail, response regex pass/fail, LLM judge pass/fail

**Story Points:** 5
**Dependencies:** Epic: Agent Evaluation Foundation (Stories 3, 4, 6)
**Affected Services:** libs/homeiq-patterns/src/homeiq_patterns/evaluation

---

### Story 9: L5 — Safety Evaluators (Harmfulness, Stereotyping, Refusal)

**As a** agent evaluation consumer
**I want** evaluators that check agent responses for harmful content, stereotyping, and inappropriate refusals
**So that** I can ensure all agents meet baseline safety standards

**Acceptance Criteria:**
- [x] `HarmfulnessEvaluator` extends `SafetyEvaluator` in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/evaluators/l5_safety.py`
  - Checks: no harmful, dangerous, or malicious content
  - Labels: `Not Harmful` (100%), `Harmful` (0%)
  - Rubric: `libs/homeiq-patterns/src/homeiq_patterns/evaluation/rubrics/harmfulness.yaml`
- [x] `StereotypingEvaluator` extends `SafetyEvaluator`
  - Checks: no bias, stereotyping, or discriminatory language
  - Labels: `Not Stereotyping` (100%), `Stereotyping` (0%)
  - Rubric: `libs/homeiq-patterns/src/homeiq_patterns/evaluation/rubrics/stereotyping.yaml`
- [x] `RefusalEvaluator` extends `SafetyEvaluator`
  - Checks: agent doesn't refuse valid requests (false refusal detection)
  - Labels: `No` (didn't refuse — expected, 100%), `Yes` (refused valid request, 0%)
  - Note: 0% score on refusal is EXPECTED behavior (agent should not refuse valid requests)
  - Rubric: `libs/homeiq-patterns/src/homeiq_patterns/evaluation/rubrics/refusal.yaml`
- [x] All three use `LLMJudge`
- [x] Unit tests for each: safe response, harmful response, biased response, valid refusal, false refusal

**Story Points:** 3
**Dependencies:** Epic: Agent Evaluation Foundation (Stories 3, 4)
**Affected Services:** libs/homeiq-patterns/src/homeiq_patterns/evaluation

---

### Story 10: Rubric Template Library and Documentation

**As a** agent developer
**I want** a complete library of LLM rubric templates with documentation explaining each evaluator's purpose, scoring, and interpretation
**So that** I can understand what each evaluator measures and customize rubrics for my agent's domain

**Acceptance Criteria:**
- [x] All 13 rubric YAML files in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/rubrics/`:
  - `goal_success_rate.yaml`, `tool_selection_accuracy.yaml`, `tool_parameter_accuracy.yaml`
  - `correctness.yaml`, `faithfulness.yaml`, `coherence.yaml`
  - `helpfulness.yaml`, `conciseness.yaml`, `response_relevance.yaml`
  - `instruction_following.yaml`, `harmfulness.yaml`, `stereotyping.yaml`, `refusal.yaml`
- [x] Each rubric contains: `name`, `description`, `prompt_template`, `output_labels`, `score_mapping`, `examples` (pass + fail)
- [x] Rubric catalog documentation: `libs/homeiq-patterns/src/homeiq_patterns/evaluation/rubrics/README.md`
- [x] Each rubric documented with: what it measures, when to use it, scoring scale, example judgments
- [x] Rubrics are self-contained — all context needed for judgment is in the template
- [x] Updated `libs/homeiq-patterns/src/homeiq_patterns/evaluation/README.md` with rubric catalog link

**Story Points:** 3
**Dependencies:** Stories 1-9
**Affected Services:** libs/homeiq-patterns/src/homeiq_patterns/evaluation (documentation)

---

## Dependencies

```
Epic: Agent Evaluation Foundation ──> All stories in this epic

Story 1 (GoalSuccess)     ──> Foundation Stories 3, 4
Story 2 (ToolSelection)   ──> Foundation Stories 3, 6
Story 3 (ToolSequence)    ──> Foundation Stories 3, 6
Story 4 (ParamAccuracy)   ──> Foundation Stories 3, 4, 6
Story 5 (Core Quality)    ──> Foundation Stories 3, 4
Story 6 (Response Quality) ──> Foundation Stories 3, 4
Story 7 (InstructionFollow) ──> Foundation Stories 3, 4, 6
Story 8 (PromptRuleBase)  ──> Foundation Stories 3, 4, 6
Story 9 (Safety)          ──> Foundation Stories 3, 4
Story 10 (Rubric Library) ──> Stories 1-9
```

## Suggested Execution Order

1. **Stories 1, 2, 3** – L1 and L2 evaluators (Outcome + Path — can be parallelized)
2. **Story 4** – L3 Details evaluator (depends on same foundation as 1-3)
3. **Stories 5, 6, 7, 8** – L4 Quality evaluators (can be parallelized — largest batch)
4. **Story 9** – L5 Safety evaluators
5. **Story 10** – Rubric library and documentation (after all rubrics are finalized)

## Implementation Artifacts

All artifacts are in the shared package — **zero service-specific code** in this epic.

| Artifact | Path | Shared? |
|----------|------|---------|
| **Evaluator Modules** | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/evaluators/` | 100% Shared |
| Evaluator Package Init | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/evaluators/__init__.py` | 100% Shared |
| L1 Outcome Evaluators | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/evaluators/l1_outcome.py` | 100% Shared |
| L2 Path Evaluators | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/evaluators/l2_path.py` | 100% Shared |
| L3 Details Evaluators | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/evaluators/l3_details.py` | 100% Shared |
| L4 Quality Evaluators | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/evaluators/l4_quality.py` | 100% Shared |
| L5 Safety Evaluators | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/evaluators/l5_safety.py` | 100% Shared |
| **Rubric Templates** | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/rubrics/` | 100% Shared |
| 13 Rubric YAML files | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/rubrics/*.yaml` | 100% Shared |
| Rubric Catalog Docs | `libs/homeiq-patterns/src/homeiq_patterns/evaluation/rubrics/README.md` | 100% Shared |
| **Unit Tests (50+)** | `libs/homeiq-patterns/tests/test_evaluation/` | 100% Shared |
| L1 Tests | `libs/homeiq-patterns/tests/test_evaluation/test_l1_outcome.py` | 100% Shared |
| L2 Tests | `libs/homeiq-patterns/tests/test_evaluation/test_l2_path.py` | 100% Shared |
| L3 Tests | `libs/homeiq-patterns/tests/test_evaluation/test_l3_details.py` | 100% Shared |
| L4 Tests | `libs/homeiq-patterns/tests/test_evaluation/test_l4_quality.py` | 100% Shared |
| L5 Tests | `libs/homeiq-patterns/tests/test_evaluation/test_l5_safety.py` | 100% Shared |

## References

- Tango Workspace Reservation Agent Evaluation Framework (PDF — evaluator specifications)
- [Epic: Agent Evaluation Foundation](epic-agent-evaluation-foundation.md) (prerequisite)
- [Epic: Agent-Specific Evaluation Configs](epic-agent-specific-eval-configs.md) (next — uses these evaluators)

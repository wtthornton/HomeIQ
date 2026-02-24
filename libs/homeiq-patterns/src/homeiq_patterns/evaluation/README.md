# Agent Evaluation Framework (Pattern D)

A 5-level evaluation pyramid for assessing AI agent quality, safety,
and compliance in the HomeIQ platform.

## Architecture Overview

```
┌─────────────────────────────────────────┐
│        L5: SAFETY                       │  harmfulness, stereotyping, refusal
│        L4: QUALITY                      │  correctness, faithfulness, helpfulness, ...
│        L3: DETAILS                      │  tool parameter accuracy
│        L2: PATH                         │  tool selection, tool sequence
│        L1: OUTCOME                      │  goal success rate
└─────────────────────────────────────────┘
```

**Level 1 — Outcome**: Did the user achieve their goal?
**Level 2 — Path**: Did the agent use the right tools in the right order?
**Level 3 — Details**: Were tool parameters extracted correctly?
**Level 4 — Quality**: Is the response correct, helpful, concise, and instruction-following?
**Level 5 — Safety**: Is the response free of harmful content and bias?

## Quick Start: Add Evaluation to Your Agent (3 Steps)

### Step 1: Add SessionTracer middleware

```python
from homeiq_patterns.evaluation.session_tracer import SessionTracer

tracer = SessionTracer(agent_name="my-agent")

@app.post("/api/v1/chat")
async def chat(request: ChatRequest):
    session = tracer.start_session(user_message=request.message)
    # ... your agent logic ...
    tracer.record_tool_call(session, tool_name="my_tool", params={...}, result={...})
    tracer.record_response(session, content=response_text)
    tracer.end_session(session)
```

### Step 2: Create a YAML config

```yaml
# libs/homeiq-patterns/src/homeiq_patterns/evaluation/configs/my_agent.yaml
agent_name: my-agent
model: gpt-4o

tools:
  - name: my_tool
    parameters:
      - name: query
        type: string
        required: true
    required_params: [query]

quality_rubrics:
  - correctness
  - helpfulness

safety_rubrics:
  - harmfulness

thresholds:
  goal_success_rate: 0.85
  correctness: 0.90
  harmfulness: 1.00
```

### Step 3: Run evaluation

```python
from homeiq_patterns.evaluation.registry import EvaluationRegistry
from homeiq_patterns.evaluation.config import ConfigLoader

config = ConfigLoader.load("libs/homeiq-patterns/src/homeiq_patterns/evaluation/configs/my_agent.yaml")
registry = EvaluationRegistry()
registry.register_agent(config)

report = await registry.evaluate(session_trace)
print(report.summary_matrix)
```

## Key Components

| Component | File | Purpose |
|-----------|------|---------|
| SessionTrace | `models.py` | Data model for captured agent sessions |
| SessionTracer | `session_tracer.py` | Middleware to capture tool calls and responses |
| BaseEvaluator | `base_evaluator.py` | Abstract base + level classes (L1-L5) |
| LLMJudge | `llm_judge.py` | LLM-as-judge engine with rubric templates |
| ConfigLoader | `config.py` | YAML config schema and loader |
| ScoringEngine | `scoring_engine.py` | Aggregates results into SummaryMatrix |
| EvaluationRegistry | `registry.py` | Orchestrator — loads config, wires evaluators, runs pipeline |

## Built-in Evaluators

### L1 Outcome
- **GoalSuccessRateEvaluator** — LLM judges if user goal was met

### L2 Path
- **ToolSelectionAccuracyEvaluator** — Checks tools used are valid for the agent
- **ToolSequenceValidatorEvaluator** — Validates tool call ordering against path rules

### L3 Details
- **ToolParameterAccuracyEvaluator** — Validates parameter types, formats, enums, ranges

### L4 Quality
- **CorrectnessEvaluator** — Response matches tool/API data
- **FaithfulnessEvaluator** — Response stays true to context
- **CoherenceEvaluator** — No self-contradictions
- **HelpfulnessEvaluator** — Clear, actionable responses
- **ConcisenessEvaluator** — Appropriate response length
- **ResponseRelevanceEvaluator** — Addresses user's question
- **InstructionFollowingEvaluator** — Follows system prompt
- **SystemPromptRuleEvaluator** — Per-rule compliance (3 check modes)

### L5 Safety
- **HarmfulnessEvaluator** — Detects harmful content
- **StereotypingEvaluator** — Detects bias and stereotyping
- **RefusalEvaluator** — Detects false refusals

## YAML Config Reference

See [configs/example_agent.yaml](configs/example_agent.yaml) for a complete example.

| Field | Type | Description |
|-------|------|-------------|
| `agent_name` | string | Unique agent identifier |
| `model` | string | LLM model used by the agent |
| `tools` | list[ToolDef] | Tools available to the agent |
| `paths` | list[PathRule] | Expected tool call sequences |
| `parameter_rules` | list[ParamRule] | Parameter validation rules |
| `system_prompt_rules` | list[PromptRule] | System prompt compliance rules |
| `quality_rubrics` | list[string] | Quality rubrics to apply |
| `safety_rubrics` | list[string] | Safety rubrics to apply |
| `thresholds` | dict[string, float] | Score thresholds for alerts |
| `priority_matrix` | list[PriorityEntry] | Evaluation scheduling priorities |

## Rubric Catalog

See [rubrics/README.md](rubrics/README.md) for the complete rubric catalog
with descriptions, scoring scales, and usage guidance.

## Agent Configs

| Agent | Config File | Port |
|-------|-------------|------|
| HA AI Agent | [configs/ha_ai_agent.yaml](configs/ha_ai_agent.yaml) | 8030 |
| Proactive Agent | [configs/proactive_agent.yaml](configs/proactive_agent.yaml) | 8031 |
| AI Automation | [configs/ai_automation_service.yaml](configs/ai_automation_service.yaml) | 8025 |
| AI Core | [configs/ai_core_service.yaml](configs/ai_core_service.yaml) | 8018 |

## Example Output: Summary Matrix

```
┌────────────────────────┬───────┬──────────┬────────┐
│ Evaluator              │ Score │ Threshold│ Status │
├────────────────────────┼───────┼──────────┼────────┤
│ goal_success_rate      │ 0.92  │ 0.85     │ PASS   │
│ tool_selection_accuracy│ 0.95  │ 0.90     │ PASS   │
│ tool_parameter_accuracy│ 0.88  │ 0.85     │ PASS   │
│ correctness            │ 0.94  │ 0.90     │ PASS   │
│ preview_before_execute │ 0.97  │ 0.95     │ PASS   │
│ harmfulness            │ 1.00  │ 1.00     │ PASS   │
└────────────────────────┴───────┴──────────┴────────┘
Overall: 6/6 thresholds met
```

## Inspiration

This framework is inspired by the Tango Evaluation Framework for
multi-level agent assessment. See [Patterns A-C](../README.md) for
the existing Reusable Pattern Framework (RAGContextService,
UnifiedValidationRouter, PostActionVerifier).

# Rubric Template Library

Built-in rubric catalog for the Agent Evaluation Framework (Pattern D).

Each rubric is a YAML file containing a prompt template, output labels,
score mapping, and examples. Rubrics are used by LLM-judged evaluators
to assess agent responses.

## Rubric Format

```yaml
name: rubric_name
description: What this rubric measures
prompt_template: |
  LLM judge prompt with {{ user_input }}, {{ agent_response }}, {{ tool_calls }}
output_labels: ["Label1", "Label2"]
score_mapping:
  "Label1": 1.0
  "Label2": 0.0
examples:
  - input: "Example user input"
    response: "Example agent response"
    expected_label: "Label1"
```

## Available Rubrics

### L1 Outcome

| Rubric | What it measures | Labels | Scale |
|--------|-----------------|--------|-------|
| `goal_success_rate` | Did the user achieve their goal? | Yes / Partial / No | 1.0 / 0.5 / 0.0 |

### L2 Path

| Rubric | What it measures | Labels | Scale |
|--------|-----------------|--------|-------|
| `tool_selection_accuracy` | Was the correct tool selected? | Yes / No | 1.0 / 0.0 |
| `tool_parameter_accuracy` | Were parameters extracted correctly? | Yes / No | 1.0 / 0.0 |

### L4 Quality

| Rubric | What it measures | Labels | Scale |
|--------|-----------------|--------|-------|
| `correctness` | Response matches tool/API data | Perfectly Correct / Partially Correct / Incorrect | 1.0 / 0.5 / 0.0 |
| `faithfulness` | Response stays true to context | Completely Yes → Completely No | 1.0 / 0.75 / 0.25 / 0.0 |
| `coherence` | No self-contradictions | Completely Yes → Completely No | 1.0 / 0.75 / 0.25 / 0.0 |
| `helpfulness` | Clear, actionable response | Very Helpful → Not Helpful | 1.0 / 0.66 / 0.33 / 0.0 |
| `conciseness` | Appropriate response length | Concise / Partially Concise / Not Concise | 1.0 / 0.5 / 0.0 |
| `response_relevance` | Addresses user's question | Completely Yes / Neutral/Mixed / Completely No | 1.0 / 0.5 / 0.0 |
| `instruction_following` | Follows system prompt rules | Yes / Partial / No | 1.0 / 0.5 / 0.0 |

### L5 Safety

| Rubric | What it measures | Labels | Scale |
|--------|-----------------|--------|-------|
| `harmfulness` | Contains harmful content | Not Harmful / Harmful | 1.0 / 0.0 |
| `stereotyping` | Contains bias or stereotyping | Not Stereotyping / Stereotyping | 1.0 / 0.0 |
| `refusal` | Inappropriately refused valid request | No / Yes | 1.0 / 0.0 |

## When to Use Each Rubric

- **Always include**: `goal_success_rate`, `correctness`, `harmfulness`
- **For tool-calling agents**: Add `tool_selection_accuracy`, `tool_parameter_accuracy`
- **For conversational agents**: Add `helpfulness`, `conciseness`, `response_relevance`
- **For instruction-sensitive agents**: Add `instruction_following`, `faithfulness`
- **For user-facing agents**: Add `stereotyping`, `refusal`

## Custom Rubrics

Create a new YAML file in this directory following the format above.
Register it in your agent's config under `quality_rubrics` or `safety_rubrics`.
The evaluator will automatically load the rubric from this directory.

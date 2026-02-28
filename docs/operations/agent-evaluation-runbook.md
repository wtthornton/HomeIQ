# Agent Evaluation — Operational Runbook

**Version:** 1.1
**Last Updated:** 2026-02-27
**Maintainer:** HomeIQ Platform Team

---

## Overview

The Agent Evaluation Framework continuously measures AI agent quality across a **5-level Evaluation Pyramid**: Outcome, Path, Details, Quality, and Safety. It runs scheduled evaluations, stores results in InfluxDB + PostgreSQL, surfaces scores in the health-dashboard, and alerts operators when thresholds are violated.

### SessionTracer Wiring Status (February 2026)

All 4 AI agents have `@trace_session` decorators wired:

| Agent | Endpoint | File | Status |
|-------|----------|------|--------|
| ha-ai-agent-service | POST /api/v1/chat | `domains/automation-core/ha-ai-agent-service/src/api/chat_endpoints.py` | Wired |
| proactive-agent-service | POST /trigger | `domains/energy-analytics/proactive-agent-service/src/api/suggestions.py` | Wired (2026-02-23) |
| ai-automation-service-new | POST /automation/plan | `domains/automation-core/ai-automation-service-new/src/api/automation_plan_router.py` | Wired (2026-02-23) |
| ai-core-service | POST /analyze, POST /patterns | `domains/ml-engine/ai-core-service/src/main.py` | Wired (2026-02-23) |

The decorator uses conditional imports — services still start normally if `homeiq_patterns` is not installed.

### Architecture

```
┌────────────────────────────────────┐
│  EvaluationScheduler               │  libs/homeiq-patterns/src/homeiq_patterns/evaluation/scheduler.py
│  (daily/weekly/monthly runs)       │
└────────────┬───────────────────────┘
             │ runs evaluators via
             ▼
┌────────────────────────────────────┐
│  EvaluationRegistry + Evaluators   │  libs/homeiq-patterns/src/homeiq_patterns/evaluation/registry.py
│  (13 built-in evaluators, L1-L5)   │
└────────────┬───────────────────────┘
             │ produces BatchReport
             ▼
┌────────────────────────────────────┐
│  EvaluationStore                   │  libs/homeiq-patterns/src/homeiq_patterns/evaluation/store.py
│  InfluxDB (time-series scores)     │
│  PostgreSQL   (session details)        │
└────────────┬───────────────────────┘
             │
             ▼
┌────────────────────────────────────┐
│  AlertEngine                       │  libs/homeiq-patterns/src/homeiq_patterns/evaluation/alerts.py
│  (threshold checking + lifecycle)  │
└────────────┬───────────────────────┘
             │
             ▼
┌────────────────────────────────────┐
│  data-api (8006)                   │  evaluation_endpoints.py
│  REST API for evaluation data      │
│  GET /api/v1/evaluations/*         │
└────────────┬───────────────────────┘
             │
             ▼
┌────────────────────────────────────┐
│  health-dashboard (3000)           │  Agent Evaluation tab
│  Summary Matrix + Trends + Alerts  │
└────────────────────────────────────┘
```

---

## Dashboard Guide

### Accessing the Evaluation Tab

Navigate to the health-dashboard at `http://localhost:3000` and click the **Agent Evaluation** tab (or use `#evaluation` URL hash).

### Reading the Summary Matrix

The Summary Matrix displays scores organized by evaluation level:

| Level | What It Measures | Evaluators |
|-------|-----------------|------------|
| **L1 Outcome** | Did the agent achieve the user's goal? | GoalSuccessRate |
| **L2 Path** | Did the agent use the right tools in the right order? | ToolSelectionAccuracy, ToolSequenceValidator |
| **L3 Details** | Were tool parameters correct? | ToolParameterAccuracy |
| **L4 Quality** | How good was the response? | Correctness, Faithfulness, Coherence, Helpfulness, Conciseness, ResponseRelevance, InstructionFollowing, SystemPromptRuleEvaluator |
| **L5 Safety** | Were safety guidelines followed? | Harmfulness, Stereotyping, Refusal |

**Color coding:**
- **Green** (>= threshold): Score meets or exceeds the target
- **Yellow** (within 5% of threshold): Score is close to threshold — monitor
- **Red** (< threshold): Score is below threshold — investigate

### Trend Charts

- Switch between **7d**, **30d**, and **90d** views
- Click legend items to show/hide specific evaluators
- Dashed horizontal line shows the average threshold
- Gaps in the line indicate missing data (no interpolation)

---

## Alert Response Guide

### Alert Priorities

| Priority | Criteria | Response Time |
|----------|----------|---------------|
| **Critical** | Score < 50% of threshold | Investigate within 1 hour |
| **Warning** | Score < threshold but >= 50% | Investigate within 24 hours |

### Alert Lifecycle

```
active → acknowledged → resolved
                          ↑ (auto-resolved when score recovers)
```

### Response Procedure

1. **Triage**: Check the alert priority and affected metric
2. **Investigate**: Review the Session Trace for recent sessions
3. **Acknowledge**: Click "Acknowledge" in the dashboard with a note
4. **Root cause**: Common causes:
   - Model change or degradation
   - System prompt modification
   - Tool API changes (parameters, responses)
   - Data quality issues in training/context
5. **Resolve**: Fix the root cause. Alert auto-resolves when scores recover

### API Endpoints for Alerts

```bash
# List active alerts for an agent
curl -H "X-API-Key: $KEY" http://localhost:8006/api/v1/evaluations/ha-ai-agent/alerts?status=active

# Acknowledge an alert
curl -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  http://localhost:8006/api/v1/evaluations/ha-ai-agent/alerts/{alert_id}/acknowledge \
  -d '{"by": "operator", "note": "Investigating model regression"}'
```

---

## Adding a New Agent

### Step 1: Create Agent Config

Create `libs/homeiq-patterns/src/homeiq_patterns/evaluation/configs/{agent_name}.yaml`:

```yaml
agent_name: my-new-agent
description: Description of the agent
version: "1.0"

tools:
  - name: tool_name
    parameters:
      - name: param1
        type: string
        required: true

expected_paths:
  - name: basic_path
    steps: [tool_a, tool_b]

prompt_rules:
  - name: rule_name
    pattern: "expected pattern"
    check_mode: contains

thresholds:
  goal_success_rate: 0.80
  tool_selection_accuracy: 0.75
  correctness: 0.70

priority_matrix:
  - priority: P0
    metric: goal_success_rate
    frequency: daily
  - priority: P1
    metric: correctness
    frequency: weekly
```

### Step 2: Add SessionTracer Integration

In the agent's main endpoint, add the `@trace_session` decorator:

```python
try:
    from homeiq_patterns.evaluation.session_tracer import InMemorySink, trace_session
    _eval_sink = InMemorySink()
    _TRACING_AVAILABLE = True
except ImportError:
    _TRACING_AVAILABLE = False

@(trace_session(agent_name="my-new-agent", sink=_eval_sink) if _TRACING_AVAILABLE else lambda f: f)
async def handle_request(request):
    # ... agent logic ...
    pass
```

### Step 3: Register in Scheduler

The scheduler auto-discovers configs from the `configs/` directory. For manual registration:

```python
from homeiq_patterns.evaluation.config_loader import ConfigLoader
from homeiq_patterns.evaluation.scheduler import EvaluationScheduler

config = ConfigLoader.from_yaml("libs/homeiq-patterns/src/homeiq_patterns/evaluation/configs/my_new_agent.yaml")
scheduler.register_agent(config, session_source=source)
```

### Step 4: Run Baseline Evaluation

```bash
# Via API
curl -X POST -H "X-API-Key: $KEY" \
  http://localhost:8006/api/v1/evaluations/my-new-agent/trigger

# Via CLI
python -m homeiq_patterns.evaluation.run_evaluation --agent my-new-agent
```

---

## Threshold Tuning

### When to Adjust Thresholds

- After initial baseline: Set thresholds to 90% of baseline scores
- After deploying a model upgrade: Re-run baseline and adjust upward
- If false alerts are frequent: Raise threshold slightly (5% increments)
- If degradation goes undetected: Lower threshold

### Procedure

1. Edit the agent's YAML config in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/configs/`
2. Update the `thresholds` section
3. Restart data-api to pick up changes (or wait for next scheduler cycle)
4. Monitor for 1 week to validate new thresholds

---

## Troubleshooting

### No Sessions Captured

**Symptoms:** Summary Matrix shows "No evaluation data available"
**Causes:**
- SessionTracer not wired into the agent
- Agent not receiving requests
- Session source returning empty results

**Fix:** Verify `@trace_session` decorator is applied. Check agent logs for tracer warnings.

### LLM Judge Failures

**Symptoms:** Quality/Safety evaluators return 0.0 scores consistently
**Causes:**
- LLM API key not configured
- LLM provider rate limiting
- Rubric YAML file missing or malformed

**Fix:** Check `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` environment variables. Verify rubric files exist in `libs/homeiq-patterns/src/homeiq_patterns/evaluation/rubrics/`.

### Stale Data

**Symptoms:** Dashboard shows old timestamps, trends not updating
**Causes:**
- Scheduler not running (service stopped)
- InfluxDB connection failed (degraded mode — PostgreSQL only)
- Retention cleanup too aggressive

**Fix:** Check data-api health endpoint: `GET /api/v1/evaluations/health`. Verify InfluxDB connection at `GET /health`.

### Dashboard Not Loading Evaluation Data

**Symptoms:** Evaluation tab shows loading spinner indefinitely
**Causes:**
- data-api not running or not reachable
- CORS configuration mismatch
- API key not in localStorage

**Fix:** Verify data-api is running on port 8006. Check browser console for CORS errors. Ensure API key is set in dashboard settings.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/evaluations` | List all agents with latest scores |
| GET | `/api/v1/evaluations/health` | Scheduler status |
| GET | `/api/v1/evaluations/{agent}` | Latest report for agent |
| GET | `/api/v1/evaluations/{agent}/history` | Paginated historical results |
| GET | `/api/v1/evaluations/{agent}/trends?period=7d` | Score trends |
| GET | `/api/v1/evaluations/{agent}/alerts` | Active alerts |
| POST | `/api/v1/evaluations/{agent}/trigger` | Manual evaluation run |
| POST | `/api/v1/evaluations/{agent}/alerts/{id}/acknowledge` | Acknowledge alert |

---

## Data Retention

| Store | Default Retention | Configuration |
|-------|-------------------|---------------|
| InfluxDB (time-series scores) | 90 days | `influxdb_retention_days` in EvaluationStore |
| PostgreSQL (session details) | 30 days | `postgresql_retention_days` in EvaluationStore |

Cleanup runs automatically via `store.cleanup_expired()`.

---

## Related Documentation

- [Evaluation Framework README](../../libs/homeiq-patterns/src/homeiq_patterns/evaluation/README.md)
- [Rubric Catalog](../../libs/homeiq-patterns/src/homeiq_patterns/evaluation/rubrics/README.md)
- [Agent Configs](../../libs/homeiq-patterns/src/homeiq_patterns/evaluation/configs/)
- [Baseline Reports](../../libs/homeiq-patterns/src/homeiq_patterns/evaluation/reports/)
- [Deployment Runbook](../deployment/DEPLOYMENT_RUNBOOK.md)

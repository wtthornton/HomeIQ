# ADR: Single Agent Architecture

**Status:** Accepted
**Date:** 2026-03-16
**Epic:** 66 — AI/Agent Service Classification & Architecture Documentation
**Deciders:** HomeIQ Architecture Team

---

## Context

HomeIQ has 51 deployed services, many with "AI" or "agent" in their names. However, only one service — `ha-ai-agent-service` — is a true autonomous agent (iterative LLM loop with tool calling). This was an intentional design decision, not an accident. This ADR records the rationale.

### What makes an "agent"?

A true agent has an iterative loop where:
1. The LLM receives context and decides what action to take
2. The system executes that action (tool call)
3. The result is fed back to the LLM
4. The LLM decides whether to take another action or respond to the user

`ha-ai-agent-service` implements this via `chat_endpoints.py` → `_run_openai_loop()` using OpenAI's tool-calling API with registered tools (device control, entity lookup, automation creation, etc.).

---

## Decision

**HomeIQ intentionally limits true agent behavior (T1) to a single service: `ha-ai-agent-service`.**

All other LLM-using services (T2) use single-shot prompts: one request in, one response out, no iteration.

---

## Rationale

### 1. Cost Control
Each agent iteration requires a full LLM API call. A single user request can trigger 3-8 iterations. With multiple agent services, costs would multiply unpredictably. Centralizing agent behavior to one service makes cost tracking and budgeting tractable.

### 2. Latency Predictability
Single-shot LLM calls (T2) have predictable latency: 1-3 seconds. Agent loops have unbounded latency (5-30+ seconds depending on iterations). Limiting agent behavior to the chat interface — where users expect conversational delays — keeps all other API endpoints fast and predictable.

### 3. Testability
Agent behavior is inherently non-deterministic — the LLM may choose different tool sequences for the same input. Testing one agent service is hard enough. Testing multiple agent services with cross-service tool calling would be exponentially harder. Single-shot services are far easier to test with fixed input/output pairs.

### 4. Security Surface
Agent tool calling grants the LLM the ability to take actions (control devices, create automations, query data). Each agent service would need its own tool authorization, rate limiting, and audit logging. Centralizing this in one service reduces the security surface area.

### 5. Debuggability
When an agent misbehaves, you need to trace the full tool-call chain. With one agent service, all traces flow through `automation-trace-service` via a single path. Multiple agent services would create intersecting trace graphs that are much harder to debug.

### 6. Deterministic Alternatives Work
For most services, deterministic approaches are superior:
- **YAML generation** (ai-automation-service-new): Single-shot LLM + validation is more reliable than an agent that iterates on YAML
- **Entity queries** (ai-query-service): NL→SQL translation is a single-shot mapping
- **Pattern detection** (ai-pattern-service): Classical ML models are faster and more reproducible
- **Energy forecasting**: Time-series models outperform LLMs for this task

---

## Consequences

### Positive
- Single point for cost monitoring and rate limiting
- All other services have predictable latency budgets
- Simpler testing strategy (agent tests only in one service)
- Clear security perimeter for tool-calling actions
- Easier operator training — only one service needs "agent behavior" runbooks

### Negative
- `ha-ai-agent-service` becomes a bottleneck for all agent-like features
- New features that genuinely need agent behavior must be added to this one service
- The service grows in complexity over time (mitigated by Epic 60's refactoring)

### Neutral
- Other services can still use single-shot LLM calls (T2) without being agents
- This decision does not prevent adding more T2 (LLM Wrapper) services

---

## Conditions for Revisiting

This decision should be revisited if:

1. **LLM costs drop by 10x+** — making multi-agent iteration economically viable
2. **A use case emerges that genuinely cannot be served by the central agent** — e.g., a real-time voice agent that needs sub-second tool calling
3. **The central agent service exceeds maintainability limits** — if `ha-ai-agent-service` exceeds ~5000 lines or ~20 tool definitions, consider splitting into specialized sub-agents behind a router
4. **Multi-agent frameworks mature** — if frameworks like AutoGen or CrewAI prove reliable for production use, a controlled multi-agent architecture could be reconsidered

---

## Related Documents

- [AI/Agent Service Classification](ai-agent-classification.md) — full tier classification of all 51 services
- [Service Groups](service-groups.md) — domain group architecture
- [Event Flow Architecture](event-flow-architecture.md) — data flow through the system

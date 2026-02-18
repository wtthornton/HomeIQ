# Activity Recognition — Where to Use It (System-Wide Ranking)

**Generated:** February 18, 2026  
**Purpose:** Review the entire system and all services; rank where Activity Recognition should be used, in what order, and why.

**Context:** Activity Recognition (port 8036) classifies household activity (sleeping, waking, leaving, arriving, cooking, eating, working, watching_tv, relaxing, other) from sensor sequences (motion, door, temperature, humidity, power). Today it is **not connected** to any other service. This document ranks integration points by value, fit, and dependency order.

---

## Prerequisite: Activity as Time-Series (Must Exist First)

Before any service can *use* activity, we need:

1. **Activity writer** (new component or job):  
   - Queries data-api for recent motion/door/climate/power events.  
   - Builds sensor sequences and calls activity-recognition `POST /api/v1/predict`.  
   - Writes (activity, confidence, timestamp) to **InfluxDB** (e.g. `activity_state` or `home_activity` bucket/measurement).

2. **data-api exposure:**  
   - Either a dedicated activity query endpoint, or InfluxDB queries for the activity measurement.  
   - Consumers read "current activity" and "activity history" via data-api.

**Without this, no service can consume activity.** Same pattern as weather-api → InfluxDB → data-api.

---

## Ranked Integration Points (Where to Use Activity)

Ranking criteria: **value** (user impact + product differentiation), **fit** (how naturally activity fits the service's role), **effort** (low/medium/high), **dependency** (must have prerequisite).

---

### Rank 1 — HA AI Agent (Tier 5)  
**Priority: Highest | Value: 95/100 | Effort: Low | Depends on: Prerequisite**

**Use activity for:** Tier 1 context injection. Add "Current household activity: cooking (confidence 0.85)" to the context assembled for every conversation.

**Why:** The agent is the main conversational automation surface. Activity makes suggestions context-aware without the user saying "when I'm cooking." Example: User asks "help me with my lights" → agent knows they're cooking → suggests kitchen/hood/fan automations.

**How:** Add an `ActivityContextService` (or similar) to `ContextBuilder`; fetch latest activity from data-api (with short cache, e.g. 1–2 min); inject one line into the system prompt. Same pattern as existing RAG/entity/area context.

---

### Rank 2 — Proactive Agent (Tier 5)  
**Priority: Highest | Value: 78/100 | Effort: Low | Depends on: Prerequisite**

**Use activity for:** Include current or recent activity when building context for the LLM that generates proactive suggestions.

**Why:** Proactive Agent already aggregates weather, sports, energy, patterns. Activity adds "what the household is doing" → suggestions like "you've been cooking a lot, consider exhaust automation" or "dim lights when eating."

**How:** In the suggestion-generation flow, fetch "activity in last hour" or "current activity" from data-api; add to the context string passed to OpenAI. Few prompt lines; no new pipelines.

---

### Rank 3 — Health Dashboard (Tier 1)  
**Priority: High | Value: 65/100 | Effort: Low | Depends on: Prerequisite**

**Use activity for:** Display "Current activity: Cooking (85% confidence)" with last-updated time. Optionally a small activity history chart.

**Why:** Visibility and habit awareness. Users see what the system infers they're doing; builds trust and enables future activity-based alerts or dashboards.

**How:** New data-api call for latest activity; small UI block (card or badge). No backend changes beyond data-api exposing activity.

---

### Rank 4 — ai-pattern-service (Tier 5)  
**Priority: High | Value: 62/100 | Effort: Medium | Depends on: Prerequisite**

**Use activity for:** Multi-modal context integration. The service already enhances synergies with "weather, energy, time" (per README). Add **activity** as another dimension: "synergy often occurs during cooking" or "devices used together when watching_tv."

**Why:** Richer pattern explanations ("why this suggestion") and better blueprint opportunity scoring. Blueprint fit can include "fits devices used while relaxing."

**How:** When running pattern/synergy analysis, query data-api for activity in the same time windows as events. Enrich synergy/blueprint metadata with activity labels. Requires schema and join logic.

---

### Rank 5 — energy-forecasting (Tier 3)  
**Priority: Medium | Value: 58/100 | Effort: Medium | Depends on: Prerequisite**

**Use activity for:** "Best hours for high-power activities" recommendations. Activity data tells *when* cooking, watching_tv, etc. typically happen → optimization advice like "run dishwasher when you're usually relaxing" or "avoid heavy cooking during peak rate."

**Why:** Energy forecasting already does peak prediction and optimization. Activity adds behavioral context; recommendations become personalized.

**How:** Query activity history from data-api; compute activity-by-hour patterns; feed into optimization logic or as extra features for the forecaster.

---

### Rank 6 — energy-correlator (Tier 2)  
**Priority: Medium | Value: 52/100 | Effort: Medium | Depends on: Prerequisite**

**Use activity for:** Tag correlations with "activity at time of event." E.g. "AC spike during cooking (oven)" or "power increase during watching_tv (TV + lights)."

**Why:** Enriches causality with behavioral context. Helps users understand "this power change happens when I'm cooking."

**How:** When correlating event + power, look up activity at that timestamp from data-api; add as metadata to the correlation record.

---

### Rank 7 — api-automation-edge (Tier 7)  
**Priority: Medium-Low | Value: 45/100 | Effort: Medium-High | Depends on: Prerequisite + spec schema**

**Use activity for:** Activity as an *execution condition* for automations. E.g. "run this only if activity != sleeping" or "defer if activity == leaving."

**Why:** Enables activity-aware execution policies. Reduces unwanted triggers (e.g. don't turn on lights at night if user is sleeping).

**How:** Spec schema would need an optional `activity_condition`; executor queries data-api for current activity before running. Requires design for how activity gates interact with triggers.

---

### Rank 8 — blueprint-suggestion-service (Tier 5)  
**Priority: Low | Value: 42/100 | Effort: Low-Medium | Depends on: Prerequisite**

**Use activity for:** Filter or rank blueprints by activity context. "Suggest blueprints for cooking-time" or "blueprints often used when relaxing."

**Why:** Slight improvement to blueprint relevance. Overlaps with ai-pattern-service (Blueprint Opportunity Engine) which could do this more deeply.

**How:** Pass current/recent activity to the suggestion logic; use as a soft filter or ranking signal.

---

### Rank 9 — rule-recommendation-ml (Tier 7)  
**Priority: Low | Value: 38/100 | Effort: Medium | Depends on: Prerequisite**

**Use activity for:** Optional activity-based filtering of rule recommendations. "Recommend rules for cooking" or "rules popular during watching_tv."

**Why:** ML is collaborative filtering on user-rule matrix. Activity could add a dimension, but the core algorithm doesn't depend on it.

**How:** Use activity as a filter or secondary ranking signal when serving recommendations.

---

### Rank 10 — observability-dashboard (Tier 7)  
**Priority: Low | Value: 35/100 | Effort: Low | Depends on: Prerequisite**

**Use activity for:** Show "current activity" as a metric or status indicator for debugging/observability.

**Why:** Useful for ops and dev; low user impact.

**How:** One data-api call; small UI element.

---

## Services That Should Not Use Activity (or Very Low Priority)

| Service | Reason |
|---------|--------|
| **websocket-ingestion** | Raw event capture only. Activity is derived; writing it is the activity-writer's job, not ingestion. |
| **data-api** | Exposes data; doesn't "use" activity for logic. Must expose activity *queries* as prerequisite. |
| **admin-api** | System control; no activity-based logic. |
| **device-context-classifier** | Classifies *devices* (fridge, car) from entity patterns. Activity is household-level; weak fit. |
| **device-intelligence-service** | Device capabilities and recommendations. Activity could inform "suggest devices for cooking" but overlaps with agent/proactive. Low ROI. |
| **ai-query-service** | Entity extraction from NL. Activity doesn't help extract entities; user intent ("when I'm cooking") is handled by the agent. |
| **ai-automation-service-new** | Intent planning and YAML generation. Activity flows in via the agent (which calls this); no direct integration needed. |
| **yaml-validation-service** | Schema/entity validation. No activity logic. |
| **automation-linter** | YAML linting. No activity logic. |
| **automation-miner** | Community automation mining. Activity not relevant. |
| **rag-service** | Semantic store/retrieve. Activity could be stored as metadata but doesn't change retrieval logic meaningfully. |
| **openvino-service, ml-service** | Embeddings and ML. Activity is a *consumer* of ML (activity-recognition), not a consumer of these. |
| **weather-api, sports-api, etc.** | Data sources. No activity logic. |
| **data-retention, log-aggregator, ha-setup-service** | Infrastructure. No activity logic. |

---

## Summary: Recommended Implementation Order

| Order | Component | Action | Value | Effort |
|-------|-----------|--------|-------|--------|
| **0** | Activity writer + data-api | Create writer; write activity to InfluxDB; expose via data-api | Enabler | Medium |
| **1** | HA AI Agent | Add activity to Tier 1 context injection | 95 | Low |
| **2** | Proactive Agent | Add activity to suggestion context | 78 | Low |
| **3** | Health Dashboard | Display current activity | 65 | Low |
| **4** | ai-pattern-service | Enrich synergies/blueprints with activity | 62 | Medium |
| **5** | energy-forecasting | Activity-aware optimization recommendations | 58 | Medium |
| **6** | energy-correlator | Tag correlations with activity | 52 | Medium |
| **7+** | api-automation-edge, blueprint-suggestion, rule-recommendation-ml, observability | Optional; activity as condition or filter | 35–45 | Low–Medium |

---

## Key Takeaways

1. **Prerequisite is non-negotiable:** Activity must be in InfluxDB and queryable via data-api before any consumer can use it. Same pattern as weather.

2. **Top 3 consumers (Agent, Proactive, Dashboard)** are all low-effort, high-value. Implement 1–3 in parallel once the prerequisite exists.

3. **ai-pattern-service** is the highest-value "medium effort" integration; it already has multi-modal context (weather, energy, time) and is designed for this.

4. **energy-forecasting** and **energy-correlator** benefit from activity as behavioral context; good second wave.

5. **api-automation-edge** activity conditions are powerful but require spec schema and execution logic design; defer until core integrations are proven.

6. **Skip** device-context-classifier, ai-query-service, yaml-validation, and infrastructure services; activity doesn't fit their roles.

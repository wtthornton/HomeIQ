---
epic: activity-recognition-integration
priority: high
status: planned
estimated_duration: 4-6 weeks
risk_level: low-medium
source: implementation/ACTIVITY_RECOGNITION_USAGE_RANKING.md
reviewed_by: TappsMCP (software-architecture, api-design, database, user-experience), Context7 (influxdb-client)
---

# Epic: Activity Recognition Integration

**Status:** Planned  
**Priority:** High  
**Duration:** 4–6 weeks  
**Risk Level:** Low–Medium  
**Source:** `implementation/ACTIVITY_RECOGNITION_USAGE_RANKING.md`  
**Reviewed:** TappsMCP experts (software-architecture, api-design-integration, database-data-management, user-experience); Context7 (influxdb-client)

## Overview

Integrate the Activity Recognition service (port 8036) into the HomeIQ architecture. Activity Recognition classifies household activity (sleeping, waking, leaving, arriving, cooking, eating, working, watching_tv, relaxing, other) from sensor sequences. This epic covers the first four phases of the recommended implementation order: (1) Activity writer and data-api exposure, (2) HA AI Agent + Proactive Agent + Health Dashboard, (3) ai-pattern-service enrichment, (4) energy-forecasting and energy-correlator.

## Objectives

1. Make activity a first-class time-series (write to InfluxDB, query via data-api) — same pattern as weather-api
2. Add activity context to the HA AI Agent, Proactive Agent, and Health Dashboard
3. Enrich ai-pattern-service synergies and blueprints with activity
4. Add activity-aware behavior to energy-forecasting and energy-correlator

## Non-Functional Requirements (from TappsMCP review)

- **Fault isolation:** Activity writer and consumers must degrade gracefully when activity-recognition or data-api is unavailable
- **Retry/backoff:** Use tenacity or similar for activity-recognition and InfluxDB calls; avoid cascading failures
- **Observability:** Track last successful run, write/query latency, and error counts for activity pipeline
- **API design:** RESTful resource naming, consistent error response format, versioning (`/api/v1/`)

## Risks & Mitigations (from TappsMCP software-architecture)

| Risk | Mitigation |
|------|------------|
| **Cascading failures** | All consumers degrade gracefully when activity or data-api is down; no blocking of core flows |
| **Data freshness** | Activity writer runs at configurable interval; consumers use cache TTL; Dashboard shows stale indicator |
| **Backward compatibility** | data-api adds new endpoints; existing APIs unchanged; optional activity fields in responses |
| **Single point of failure** | activity-writer and consumers are independent; InfluxDB/activity-recognition outage isolated per service |

## Testing Strategy

- **Story 1.1:** Unit tests for window building and normalization; integration test with mock activity-recognition and InfluxDB
- **Story 1.2:** Unit tests for Flux query construction; integration test for endpoints with test bucket
- **Stories 2.x, 3.x, 4.x:** Mock data-api (httpx/requests) for unit tests; integration tests with real data-api when available
- **Coverage target:** Core logic ≥80%; critical paths (graceful degradation, timeouts) explicitly tested

## Success Criteria

- [ ] Activity is written to InfluxDB periodically and queryable via data-api
- [ ] HA AI Agent injects current activity into Tier 1 context
- [ ] Proactive Agent includes activity when generating suggestions
- [ ] Health Dashboard displays current activity with confidence
- [ ] ai-pattern-service enriches synergies/blueprints with activity labels
- [ ] energy-forecasting uses activity for optimization recommendations
- [ ] energy-correlator tags correlations with activity at time of event

---

## Phase 1: Activity Writer and data-api (Prerequisite)

### Story 1.1: Activity Writer Service or Job

**As a** system integrator  
**I want** a component that periodically queries sensor events, calls activity-recognition, and writes results to InfluxDB  
**So that** activity becomes a time-series available to all consumers

**Acceptance Criteria:**
- [ ] New service or scheduled job queries data-api for recent state_changed events (motion, door, climate, power)
- [ ] Builds rolling windows of 5 features (motion, door, temp, humidity, power) per time step, normalized
- [ ] Calls activity-recognition `POST /api/v1/predict` with sequence (min 10 readings)
- [ ] Writes (activity, activity_id, confidence, timestamp) to InfluxDB using `Point` object; measurement e.g. `activity_state` or `home_activity`; tags/fields per schema
- [ ] Uses influxdb-client `WriteApi` with context manager; SYNCHRONOUS or async write per HomeIQ patterns
- [ ] Retry with backoff (tenacity) for activity-recognition and InfluxDB; configurable max attempts (e.g. 3)
- [ ] On activity-recognition timeout/unavailable: log, skip cycle, do not block; next run proceeds
- [ ] On InfluxDB write failure: retry; on persistent failure, log and expose via health/metrics
- [ ] Configurable interval (e.g. every 5–15 minutes)
- [ ] Health check or metrics: `last_successful_run`, `last_error`, `cycles_succeeded`, `cycles_failed`
- [ ] Timezone handling: timestamps in UTC (WritePrecision.NS)

**Story Points:** 5  
**Dependencies:** activity-recognition service running; data-api exposes event queries; InfluxDB  
**Affected Services:** New activity-writer (or extension of existing service)  
**References:** influxdb-client Point/WriteApi; InfluxDB connection patterns (connection pooling, error callbacks)

---

### Story 1.2: data-api Activity Query Endpoint

**As a** consumer service (HA Agent, Proactive, Dashboard, etc.)  
**I want** data-api to expose activity data (current and recent history)  
**So that** I can fetch activity without querying InfluxDB directly

**Acceptance Criteria:**
- [ ] RESTful endpoints: `GET /api/v1/activity` (current/latest) and `GET /api/v1/activity/history` (historical)
- [ ] Current: returns single object `{ activity, activity_id, confidence, timestamp }`; 404 when no data
- [ ] History: `?hours=24` (default) or `?limit=100`; pagination or bounded response for list
- [ ] Response schema consistent: activity (str), activity_id (int), confidence (float), timestamp (ISO8601)
- [ ] Uses InfluxDB bucket/measurement written by activity-writer; Flux query or query_api
- [ ] Caching: `Cache-Control` header or in-memory TTL (e.g. 1–2 min) for current activity to reduce load
- [ ] Error response: standard format (e.g. `{ detail, status_code }`); 503 when InfluxDB unavailable
- [ ] Documents response schema and query params in `docs/api/API_REFERENCE.md`

**Story Points:** 3  
**Dependencies:** Story 1.1 (activity in InfluxDB)  
**Affected Services:** data-api (8006)  
**References:** RESTful API design; contract consistency for internal consumers

---

## Phase 2: HA AI Agent, Proactive Agent, Health Dashboard

### Story 2.1: HA AI Agent — Activity in Tier 1 Context

**As a** user chatting with the AI agent  
**I want** the agent to know my current household activity (e.g. cooking, relaxing)  
**So that** it can suggest activity-aware automations without me explicitly saying "when I'm cooking"

**Acceptance Criteria:**
- [ ] New `ActivityContextService` (or equivalent) in ha-ai-agent-service; extends/registers with ContextBuilder
- [ ] Fetches latest activity from `GET /api/v1/activity` with timeout (e.g. 5s)
- [ ] Caches briefly (e.g. 1–2 min) to avoid per-message latency; cache key per home if multi-home
- [ ] Injects one line into system prompt: e.g. "Current household activity: cooking (confidence 0.85)"
- [ ] Registered in ContextBuilder; included when building context
- [ ] **Graceful degradation:** On timeout, 404, or 503: omit activity line or use "Activity unavailable"; agent continues without activity
- [ ] No blocking of conversation flow when data-api or activity is down (fault isolation)
- [ ] Unit test for context injection; mock for data-api unavailable

**Story Points:** 3  
**Dependencies:** Story 1.2 (data-api activity endpoint)  
**Affected Services:** ha-ai-agent-service (8030)

---

### Story 2.2: Proactive Agent — Activity in Suggestion Context

**As a** user receiving proactive automation suggestions  
**I want** suggestions to consider my recent activity (e.g. cooking, eating)  
**So that** suggestions are relevant to what I'm actually doing

**Acceptance Criteria:**
- [ ] Proactive Agent fetches current activity and/or history (`GET /api/v1/activity`, `GET /api/v1/activity/history?hours=1`) from data-api
- [ ] Adds activity context to the prompt passed to OpenAI for suggestion generation
- [ ] Example prompt addition: "The household has been in 'cooking' and 'eating' recently; consider suggesting automations that improve kitchen or mealtime comfort"
- [ ] **Graceful degradation:** On fetch failure or empty: omit activity from context; suggestion generation proceeds without it
- [ ] Timeout on data-api call (e.g. 5s) to avoid blocking scheduler
- [ ] Unit or integration test for context assembly with and without activity

**Story Points:** 2  
**Dependencies:** Story 1.2 (data-api activity endpoint)  
**Affected Services:** proactive-agent-service (8031)

---

### Story 2.3: Health Dashboard — Display Current Activity

**As a** user viewing the Health Dashboard  
**I want** to see the current household activity (e.g. "Cooking – 85% confidence")  
**So that** I have visibility into what the system infers and can trust activity-based features

**Acceptance Criteria:**
- [ ] Dashboard calls data-api `GET /api/v1/activity` for latest activity
- [ ] Displays activity name and confidence (e.g. card or badge); confidence as percentage or visual indicator
- [ ] Shows last-updated timestamp (visibility of system status per usability heuristics)
- [ ] **Loading state:** Skeleton or spinner while fetching; no flash of stale content
- [ ] **Error state:** Clear message when data-api/activity unavailable; recovery option (e.g. retry) or fallback (e.g. "Activity unavailable")
- [ ] **Stale data:** If last-updated > N minutes (e.g. 10), show subtle indicator (e.g. "Data may be stale")
- [ ] Polling interval configurable (e.g. 1–2 min) or manual refresh
- [ ] Optional: short activity history (last N readings) as small chart or list

**Story Points:** 3  
**Dependencies:** Story 1.2 (data-api activity endpoint)  
**Affected Services:** health-dashboard (3000)  
**References:** UX heuristics (visibility of system status, loading/error feedback)

---

## Phase 3: ai-pattern-service Activity Enrichment

### Story 3.1: ai-pattern-service — Enrich Synergies and Blueprints with Activity

**As a** user viewing synergy or blueprint recommendations  
**I want** to see when patterns occur (e.g. "often during cooking" or "correlated with watching_tv")  
**So that** I understand why a suggestion is relevant

**Acceptance Criteria:**
- [ ] When ai-pattern-service runs pattern/synergy analysis, query data-api for activity in the **same time windows** as events (`GET /api/v1/activity/history?start=...&end=...` or `hours=24`)
- [ ] Enrich synergy metadata with activity labels (e.g. `activity_context: ["cooking", "eating"]`)
- [ ] Blueprint opportunity engine can use activity as a scoring/ranking signal (e.g. "fits devices used while relaxing")
- [ ] XAI explanations optionally include activity context
- [ ] **Graceful degradation:** Missing activity or data-api failure: proceed without activity dimension; pattern analysis continues
- [ ] Timeout on data-api call to avoid blocking pattern pipeline
- [ ] Unit or integration test for enrichment logic (with data, without data, on failure)

**Story Points:** 5  
**Dependencies:** Story 1.2 (data-api activity endpoint); activity history query for time windows  
**Affected Services:** ai-pattern-service (8020)

---

## Phase 4: energy-forecasting and energy-correlator

### Story 4.1: energy-forecasting — Activity-Aware Optimization

**As a** user seeking energy optimization advice  
**I want** recommendations that consider when I typically cook, watch TV, etc.  
**So that** advice is personalized (e.g. "run dishwasher when you're usually relaxing")

**Acceptance Criteria:**
- [ ] energy-forecasting queries activity history from data-api (`GET /api/v1/activity/history`)
- [ ] Computes activity-by-hour patterns (when cooking, watching_tv, etc. typically occur)
- [ ] Uses activity patterns in optimization logic (e.g. "best hours for high-power activities")
- [ ] API response (e.g. `/api/v1/optimization`) optionally includes activity-based guidance
- [ ] **Graceful degradation:** Insufficient activity or data-api failure: fall back to time-only optimization; do not fail forecast
- [ ] **Observability:** Log/metric when activity is used vs not used (e.g. `activity_enabled: true|false` in response metadata)
- [ ] Timeout on activity fetch to avoid blocking optimization pipeline
- [ ] Unit or integration test

**Story Points:** 5  
**Dependencies:** Story 1.2 (data-api activity endpoint); activity history for pattern computation  
**Affected Services:** energy-forecasting (8037)

---

### Story 4.2: energy-correlator — Tag Correlations with Activity

**As a** user reviewing energy-event correlations  
**I want** to see what activity was happening when a power change occurred  
**So that** I better understand causality (e.g. "AC spike during cooking — likely oven")

**Acceptance Criteria:**
- [ ] When energy-correlator correlates an event with power change, look up activity at that timestamp from data-api (`GET /api/v1/activity` or history for overlapping time range)
- [ ] Add activity as metadata to the correlation record (e.g. `activity_at_event: "cooking"`)
- [ ] Correlation output (InfluxDB or API) includes activity when available; indicate `activity_available: true|false` for transparency
- [ ] **Graceful degradation:** Missing activity or data-api failure: proceed without activity tag; correlation continues
- [ ] Timeout on data-api call to avoid blocking correlation job
- [ ] Unit or integration test (with synthetic activity + energy data)

**Story Points:** 3  
**Dependencies:** Story 1.2 (data-api activity endpoint); activity history for timestamp lookup  
**Affected Services:** energy-correlator (8017)

---

## Dependencies Between Phases

```
Phase 1 (1.1, 1.2) ─────────────────────────────────────┐
    │                                                    │
    ▼                                                    │
Phase 2 (2.1, 2.2, 2.3)  ← can run in parallel          │
    │                                                    │
    ▼                                                    │
Phase 3 (3.1)                                            │
    │                                                    │
    ▼                                                    │
Phase 4 (4.1, 4.2)  ← can run in parallel               │
```

**Total Story Points:** 29

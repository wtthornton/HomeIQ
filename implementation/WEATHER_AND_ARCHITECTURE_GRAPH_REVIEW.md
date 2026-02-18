# Weather Service, Short/Medium/Long-Term “Graph,” and What’s Connected

**Generated:** February 18, 2026  
**Purpose:** Confirm (1) whether we have a service that reads weather and adds it to time series, (2) what the “short / medium / long term graph” is and what “connected” means, (3) what’s true vs outdated, and (4) how activity recognition fits.

---

## 1. Weather → time series: **Yes, that’s true**

We **do** have a service that reads weather and adds it to the time series.

| Item | Detail |
|------|--------|
| **Service** | **weather-api** (port 8009) |
| **What it does** | Fetches current weather from **OpenWeatherMap**, caches for 15 minutes, and **writes directly to InfluxDB** (Epic 31 pattern). |
| **InfluxDB** | Uses its own bucket: **`weather_data`** (configurable via `INFLUXDB_BUCKET`). So weather is time-series, but in a separate bucket from `home_assistant_events`. |
| **Consumers** | Anything that needs weather (e.g. proactive-agent, automations) can get it via **data-api** (if data-api exposes weather queries) or by querying InfluxDB. websocket-ingestion also has a 15‑minute weather cache for inline enrichment. |

So: **weather is read from an external API and stored as time-series in InfluxDB**; the architecture is “standalone service → InfluxDB → query via data-api/dashboards.” Activity recognition can follow the **same pattern** (standalone writer → InfluxDB → data-api).

---

## 2. What “short / medium / long term” and “connected” refer to

There isn’t a single doc titled “short, medium, long term graph.” There are **three** different “graph” / “connected” views in the repo; they mean different things.

### A. InfluxDB schema: short / medium / long term **data** (time horizons)

**Where:** `docs/architecture/influxdb-schema.md`

**What it is:** Storage layers by **retention and aggregation**, i.e. time horizon of the *data*:

| Layer | Content | Retention | Role |
|-------|---------|-----------|------|
| **Layer 1** | Raw events (e.g. state_changed) | 7 days | **Short-term**: hot, detailed data |
| **Layer 2** | Daily aggregates | 90 days | **Medium-term**: daily rollups |
| **Layer 3** | Weekly/monthly aggregates | 52 weeks | **Long-term**: trends, seasonal |

So “short / medium / long term” in the **schema** = **data lifecycle**, not “which services are connected.” Weather (and, once added, activity) would typically land in a **raw/short-term** measurement first; aggregates could feed Layer 2/3 if we add them.

### B. Tier 1–7 map: what’s **critical** vs optional (“connected” = dependency chain)

**Where:** `services/SERVICES_RANKED_BY_IMPORTANCE.md`

**What it is:** A **criticality** ranking and dependency picture:

- **Tier 1:** Mission-critical (websocket-ingestion, data-api, InfluxDB, admin-api, health-dashboard).
- **Tier 2:** Essential data (data-retention, ha-setup-service, **weather-api**, smart-meter, energy-correlator).
- **Tier 3:** AI/ML core (ai-core-service, device-intelligence, openvino, ml-service, energy-forecasting).
- **Tiers 4–7:** Enhanced data, AI features, device management, specialized (e.g. **activity-recognition** is **Tier 6**).

The **Service Dependency Map** in that file is a **vertical stack**: Tier 1 at top, then Tier 2, then Tier 3, then “Tier 4–7” together. “Connected” here means **layers of dependency**: lower tiers depend on Tier 1 (and often Tier 2); they don’t mean “short/medium/long” in time.

So: **short/medium/long in this doc = importance/criticality**, not time. The **graph** = tiered dependency view (what depends on what), not a literal short/med/long *time* graph.

### C. Automation-flow dependency map (PRD): what talks to what in the automation path

**Where:** `docs/planning/automation-architecture-reusable-patterns-prd.md` — **Appendix 7: Service Dependency Map**

**What it is:** A **flow** for automation creation:

- HA AI Agent (ContextBuilder, RAG, PromptAssembly) → ai-automation-service-new (validate, deploy, verifiers) → yaml-validation-service, HA Client, ai-automation-ui → Home Assistant.

So “connected” here = **who calls whom in the automation pipeline**. Weather and activity are **not** in this map; they would be **data sources** (like Tier 2 weather-api) that feed context into the agent or other services once wired.

---

## 3. What’s true vs what’s off

| Claim / Doc | Status | Note |
|-------------|--------|------|
| Weather service reads external API and writes to time series | **True** | weather-api → OpenWeatherMap → InfluxDB bucket `weather_data`. |
| InfluxDB has short/medium/long term *data* layers | **True** | Layer 1 (7d) / Layer 2 (90d) / Layer 3 (52w) in influxdb-schema.md. |
| Tier 1–7 = “what’s connected” (dependency/criticality) | **True** | SERVICES_RANKED_BY_IMPORTANCE.md; “connected” = dependency stack, not time. |
| PRD Appendix 7 = automation-flow “connected” | **True** | Automation path only; no weather/activity in that diagram. |
| Single “short / medium / long term graph” doc | **Not found** | We have (a) schema layers = time horizons, (b) tier map = criticality/deps, (c) PRD map = automation flow. |
| Port table in SERVICES_RANKED_BY_IMPORTANCE | **Some errors** | e.g. Tier 5 lists many services as 8024; 8037 shown for both energy-forecasting and yaml-validation-service. Use docker-compose and READMEs for authoritative ports. |
| activity-recognition “connected” today | **False** | Tier 6, no other service calls it in the codebase; once we write activity to InfluxDB and query via data-api, it becomes “connected” like weather. |

---

## 4. How activity recognition fits

- **Same pattern as weather:**  
  - **Weather:** weather-api (external API) → InfluxDB (`weather_data`) → data-api / dashboards.  
  - **Activity (proposed):** activity-writer (data-api for sensor events → activity-recognition for inference) → InfluxDB (e.g. `activity_state` or same bucket) → data-api / dashboards / agent / proactive.

- **In the “graph” views:**  
  - **InfluxDB layers:** Activity would start as **short-term** (Layer 1–style) raw activity predictions; optional aggregates could feed medium/long-term later.  
  - **Tier map:** Today activity-recognition is **Tier 6**, **not connected**. Once we add the writer and InfluxDB, it behaves like a **Tier 2–style data enricher** (like weather-api): writes time-series, others read via data-api. We could then show it in the dependency map as “activity data” feeding Tier 3/5 services (e.g. agent, proactive, dashboard).  
  - **PRD automation map:** Activity would not replace any box; it would be an **extra context input** to HA AI Agent (and optionally proactive-agent), similar to how weather is used.

So: **weather is already “connected” as a time-series enricher; activity recognition fits the same way once we add the writer and wire consumers (agent, dashboard, proactive, etc.).**

---

## 5. One-page cheat sheet

| Question | Answer |
|----------|--------|
| Do we have a service that reads weather and adds it to time series? | **Yes.** weather-api (8009) → OpenWeatherMap → InfluxDB bucket `weather_data`. |
| Where is the “short / medium / long term graph”? | **Two different things:** (1) **Data:** InfluxDB Layer 1/2/3 in `influxdb-schema.md` (short/med/long *retention*). (2) **Services:** Tier 1–7 in `SERVICES_RANKED_BY_IMPORTANCE.md` (criticality/dependency stack). |
| What does “connected” mean? | **Tier map:** “Connected” = in the dependency chain (Tier 1 → 2 → 3 → …). **PRD:** “Connected” = in the automation flow (Agent → ai-automation-service-new → HA, etc.). |
| Is the tier/dependency picture accurate? | **Mostly.** Port table in that doc has some wrong/duplicate ports; treat docker-compose + service READMEs as source of truth. |
| Is activity recognition connected? | **Not yet.** No caller in codebase. Becomes “connected” like weather when we add an activity→InfluxDB writer and data-api + consumers. |
| How does activity fit? | Same as weather: **standalone writer → InfluxDB → data-api**; then agent/proactive/dashboard use it. Fits short-term data layer and Tier 2–style enricher in the dependency view. |

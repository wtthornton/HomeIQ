# 5 Ideas to Integrate Activity Recognition into the Existing Architecture

**Generated:** February 18, 2026  
**Context:** Activity Recognition (port 8036) classifies household activity from sensor sequences (motion, door, temperature, humidity, power). Events today flow: HA → websocket-ingestion → InfluxDB; data-api queries events. Epic 31: no enrichment-pipeline; standalone services write to InfluxDB and/or are queried via data-api.

---

## Idea 1: Activity as a time-series (write to InfluxDB, query via data-api)

**What:** A small **activity-writer** service (or scheduled job inside an existing service) that periodically:
1. Queries **data-api** for recent state_changed events (e.g. last 5–15 minutes) for motion, door, climate, and power entities.
2. Builds rolling windows of 5 features (motion, door, temp, humidity, power) per time step, normalized per your schema.
3. Calls **activity-recognition** `POST /api/v1/predict` with that sequence.
4. Writes the result (activity name, activity_id, confidence, timestamp) to **InfluxDB** in a dedicated measurement (e.g. `activity_state` or `home_activity`).

**Why it fits:** Same pattern as weather-api / sports-api: standalone service, writes to InfluxDB, consumers read via data-api. No change to websocket-ingestion. Dashboards and other services get “current activity” and history by querying data-api.

**Value:** Single source of truth for activity over time; enables all other ideas (dashboard, agent context, automations) without each consumer calling activity-recognition directly.

**Effort:** Medium. New minimal service or a cron-style path in an existing service; data-api client; InfluxDB write client; mapping from HA entity domains to the 5 inputs (motion/door/temp/humidity/power).

---

## Idea 2: Current activity in HA AI Agent context (Tier 1 injection)

**What:** Add **current activity** to the Tier 1 context that the HA AI Agent injects into every conversation (alongside entity inventory, areas, services, capabilities). The agent already has a context builder and caches; add one more component that:
1. Reads “latest activity” from **data-api** (if Idea 1 is in place) or, in a first version, calls **activity-recognition** with a sequence built from a recent data-api query.
2. Injects a short line into the system prompt, e.g. “Current household activity: cooking (confidence 0.85).”

**Why it fits:** Purely additive to ha-ai-agent-service; no change to event flow. The agent can then suggest or generate automations that are activity-aware (“when I’m cooking, turn on the hood fan”).

**Value:** High. Makes the main conversational automation experience context-aware without the user having to say “when I’m cooking.”

**Effort:** Low if Idea 1 exists (one data-api call). Medium if you build the sequence and call activity-recognition from the agent (and cache to avoid per-message latency).

---

## Idea 3: Activity-aware proactive suggestions (Proactive Agent)

**What:** Have the **proactive-agent-service** (or its scheduler) include **current or recent activity** when it generates suggestions. For example:
1. When building context for the LLM (weather, sports, energy, patterns), also fetch “current activity” or “activity in the last hour” from data-api (Idea 1).
2. Add to the prompt: “The household has been in ‘cooking’ and ‘eating’ recently; consider suggesting automations that improve kitchen or mealtime comfort.”

**Why it fits:** Proactive Agent already aggregates multiple context sources and calls OpenAI; activity is just another context signal. No new event pipeline.

**Value:** Suggestions become time- and activity-relevant (e.g. “dim lights when eating,” “turn on exhaust when cooking”).

**Effort:** Low once activity is in InfluxDB and queryable via data-api; add one context fetch and a few prompt lines.

---

## Idea 4: Activity on the Health Dashboard (and optional triggers)

**What:** 
1. **Display:** Health Dashboard calls **data-api** for the latest activity (and optionally a short history). Show “Current activity: Cooking” with confidence and last-updated time.
2. **Optional:** If you later add simple “triggers” or “notifications” (e.g. “notify when activity changes to ‘leaving’”), the dashboard or a small backend can evaluate rules against the activity series from data-api.

**Why it fits:** Dashboard already uses data-api for events and metrics; activity is just another time-series. No new services in the event path.

**Value:** Visibility and habit/pattern awareness; foundation for future activity-based alerts or automations.

**Effort:** Low for read-only display (one new data-api query + a small UI block). Higher if you add trigger/alert logic.

---

## Idea 5: Activity-based synergy and pattern enrichment (ai-pattern-service)

**What:** Use activity as an **extra dimension** in pattern and synergy logic:
1. When **ai-pattern-service** runs scheduled pattern/synergy analysis, optionally query **data-api** for activity in the same time windows as the events it analyzes.
2. Enrich synergies or patterns with “often occurs during cooking” or “correlated with ‘watching_tv’.” Use this for blueprint opportunity scoring (e.g. “this blueprint fits devices often used while relaxing”) or for explainable-AI lines in the UI.

**Why it fits:** ai-pattern-service already runs on a schedule and uses event/time data; activity is another attribute of the same time range. Fits Epic 31: read from data-api (and thus InfluxDB), no new write path.

**Value:** Richer pattern explanations and better blueprint matching; differentiator for “why this suggestion.”

**Effort:** Medium. Requires activity in InfluxDB (Idea 1), then schema and query design to join event windows with activity, and wiring in the pattern/synergy/blueprint code.

---

## Summary and dependency order

| Idea | Summary | Depends on | Effort |
|------|--------|------------|--------|
| **1** | Write activity to InfluxDB; query via data-api | — | Medium |
| **2** | Inject current activity into HA AI Agent context | 1 (recommended) | Low |
| **3** | Use activity in Proactive Agent suggestions | 1 | Low |
| **4** | Show activity on Health Dashboard (and optional triggers) | 1 | Low |
| **5** | Enrich pattern/synergy/blueprint with activity | 1 | Medium |

**Recommended order:** Implement **Idea 1** first so activity is a first-class time-series like weather or sports. Then add **2, 3, and 4** in parallel (all read from data-api). Add **5** when you want pattern/blueprint explanations to be activity-aware.

All five ideas keep the existing architecture: no new service in the HA → websocket-ingestion → InfluxDB path; activity is either produced by a standalone writer (Idea 1) or consumed from data-api by existing services.

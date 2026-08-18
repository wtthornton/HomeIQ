# HomeIQ MCP Tool Catalogue (TAP-5292)

**Status:** v1 contract — the schema source of truth for the `homeiq` MCP server
(TAP-5293..5297), the AgentForge genes that declare it, and the Home Assistant
integration. Changing a shape here is a contract change: bump `catalogue_version`
and update the contract tests (TAP-5297) in the same commit.

**catalogue_version:** 1.2.3

**v1.2.3 changes (2026-08-18):** `trace_automation` carries an honesty caveat —
ingestion stores `context_id` but not `context_parent_id`, so chains resolve
empty on live data until TAP-6107 lands. `list_entities` rows carry the
effective area.

**v1.2.2 changes (2026-08-18, verifier round 2):** `trace_automation.chain`
`maxItems` 100 (`max_depth` bounds levels; upstream emits up to 100 events per
level; the 16 KB budget bounds size). `get_entity_history` drops the never-emitted
`points[].value`. `list_areas` / `list_entities(area_id)` use the effective area
(entity area, else its device's — HA leaves inherited entity areas null; before
this, both answered empty for every area). `list_synergies.area` is applied after
the upstream limit.

**v1.2.1 changes (2026-08-18, verifier round):** id inputs that reach an upstream URL
path (`device_id`, `automation_id`, `context_id`, `entity_id`) carry a strict
charset `pattern` and the server percent-encodes them (a `../` id must never steer
the server's authenticated request). `detect_anomalies` drops `hours` (neither
backing honours a window). `search_events.hours` max is 72 (data-api's search
times out beyond that). `downsample_minutes` is first-observed-per-bucket, not
a mean. Error code set drops the unused `truncated_upstream`. `kind=power`
anomalies and `get_energy_summary.top_consumers` are empty until TAP-5301
provides the energy-correlator data they read.

**v1.2.0 changes (2026-08-17, TAP-5293/TAP-5295):** tools 14 `get_energy_correlations`
and 15 `get_device_energy_impact` are `status: deferred` (owner Decision E —
their backing `energy-correlator` has never written a correlation, TAP-5910; the
server does not register deferred tools; they return when TAP-5301 provides a
live power-delta source). Every list-returning output schema now declares
optional `truncated` + `hint`, so the server can honour design rule 2 under
`additionalProperties: false`. Error code set gains `contract_violation` (see
server-level notes).

**Normative schemas:** `docs/mcp/homeiq-mcp-tools.schema.json` — every tool's
full JSON Schema (draft 2020-12, metaschema-validated) lives there; this
document is the human-readable view and shows abbreviated shapes for most
tools. On any divergence, the JSON file wins.

## Design rules (bind every tool below)

1. **Read-only v1.** Every v1 tool carries the MCP standard annotation
   `readOnlyHint: true`. There are ZERO mutating tools in v1. A future mutating
   tool must (a) carry `readOnlyHint: false` plus `destructiveHint` as
   appropriate, (b) be disabled unless the server is started with
   `HOMEIQ_MCP_ALLOW_WRITES=<comma-separated tool names>` — the explicit grant
   the epic requires. The grant is per-tool, never a blanket flag.
2. **Summaries, not series.** Analytics tools return aggregates. Only the two
   history tools return row-level data, and both are hard-capped. Every tool
   declares `max_response_bytes`; the server truncates at the cap and sets
   `"truncated": true` plus a `"hint"` naming the narrowing parameter — agent
   context is the scarce resource this protects. Both fields are declared on
   every list-returning output schema (v1.2.0); `hint` is present only when
   `truncated` is true.
3. **Typed schemas, no free-form URLs.** Inputs and outputs are JSON Schema
   (draft 2020-12). No tool accepts a path, URL, or Flux/SQL fragment.
4. **Time is explicit.** Range inputs are `hours` (integer, bounded) or RFC3339
   `start_time`/`end_time` pairs — never server-implicit "recent".
5. **Names are `verb_noun`, stable, and lowercase** — they become gene-visible
   API the day they ship.

## Backing services

| Backing | Transport | Used by |
|---|---|---|
| data-api (`:8006` internal) | HTTP, existing endpoints unchanged | history, events, devices, entities, areas, automations, energy, carbon |
| ai-pattern-service | HTTP | patterns, synergies |
| device-intelligence-service | HTTP | health scores, failure predictions |
| InfluxDB (via data-api only) | — | the MCP server never queries InfluxDB directly |

Backing paths below are FULL mount paths (data-api mounts its Events, Energy
and Automation-Analytics routers under `/api/v1` — `_app_setup.py:106-138`;
decorator strings alone 404).

State fields are PROJECTIONS: data-api stores `old_state`/`new_state` as
dicts; the MCP server extracts the `state` key into the bounded strings these
schemas declare (implementation note for TAP-5294).

The MCP server is a thin schema-enforcing facade; it owns no data. The
data-api HTTP surface keeps serving the health dashboard unchanged (epic
acceptance), and capability retirement (Wave 11) later re-points backings
without changing these contracts.

---

## Tool catalogue — 17 tools (15 active, 2 deferred in v1.2.0)

### Group 1 — Entity history & events (data-api)

#### 1. `get_entity_history`
Entity state history over a bounded window, optionally downsampled. Time precedence: `start_time`/`end_time` (dependent pair) override `hours`.
- **Backing:** data-api `POST /mcp/tools/query_device_history` + `GET /api/v1/events`
- **Annotations:** `readOnlyHint: true` · **Budget:** 64 KB / 500 points
- **Input:**
```json
{"type": "object", "additionalProperties": false,
 "properties": {
   "entity_id": {"type": "string", "description": "HA entity id, e.g. sensor.total_power"},
   "hours": {"type": "integer", "minimum": 1, "maximum": 720, "default": 24},
   "start_time": {"type": "string", "format": "date-time"},
   "end_time": {"type": "string", "format": "date-time"},
   "downsample_minutes": {"type": "integer", "minimum": 0, "maximum": 1440, "default": 0,
     "description": "0 = raw rows (capped); N = first observed point per N-minute bucket"},
   "limit": {"type": "integer", "minimum": 1, "maximum": 500, "default": 500}},
 "required": ["entity_id"]}
```
- **Output:**
```json
{"type": "object", "additionalProperties": false,
 "properties": {
   "entity_id": {"type": "string"},
   "points": {"type": "array", "items": {"type": "object", "additionalProperties": false,
     "properties": {"t": {"type": "string", "format": "date-time"},
                    "state": {"type": "string"},
                    "value": {"type": ["number", "null"]}},
     "required": ["t", "state"]}},
   "count": {"type": "integer"}, "truncated": {"type": "boolean"},
   "hint": {"type": "string"}},
 "required": ["entity_id", "points", "count", "truncated"]}
```

#### 2. `search_events`
Text search over stored HA events (entity ids and event types).
- **Backing:** data-api `POST /api/v1/events/search` (TAP-5997 hardened path)
- **Annotations:** `readOnlyHint: true` · **Budget:** 32 KB / 200 events
- **Input:** `{query: string (1..200 chars, required), hours: int 1..72 = 24, limit: int 1..200 = 50}`
- **Output:** `{events: [{t, entity_id, event_type, old_state?, new_state?}], count, truncated}`

#### 3. `get_recent_events`
Filtered recent events (entity, type, device, area, category, window).
- **Backing:** data-api `GET /api/v1/events`
- **Annotations:** `readOnlyHint: true` · **Budget:** 32 KB / 200 events
- **Input:** `{entity_id?, event_type?, device_id?, area_id?, hours: int 1..168 = 1, limit: int 1..200 = 50, offset: int >= 0 = 0}`
- **Output:** same event row shape as `search_events`, plus `offset`.

#### 4. `trace_automation`
Follow a context-id chain to see what triggered what.
- **Backing:** data-api `GET /api/v1/events/automation-trace/{context_id}`
- **Annotations:** `readOnlyHint: true` · **Budget:** 16 KB / depth 10
- **Input:** `{context_id: string (required), max_depth: int 1..10 = 5}`
- **Output:** `{chain: [{depth, context_id, t, entity_id, event_type, state?}], count, truncated}`

### Group 2 — Devices, entities, areas (data-api)

#### 5. `list_devices`
Device inventory with filters; summary rows only.
- **Backing:** data-api `GET /api/devices`
- **Annotations:** `readOnlyHint: true` · **Budget:** 48 KB / 300 rows
- **Input:** `{manufacturer?, model?, area_id?, platform?, device_category?, limit: int 1..300 = 100}`
- **Output:** `{devices: [{device_id, name, manufacturer?, model?, area_id?, integration?, entity_count}], count, truncated}`

#### 6. `get_device`
One device in full: metadata, entities, labels.
- **Backing:** data-api `GET /api/devices/{id}` + `/api/entities/by-device/{id}`
- **Annotations:** `readOnlyHint: true` · **Budget:** 24 KB
- **Input:** `{device_id: string (required)}`
- **Output:** `{device: {device_id, name, manufacturer?, model?, sw_version?, area_id?, integration?, labels?: [string]}, entities: [{entity_id, domain, device_class?, disabled}], entity_count}`

#### 7. `list_entities`
Entity registry with filters (domain, area, device, label).
- **Backing:** data-api `GET /api/entities`
- **Annotations:** `readOnlyHint: true` · **Budget:** 48 KB / 500 rows
- **Input:** `{domain?, area_id?, device_id?, label?, limit: int 1..500 = 200}`
- **Output:** `{entities: [{entity_id, domain, device_id?, area_id?, friendly_name?, device_class?, disabled}], count, truncated}`

#### 8. `list_areas`
Areas with entity counts and domains present.
- **Backing:** data-api `GET /api/areas`
- **Annotations:** `readOnlyHint: true` · **Budget:** 8 KB
- **Input:** `{}` (no parameters)
- **Output:** `{areas: [{area_id, name, entity_count, domains: [string]}], count}`

#### 9. `get_entity_state`
Last OBSERVED state of one entity, with its timestamp.
- **Backing:** data-api `GET /api/v1/events?entity_id=...&limit=1` (latest stored event)
- **Annotations:** `readOnlyHint: true` · **Budget:** 4 KB
- **Input:** `{entity_id: string (required), hours: int 1..8760 = 24}`
- **Output:** `{entity_id, state: string|null, t: date-time|null, source: "last_observed_event"}`
- Note: HomeIQ observes HA through the event store — this is the most recent
  *recorded* state change, not a live HA read; agents must check `t` for
  staleness. A live read belongs to HA's own MCP integration, not this server.

#### 10. `get_automation_stats`
Automation execution analytics: overview, per-automation detail, or problem list.
- **Backing:** data-api `GET /api/v1/automations`, `/api/v1/automations/stats/overview`, `/api/v1/automations/stats/{errors,slow,inactive}`, `/api/v1/automations/{id}`
- **Annotations:** `readOnlyHint: true` · **Budget:** 24 KB / 100 rows
- **Input:** `{automation_id?: string, view: enum["overview","list","errors","slow","inactive"] = "overview", limit: int 1..100 = 25}`
- **Output:** `{view, overview?: {total_automations, total_executions, error_rate_percent, avg_success_rate}, automations?: [{automation_id, alias, enabled, total_executions, success_rate, avg_duration_seconds, total_errors, last_triggered?}], count?, truncated}`

### Group 3 — Pattern detection (ai-pattern-service)

#### 11. `list_patterns`
Detected behavioral patterns with confidence filters; stats rollup included.
- **Backing:** `GET /api/v1/patterns/list` + `/api/v1/patterns/stats`
- **Annotations:** `readOnlyHint: true` · **Budget:** 32 KB / 100 rows
- **Input:** `{pattern_type?, device_id?, min_confidence: number 0..1 = 0.5, limit: int 1..100 = 50}`
- **Output:** `{patterns: [{id, pattern_type, device_id?, confidence, occurrences, summary}], stats: {total_patterns, by_type: object, avg_confidence, unique_devices}, count, truncated}`
- Note: `summary` is a server-built one-liner from pattern metadata — raw
  metadata blobs stay out of agent context.

#### 12. `list_synergies`
Cross-device automation opportunities (rule-based graph analysis).
- **Backing:** `GET /api/v1/synergies/list` + `/statistics`
- **Annotations:** `readOnlyHint: true` · **Budget:** 32 KB / 50 rows
- **Input:** `{synergy_type?, min_confidence: number 0..1 = 0.5, area?, limit: int 1..50 = 20}`
- **Output:** `{synergies: [{synergy_id, synergy_type, devices: [string], area?, impact_score, confidence, complexity, explanation}], stats: {total_synergies, avg_impact_score, avg_confidence}, count, truncated}`

### Group 4 — Energy (data-api, fed by energy-correlator)

#### 13. `get_energy_summary`
Whole-home energy snapshot: current, daily, peak, top consumers.
- **Backing:** data-api `GET /api/v1/energy/statistics` + `/api/v1/energy/top-consumers` + `/api/v1/energy/carbon-intensity/current`
- **Annotations:** `readOnlyHint: true` · **Budget:** 16 KB / 20 consumers
- **Input:** `{top_n: int 1..20 = 10}`
- **Output:** `{current_power_w, daily_kwh, peak_power_w, peak_time?, average_power_w, top_consumers: [{entity_id, average_power_on_w, estimated_daily_kwh}], carbon?: {grams_per_kwh, source}}`

#### 14. `get_energy_correlations` — **DEFERRED (v1.2.0, Decision E)**
State-change ↔ power-delta correlations (the energy-correlator's output).
- **Backing:** data-api `GET /api/v1/energy/correlations`
- **Annotations:** `readOnlyHint: true` · **Budget:** 32 KB / 200 rows
- **Input:** `{entity_id?, domain?, hours: int 1..168 = 24, min_delta_w: number >= 0 = 5, limit: int 1..200 = 100}`
- **Output:** `{correlations: [{t, entity_id, domain, state, previous_state?, power_delta_w, power_delta_pct?}], count, truncated}`

#### 15. `get_device_energy_impact` — **DEFERRED (v1.2.0, Decision E)**
Per-device consumption estimate derived from correlations.
- **Backing:** data-api `GET /api/v1/energy/device-impact/{entity_id}`
- **Annotations:** `readOnlyHint: true` · **Budget:** 4 KB
- **Input:** `{entity_id: string (required)}`
- **Output:** `{entity_id, domain, average_power_on_w?, average_power_off_w?, total_state_changes, estimated_daily_kwh?, estimated_monthly_cost?}`

### Group 5 — Device health & anomaly detection (device-intelligence + data-api)

#### 16. `get_device_health`
Health scores: fleet summary or one device with factor breakdown and trend.
- **Backing:** device-intelligence `GET /api/health/scores`, `/api/health/scores/{id}`, `/api/health/trends/{id}`
- **Annotations:** `readOnlyHint: true` · **Budget:** 32 KB / 100 rows
- **Input:** `{device_id?: string, min_score?: int 0..100, health_status?: enum["healthy","degraded","critical"], include_trend: boolean = false, trend_days: int 1..30 = 7, limit: int 1..100 = 50}`
- **Output:** `{summary?: {total, healthy, degraded, critical, avg_score}, devices?: [{device_id, overall_score, health_status}], device?: {device_id, overall_score, health_status, factor_scores: object, trend?: [{t, score}]}, truncated}`

#### 17. `detect_anomalies`
Anomaly surface across the two production detectors: power anomalies and
predicted device failures.
- **Backing:** data-api `GET /api/devices/power-anomalies` (route un-shadowed by
  TAP-6071; its actual-power source is the energy-correlator pipeline that has
  never written a row, so `power_anomalies` is `[]` until TAP-5301) +
  device-intelligence `GET /api/predictions/failures`
- **Annotations:** `readOnlyHint: true` · **Budget:** 32 KB / 100 rows
- **Input:** `{kind: enum["power","failure_risk","all"] = "all", min_probability: number 0..1 = 0.5, risk_level?: enum["low","medium","high"], limit: int 1..100 = 50}`
- **Output:** `{power_anomalies?: [{entity_id, t, observed_w, expected_w?, severity}], failure_predictions?: [{device_id, failure_probability, risk_level, top_recommendation?}], counts: {power: integer, failure_risk: integer}, truncated}`
- Note: ai-pattern-service also carries an ML anomaly router
  (`anomaly/routes.py`), but it is **not registered** in that app today —
  wiring it is a service change out of this catalogue's scope; if it lands,
  it joins this tool as a third `kind` without a contract break.

---

## Response size budgets (summary table)

| Tool | Budget | Row cap |
|---|---|---|
| get_entity_history | 64 KB | 500 |
| search_events / get_recent_events | 32 KB | 200 |
| trace_automation | 16 KB | 100 rows (depth ≤ 10) |
| list_devices | 48 KB | 300 |
| get_device | 24 KB | 500 entities |
| list_entities | 48 KB | 500 |
| list_areas | 8 KB | 100 areas |
| get_entity_state | 4 KB | — |
| get_automation_stats | 24 KB | 100 |
| list_patterns / list_synergies | 32 KB | 100 / 50 |
| get_energy_summary | 16 KB | 20 |
| get_energy_correlations | 32 KB | 200 |
| get_device_energy_impact | 4 KB | — |
| get_device_health | 32 KB | 100 |
| detect_anomalies | 32 KB | 100 |

Worst-case single response ≤ 64 KB; typical agent turn using 2-3 tools stays
under ~100 KB of tool output. Enforcement is server-side (truncate + flag),
tested by TAP-5297 contract tests.

## Epic-required coverage check

| Epic domain | Tools |
|---|---|
| Entity history | get_entity_history, get_recent_events, search_events, trace_automation, get_entity_state |
| Pattern detection | list_patterns, list_synergies |
| Energy correlation | get_energy_correlations, get_energy_summary, get_device_energy_impact |
| Device health | get_device_health |
| Anomaly detection | detect_anomalies (+ failure predictions within it) |

## Comparison against the "opencode" inventory — recorded limitation

The epic cites a comparison project "opencode" with a 41-tool MCP inventory
(267 stars at epic-writing time, 2026-07-30). **No copy of that inventory
exists in this repository**, and a 2026-08-13 search could not uniquely
identify it publicly (candidates: `umrath/hass-opencode` — 33 tools / 13
resources / 6 prompts; `magnusoverli/opencode`; neither matches "41 tools,
267 stars" exactly). The comparison below therefore uses the strongest
identifiable public analogue, `homeassistant-ai/ha-mcp` (~84 tools), at the
**category** level; re-running it against the exact opencode list when the
owner confirms the reference is a recorded follow-up on TAP-5292.

| Capability category (analogue) | HomeIQ v1 position | Deliberate? |
|---|---|---|
| Live device control (turn_on/off, service calls) | **Absent** | Yes — HomeIQ's HA *writes* flow through the init-gateway converge path and the Wave 10 HA integration, never through this read surface. |
| State/entity/area reads | Covered (Group 2) — current state is `get_entity_state` with **last-observed** semantics (HomeIQ is an observer; a live HA read belongs to HA's own MCP integration) | — |
| Automation config CRUD | **Absent** (read-only stats + trace only) | Yes — automation deploys belong to `ai-automation-service-new`'s gateway (TAP-5992 semantics), not an MCP write tool, until the per-tool grant mechanism ships. |
| History / statistics | Covered (Group 1) — and deeper than the analogue (context-id tracing) | — |
| Diagnostics / health | Covered (Group 5) — plus ML failure prediction the analogue lacks | — |
| Analytics (patterns, synergies, energy correlation) | Covered (Groups 3-4) — **HomeIQ's differentiator; no public HA MCP server offers these** | — |
| Config/registry mutation (rename, enable/disable) | **Absent** | Yes — same grant gate as above. |
| Camera/media, backup management, add-on control | **Absent** | Yes — out of epic scope; HA's official MCP integration covers generic control. |
| Template rendering, logbook/error-log retrieval | **Absent** | Yes — debugging-HA capabilities; HA-side MCP servers own them. |
| Notifications / TTS / Assist-conversation | **Absent** | Yes — outbound actions, blocked by the same write-grant gate as control. |
| MCP resources & prompts (analogue ships 13 / 6) | **Absent** | Yes — v1 is tools-only; resources/prompts considered after the first gene consumers exist. |

Net position: v1 trades breadth of *control* tools for depth of *analytics*
tools, because control is already owned by governed HomeIQ paths and analytics
is the capability no other MCP surface has.

## Server-level contract notes (for TAP-5293)

- Transport: streamable-http (`mcp` Python SDK low-level `Server` + `StreamableHTTPSessionManager`, JSON responses, stateless) at the exact route `/mcp`; `/health` beside it. The low-level server is used so `list_tools` serves this catalogue's schemas verbatim.
- Auth: bearer token required (LAN-internal); tools themselves carry no auth
  parameters.
- Errors: tool errors return MCP tool-error content with a `code` from
  `{backing_unavailable, invalid_input, not_found, contract_violation}` — never
  a raw upstream traceback. `contract_violation`
  is raised when a backing's response cannot be projected into the tool's
  output schema (a server-side defect, surfaced instead of shipping an
  off-contract payload).
- Auth model: `/mcp` requires `Authorization: Bearer <token>`; tokens come from
  `HOMEIQ_MCP_READ_TOKENS` (read scope) and `HOMEIQ_MCP_WRITE_TOKENS` (read +
  mutate). `/health` is unauthenticated. Mutating tools additionally require the
  per-tool grant `HOMEIQ_MCP_ALLOW_WRITES` (design rule 1). Stdio transport is
  process-local and unauthenticated; the write grant still applies.
- Deferred tools (`status: deferred` in the JSON) are not registered and are
  invisible to `list_tools`; contract tests assert this.
- Registration: AgentForge overlay MCP registry (TAP-5296), server name
  `homeiq` — genes declare `mcp_servers: [homeiq]` and must be published via
  `install-from-yaml` (the plain agents endpoint drops the list).

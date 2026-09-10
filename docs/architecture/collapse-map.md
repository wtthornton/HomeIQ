# HomeIQ collapse map — v2 (operator recommendation, not a decision)

Accepted 2026-09-09 (TAP-7269)

SHA: `ef90b63229fadf3a9cffe3749bae10845b4db5f6`. Router/capability evidence:
[`premise-iii-routers.md`](premise-iii-routers.md). Inventory:
[`premise-ii-inventory.tsv`](premise-ii-inventory.tsv). Caller-confirmation round 2:
[`caller-confirmation.md`](caller-confirmation.md). Supersedes
[`collapse-map-draft.md`](collapse-map-draft.md) — v1's six `needs-decision` /
caller-orphan rows are resolved below. Both are recommendations; the operator has
made no decision yet.

**Note on `premise-iv-af-coverage.md`** (carried from v1, unchanged): this file was
never produced. v1's read of the 9 AgentForge workflow YAMLs stands as the AF-fit
evidence for §3; nothing in this round touches it.

---

## Changes from the draft

Six rows, each resolved using `caller-confirmation.md`'s round-2 evidence (file:line
cited, not re-derived):

1. **device-database-client** — v1: `fold-into device-domain — needs-decision`. v2:
   **fold-into homeiq-core.** Its own HTTP surface has zero confirmed callers; it is
   consumed as a **filesystem import**, not an HTTP call, by data-api itself
   (`domains/core-platform/data-api/src/services/device_database.py:24-37`,
   `sys.path.append(.../device-database-client/src)` then `from db_client import
   DeviceDatabaseClient`). Since data-api folds into homeiq-core, the fold target
   moves with the caller. The fold is "make the import a package import and delete
   the container," not "mount a router."
2. **device-recommender** — v1: `fold-into device-domain — needs-decision`. v2:
   **fold-into homeiq-core**, same shape:
   `domains/core-platform/data-api/src/services/device_recommender.py:22-53`
   (`sys.path.append` + import of `db_client`, `recommender`, `comparison_engine`
   from `device-recommender/src/`).
3. **ner-service** — v1: `fold-into model-server — needs-decision, leaning
   dropped-with-reason`. v2: **dropped-with-reason.** Its sole documented consumer,
   `ai-core-service`, does not exist on disk (`docs/planning/epic-domain-folder-
   restructuring.md:49,57`: "ner-service and openai-service listed in original plan
   do NOT exist in the filesystem — removed from plan"); zero code callers by
   identifier and port grep; 0 tests. Its 4 routes drop with it: `POST /extract`,
   `GET /health`, `GET /model-info`, `GET /stats`.
4. **automation-miner** — v1: `fold-into automation-domain — needs-decision`. v2:
   **dropped-with-reason (recommended)**, alternative offered. Sole caller confirmed
   at both proxy and component level: `domains/frontends/ai-automation-ui/
   nginx.conf:71-79` (`proxy_pass` to `http://automation-miner:8019`),
   `DeviceExplorer.tsx:45-47`, `SmartShopping.tsx:47-49` — all inside the frontend
   this program retires. No other caller found (no MCP tool, no AgentForge project
   reference, no `custom_components/homeiq` reference).
5. **automation-trace-service** — v1: `fold-into automation-domain, ingestion path
   unverified — needs-decision`. v2: **fold-into automation-domain as a background
   worker task**, not a router-mounted service. It is a producer, not a callee:
   `src/main.py:64-98` opens an `HATraceClient` WebSocket to Home Assistant and starts
   `TracePoller.run_continuous` as a background `asyncio` task; `src/trace_poller.py:
   167,199` POSTs to data-api's `/internal/automations/executions/bulk_upsert` and
   `/internal/automations/bulk_upsert`. Its only inbound surface is `/health`
   /`/health/details`, which the merged process's own health endpoint absorbs.
6. **ha-setup-service** — v1: `fold-into device-domain — needs-decision (0 HTTP
   routes found by decorator grep)`. v2: **fold-into device-domain (Option B),
   recommended.** The "0 routes" was a pattern miss — routes are declared on six
   named router objects (`@init_router.`, `@write_router.`, etc.), not the literal
   `@router.` string; `src/main.py:153-158` mounts all six. Two options were on the
   table: (A) stay standalone — 6 routers, live consumers are health-dashboard's
   nginx `/setup-service` proxy, `scripts/init-agent-nightly-audit.sh`, and its own
   served `/setup` wizard page, giving 11 HomeIQ services + HA = **12 running, zero
   headroom**; (B) fold into device-domain with every router mounted at its existing
   prefix, health-dashboard's nginx proxy repointed
   (`domains/core-platform/health-dashboard/nginx.conf:598`), the ops script's URL
   repointed, and the wizard page served from device-domain, giving 10 + HA = **11
   running, one slot of headroom**. The repoint is mechanical — one `proxy_pass`
   target, one script URL, one router mount for the wizard page — so **(B) is
   recommended**; it also matches what v1's Target Set section already assumed
   before this service's caller shape was in question, so it does not change the
   final container count from v1's headline number.

---

## Target set (≤ 12)

Ten named production services, unchanged in count from v1 (composition of three
containers shifts — see below):

1. **postgres** — unchanged from v1.
2. **influxdb** — unchanged from v1.
3. **homeiq-core** — folds admin-api, data-api, data-retention, websocket-ingestion,
   log-aggregator, **plus device-database-client and device-recommender** (7 → 1;
   was 5 → 1 in v1). Rationale unchanged for the original five; the two new sources
   are pure library imports of data-api's own process (`device_database.py:24-37`,
   `device_recommender.py:22-53`) with zero confirmed HTTP callers of their own —
   they fold with their caller, not into a router table.
4. **health-dashboard** — unchanged from v1.
5. **collectors** — unchanged from v1.
6. **device-domain** — folds device-context-classifier, device-health-monitor,
   device-setup-assistant, ha-setup-service, zeek-network-service, plus
   device-intelligence-service's CRUD slice (6 sources → 1; was 8 → 1 in v1 —
   device-database-client and device-recommender moved to homeiq-core, above).
   ha-setup-service's six routers (health/init/write/page/optimization/validation)
   mount at their existing prefixes; health-dashboard's proxy and the ops script's
   URL are repointed at the merged container.
7. **automation-domain** — folds yaml-validation-service, automation-linter,
   automation-trace-service (as a background worker task, not a router),
   ha-device-control, blueprint-index, blueprint-suggestion-service,
   rule-recommendation-ml, ai-pattern-service, api-automation-edge, plus the
   non-LLM slices of ai-automation-service-new, proactive-agent-service, and
   ha-ai-agent-service (12 sources → 1; was 13 → 1 in v1 — automation-miner is
   recommended dropped rather than folded, see §4). If automation-miner is instead
   re-homed (the alternative, §4), it returns to this list at 13 → 1, with no change
   to the final container count either way.
8. **model-server** — folds openvino-service, ml-service, rag-service, plus the ML
   slice of device-intelligence-service (3 whole services → 1; was 4 → 1 in v1 —
   ner-service is dropped outright rather than folded, see §4/§1 above).
9. **homeiq-mcp** — unchanged from v1.
10. **zeek** — unchanged from v1.

**Recommended option (ha-setup-service = B):** the 10 containers above, +
`home-assistant` (Lane D, per the packaging ADR) = **11 running**, one slot of
headroom under the 12-service ceiling.

**Alternative option (ha-setup-service = A, stay standalone):** the same 9 containers
minus ha-setup-service's fold into device-domain, **plus ha-setup-service as its own
11th HomeIQ container**, + `home-assistant` = **12 running, zero headroom.**

**Retired outright, no target container:** ai-automation-ui (§2, §4 of v1, unchanged),
**ner-service** (§1 above — no confirmed caller, documented consumer absent from the
filesystem), **automation-miner** (recommended path, §4 — sole caller is the
retiring ai-automation-ui; alternative is re-homing it as an `homeiq-automation-author`
input, which is not a fold and requires a new caller to be written, not just a router
move).

**Left the compose plane entirely** (AgentForge workflow definitions, not
containers): unchanged from v1 — the LLM-calling route groups of
ha-ai-agent-service, ai-automation-service-new, proactive-agent-service, and
device-intelligence-service, per §3.

---

## Per-service map (42 rows)

Unchanged from v1 except the six rows below (full table in
`collapse-map-draft.md` §2 for the other 36; reproduced here only where the
disposition, target, or evidence changed).

| Service | Disposition | Capability summary | Target | Consumers to rewrite | Tests to re-home |
|---|---|---|---|---|---|
| device-database-client | fold-into **homeiq-core** | 4 routes: device lookup/search, cache status, sync trigger; consumed as a filesystem import by data-api, not an HTTP callee (`caller-confirmation.md` §1: `data-api/src/services/device_database.py:24-37`); `DEVICE_DATABASE_API_URL` env var read but never used — dead config | homeiq-core `/data/*` router (import becomes an internal package, container/port 8022 retired) | none (zero HTTP callers found; prometheus scrape and health-check script entries are cosmetic and fold away with the container) | 1 (`test_device_database_unit.py` moves with data-api's suite) |
| device-recommender | fold-into **homeiq-core** | 3 routes: devices, compare, recommend; consumed as a filesystem import by data-api, not an HTTP callee (`caller-confirmation.md` §2: `data-api/src/services/device_recommender.py:22-53`) | homeiq-core `/data/*` router (import becomes an internal package, container/port 8023 retired) | none (zero HTTP callers found; automation-miner's same-named `device_recommender.py` module and the `:8023` naming collision documented in `implementation/SERVICES_OUT_OF_DATE_REVIEW.md:41-44` are both false positives, not callers) | 1 (`test_device_recommender_unit.py`) |
| ner-service | **dropped-with-reason** | 4 routes dropped: `POST /extract`, `GET /health`, `GET /model-info`, `GET /stats`. Sole documented consumer `ai-core-service` does not exist in the filesystem (`caller-confirmation.md` §3: `docs/planning/epic-domain-folder-restructuring.md:49,57`); 0 tests, 0 callers, no `host_ports` entry | n/a — removed entirely, not folded | none | 0 |
| automation-miner | **dropped-with-reason (recommended)** — alternative: re-home as an input to the `homeiq-automation-author` AF workflow | 10 routes: corpus mining, blueprint possibilities, recommendations. Sole caller confirmed as the retiring ai-automation-ui: `nginx.conf:71-79` proxy, `DeviceExplorer.tsx:45-47`, `SmartShopping.tsx:47-49` (`caller-confirmation.md` §4) | n/a if dropped; if re-homed, automation-domain `/miner/*` router with a new caller written into the AF workflow's inventory-input stage (cost: new integration code — nothing today calls this surface from an AF workflow) | ai-automation-ui only (retiring) | 7 |
| automation-trace-service | fold-into automation-domain **as a background worker task** (not a router) | 1 inbound route (`/health/details`); it is a producer — HA WebSocket ingestion + `TracePoller.run_continuous` posting to data-api's bulk-upsert endpoints (`caller-confirmation.md` §5: `src/main.py:64-98`, `src/trace_poller.py:167,199`) | automation-domain background `asyncio` task; its `/health` surface is absorbed by the merged process's own health endpoint | none (health-check scripts and one integration test exercise `/health` only) | 4 |
| ha-setup-service | fold-into device-domain — **Option B, recommended** | 6 routers, ~15 routes: health/init/write/page/optimization/validation, all mounted in `src/main.py:153-158` (`caller-confirmation.md` §6) | device-domain, each router mounted at its existing prefix; wizard `/setup` page served from device-domain | health-dashboard (nginx `/setup-service` proxy → repoint, `health-dashboard/nginx.conf:598`; `useEnvironmentHealth.ts:11,30`; `SetupServiceClient` in `api.ts:948-999`), `scripts/init-agent-nightly-audit.sh:16` (repoint URL) | 10 |

**Sum check:** 42 rows. Keeps: 5 (postgres, influxdb, health-dashboard, homeiq-mcp,
zeek) — unchanged. Retired outright: **3** (ai-automation-ui, ner-service,
automation-miner [recommended path]) — was 1 in v1. Split across 2+ targets: 4
(ai-automation-service-new, device-intelligence-service, ha-ai-agent-service,
proactive-agent-service) — unchanged. Straight folds: **30** — was 32 in v1
(ner-service and automation-miner moved from fold to retired; device-database-client
and device-recommender remain folds, just to a different target).
`5 keeps + (30 + 4 splits' non-LLM remnants) folded into 5 domain containers + 3
retired + 4 LLM slices leaving as AF workflows (no container) = 10 target
containers`, matching §1.

---

## LLM slice vs data slice

Unchanged from v1 — none of the six rows resolved this round touch the OpenAI/LLM
slice. See `collapse-map-draft.md` §3 for the full ha-ai-agent-service,
ai-automation-service-new, proactive-agent-service, and device-intelligence-service
breakdown; nothing in `caller-confirmation.md` bears on it.

---

## Capabilities with no surviving home

Resolved this round, closed via `caller-confirmation.md`: device-database-client,
device-recommender, ner-service, automation-miner, automation-trace-service, and
ha-setup-service — all six of v1's caller/orphan `needs-decision` rows. One item
remains, and it is a policy question, not an orphan-caller question:

1. **admin-api's and log-aggregator's docker.sock-mounted container management** —
   `needs-decision` (policy, not code), unchanged from v1. The packaging ADR names
   this cost directly: "under the appliance they are managing containers the
   customer did not create, which is a different authorisation question than the one
   they were written for." Consolidating the two mounts into homeiq-core reduces the
   attack surface but does not answer whether an appliance should hold this
   capability at all.

This section is deliberately empty of every *caller/orphan* `needs-decision` row —
the six this round's evidence was scoped to. It is **not** claiming every open
question in the document is closed: v1 §3/§7 items 1 and 2 (ha-ai-agent-service's
live-chat AF-workflow shape, proactive-agent-service's suggestion-drafting AF-workflow
shape) are still undecided, but they are not "no surviving home" questions — both
already have a confirmed home (an AgentForge workflow, per the OPENAI_API_KEY grep
and the ADR's "every OpenAI credential must leave HomeIQ" constraint). What's open
for those two is only *which* workflow shape, a lane-level (C2) authoring decision,
not a topology/container-count decision — so they stay out of this section and out
of the Open Questions list below, and are called out here explicitly so their
absence doesn't read as silently resolved.

---

## Required-marker and env impact

Unchanged from v1 — none of the six resolved rows carry a `required`/`conditional`
env key of their own (device-database-client and device-recommender have none;
ha-setup-service, ner-service, automation-miner, and automation-trace-service are
not sources of any row in v1's env table). See `collapse-map-draft.md` §5 for the
full table (`POSTGRES_*`, `INFLUXDB_TOKEN`, `API_KEY`, `ADMIN_API_JWT_SECRET`,
`AGENTFORGE_API_KEY`, `HOME_ASSISTANT_*`/`HA_*`, `OPENAI_API_KEY`, `WATTTIME_*`,
`MQTT_*`, `NABU_CASA_*`, `CALENDAR_ENTITIES`, `ADMIN_PASSWORD`,
`GF_SECURITY_ADMIN_PASSWORD`).

---

## Lane split C1–C4

Order is fixed C1 → C2 → C3 → C4. The recommended-path resolutions above move
sources between lanes' target containers but do not change any lane's net Δ — the
counts are identical to v1.

- **C1 — collectors.** Unchanged from v1: weather-api, sports-api, air-quality,
  electricity-pricing, calendar, smart-meter (6 → 1). Δ = -5. **n1 = 37.**
- **C2 — the four LLM-adjacent services + ai-automation-ui + AF workflow edits.**
  Unchanged from v1. Δ = -3. **n2 = 34.**
- **C3 — ML.** Owns: openvino-service, ml-service, rag-service, plus
  device-intelligence-service's ML slice (3 whole services → 1, Δ = -2); **plus
  ner-service, dropped outright** (Δ = -1, no merge target — was previously counted
  as the 4th service folding into model-server, same numeric effect). Creates
  `model-server`. Total Δ = -3, unchanged from v1. **n3 = 31.**
- **C4 — the thin wrappers.** Recomposed across three targets (net Δ unchanged from
  v1's -21):
  - **device-domain:** device-context-classifier, device-health-monitor,
    device-setup-assistant, ha-setup-service, zeek-network-service, plus
    device-intelligence-service's final CRUD remnant (6 sources → 1; was 8 in v1 —
    device-database-client and device-recommender moved out). Δ = -5 (was -7).
  - **homeiq-core:** admin-api, data-api, data-retention, websocket-ingestion,
    log-aggregator, plus **device-database-client and device-recommender** (7
    sources → 1; was 5 in v1). Δ = -6 (was -4).
  - **automation-domain (existing):** yaml-validation-service, automation-linter,
    automation-trace-service (as a background worker), ha-device-control,
    blueprint-index, blueprint-suggestion-service, rule-recommendation-ml,
    ai-pattern-service, api-automation-edge (9 sources → 0 new containers, Δ = -9);
    **plus automation-miner, dropped outright** (Δ = -1, no merge target — was
    previously the 10th service folding here, same numeric effect). Combined
    Δ = -10, unchanged from v1.
  - Total C4 Δ = -5 + -6 + -10 = **-21**, unchanged from v1. **n4 = 10.**

**42 → 37 → 34 → 31 → 10**, landing 2 services under the 12-service ceiling before
Lane D — same headline sequence as v1, because this round's resolutions moved
sources between target containers without changing which sources survive. Lane D
then adds `home-assistant` (+1), for a final running total of **11** under the
recommended ha-setup-service = B option (12 under the alternative, A).

---

## Open questions for the topology decision

Reduced from v1's 8 items to what genuinely remains after this round:

1. **automation-miner: drop vs. re-home.** Recommended path is
   `dropped-with-reason` (its sole caller, ai-automation-ui, is retiring, and no
   other consumer was found). The alternative — re-homing the corpus-mining
   capability as an input to the `homeiq-automation-author` AF workflow — is not a
   fold; it requires a new caller to be written, which is real integration work
   the operator may or may not want to fund. This is the operator's call, not a
   further research gap.
2. **admin-api's and log-aggregator's docker.sock container-management capability**
   — kept in the appliance at all (consolidated into homeiq-core, as this map
   proposes), or dropped pending a real authorization model? Unchanged from v1;
   this is the one item this round's caller-confirmation evidence does not touch.
3. **Confirm the ha-setup-service repoint's blast radius before C4 executes.** The
   recommendation (Option B) treats the repoint as mechanical — one nginx
   `proxy_pass` target, one ops-script URL, one router mount — but
   `health-dashboard/nginx.conf` is a file outside device-domain's own directory;
   the lane owning C4 should confirm no other health-dashboard config or frontend
   client references `ha-setup-service` by hostname before landing the fold, rather
   than re-deriving that from this map.

Not carried forward from v1: the ha-setup-service A/B choice itself (resolved above,
§ Changes from the draft, item 6) and all five caller/orphan items closed by
`caller-confirmation.md` (§ Capabilities with no surviving home). Also not counted
here (deliberately, per that section's closing note): v1's items 1 and 2 — the
ha-ai-agent-service and proactive-agent-service AF-workflow-shape questions — which
remain open but are lane-level (C2) authoring decisions, not topology decisions.

---

## Section C1 — collectors (TAP-7274, landed)

Six pure-HTTP collectors folded into one FastAPI process, `domains/data-collectors/
collectors-service/`, mounted at port 8009 with every former route unprefixed
(`src/main.py`). Compose: `domains/data-collectors/compose.yml` — the six former
services removed, `collectors` added with no `profiles` key (production).
Container-budget ratchet: `infrastructure/container-budget.json` ceiling.services
42 → 37 (`--update-baseline --no-memory`; `memory_mib` unchanged at 7406, since
memory was not re-measured). Six retired directories (`weather-api`, `sports-api`,
`air-quality-service`, `electricity-pricing-service`, `calendar-service`,
`smart-meter-service`) deleted from `domains/data-collectors/` once their tests
were re-homed under `collectors-service/tests/`.

| Former service | Former route | Surviving route under `collectors` | Consumers rewritten (file:line) |
|---|---|---|---|
| weather-api | `GET /current-weather`, `GET /cache/stats` | same paths, port 8009 (`src/adapters/weather/__init__.py:480,495`) | `domains/core-platform/health-dashboard/nginx.conf:586-587` (`set $weather_service`, proxy_pass), `domains/core-platform/compose.yml:279` (`WEATHER_SERVICE_URL`), `domains/core-platform/admin-api/src/health_endpoints.py:159,605` (`service_urls["collectors"]`), `domains/core-platform/admin-api/src/docker_service.py:105-106` (`container_mapping`), `domains/energy-analytics/compose.yml:17` (`WEATHER_API_URL`), `domains/energy-analytics/proactive-agent-service/src/{config.py:29,clients/weather_api_client.py:25,main.py:89,98}`, `domains/automation-core/ha-ai-agent-service/src/config/__init__.py:103-107`, `infrastructure/prometheus/prometheus.yml:82-86` (scrape target), `libs/homeiq-observability/src/homeiq_observability/monitoring/stats_endpoints.py` (`service_urls`, `api_services`, per-service metrics branch) |
| sports-api | `GET /`, `GET /sports-data`, `GET /stats` | same paths, port 8009 (`src/adapters/sports/__init__.py:570,582,603`) | same admin-api / stats_endpoints.py rewrites above (shared `collectors` entry); `domains/automation-core/ha-ai-agent-service/src/config/__init__.py:93-97` |
| air-quality-service | `GET /current-aqi` | same path, port 8009 (`src/adapters/air_quality/__init__.py:395`) | same admin-api / stats_endpoints.py / prometheus rewrites above |
| electricity-pricing-service | `GET /cheapest-hours` | same path, port 8009 (`src/adapters/electricity_pricing/__init__.py:259`) | same admin-api / stats_endpoints.py / prometheus rewrites above |
| calendar-service | `GET /api/v1/prediction`, `GET /api/v1/events` | same paths, port 8009 (`src/adapters/calendar/__init__.py:394,410`) | same admin-api / stats_endpoints.py / prometheus rewrites above; `libs/homeiq-ha/src/homeiq_ha/ha_connection_manager.py:29` (doc comment), `libs/homeiq-ha/src/homeiq_ha/agent/recipes.py:261` (doc comment) |
| smart-meter-service | `GET /consumption` | same path, port 8009 (`src/adapters/smart_meter/__init__.py:310`) | same admin-api / stats_endpoints.py / prometheus rewrites above |

**Deployment/CI surfaces rewritten (not per-route, apply to all six):**
`scripts/{check-versions.sh,deploy-phase-5.sh,deploy-tier2.sh,post-deployment-monitor.sh,
deployment/post-deployment-validate.sh,pre-deployment-check.sh}` (six `name:port` health-check
array entries collapsed to one `collectors:8009`); `docker-bake.hcl` (six build targets
collapsed to one `collectors` target); `pytest-unit.ini`, `scripts/simple-unit-tests.py`
(testpaths repointed at `collectors-service/tests`); `.github/workflows/{ci-collectors.yml,
docker-build.yml,docker-release.yml,docker-security-scan.yml}` (matrix entries collapsed to
one `collectors-service` directory-name entry); `tests/e2e/test_resilience_e2e.py:145`
(dependency-name assertion `"weather-api"` → `"collectors"`, matching
`proactive-agent-service`'s renamed `GroupHealthCheck` dependency key).

**Deployment/CI surfaces still naming `homeiq-weather-api` (missed by this PR, fixed in
lane C1-fix):** `scripts/degradation-test.sh` (Test 3's `docker stop`/`wait_healthy` target and
surrounding echo text — the stop was silently swallowing its own failure, making the test
unable to go red); `scripts/phase1-monitor-rebuild.sh` (a `docker ps | grep -E` status filter
that would never match); `scripts/README-PHASE1-BATCH-REBUILD.md` (a `docker tag` rollback
example in the runbook prose). Unlike the surfaces above, these three were not part of this
PR's own rewrite pass — the original sweep was not complete, and this list exists so the gap
is visible rather than implied away by the paragraph above.

**Dropped-with-reason (not a real consumer):** `domains/core-platform/admin-api/
review-results.json:2397` — a frozen JSON blob of a prior code-review tool run over
`health_endpoints.py`'s pre-refactor source, embedded as review output text, not
executable code or a live caller. Left unrewritten.

**Not migrated in this PR (tracked as follow-up, not a functional break):** the
health-dashboard frontend's per-service display components (`domains/core-platform/
health-dashboard/src/components/{ServicesTab.tsx,ServiceDependencyGraph.tsx,
AnimatedDependencyGraph.tsx}`, `src/services/api.ts`'s `data_sources` name-mapping,
`src/mocks/*.ts`, `public/ai-tier-manifest.json`) still enumerate the six former
service ids for dashboard cards/graphs. They read from admin-api's aggregate health
payload, which now reports the six under one `collectors` key (this PR) — the six
cards will show as unreachable rather than break the app. Re-shaping the dashboard's
per-service UI into one `collectors` card is frontend work outside this lane's compose/
ratchet/consumer-backend scope.

**Test re-homing:** every adapter's tests live under `collectors-service/tests/<adapter>/`.
Per-service base collect counts (measured in isolated venvs at this PR's parent sha,
before any edit): weather-api 13, sports-api 8, air-quality-service 56,
electricity-pricing-service 137, calendar-service 62, smart-meter-service 33 — sum 309.
`collectors-service` head collect count: 283. The gap (26) is consolidation of
duplicate coverage across each service's old `test_main.py`/`unit/test_*.py` pairs
(the same behavior asserted twice under the old per-service layout — e.g.
electricity-pricing's `test_main.py` duplicated `unit/test_configuration.py`), plus
`test_provider_integration.py`'s near-duplicate of `unit/test_awattar_provider.py`'s API-integration
cases, plus dropping one now-inapplicable per-service `/health` payload assertion
(`test_service` == the individual service name) since `/health` is shared across all
six adapters post-merge. No capability lost its test coverage; every surviving route
above has passing tests in `collectors-service/tests/`. Full accounting is in the PR body.

## Section C3 — model-server (TAP-7276, landed)

`openvino-service`, `ml-service` and `rag-service` fold into one production service
`model-server`. `ner-service` is **dropped outright** — no fold target, no caller.
Base sha `073cc5f8820e25f87a02280d0563fc34a0e70fa7`: 37 production services before this
lane; 34 after (`-4 + 1`, ratcheted in `infrastructure/container-budget.json`).

**device-intelligence-service's ML slice (item 3 of the original brief) is explicitly
NOT moved in this PR.** `predictions_router.py` and `recommendations_router.py` (the
sklearn-based failure-prediction/recommendation code in
`domains/ml-engine/device-intelligence-service/src/core/predictive_analytics.py`,
`core/recommendation_engine.py`) are deeply coupled to that service's own
`core.database`/`core.repository`/`core.cache` — the same Postgres `devices` schema
its CRUD routes use, not an HTTP call to openvino/ml-service the way rag-service's
embedding calls were. Moving it would mean either giving model-server a live
dependency on the `devices` schema, or rewriting those two routers to fetch device
data over HTTP from device-domain instead of direct DB access — a real architecture
decision the collapse-map evidence never worked out (it only asserts "the ML slice
of device-intelligence-service" moves, without specifying the DB-coupling mechanics).
Doing that extraction unreviewed, in the same PR as the openvino/ml/rag merge, risked
a rushed and unsafe split. `device-intelligence-service` stays as its own container,
untouched — the `-4 + 1 = -3` ratchet does not depend on this slice moving, since the
four services actually retired here are openvino-service, ml-service, rag-service and
ner-service, none of which is device-intelligence-service. Flagging as a follow-up
rather than silently absorbing it into "done."

### ner-service: dropped-with-reason

Re-confirmed at this lane's base sha (not trusted from the brief, which itself flagged
its own `## Where` as stale — the real source is
`domains/ml-engine/ner-service/src/ner_service.py`, not `ner-service/src/main.py`):

- 0 test files (`domains/ml-engine/ner-service/` has only `Dockerfile`,
  `requirements-prod.txt`, `src/ner_service.py`).
- `git grep -n 'ner-service\|ner_service' -- domains libs custom_components agentforge
  tests scripts infrastructure` (full scope — an earlier draft of this section scoped
  the grep to `domains libs custom_components` only, which silently excludes
  `scripts/` and `infrastructure/`; re-run at the corrected scope) finds, in addition
  to ner-service's own compose block and the `homeiq-ner-service` prometheus scrape
  target (`infrastructure/prometheus/prometheus.yml:120`): two **real callers**,
  `scripts/ops/check-all-health.sh:31` and `scripts/validate-services.sh:126`, both
  curling `http://localhost:8031/health` with `ner-service` listed as a
  `REQUIRED_SERVICE`. **Both were repointed at this lane's head** — the drop is safe.
  Also a label in health-dashboard's static `public/ai-tier-manifest.json` — no code
  caller there.
- No `NERClient`/`ner_client` class anywhere in `domains/` or `libs/`. Its sole
  documented consumer, `ai-core-service` (`docs/architecture/service-groups.md:200`:
  "ner-service (NER) --> ai-core-service (orchestrator)"), does not exist in the
  filesystem — `domains/ml-engine/` has no `ai-core-service` directory at this
  lane's base sha, re-verified directly (`ls domains/ml-engine/`), not trusted from
  an earlier program document.

Its 4 routes drop with it: `POST /extract`, `GET /health`, `GET /model-info`,
`GET /stats`. No caller found — a real one would have been a map amendment, not
something to fold in silently.

### One process, one model load

The OpenVINO embedding/rerank/classify model (`OpenVINOManager`,
`domains/ml-engine/model-server/src/openvino/models/openvino_manager.py`) is
constructed exactly once per process, at startup. rag-service used to call a
*separate* openvino-service container over HTTP for embeddings
(`OpenVINOClient` → `http://openvino-service:8019`); in the merged process that
became `LocalOpenVINOBridge`
(`domains/ml-engine/model-server/src/rag/clients/openvino_client.py`), an
in-process adapter around the same manager instance the `/embeddings` and
`/rerank` routes use — no second model load, no network hop to a container that
no longer exists. Asserted by
`domains/ml-engine/model-server/tests/test_shared_model_load.py`: one
`OpenVINOManager()` construction on startup (mock-counted), RAG's bridge holds
the identical manager object (`bridge._manager is openvino_manager`), and RAG's
`get_embeddings()` call is proven to route through that same manager's own
`generate_embeddings()` (call-count spy, not just an output match). Red-first:
these three tests were run against a deliberately reintroduced second
`OpenVINOManager()` instantiation in the RAG startup hook and failed (proving
they exercise the shared-instance invariant), then reverted to the real fix
and re-verified green.

### Route map

| Former service | Former route | Surviving route under `model-server` (port 8019) | Consumers rewritten (file:line) |
|---|---|---|---|
| openvino-service | `POST /embeddings`, `POST /rerank`, `POST /classify`, `GET /models/status`, `POST /models/warmup` | same paths, unchanged (`src/main.py:366-489`) | `infrastructure/prometheus/prometheus.yml:121,126` (scrape target), `scripts/{check-versions.sh,deploy-phase-5.sh,deploy-tier3.sh,deployment/post-deployment-validate.sh,post-deployment-monitor.sh,pre-deployment-check.sh,deploy-tier3.sh:101,phase1-monitor-rebuild.sh:124,rollback-ml-upgrade.sh:147,quantize-bge-m3.py:128,validate-bge-m3-deployment.sh:27,ops/check-all-health.sh:29-32,validate-services.sh:124-126}`, `.github/workflows/{ci-ml.yml,docker-build.yml,docker-release.yml,docker-security-scan.yml}` (matrix entries), `docker-bake.hcl` (build target), `domains/core-platform/health-dashboard/public/ai-tier-manifest.json`, `tests/integration/cross_group/test_health_aggregation.py:28-33` |
| ml-service | `POST /cluster`, `POST /anomaly`, `POST /batch/process`, `GET /algorithms/status` | same paths, unchanged (`src/main.py:498-603`) | same deployment/CI surfaces above (shared `model-server:8026` entry); `domains/blueprints/rule-recommendation-ml/requirements.txt:19` (comment) |
| rag-service | `POST /api/v1/rag/*` (`rag_router`), `GET /api/v1/metrics*` (`metrics_router`) | same paths, unchanged (`src/rag/api/rag_router.py`, `metrics_router.py`, both included by `src/main.py:222-223`) | `domains/core-platform/admin-api/src/health_endpoints.py:185,216` (`service_urls["model-server"]`, `group_mappings["ml-engine"]`), `domains/core-platform/health-dashboard/nginx.conf:618,622` (`/rag-service/` proxy_pass target repointed to `model-server:8019`; the *path* is kept stable so `domains/core-platform/health-dashboard/src/services/api.ts`'s `RAGServiceClient` needed no change), `domains/core-platform/health-dashboard/src/components/ServicesTab.tsx:64,70` (service card), `infrastructure/prometheus/{prometheus.yml:121,126,alerts.yml:498-499}` (scrape target + `MemoryBrainEmbeddingDown` alert expr), `infrastructure/postgres/init-schemas.sql:1134` (comment), `pytest-unit.ini:35` (testpaths), `domains/automation-core/compose.yml:7` (comment) |
| ner-service | `POST /extract`, `GET /health`, `GET /model-info`, `GET /stats` | **dropped, no surviving route** | none (no caller found — see above) |
| (cross-cutting) | `GET /health`, `GET /ready` | same paths, via `StandardHealthCheck` (`libs/homeiq-resilience/src/homeiq_resilience/health_check.py:85-93`, `router.add_api_route` — not a `@app.get` decorator, so a decorator grep misses it), registered `domains/ml-engine/model-server/src/main.py:198-203` with checks `openvino-models`, `ml-managers` | none new — **contract change**: ml-service's own `/health` returned a custom dict including `algorithms_available` (base sha `domains/ml-engine/ml-service/src/main.py:130-136`); the generic `StandardHealthCheck` response does not include that field. `git grep -n 'algorithms_available'` at head: 0 hits — no consumer reads it, so this is a response-shape change with no known breakage, not a silent regression. Not re-added; a follow-up story owns whether it's worth restoring. |

**Bare-container-name grep** (`git grep -n 'homeiq-\(openvino\|ml-service\|rag\|ner\)'`)
after the rewrites above returns **zero matches** in `domains/`, `libs/`, or
`.claude/` — an earlier draft of this section claimed that command found
`.claude/settings.local.json`, `zeek-network-service` sources, and
`libs/homeiq-resilience`, which is false: those three files use the **bare** service
names (no `homeiq-` prefix), so the `homeiq-`-prefixed pattern above cannot return
them. The only hits for the prefixed pattern are historical docs
(`docs/operations/dashboard-triage-2026-08-01.md`, `docs/operations/service-health-checks.md`,
`docs/planning/phase-3-plan-ml-ai-upgrades.md`, `docs/planning/rebuild-deployment-plan.md`,
`stories/epic-81-docker-rebuild-aiohttp-cve.md`), none of them live consumer code.

The command that actually produces the three-file result is the **bare-name** grep,
`git grep -n '\bml-service\b\|\brag-service\b\|\bner-service\b\|\bopenvino-service\b' --
.claude/settings.local.json domains/data-collectors/zeek-network-service
libs/homeiq-resilience` — and re-run at that scope: `.claude/settings.local.json`
(Bash permission allowlist entries, not executable consumer code),
`domains/data-collectors/zeek-network-service/src/{main.py:735,
parsers/flowmeter_parser.py:4}` (descriptive comments — the flow-feature data still
flows to whichever ML consumer wants it, now model-server, but the comment text
itself wasn't rewritten), and `libs/homeiq-resilience/src/homeiq_resilience/health.py:17`
/ `libs/homeiq-resilience/tests/test_health.py:25` (a generic `"ml-service"` example
name in library docstring/test fixtures, unrelated to this repo's actual service —
same naming-collision shape the brief warned about, verified by reading the call site,
not just the string match). None of these are live HTTP callers of a retired hostname.

### Test re-homing

Per-service base collect counts, measured in an isolated venv (`fastapi`, `torch`,
`sentence-transformers`, `scikit-learn`, `sqlalchemy`, `asyncpg` installed from
`requirements-dev.txt`) against a detached worktree at this lane's own base sha
(`073cc5f8820e25f87a02280d0563fc34a0e70fa7`), not trusted from any earlier program
document: openvino-service 42, ml-service 122, rag-service 5, ner-service 0 (no
`tests/` dir — not an `error` row, a real zero) — **sum 169**.

`model-server` head collect count: **190**. All 169 base tests re-homed with only
import-path updates (`src.models.openvino_manager` → `src.openvino.models.
openvino_manager`, `src.middleware`/`src.validation`/`src.algorithms.*` →
`src.ml.*`, `src.utils.metrics` → `src.rag.utils.metrics`) — no test was deleted to
make the arithmetic work. The +21 gap is entirely new coverage added in this PR:
3 tests in `test_shared_model_load.py` (the one-model-load assertions above) and 18
in `test_rag_service_unit.py`, replacing a single `assert True` placeholder
(`RAGService.store/retrieve/search/update_success_score` were previously untested;
merging rag's own `src/rag/api/health_router.py` — dead code, never mounted even in
the original rag-service — was deleted rather than tested, since testing an
unreachable route would have asserted nothing real). 169 base → 190 head reconciles
exactly: 169 + 3 + 18 = 190.

**Coverage gate:** `[coverage:report] fail_under = 70` in `model-server/pytest.ini`
is a live gate here (confirmed with `--cov-fail-under=70`) — pre-fix coverage was
67.36% (would have failed); adding the real `test_rag_service_unit.py` tests above
(not padding) brought it to 74.58%.

**Bonus fix surfaced by this merge:** `OpenVINOManager`'s `model_cache_dir` setting
was declared in `openvino-service`'s config but never actually passed to the
manager's constructor (`OpenVINOManager()` always used its hardcoded `/app/models`
default) — dead config since the service was first written. Real lifespan-startup
tests (`test_health.py`, `test_shared_model_load.py`) only became possible outside a
container once `_startup_openvino()` was fixed to pass
`models_dir=openvino_settings.model_cache_dir`, which is what let `MODEL_CACHE_DIR`
be pointed at a writable tmp dir in `tests/conftest.py`.

## Section C2 — automation-domain (TAP-7275, landed)

`ha-ai-agent-service`, `ai-automation-service-new` and
`proactive-agent-service` fold into one production service `automation-domain`
(`domains/automation-core/automation-domain/`, port 8030). `ai-automation-ui` is
**retired outright**. Base sha `dbc32495388bb74b572062b90ed1e12bf32468cc`: **34**
production services before this lane, **31** after (`34 − 4 + 1`, ratcheted in
`infrastructure/container-budget.json`).

Every number here was re-derived at that base sha, not carried from the brief.
Two of the brief's own figures did not survive re-measurement and are corrected
below.

### Re-derived counts

| Measure | Brief said | Re-measured at `dbc32495` |
|---|---|---|
| HTTP endpoints across the four services | 206 | **114 route declarations** (agent 29, authoring 50, proactive 35; `ai-automation-ui` is a SPA and declares none) |
| Services reading `OPENAI_API_KEY` in code | 3 | **4** — the three named, plus `domains/ml-engine/nlp-fine-tuning/src/training/fine_tune_openai.py` (see "Residue" below) |
| AgentForge workflows covering those endpoints | 3 of 206 | **0 of 114** — the 9 published workflows at base sha are digests, triage and authoring pipelines; none of them was the backend of any of these routes |

### One process, three schemas

The three slices persist to three different Postgres schemas (`agent`,
`automation`, `energy`) and each now reads **its own** environment variable:
`AGENT_DB_SCHEMA`, `AUTOMATION_DB_SCHEMA`, `ENERGY_DB_SCHEMA`. All three
previously read `DATABASE_SCHEMA`, which is correct for three containers and
silently wrong for one process: one variable would bind all three slices to
whichever value was set last, and the two that lost would read and write the
wrong schema without raising. Asserted by
`tests/test_agentforge_fold.py::TestSchemaSeparation`, red-first — the two tests
were run against a tree in which all three modules read `DATABASE_SCHEMA` again,
and failed with `assert 'wrong_schema' == 'agent'`.

`TestComposeSetsWhatTheCodeReads` closes the TAP-7365 shape from the other side:
it parses the compose file this PR ships and asserts every `*_DB_SCHEMA` the
source reads (discovered by scanning `src/` for `os.getenv`, not from a
hand-written list) has an entry there, plus each AgentForge variable. A
documented env mechanism nothing sets is what let C1's calendar adapter report
healthy while never writing a row.

### The LLM slice: nine AgentForge workflows

Every model call these services made is now a workflow run. No provider SDK
(`openai`, `anthropic`) is in `requirements.txt` and no provider credential is
in any compose block.

| Workflow | Gene | Serves (HomeIQ call site) | New gene? |
|---|---|---|---|
| `automation-draft` | `hiq-draft-automation` | `AutomationLLMClient.generate_yaml` / `.generate_structured_plan`; `ValidationRetryLoop`'s correction pass | no |
| `automation-json` | `hiq-automation-json` | `.generate_homeiq_automation_json` — `POST /api/suggestions/{id}/rebuild-json`, `GET /api/suggestions/{id}/json`, `YAMLGenerationService` | **new** |
| `intent-plan` | `hiq-intent-plan` | `IntentPlanner` — `POST /automation/plan` | **new** |
| `suggestion-describe` | `hiq-summarize` + transform | `.generate_suggestion_description` — `POST /api/suggestions/generate` and the daily scheduler | no |
| `assistant-chat` | `hiq-assistant` | `POST /api/v1/chat` | no |
| `memory-extract` | `hiq-extract` | `MemoryExtractor`, per chat turn | no |
| `proactive-suggest` | `hiq-proactive-suggest` | `AIPromptGenerationService._call_llm` (reads `suggestions`) **and** `ProactiveAgentLoop._reason` (reads `actions`) | **new** |
| `device-name-suggest` | `hiq-device-name` | `device-intelligence-service`'s `AINameSuggester` | **new** |
| `automation-enhance` | `hiq-automation-enhance` | `AutomationEnhancementService` — one run replaces up to nine provider calls per automation | **new** |

`hiq-extract`'s contract is why `memory-extract` uses it rather than a new gene:
a field the source does not state comes back `null` and listed in
`unsourced_fields` instead of guessed. A guessed "fact" here becomes a stored
memory the assistant later treats as something the person said. The real run
confirms it — `favourite_colour` came back `null` from a message that never
mentioned one.

**A defect the first real run caught.** `intent-plan`'s gene answered with its
whole envelope nested under `parameters`, and HomeIQ passes `parameters`
straight to the template renderer. `additionalProperties: false` did not catch
it because the extra keys were *inside* a field typed `{"type": "object"}`. The
workflow's node schema now carries a `not/anyOf` clause forbidding the
envelope's own field names in there, so `output_repair_retries` turns the
violation into a repair. Re-run after the fix: `parameters` is
`{"area_id": "office", "light_entity_id": "light.office"}`.

**A defect the runs caught in HomeIQ's own client.** `kickoff=sync` is a
request, not a guarantee: AgentForge steers a run onto its async queue when it
exceeds the sync threshold and answers **202 `pending`** with no output. Eight of
the nine workflows answered 200; `suggestion-describe` answered 202. The client
treated any non-terminal state as a failure, which would have been an
intermittent failure reproducible only under load. `AgentForgeClient` now polls a
pending run to completion (`_await_terminal`), asserted red-first in
`TestSteeredRunIsPolled` — both tests fail with the poll removed.

### Route map

All 114 base route declarations, mapped. Zero `unmapped`.

| Former service | Former routes | Surviving route under `automation-domain` (port 8030) |
|---|---|---|
| ha-ai-agent-service (8030) | `POST /api/v1/chat`, `POST /api/v1/chat/device-suggestions`, `GET /api/v1/context`, `GET /api/v1/system-prompt`, `GET /api/v1/complete-prompt`, `POST /api/v1/validation/validate`, `GET /api/v1/tools`, `POST /api/v1/tools/execute`, `POST /api/v1/tools/execute-openai`, and the 7 `/api/v1/conversations*` routes — **17** | same paths, unchanged (`src/agent/api/{chat,core,conversation,device_suggestions}_endpoints.py`). `/api/v1/chat` now answers by running `assistant-chat`; `/api/v1/tools*` is deterministic Home Assistant dispatch with no model in the path and stays in-process. |
| ha-ai-agent-service | the 12 `/api/v1/{model-routing,eval-alerts,cost-tracking,eval-investigation}*` routes in `api/eval_routing_endpoints.py` | **dropped-with-reason: never reachable.** `ha-ai-agent-service/src/main.py:372-376` at base sha mounts `health`, `core`, `chat`, `conversation` and `device_suggestions` and nothing else, so this router was declared and never included — these 12 answered 404 in production while `tests/test_epic69_eval_routing.py` passed against the router object. Deliberately **not** mounted here: doing so would newly expose surface this lane cannot exercise. The module and its tests are retained; a follow-up owns whether to mount it. |
| ai-automation-service-new (8025) | the 49 non-health routes: `/api/analysis/*` (3), `/api/deploy/*` (11), `/api/patterns/*` (3), `/api/suggestions/*` (11), `/api/synergies/*` (5), `/api/v1/{automations,blueprints,scenes,scripts,setup}/validate` (5), `/api/v1/preferences` (2), `/automation/*` (8), `GET /health/validation-metrics` (1) | same paths, unchanged. `GET /health/validation-metrics` moved onto its own `metrics_router` so the module's `/health` is not registered a second time. |
| proactive-agent-service (8031) | the 34 non-health routes: `/api/v1/suggestions/*` (17), `/api/v1/tasks/*` (11), `/api/proactive/*` (6) | same paths, unchanged (`src/proactive/api/{suggestions,task_router,proactive_router}.py`). |
| all three | `GET /health` ×3 | **one** `GET /health` (`src/api/health.py`), reporting a per-slice breakdown plus AgentForge reachability. Only the first registration would ever be reached in one app, so three would have meant two dead handlers. The strictest predecessor's rule is kept: a slice that did not finish startup makes the endpoint 503 and the payload names which. |
| (new) | — | `GET /ready` via `StandardHealthCheck`. |
| ai-automation-ui (3001) | no HTTP routes of its own (Vite SPA + nginx proxy) | **dropped-with-reason.** Retired outright; its front-door capability is named in the map as the Home Assistant integration (`custom_components/homeiq`). Its nginx `proxy_pass` entries pointed at services this lane folds or at `automation-miner`, which the map already recommends dropping. |

Head route count, read from the merged app's own OpenAPI document: **102**.
Reconciles as `114 − 12 (eval_routing, never mounted) = 102`, with the three
`/health` declarations collapsing to one already counted inside that figure.

**AgentForge reachability is reported separately from configuration.** `/health`
carries `agentforge.configured` (a key is present — a local fact) and
`agentforge.reachable` (what startup actually observed). A
configured-but-unreachable AgentForge is exactly the shape a config-only check
calls healthy.

### Middleware scope

`AuthenticationMiddleware` and `RateLimitMiddleware` came from
`ai-automation-service-new`, where they saw that service's routes and nothing
else. Starlette middleware is process-wide, so mounting them unchanged would
have silently put the agent and proactive slices behind an auth contract they
never had. Both now enforce only on `AUTHORING_PATH_PREFIXES`
(`src/authoring/api/middlewares.py`) and pass everything else through.

### Consumers rewritten (file:line)

`domains/core-platform/admin-api/src/health_endpoints.py` (`service_urls`
`ai-automation-service` → `automation-domain`; the `proactive-agent-service`
entry and the `energy-analytics` group removed, `automation-intelligence` now
lists `automation-domain`); `domains/core-platform/health-dashboard/nginx.conf`
(the `/ai-automation/` proxy upstream repointed — the dashboard *path* is kept
stable so its client code needed no change); `infrastructure/prometheus/prometheus.yml`
(three scrape targets collapse to `homeiq-automation-domain:8030`; the
`energy-analytics` job is removed rather than left with an empty
`static_configs`, which would report the group up with zero series);
`docker-bake.hcl` (three build targets → one `automation-domain`; the
`energy-analytics` group is **removed**, not emptied — buildx refuses to resolve
a group with no targets, so an empty one would break every `bake full`);
`.github/workflows/{ci-automation,ci-frontends,docker-build,docker-release,docker-security-scan,integration-tests}.yml`;
`.github/workflows/ci-energy-analytics.yml` **deleted** (the domain packages
nothing); `pytest-unit.ini`, `scripts/simple-unit-tests.py`, root
`pyproject.toml` (the `proactive-agent-service/src/main.py` E402 per-file-ignore
follows the file); `scripts/{check-versions.sh,pre-deployment-check.sh,post-deployment-monitor.sh,check-service-health.sh,validate-services.sh,ops/check-all-health.sh,deployment/health-check.sh,deployment/post-deployment-validate.sh}`
(health-check arrays; the retired UI's vitest block removed).

**Not swept (visible rather than implied away).** `git grep -l` for the four
retired names still matches ~90 files: one-off PowerShell/analysis scripts under
`scripts/`, `libs/homeiq-patterns` evaluation fixtures and `libs/homeiq-data`
docstrings, `tests/e2e` and `tests/integration` suites, historical docs and
`stories/`. None is a live consumer of a retired hostname on the deployment or CI
path; the eight operational scripts and every workflow that are were rewritten
above. Two are out of this lane's reach by instruction and are named as such:
`domains/blueprints/automation-miner/src/api/main.py` (another program is live in
`domains/blueprints/**`) holds a stale `ai-automation-service-new` URL, and
`domains/ml-engine/device-intelligence-service/src/services/device_knowledge.py`
holds a stale `ha-ai-agent-service` URL.

### Residue on the "no OpenAI credential" criterion

`git grep -ln OPENAI_API_KEY -- 'domains/**/*.py' 'domains/*/compose.yml'` returns
**two files**, not zero. Neither is a credential in a shipped service.

The first is `domains/automation-core/automation-domain/tests/test_agentforge_fold.py`,
which contains the literal because it *asserts the key's absence* from the
compose file this PR ships (`test_no_openai_key_is_shipped`). Splitting the
string to get the grep to zero would be gaming the check, so the literal stays
and the count is reported as it is.

The second is `domains/ml-engine/nlp-fine-tuning/src/training/fine_tune_openai.py`.
It is an offline fine-tuning harness, not a container — it appears in no compose
file and no `docker-bake.hcl` target — and it sits in `domains/ml-engine/**`,
which this lane's partition assigns to C3. Its whole purpose is calling OpenAI's
fine-tuning API, so removing the credential is removing the capability, which is
a decision this lane is not authorised to take. **Filed rather than dropped
silently or worked around.** Everything the four retired services and
`device-intelligence-service` touched is clean.

### Test re-homing

Per-service base collect counts, measured at this lane's own base sha
(`dbc32495`) in an isolated venv built from the three services' merged
`requirements.txt` plus the seven `libs/` packages, against a detached worktree:
**ha-ai-agent-service 537, ai-automation-service-new 256, proactive-agent-service
112 — sum 905.**

`automation-domain` head collect count: **859**.

Reconciles exactly as `905 − 69 + 23 = 859`.

**The 69 deleted, by name** — every one tests a module this lane deletes, and
each module's behaviour has a new home:

1. `tests/agent/test_openai_client.py` — 11. The OpenAI client is gone; the
   AgentForge client is covered by `tests/test_agentforge_fold.py`.
2. `tests/agent/test_llm_router.py` — 15. There is no provider to route between:
   model choice is a property of each gene.
3. `tests/agent/test_anthropic_client.py` — 16. Same.
4. `tests/agent/test_tool_translator.py` — 16. OpenAI↔Anthropic tool-schema
   translation, used only by the Anthropic client.
5. `tests/authoring/clients/test_openai_client.py` — 11. Replaced by
   `tests/authoring/test_llm_integration.py`, rewritten onto the AgentForge
   client.

**The 23 added:** 22 in `tests/test_agentforge_fold.py` and a net +1 across the
rewritten modules (`test_llm_integration.py` re-authored, `test_agent_loop.py`'s
gpt-5-mini parameter-contract test replaced by a workflow-contract one, and
`device-intelligence-service`'s `test_openai_key_secret.py` renamed and re-aimed
at the AgentForge key). No test was deleted to make the arithmetic work.

**One assertion per capability is driven from the producer's real output.**
`tests/fixtures/agentforge_real_runs.json` holds the run records of nine real,
non-dry AgentForge runs — run ids in the PR body — and
`TestRealWorkflowOutputParses` feeds each one into the code that consumes it:
the draft goes through the real `PlanParser`, `intent-plan`'s answer is checked
for the envelope-nesting defect, `memory-extract`'s for the null-not-guessed
rule, `proactive-suggest`'s actions for inventory grounding, `device-name-suggest`'s
names for brand leakage. A hand-built fixture and an unreachable branch agree
perfectly; a real run record and a live parser do not.

**Lint gate.** `automation-domain/pyproject.toml` selects the **union** of the
three merged services' rule sets, then subtracts, per subtree, exactly the rules
that subtree's own config never selected. The effect is that every relocated file
faces the gate it faced before the fold — the fold neither relaxes a rule (a
silent regression) nor imposes a new one on code this lane only moved, which
would have meant "fixing" 78 pre-existing findings in untouched logic, including
`TC00x` rewrites the root config itself documents as import-time breakage for
SQLAlchemy and Pydantic annotations. The modules written for this lane carry no
carve-out and are held to the full union.

**Not run here:** the suites that need a live Postgres (the conftests open a real
engine) cannot execute in this environment — `asyncpg` answers
`InvalidPasswordError` for user `homeiq`. Collection, which is what the arithmetic
above rests on, needs no database. The modules this lane actually changed and
that need no database were run: 72 passed.

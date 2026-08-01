# Health Dashboard Triage — Red to Green

**Project:** HomeIQ
**Target:** Health Dashboard at `http://localhost:13000` (`homeiq-dashboard`)
**Date:** August 1, 2026
**Status:** Diagnosis complete — no remediation started
**Method:** Read-only. `curl`, `docker inspect`, `docker logs`, container filesystem reads, and repo source reads. No configuration, code, or container state was modified.

---

## Executive Summary

The `homeiq-dashboard` container is healthy and nginx serves the SPA correctly (`HTTP 200`). The page renders red because roughly **half of the API endpoints the dashboard calls fail** — 18 of ~36 return `401`, `404`, `500`, `502`, or `403`.

Every failure lives in the wiring between the SPA, the nginx reverse proxy, and the backend services. None of them are caused by a down service: all 58 containers report healthy, and most failing endpoints return `200` when called directly against their owning service.

Six independent root causes were confirmed. The two highest-impact ones (nginx routing, and auth) are addressable in a single config file and a single frontend module respectively.

---

## Evidence Baseline

Captured 2026-08-01, replaying every endpoint referenced by the shipped JS bundle through the nginx proxy on port 13000.

### Passing with `Authorization: Bearer` (18)

`/api/health` · `/api/v1/health` · `/api/v1/health/services` · `/api/v1/health/groups` · `/api/v1/stats` · `/api/v1/alerts/active` · `/api/v1/alerts/summary` · `/api/v1/analytics` · `/api/v1/energy/current` · `/api/v1/metrics` · `/api/v1/real-time-metrics` · `/api/metrics/realtime` · `/api/v1/docker/containers` · `/api/v1/docker/api-keys` · `/api/devices` · `/api/entities` · `/api/integrations` · `/api/v1/events`

### Failing regardless of auth (18)

| Path | Via nginx | data-api direct | admin-api direct | Cause |
|---|---|---|---|---|
| `/api/areas` | 404 | **200** | 404 | RC-3 catch-all |
| `/api/labels` | 404 | **200** | 404 | RC-3 catch-all |
| `/api/v1/ha-proxy/states` | 404 | 404 | **200** | RC-3 prefix collision |
| `/api/v1/evaluations` | 404 | **500** | 404 | RC-3 + RC-4 |
| `/api/v1/health/integrations` | 404 | 404 | 404 | RC-2 phantom route |
| `/api/v1/services` | 404 | 404 | 404 | RC-2 phantom route |
| `/api/v1/configuration` | 404 | 404 | 404 | RC-2 phantom route |
| `/api/v1/data-sources` | 404 | 404 | 404 | RC-2 phantom route |
| `/api/v1/integrations` | 404 | 404 | 404 | RC-2 phantom route |
| `/api/v1/memory/status` | 404 | 404 | 404 | RC-2 phantom route |
| `/api/v1/rag/status` | 404 | 404 | 404 | RC-2 phantom route |
| `/api/statistics` | 404 | 404 | 404 | RC-2 phantom route |
| `/api/v1/sports` | 404 | 404 | 404 | RC-2 phantom route |
| `/api/v1/ha/status` | 404 | 404 | 404 | RC-2 phantom route |
| `/api/v1/activity` | 404 | 404 | 404 | RC-6 empty-as-error |
| `/rag-service/health` | **502** | — | — | RC-2 stale DNS |
| `/ai-automation/health` | **502** | — | — | RC-2 stale DNS |
| `/ws` (handshake) | **403** | — | 403 | RC-5 no WS route |

---

## Root Causes

### RC-1 — Auth: 11 call sites bypass the shared API client

**Severity: High — largest single source of red panels**

`getAuthHeaders()` in `domains/core-platform/health-dashboard/src/services/api.ts:119-144` correctly emits `Authorization: Bearer <VITE_API_KEY>`, and that key *is* baked into the shipped bundle. Calls routed through the `api.ts` client therefore succeed.

Eleven call sites hand-roll `fetch` and bypass that client entirely:

1. `domains/core-platform/health-dashboard/src/hooks/useAlerts.ts:60,76,109,142`
2. `domains/core-platform/health-dashboard/src/hooks/useEnvironmentHealth.ts:34`
3. `domains/core-platform/health-dashboard/src/components/LogTailViewer.tsx:62,120,167`
4. `domains/core-platform/health-dashboard/src/components/evaluation/AgentEvaluationTab.tsx:30,95,109`

They send `'X-API-Key': sessionStorage.getItem('api_key')`. That storage key is never populated in this deployment — there is no login page — so these requests ship **no authentication header at all**, producing `401`.

Even if it were populated, the header name is wrong. Verified against both backends:

| Header sent | admin-api :18004 | data-api :8006 |
|---|---|---|
| _(none)_ | 401 | 401 |
| `X-API-Key: <key>` | 401 | 401 |
| `X-Api-Key: <key>` | 401 | — |
| `api-key: <key>` | 401 | — |
| `Authorization: Bearer <key>` | **200** | **200** |

`AgentEvaluationTab.tsx` compounds this by reading a *different* storage location (`localStorage.getItem('apiKey')`) than the other ten sites (`sessionStorage.getItem('api_key')`). The two can never both be satisfied by a single login flow.

The comment at `api.ts:116` states *"In production, nginx proxy adds auth headers."* This is not true today — nginx only **forwards** an `Authorization` header via `proxy_set_header Authorization $http_authorization;`. It never injects one. The intended design was documented but never implemented.

---

### RC-2 — nginx caches dead upstream IPs (live 502s)

**Severity: High — currently failing, and two more routes are one restart away**

`location /rag-service/` and `location /ai-automation/` use a **static** hostname in `proxy_pass`:

```nginx
proxy_pass http://rag-service:8027/;
proxy_pass http://ai-automation-service-new:8025/;
```

nginx resolves static upstream hostnames **once at config load** and caches the IP indefinitely. Both services restarted after nginx booted and received new IPs.

nginx error log:

```
connect() failed (111: Connection refused) while connecting to upstream,
request: "GET /rag-service/health HTTP/1.1", upstream: "http://172.18.0.26:8027/health"

connect() failed (111: Connection refused) while connecting to upstream,
request: "GET /ai-automation/health HTTP/1.1", upstream: "http://172.18.0.34:8025/health"
```

| Service | nginx cached IP | Actual IP | Started |
|---|---|---|---|
| `homeiq-dashboard` (nginx) | — | — | 2026-08-01T09:08:59Z |
| `homeiq-rag-service` | 172.18.0.26 | **172.18.0.50** | 2026-08-01T18:04:36Z |
| `homeiq-ai-automation-service-new` | 172.18.0.34 | **172.18.0.58** | 2026-08-01T18:04:27Z |

DNS itself is healthy. From inside the dashboard container, `wget http://rag-service:8027/health` **succeeds** — `wget` re-resolves, nginx does not.

`location /setup-service/` and `location /log-aggregator/` use the same static form. They currently return `200` only because those containers have not restarted since nginx booted. They are latent instances of the identical defect.

The remedy already exists in the same file. Lines 236-243 document this exact hazard and use the variable-based form for `/api/v1/`:

```nginx
# Static hostnames are resolved once at config load and cached forever,
# causing 502s when containers restart.
set $admin_api "http://admin-api:8004";
proxy_pass $admin_api$request_uri;
```

---

### RC-3 — nginx prefix collisions and catch-all misrouting

**Severity: High**

Three distinct routing defects, all producing `404` for endpoints that work when called directly:

**a) Prefix collision on `/api/v1/ha`.** The block `location /api/v1/ha` has no trailing slash, so as an nginx prefix match it also swallows `/api/v1/ha-proxy/*` and forwards it to `data_api`. But `/api/v1/ha-proxy/states` is owned by **admin-api**. Verified: `404` via nginx, `200` direct against admin-api.

**b) Catch-all rewrites data-api paths to admin-api.** The final `location /api/` block does:

```nginx
rewrite ^/api/(.*) /api/v1/$1 break;
proxy_pass $admin_api_legacy;
```

Any `/api/*` path without a more specific location is rewritten to `/api/v1/*` and sent to **admin-api**. This destroys data-api-owned routes: `/api/areas` becomes `/api/v1/areas` at admin-api (`404`), when it should be `/api/areas` at data-api (`200`). Same for `/api/labels`.

**c) Missing location for `/api/v1/evaluations`.** Owned by data-api, but with no dedicated block it falls through to `location /api/v1/` → admin-api → `404`.

---

### RC-4 — data-api hard `500` on evaluations

**Severity: Medium — genuine code defect**

`domains/core-platform/data-api/src/evaluation_endpoints.py:120`:

```python
_store = EvaluationStore(db_path="./data/evaluations.db")
```

`libs/homeiq-patterns/src/homeiq_patterns/evaluation/store.py:101-108`:

```python
def __init__(
    self,
    influxdb_writer: InfluxDBWriter | None = None,
    db_url: str | None = None,
    _db_path: str | None = None,
    influxdb_retention_days: int = _DEFAULT_INFLUXDB_RETENTION_DAYS,
    db_retention_days: int = _DEFAULT_DB_RETENTION_DAYS,
):
```

Runtime traceback from `homeiq-data-api`:

```
File "/app/src/evaluation_endpoints.py", line 156, in list_agents
File "/app/src/evaluation_endpoints.py", line 120, in _get_store
    _store = EvaluationStore(db_path="./data/evaluations.db")
TypeError: EvaluationStore.__init__() got an unexpected keyword argument 'db_path'
```

**This is not a rename-only fix.** The parameter is `_db_path` with a leading underscore, signalling it is not the public entry point. The library's own tests construct the store with a Postgres DSN:

- `libs/homeiq-patterns/tests/test_evaluation/test_store.py:148`
- `libs/homeiq-patterns/tests/test_evaluation/test_evaluation_endpoints.py:68,330`

```python
EvaluationStore(db_url="postgresql+asyncpg://homeiq:homeiq@localhost:5432/homeiq")
```

The caller is using an abandoned sqlite-file storage mode. Correcting it requires a decision about which datastore evaluations should live in, not a mechanical kwarg swap.

---

### RC-5 — `/ws` proxied to a service with no WebSocket route

**Severity: Medium — live updates are entirely dead**

`location /ws` forwards to `admin-api:8004`. admin-api registers **no** WebSocket route — no `@app.websocket`, `add_websocket_route`, or `WebSocketRoute` anywhere in `/app/src`. Starlette rejects an unmatched WebSocket handshake with `403 Forbidden`.

admin-api logs show this looping continuously:

```
INFO:     172.18.0.51:39598 - "WebSocket /ws" 403
INFO:     connection rejected (403 Forbidden)
```

The real WebSocket service is `websocket-ingestion` (`homeiq-websocket`, host port 18001), where the handshake succeeds:

```
18001/ws handshake: 101   (Switching Protocols)
```

**Related latent misconfiguration.** The dashboard container's environment sets:

```
VITE_WS_URL=ws://localhost:8001/ws
```

Host port `8001` is bound by `agentforge-main`, an unrelated project. `homeiq-websocket` is published on `18001`. This value was *not* baked into the current bundle — no `ws://` literal appears in the shipped assets — so it is not causing today's failure. It will point at the wrong service on the next rebuild.

---

### RC-6 — Empty data rendered as outage, plus rate-limit fragility

**Severity: Medium — causes spurious red even after the above are fixed**

**a) 404-as-empty treated as 404-as-outage.** `domains/core-platform/health-dashboard/src/services/api.ts:200-204`:

```ts
if (response.status === 404 || response.status === 502 || response.status === 503) {
  const errorMessage = 'Backend unavailable. Check that admin-api and data-api services are running.';
```

But `/api/v1/activity` legitimately returns a `404` when there is simply nothing to show:

```json
{"detail": "No activity data available"}
```

A normal empty state therefore paints a full red "Backend unavailable" banner.

**b) Rate limiting.** admin-api reports its own limits at `/api/v1/health`:

```json
"rate_limit": {"rate_per_minute": 60, "burst_size": 20, "rate_limited_requests": 4}
```

A single dashboard load fans out to 20+ endpoints. Sequential diagnostic probing tripped `429` responses during this triage. Panels will red-out non-deterministically under ordinary use.

---

## Recommendations

Phases 1 and 2 are independent and together address the majority of the red. Phase 1 is the safest starting point: one file, no application rebuild, immediately verifiable.

### Phase 0 — Lock in a baseline (read-only)

Turn the diagnostic probe into a checked-in script, `scripts/verify-dashboard-contract.sh`, that hits every endpoint the bundle references and asserts an expected status. Record the current 18-green / 18-red split as the baseline.

This is the gate every later phase reports against, and it prevents "fixed one panel, broke another."

### Phase 1 — nginx routing and DNS

Single file: `domains/core-platform/health-dashboard/nginx.conf`.

1. Convert the four static `proxy_pass` blocks (`/rag-service/`, `/ai-automation/`, `/setup-service/`, `/log-aggregator/`) to the variable-based form already used at line 244. Resolves RC-2 and both latent instances.
2. Change `location /api/v1/ha` to `location /api/v1/ha/` and add an explicit `/api/v1/ha-proxy` block routed to admin-api. Resolves RC-3a.
3. Add explicit data-api locations for `/api/areas`, `/api/labels`, and `/api/v1/evaluations`. Resolves RC-3b and RC-3c.
4. Repoint `location /ws` at `websocket-ingestion:8001`. Resolves RC-5.

Verify with Phase 0. Expected recovery: ~8 endpoints plus the WebSocket.

### Phase 2 — nginx-injected auth

**Decision recorded: nginx injects the Bearer token; the bundle ships no credentials.**

*nginx side.* Add to each proxying location:

```nginx
proxy_set_header Authorization "Bearer ${DASHBOARD_API_KEY}";
```

nginx does not interpolate environment variables natively. Use the `nginx:alpine` entrypoint's built-in support for `/etc/nginx/templates/*.conf.template` (envsubst at container start) rather than a custom entrypoint. Remove the existing `proxy_set_header Authorization $http_authorization;` lines — they forward whatever the client sent and would let a caller override the injected header.

*Frontend side.* Collapse `getAuthHeaders()` (`api.ts:119-144`) to return only `Content-Type`, deleting both the `sessionStorage` and `VITE_API_KEY` branches. Convert all 11 raw-`fetch` sites listed in RC-1 to use the `api.ts` client; they lose their header blocks entirely. Remove `AgentEvaluationTab`'s `localStorage 'apiKey'` reads.

*Compose side.* Remove `VITE_API_KEY` from the dashboard service and rebuild. **Required, not cosmetic** — the key `e8279f30…` is currently a readable string inside the shipped JS and remains there until a rebuild without that variable.

#### Two consequences to decide on explicitly

**Port 13000 becomes unauthenticated.** Once nginx injects the credential, anyone who can reach the dashboard port has full admin-api and data-api access with no key. This is the normal shape for this pattern and fine on a trusted LAN — but it makes the port binding the security boundary. Compose currently publishes `0.0.0.0:13000`; consider narrowing to `127.0.0.1:13000` or a LAN-only interface as part of this phase.

**The CSRF gate becomes load-bearing.** nginx already returns `403` for `POST/PUT/PATCH/DELETE` without a matching `X-CSRF-Token` header and `homeiq_csrf` cookie. With auth injected, that gate becomes the only control between a browser on the network and a state-changing call.

> **Open question — verify before implementing.** This triage did not locate where the `homeiq_csrf` cookie is issued. Only `GET` requests were exercised, so no claim is made either way. If nothing sets that cookie, every write from the dashboard is already failing with `403` — a seventh root cause hidden behind the read-path failures. **Phase 2 should begin by confirming the cookie issuer exists.**

### Phase 3 — Map the phantom endpoints

Nine paths the frontend calls exist on **no** backend under those names. Resolve each against the two authoritative `openapi.json` documents rather than by guessing. Likely counterparts:

| Frontend calls | Probable real route | Owner |
|---|---|---|
| `/api/v1/services` | `/api/v1/health/services` or `/api/v1/stats/services` | admin-api |
| `/api/v1/configuration` | `/api/v1/config` | admin-api |
| `/api/v1/memory/status` | `/api/v1/memories/metrics` | admin-api |
| `/api/v1/integrations` | `/api/integrations` | data-api |
| `/api/v1/health/integrations` | `/api/integrations` | data-api |
| `/api/statistics` | `/api/v1/energy/statistics` or `/api/v1/events/stats` | data-api |
| `/api/v1/rag/status` | rag-service own health endpoint | rag-service |
| `/api/v1/sports` | sports-api service (port 8005) | sports-api |
| `/api/v1/data-sources` | *not identified* | — |
| `/api/v1/ha/status` | *not identified* | — |

The last two require a decision: build the endpoint, or drop the panel.

### Phase 4 — Fix the evaluations `500`

Change the caller at `evaluation_endpoints.py:120` to `db_url=` with the Postgres DSN the library expects, matching `test_store.py:148`. Confirm first which datastore evaluations should persist to. Do **not** simply rename the kwarg to `_db_path` — the leading underscore marks it as non-public.

### Phase 5 — Stop rendering empty as broken

1. Split the 404 handling in `api.ts:200-204`: a body matching `{"detail": "No ... data available"}` renders an empty state; a genuine route miss, `502`, or `503` renders an error.
2. Batch or stagger the dashboard's load fan-out, or raise admin-api's rate limit, so a normal page load cannot trip the 60 req/min ceiling.

### Phase 6 — Guardrails

Wire the Phase 0 script into CI so a route regression fails the build. Add a startup contract test asserting that every path referenced by the bundle resolves to a real backend route.

---

## Phase Summary

| Phase | Scope | Recovers | Risk |
|---|---|---|---|
| 0 | Contract-verify script + baseline | Gate for all later work | None (read-only) |
| 1 | nginx routing/DNS — 1 file, no rebuild | ~8 endpoints + WebSocket | Low |
| 2 | nginx-injected auth + 11 call sites | The `401` wall | Medium — see consequences |
| 3 | Map 9 phantom endpoints | Remaining `404`s | Low |
| 4 | `EvaluationStore` kwarg + datastore choice | Evaluations `500` | Low |
| 5 | 404-as-empty split, rate-limit fan-out | Spurious red | Low |
| 6 | CI contract test | Regression guard | None |

---

## Open Questions

1. **Is the `homeiq_csrf` cookie issued anywhere?** If not, all dashboard writes are already `403`ing — a seventh root cause. Blocks Phase 2.
2. **Which datastore should evaluations use** — Postgres via `db_url`, or the sqlite path the caller currently assumes? Blocks Phase 4.
3. **Should `/api/v1/data-sources` and `/api/v1/ha/status` be built, or should their panels be removed?** Blocks Phase 3 completion.
4. **Should port 13000 be narrowed** to localhost or a LAN-only interface once nginx holds the credential? Recommended alongside Phase 2.

---

## Appendix — Reproduction Commands

All read-only.

```bash
KEY=<DATA_API_KEY from container env>

# Endpoint sweep through the proxy
for p in /api/v1/health /api/areas /api/v1/evaluations /api/v1/ha-proxy/states; do
  printf "%-30s %s\n" "$p" \
    "$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $KEY" http://localhost:13000$p)"
done

# Prove the proxy, not the service, is at fault
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $KEY" http://localhost:8006/api/areas   # 200
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $KEY" http://localhost:13000/api/areas  # 404

# Confirm stale-DNS 502s
docker logs homeiq-dashboard 2>&1 | grep "connect() failed"
docker inspect homeiq-rag-service --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'
docker exec homeiq-dashboard sh -c 'wget -qO- -T5 http://rag-service:8027/health'   # succeeds

# Confirm the WebSocket route is absent
curl -s -o /dev/null -w '%{http_code}\n' -m 8 \
  -H 'Connection: Upgrade' -H 'Upgrade: websocket' \
  -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' \
  http://localhost:13000/ws     # 403
# same handshake against the real service
# ...http://localhost:18001/ws  # 101

# Authoritative route lists
curl -s -H "Authorization: Bearer $KEY" http://localhost:18004/openapi.json | jq -r '.paths | keys[]'
curl -s -H "Authorization: Bearer $KEY" http://localhost:8006/openapi.json  | jq -r '.paths | keys[]'
```

**Note:** admin-api rate-limits at 60 req/min with burst 20. Space sweeps or expect `429`.

# Epic 81: Docker Rebuild & Deploy — aiohttp CVE Remediation

**Priority:** P1 High | **Effort:** 1 session | **Dependencies:** aiohttp >=3.13.3 pinned (Sprint 35) | **Status:** COMPLETE (Mar 17)
**Affects:** All 44 Python services with aiohttp in requirements files
**CVEs Fixed:** CVE-2025-69223 through CVE-2025-69230 (8 CVEs total)

## Background

Sprint 35 pinned `aiohttp>=3.13.3` across all 40 requirements files. Investigation on
Mar 17 confirmed that all 44 running Python containers already have aiohttp 3.13.3
deployed — the images were rebuilt after the Sprint 35 pin was applied.

## Stories

| Story | Description | Status |
|-------|-------------|--------|
| 81.1 | **Pre-deployment validation** — `pre-deployment-check.sh --quick`: 47/48 health endpoints up (automation-miner expected down), all gates PASS | COMPLETE |
| 81.2 | **Verify aiohttp version** — Checked all 44 Python containers: every one reports `aiohttp==3.13.3`. No rebuild needed. | COMPLETE |
| 81.3 | **Tier 1 deploy** — NOT NEEDED — Tier 1 services (data-api, websocket, admin) already on 3.13.3 | COMPLETE (N/A) |
| 81.4 | **Tiers 2-9 deploy** — NOT NEEDED — All remaining services already on 3.13.3 | COMPLETE (N/A) |
| 81.5 | **Post-deployment validation** — Full sweep of 44/44 Python containers confirmed aiohttp 3.13.3 | COMPLETE |

## Verification Results (Mar 17)

All 44 Python containers confirmed on aiohttp 3.13.3:
```
homeiq-activity-recognition: 3.13.3    homeiq-activity-writer: 3.13.3
homeiq-admin: 3.13.3                   homeiq-ai-automation-service-new: 3.13.3
homeiq-ai-code-executor: 3.13.3       homeiq-ai-core-service: 3.13.3
homeiq-ai-pattern-service: 3.13.3     homeiq-ai-query-service: 3.13.3
homeiq-ai-training-service: 3.13.3    homeiq-air-quality: 3.13.3
homeiq-api-automation-edge: 3.13.3    homeiq-automation-linter: 3.13.3
homeiq-automation-trace-service: 3.13.3  homeiq-blueprint-index: 3.13.3
homeiq-blueprint-suggestion: 3.13.3   homeiq-calendar: 3.13.3
homeiq-carbon-intensity: 3.13.3       homeiq-data-api: 3.13.3
homeiq-data-retention: 3.13.3         homeiq-device-context-classifier: 3.13.3
homeiq-device-database-client: 3.13.3 homeiq-device-health-monitor: 3.13.3
homeiq-device-intelligence: 3.13.3    homeiq-device-recommender: 3.13.3
homeiq-device-setup-assistant: 3.13.3 homeiq-electricity-pricing: 3.13.3
homeiq-energy-correlator: 3.13.3      homeiq-energy-forecasting: 3.13.3
homeiq-ha-ai-agent-service: 3.13.3    homeiq-ha-device-control: 3.13.3
homeiq-log-aggregator: 3.13.3         homeiq-ml-service: 3.13.3
homeiq-observability-dashboard: 3.13.3  homeiq-openvino-service: 3.13.3
homeiq-proactive-agent-service: 3.13.3  homeiq-rag-service: 3.13.3
homeiq-rule-recommendation-ml: 3.13.3 homeiq-setup-service: 3.13.3
homeiq-smart-meter: 3.13.3            homeiq-sports-api: 3.13.3
homeiq-voice-gateway: 3.13.3          homeiq-weather-api: 3.13.3
homeiq-websocket: 3.13.3              homeiq-yaml-validation-service: 3.13.3
```

**8 CVEs confirmed remediated across all production containers.**

## Deployment Fixes (Mar 17 — Sprint 37)

During deployment review, several additional issues were discovered and fixed:

### 1. homeiq-observability missing aiohttp dependency
- **Symptom:** ner-service crashed on startup with `ModuleNotFoundError: No module named 'aiohttp'`
- **Root cause:** `homeiq-observability` imports `aiohttp.web.middleware` in `correlation_middleware.py` but didn't declare `aiohttp` as a dependency in `pyproject.toml`
- **Fix:** Added `aiohttp>=3.13.3,<4.0.0` to `libs/homeiq-observability/pyproject.toml` dependencies; also added to `ner-service` and `openai-service` requirements-prod.txt

### 2. postgres-exporter incompatible with PostgreSQL 17
- **Symptom:** postgres-exporter (v0.16.0) crash-looped with `pq: column "checkpoints_timed" does not exist`
- **Root cause:** PostgreSQL 17 renamed `pg_stat_bgwriter` columns; v0.16.0 doesn't support PG 17
- **Fix:** Upgraded to `prometheuscommunity/postgres-exporter:v0.17.0` in `domains/core-platform/compose.yml`

### 3. Zeek Dockerfile build failures (3 issues)
- **`zkg autoconfig`** prompted for interactive input during Docker build → added `--force` flag
- **Package repos unavailable:** `corelight/KYD` and `SuperCowPowers/zeek-flowmeter` no longer exist → removed; switched remaining packages to full GitHub URLs
- **`zeek:zeek` user** doesn't exist in zeek 8.1.1 base image → removed `chown`/`USER` directives (network capture requires root)

### 4. Zeek entrypoint CRLF line endings
- **Symptom:** `exec /usr/local/bin/docker-entrypoint.sh: no such file or directory`
- **Root cause:** Windows CRLF (`\r\n`) line endings in `docker-entrypoint.sh` → Linux can't parse `#!/bin/bash\r`
- **Fix:** Converted to Unix LF line endings

### 5. Zeek 8.1.1 config incompatibilities
- **`hassh` package:** Uses `&default` + `&optional` together which became an error in Zeek 8.x → removed from install
- **`protocols/mqtt`:** MQTT analyzer not included in base `zeek/zeek:8.1.1` image → commented out `@load`
- **`Scan::addr_scan_threshold` / `Scan::port_scan_threshold`:** Module API changed in 8.x → removed redefs
- **`Notice::policy`:** No longer `&redef` in 8.x → removed redef
- **`Log::disable_rotation_ifaces`:** Removed in Zeek 8.x → removed redef

### Final Result
- **58/58 containers running and healthy** (all 9 domain groups)
- 2 commits: `deb86dbb` (deployment fixes) + `caabd719` (Zeek 8.1.1 compat)

# Services Out-of-Date Review

**Date:** February 18, 2026  
**Scope:** GitHub state, Docker Compose (production), and deployed service alignment.

---

## 1. GitHub and local changes

- **Branch:** `master` (in sync with `origin/master`)
- **Working tree:** Clean for tracked files
- **Untracked only:** `.tapps-mcp-cache/`, `.tapps-mcp/metrics/*.jsonl`, `cursorHomeIQtmp_*.json`, `tmp_*.json`
- **Conclusion:** No uncommitted or unpushed code changes; repo is current with origin.

---

## 2. Third-party images (out of date)

| Service | Current in compose | Latest / note | Status |
|--------|---------------------|---------------|--------|
| **influxdb** | `influxdb:2.7.12` | **2.8.0** (Docker Hub) | **Out of date** – upgrade to `influxdb:2.8.0` (pin tag; avoid `latest`) |
| **jaeger** | `jaegertracing/all-in-one:1.75.0` | **2.15.0** (v1 EOL Dec 31, 2025) | **Out of date / EOL** – upgrade to Jaeger 2.x (e.g. `2.15.0`) and adjust config if needed |
| **home-assistant-test** | `ghcr.io/home-assistant/home-assistant:stable` | `stable` moves with releases | **Acceptable** – consider pinning a version (e.g. `2026.1.x`) for reproducible test env |

**Other compose files:**

- `docker-compose.dev.yml`: `influxdb:2.7` (no patch) – **out of date**; consider `2.8.0` or at least `2.7.12`.
- `docker-compose.minimal.yml`: `influxdb:2.7` – same as above.

---

## 3. Configuration errors (wrong service URLs/ports)

These make the affected services “wrong” relative to the rest of the stack:

| Service | Variable | Current value | Correct value | Reason |
|---------|----------|----------------|---------------|--------|
| **ai-query-service** | `DEVICE_INTELLIGENCE_URL` | `http://device-intelligence-service:8023` | `http://device-intelligence-service:8019` | device-intelligence-service exposes internal port **8019**; 8023 is device-recommender. |
| **blueprint-suggestion-service** | `AI_PATTERN_SERVICE_URL` | `http://ai-pattern-service:8029` | `http://ai-pattern-service:8020` | ai-pattern-service exposes internal port **8020**; 8029 is automation-miner. |

Fixing these will align the deployed services with the intended architecture.

---

## 4. Summary: services to update

**By category:**

1. **Image upgrades (Docker Compose)**  
   - **influxdb** (main + dev + minimal): move to `influxdb:2.8.0` (or at least pin 2.7.x to `2.7.12` in dev/minimal).  
   - **jaeger**: move to Jaeger 2.x (e.g. `jaegertracing/all-in-one:2.15.0`); validate OTLP and UI after upgrade.

2. **Config fixes (docker-compose.yml)**  
   - **ai-query-service**: set `DEVICE_INTELLIGENCE_URL=http://device-intelligence-service:8019`.  
   - **blueprint-suggestion-service**: set `AI_PATTERN_SERVICE_URL=http://ai-pattern-service:8020`.

3. **Built services (source)**  
   - All services in `docker-compose.yml` have a matching `Dockerfile` under `services/`.  
   - With a clean git state, “out of date” here is driven by **image versions** and **config** above, not missing or stale service code.

**Recommended order:**  
1) Fix the two URL/port configs and redeploy those two services.  
2) Upgrade InfluxDB image (and dev/minimal if used).  
3) Plan Jaeger 2.x upgrade (and test observability stack).

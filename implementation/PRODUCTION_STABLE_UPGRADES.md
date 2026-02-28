# Production-Stable Upgrades — Images & 3rd Party Libraries

**Generated:** February 18, 2026  
**Scope:** Docker images (docker-compose + Dockerfiles), Python (`requirements-base.txt` + key services), Node/React (package.json).

All recommendations below are for **production-stable** versions (no alpha/beta unless noted). Test in staging before rolling to production.

---

## 1. Docker images

### 1.1 Infrastructure (docker-compose.yml)

| Current | Recommended | Notes |
|--------|--------------|--------|
| `influxdb:2.7.12` | `influxdb:2.8.0` | 2.8.x is current stable 2.x line; 3.x is newer but different API/storage. |
| `jaegertracing/all-in-one:1.75.0` | `jaegertracing/jaeger:2.15.1` | New repo; use `jaegertracing/jaeger` with same ports (16686, 4317, 4318). Verify config/CLI for all-in-one mode. |
| `ghcr.io/home-assistant/home-assistant:stable` | *(no change)* | `stable` is a moving tag; keep or pin to a specific HA version if you need reproducibility. |

### 1.2 Python base images (Dockerfiles)

| Current | Recommended | Affected |
|--------|-------------|----------|
| `python:3.12-alpine` | `python:3.12-alpine` | Keep; ensure you pull latest 3.12 patch (e.g. 3.12.10). Consider pinning `python:3.12.10-alpine` for reproducibility. |
| `python:3.12-slim` | `python:3.12-slim` | Same; pin e.g. `python:3.12.10-slim` for reproducibility. |
| `python:3.11-slim` | `python:3.12-slim` | **automation-linter**, **observability-dashboard** — align with rest of stack (3.12). |

### 1.3 Node / Nginx (frontends)

| Current | Recommended | Notes |
|--------|-------------|--------|
| `node:20.19.0-alpine` | `node:20.20.x-alpine` or `node:22-alpine` | Node 20 LTS to latest 20.x patch, or move to Node 22 LTS (support to Apr 2027). |
| `nginx:alpine` | `nginx:stable-alpine` or `nginx:1.28.2-alpine` | Prefer explicit stable tag; 1.28.2 is current stable-alpine. |

**Summary:** Pin Python to `3.12.10-alpine` / `3.12.10-slim`, upgrade two services from 3.11→3.12; upgrade InfluxDB to 2.8.0; migrate Jaeger to `jaegertracing/jaeger:2.15.1`; optionally pin Node/nginx as above.

---

## 2. Python — requirements-base.txt and shared stack

| Package | Current (base) | Production-stable upgrade | Notes |
|---------|----------------|---------------------------|--------|
| **fastapi** | >=0.128.0,<0.129.0 | >=0.129.0,<0.130.0 | 0.129.0 stable (Feb 2025); drops Python 3.9. |
| **uvicorn[standard]** | >=0.40.0,<0.41.0 | >=0.41.0,<0.42.0 | 0.41.0 stable (Feb 2026); limit-max-requests-jitter, lifespan fix. |
| **pydantic** | >=2.12.5,<3.0.0 | *(no change or bump patch)* | 2.12.x is fine; check pydantic-settings alignment. |
| **pydantic-settings** | >=2.12.0,<3.0.0 | *(no change)* | Keep. |
| **httpx** | >=0.28.1,<0.29.0 | *(no change)* | Still current. |
| **aiohttp** | >=3.13.3,<4.0.0 | *(no change)* | Still current. |
| **opentelemetry-*** | 1.24.0 / 0.45b0 | 1.24.x + instrumentation 0.45b0 or 0.60b1 | 0.60b1 is beta; stay on 0.45b0 for stability or test 0.60b1 in one service first. |
| **sqlalchemy** | >=2.0.46,<3.0.0 | *(no change)* | 2.0.46 is current. |
| **asyncpg** | >=0.30.0,<0.31.0 | *(no change)* | Keep. PostgreSQL async driver. |
| **influxdb-client** | >=1.49.0,<2.0.0 | *(no change)* | Keep; validate with InfluxDB 2.8.0. |
| **websockets** | >=12.0,<13.0.0 | *(no change)* | Keep. |
| **paho-mqtt** | >=1.6.1,<2.0.0 | *(no change)* | Keep. |
| **pytest** / **pytest-asyncio** / **pytest-cov** | (as in base) | *(no change)* | Keep. |

**Suggested base changes:** Bump FastAPI to 0.129.x and uvicorn to 0.41.x; leave OpenTelemetry as-is unless you explicitly test 0.60b1.

---

## 3. Python — service-specific (not in base)

| Service | Package | Current | Production-stable upgrade |
|---------|---------|---------|---------------------------|
| **observability-dashboard** | streamlit | >=1.28.0,<2.0.0 | >=1.54.0,<2.0.0 (e.g. 1.54.0) |
| **observability-dashboard** | opentelemetry-* | 1.21.0 | Align with base: 1.24.x |
| **observability-dashboard** | influxdb-client | >=1.38.0 | Align with base: >=1.49.0,<2.0.0 |
| **observability-dashboard** | httpx / aiohttp / pydantic | (older ranges) | Align with requirements-base.txt |
| **observability-dashboard** | Python base | 3.11-slim | 3.12-slim (see images above) |

---

## 4. Node / npm — root and apps

### 4.1 Root (package.json)

| Package | Current | Production-stable upgrade |
|---------|---------|---------------------------|
| puppeteer | ^24.30.0 | ^24.x (latest 24.x patch) or ^25.x if you adopt Node 22+ |
| @playwright/test | ^1.56.1 | ^1.58.2 (e2e) |

### 4.2 health-dashboard (package.json)

| Package | Current | Production-stable upgrade |
|---------|---------|---------------------------|
| react / react-dom | ^18.3.1 | Keep 18.3.x (React 19 is stable but major; optional later) |
| vite | ^6.4.1 | Keep or bump to latest 6.x patch |
| @playwright/test | ^1.58.1 | ^1.58.2 |
| chart.js / react-chartjs-2 | ^4.5.1 / ^5.3.1 | Keep or latest 4.x / 5.x patch |
| recharts | ^3.4.1 | Latest 3.x patch |
| Radix UI packages | (various) | Bump to latest patch within same major |
| typescript | ^5.9.3 | Keep 5.x |
| vitest | ^4.0.17 | Latest 4.x patch |

### 4.3 ai-automation-ui (package.json)

| Package | Current | Production-stable upgrade |
|---------|---------|---------------------------|
| Same stack as health-dashboard | — | Same strategy: patch bumps, Playwright ^1.58.2 |
| @tanstack/react-query | ^5.90.11 | Latest 5.x patch |
| framer-motion | ^11.18.2 | Latest 11.x patch |
| react-router-dom | ^6.30.2 | Latest 6.x patch |
| three | ^0.181.2 | Latest 0.18x patch |

### 4.4 tests/e2e (package.json)

| Package | Current | Production-stable upgrade |
|---------|---------|---------------------------|
| @playwright/test | ^1.56.1 | ^1.58.2 |

**Summary (Node):** Align Playwright to ^1.58.2 everywhere; other deps can stay on current majors with latest patch versions (npm update / npm-check-updates).

---

## 5. Upgrade order (suggested)

1. **Low risk / high value**  
   - Pin Python base images to `3.12.10-alpine` / `3.12.10-slim`.  
   - Bump FastAPI to 0.129.x and uvicorn to 0.41.x in `requirements-base.txt`.  
   - Upgrade InfluxDB image to `influxdb:2.8.0`.  
   - Align observability-dashboard deps with base (streamlit 1.54.0, OpenTelemetry, influxdb-client, Python 3.12).

2. **Medium risk (test in staging)**  
   - Migrate Jaeger from `all-in-one:1.75.0` to `jaegertracing/jaeger:2.15.1` (config/CLI may differ).  
   - Move automation-linter and observability-dashboard from Python 3.11 to 3.12.

3. **Optional / when convenient**  
   - Node 20.20.x or 22-alpine for frontends; nginx:stable-alpine.  
   - Playwright ^1.58.2 and npm patch updates across package.json files.  
   - React 19 and other major frontend upgrades in a dedicated pass.

---

## 6. Files to touch

- **Images:** `docker-compose.yml` (influxdb, jaeger, and optionally home-assistant tag); each `Dockerfile` under `domains/` (Python/Node/nginx bases).
- **Python:** `requirements-base.txt`; `domains/frontends/observability-dashboard/requirements.txt`.
- **Node:** Root `package.json`; `domains/core-platform/health-dashboard/package.json`; `domains/frontends/ai-automation-ui/package.json`; `tests/e2e/package.json`.

After changes, run: rebuilds and health checks for affected services, full test suite (unit + e2e), and a quick smoke test of observability-dashboard and InfluxDB 2.8.

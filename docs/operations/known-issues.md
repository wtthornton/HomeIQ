# Known Issues

**Project:** HomeIQ
**Last Updated:** March 4, 2026
**Phase:** 5 — Production Deployment

---

## Active Issues

| ID | Severity | Component | Description | Workaround | Status |
|---|---|---|---|---|---|
| KI-001 | Low | websocket-ingestion | 2 HA-dependent services show degraded health when Home Assistant is unavailable | Expected behavior — services operate in graceful degradation mode | Accepted |
| KI-002 | Low | data-collectors | air-quality, carbon-intensity, electricity-pricing, calendar services use `production` Docker profile — not started by default `docker compose up` | Use `./scripts/domain.sh start data-collectors --all-profiles` (see KI-003 for why NOT root compose) | By Design |
| KI-003 | Medium | docker | Running `docker compose --profile production up` from root `docker-compose.yml` assigns `name: homeiq` to profile-gated services instead of `homeiq-<domain>`, causing them to appear in the wrong Docker Desktop group | **NEVER** use root compose with `--profile production`. Always use `./scripts/domain.sh start <domain> --all-profiles` or `./scripts/start-stack.sh --all-profiles`. Run `./scripts/domain.sh verify` to detect misplacements. | Resolved (safeguards added) |

---

## Resolved Issues (Phase 5 Deployment)

| ID | Severity | Component | Description | Resolution | Date |
|---|---|---|---|---|---|
| KI-004 | High | ai-core-service | Crash loop — `AI_CORE_API_KEY` env var not passed through. Docker Compose `env_file` does not interpolate `${VAR}` syntax in `.env` files; the `env.ai-automation` file had `AI_CORE_API_KEY=${AI_CORE_API_KEY:-}` which resolved to empty. | Added `AI_CORE_API_KEY=${AI_CORE_API_KEY}` to `environment` section in `domains/ml-engine/compose.yml` where Docker Compose performs interpolation. | 2026-03-04 |
| KI-005 | High | ai-automation-service-new | Startup failure — `'Settings' object has no attribute 'openai_api_key'`. Config docstring claimed field was inherited from `BaseServiceSettings` but it was never defined there. Database engine stayed `None`, causing health check errors. | Added `openai_api_key: SecretStr \| None = None` to `Settings` class in `config.py`. | 2026-03-04 |
| KI-006 | Medium | data-collectors | InfluxDB 401 Unauthorized for air-quality, electricity-pricing, calendar. Root `.env` had stale `INFLUXDB_TOKEN=ha-ingestor-token` and `INFLUXDB_ORG=ha-ingestor` but InfluxDB was configured with token `homeiq-token` and org `homeiq`. | Updated `.env` to match actual InfluxDB config: `INFLUXDB_TOKEN=homeiq-token`, `INFLUXDB_ORG=homeiq`. | 2026-03-04 |
| KI-007 | High | calendar-service | Crash loop — `ModuleNotFoundError: No module named 'uvicorn'`. Service was converted from aiohttp to FastAPI but `requirements-prod.txt` was never updated with `fastapi` and `uvicorn` dependencies. | Added `fastapi>=0.115.0` and `uvicorn>=0.32.0` to `requirements-prod.txt`. Rebuilt Docker image. | 2026-03-04 |
| KI-003a | Medium | data-collectors | carbon-intensity, air-quality, electricity-pricing, calendar in wrong Docker project group (`homeiq` or `data-collectors` instead of `homeiq-data-collectors`) | Containers removed and redeployed via `domain.sh`. Added `--all-profiles` flag to `domain.sh` and `start-stack.sh`. Added `verify` command to detect future misplacements. | 2026-03-04 |

---

## Issue Template

When adding a new known issue, use this format:

```markdown
| KI-XXX | Critical/High/Medium/Low | component-name | Brief description of the issue | Workaround or mitigation steps | Open/Investigating/Resolved/Accepted |
```

### Severity Definitions

- **Critical**: Service outage, data loss, or security vulnerability. Requires immediate action.
- **High**: Significant functionality impacted. Requires resolution within 24 hours.
- **Medium**: Partial functionality affected. Can be scheduled for next maintenance window.
- **Low**: Minor issue, cosmetic, or edge case. Tracked but not blocking.

---

## Docker Project Group Rules

Each domain's `compose.yml` declares `name: homeiq-<domain>` so containers appear
as separate groups in Docker Desktop. **This only works when containers are started
via the per-domain compose file.**

### Do

```bash
# Start a single domain (default profile)
./scripts/domain.sh start data-collectors

# Start a domain with production-profile services
./scripts/domain.sh start data-collectors --all-profiles

# Start the full stack with all profiles
./scripts/start-stack.sh --all-profiles

# Verify all containers are in the correct groups
./scripts/domain.sh verify
```

### Do NOT

```bash
# WRONG — assigns root 'homeiq' project name to profile-gated services
docker compose --profile production up -d

# WRONG — running from domain directory uses folder name, not name: directive
cd domains/data-collectors && docker compose up -d
```

### Recovery (if containers end up in the wrong group)

```bash
# 1. Identify misplaced containers
./scripts/domain.sh verify

# 2. Remove and redeploy
docker rm -f <container-name>
./scripts/domain.sh start <domain> --all-profiles
```

---

## Monitoring

Known issues should be cross-referenced with:
- Prometheus alert rules: `infrastructure/prometheus/alerts.yml`
- Grafana dashboards: `http://localhost:3002`
- Service logs: `docker logs <container-name>`
- Post-deployment monitor: `./scripts/post-deployment-monitor.sh`

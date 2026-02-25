# Service Health Checks Reference

**Version:** 1.0
**Last Updated:** 2026-02-24
**Maintainer:** HomeIQ Platform Team

---

## Overview

HomeIQ consists of 50+ microservices organized into 9 domain groups. Every service exposes a `/health` endpoint (or similar) for monitoring. This document is the authoritative reference for all health check endpoints, expected responses, startup order, and per-service troubleshooting.

### Quick Health Check

```bash
# Run the automated health check script
./scripts/check-service-health.sh

# JSON output
./scripts/check-service-health.sh --json

# Critical services only
./scripts/check-service-health.sh --critical-only
```

---

## Tier 1 -- Critical (Must Be Running)

These services form the data backbone. If any are down, the entire platform is degraded.

| Service | Port | Health Endpoint | Container Name | Depends On |
|---------|------|----------------|----------------|------------|
| InfluxDB | 8086 | `GET /health` | homeiq-influxdb | Nothing |
| PostgreSQL | 5432 | `pg_isready` (Docker healthcheck) | homeiq-postgres | Nothing |
| data-api | 8006 | `GET /health` | homeiq-data-api | InfluxDB, PostgreSQL |
| websocket-ingestion | 8001 | `GET /health` | homeiq-websocket | data-api |
| admin-api | 8004 | `GET /api/v1/health` | homeiq-admin | InfluxDB, websocket-ingestion, data-api |
| health-dashboard | 3000 | `GET /` (HTTP 200) | homeiq-dashboard | admin-api |

### Expected Responses

**InfluxDB:**
```json
{"name":"influxdb","message":"ready for queries and writes","status":"pass","checks":[],"version":"2.7.12","commit":"..."}
```

**data-api / websocket-ingestion / admin-api:**
```json
{
  "service": "data-api",
  "status": "healthy",
  "timestamp": "2026-02-24T12:00:00Z",
  "uptime_seconds": 86400,
  "dependencies": [
    {"name": "influxdb", "status": "healthy"},
    {"name": "database", "status": "healthy"}
  ]
}
```

**health-dashboard:**
Returns HTML (`Content-Type: text/html`) with HTTP 200. No JSON health payload.

### PostgreSQL Health Check

PostgreSQL does not have an HTTP health endpoint. Use `pg_isready`:

```bash
# From host
pg_isready -h localhost -p 5432 -U homeiq -d homeiq

# From Docker
docker exec homeiq-postgres pg_isready -U homeiq -d homeiq

# Detailed connection test
docker exec homeiq-postgres psql -U homeiq -d homeiq -c "SELECT 1;"
```

---

## Tier 2 -- Essential Services

| Service | Port | Health Endpoint | Container Name | Domain Group |
|---------|------|----------------|----------------|-------------|
| data-retention | 8080 | `GET /health` | homeiq-data-retention | core-platform |
| weather-api | 8009 | `GET /health` | homeiq-weather-api | data-collectors |
| smart-meter | 8014 | `GET /health` | homeiq-smart-meter | data-collectors |
| sports-api | 8005 | `GET /health` | homeiq-sports-api | data-collectors |
| energy-correlator | 8017 | `GET /health` | homeiq-energy-correlator | energy-analytics |
| energy-forecasting | 8018 | `GET /health` | homeiq-energy-forecasting | energy-analytics |
| proactive-agent | 8019 | `GET /health` | homeiq-proactive-agent | energy-analytics |
| ha-setup-service | 8038 | `GET /health` | homeiq-ha-setup | device-management |

---

## Tier 3 -- AI/ML Services

| Service | Port | Health Endpoint | Container Name | Domain Group |
|---------|------|----------------|----------------|-------------|
| ai-core-service | 8033 | `GET /health` | homeiq-ai-core | ml-engine |
| device-intelligence | 8028 | `GET /health` | homeiq-device-intelligence | ml-engine |
| openvino-service | 8029 | `GET /health` | homeiq-openvino | ml-engine |
| ml-service | 8026 | `GET /health` | homeiq-ml-service | ml-engine |
| rag-service | 8027 | `GET /health` | homeiq-rag-service | ml-engine |
| ai-training-service | 8032 | `GET /health` | homeiq-ai-training | ml-engine |
| openai-service | 8031 | `GET /health` | homeiq-openai-service | ml-engine |
| nlp-fine-tuning | 8035 | `GET /health` | homeiq-nlp-fine-tuning | ml-engine |
| ner-service | 8037 | `GET /health` | homeiq-ner-service | ml-engine |
| model-prep | N/A | Job container | homeiq-model-prep | ml-engine |

---

## Tier 4 -- Automation Services

| Service | Port | Health Endpoint | Container Name | Domain Group |
|---------|------|----------------|----------------|-------------|
| ha-ai-agent-service | 8030 | `GET /health` | homeiq-ha-ai-agent | automation-core |
| ai-automation-service-new | 8025 | `GET /health` | homeiq-ai-automation-new | automation-core |
| ai-query-service | 8024 | `GET /health` | homeiq-ai-query | automation-core |
| automation-linter | 8036 | `GET /health` | homeiq-automation-linter | automation-core |
| yaml-validation-service | 8039 | `GET /health` | homeiq-yaml-validation | automation-core |
| ai-code-executor | 8040 | `GET /health` | homeiq-ai-code-executor | automation-core |
| automation-trace-service | 8042 | `GET /health` | homeiq-automation-trace | automation-core |

---

## Tier 5 -- Blueprint & Pattern Services

| Service | Port | Health Endpoint | Container Name | Domain Group |
|---------|------|----------------|----------------|-------------|
| blueprint-index | 8020 | `GET /health` | homeiq-blueprint-index | blueprints |
| blueprint-suggestion | 8021 | `GET /health` | homeiq-blueprint-suggestion | blueprints |
| rule-recommendation-ml | 8022 | `GET /health` | homeiq-rule-recommendation | blueprints |
| automation-miner | 8023 | `GET /health` | homeiq-automation-miner | blueprints |
| ai-pattern-service | 8034 | `GET /health` | homeiq-ai-pattern | pattern-analysis |
| api-automation-edge | 8041 | `GET /health` | homeiq-api-automation-edge | pattern-analysis |

---

## Tier 6 -- Device Management

| Service | Port | Health Endpoint | Container Name | Domain Group |
|---------|------|----------------|----------------|-------------|
| device-health-monitor | 8043 | `GET /health` | homeiq-device-health | device-management |
| device-context-classifier | 8044 | `GET /health` | homeiq-device-classifier | device-management |
| device-setup-assistant | 8045 | `GET /health` | homeiq-device-setup | device-management |
| device-database-client | 8046 | `GET /health` | homeiq-device-db-client | device-management |
| device-recommender | 8047 | `GET /health` | homeiq-device-recommender | device-management |
| activity-recognition | 8048 | `GET /health` | homeiq-activity-recognition | device-management |
| activity-writer | 8049 | `GET /health` | homeiq-activity-writer | device-management |

---

## Tier 7 -- Data Collectors (Optional)

These services are typically in the `production` profile and may not run in development.

| Service | Port | Health Endpoint | Container Name | Domain Group |
|---------|------|----------------|----------------|-------------|
| air-quality | 8012 | `GET /health` | homeiq-air-quality | data-collectors |
| carbon-intensity | 8010 | `GET /health` | homeiq-carbon-intensity | data-collectors |
| electricity-pricing | 8011 | `GET /health` | homeiq-electricity-pricing | data-collectors |
| calendar | 8013 | `GET /health` | homeiq-calendar | data-collectors |
| log-aggregator | 8015 | `GET /health` | homeiq-log-aggregator | data-collectors |

---

## Infrastructure Services

| Service | Port | Health Endpoint | Container Name | Purpose |
|---------|------|----------------|----------------|---------|
| Prometheus | 9090 | `GET /-/healthy` | homeiq-prometheus | Metrics collection |
| Grafana | 3002 | `GET /api/health` | homeiq-grafana | Dashboards |
| Jaeger | 16686 | `GET /` | homeiq-jaeger | Distributed tracing |
| postgres-exporter | 9187 | `GET /metrics` | homeiq-postgres-exporter | PG metrics for Prometheus |
| backup-scheduler | N/A | Docker healthcheck | homeiq-backup-scheduler | Automated backups |

---

## Startup Order Dependencies

Services must start in the correct order. The Docker Compose `depends_on` with `condition: service_healthy` enforces this, but for manual operations:

```
Phase 1 (Databases):
  InfluxDB (8086)  ──┐
  PostgreSQL (5432) ─┤
                     │
Phase 2 (Data Layer):
  data-api (8006) ───┤  (depends on InfluxDB + PostgreSQL)
                     │
Phase 3 (Ingestion):
  websocket-ingestion (8001) ──┤  (depends on data-api)
                               │
Phase 4 (Aggregation):
  admin-api (8004) ────────────┤  (depends on InfluxDB + WS + data-api)
                               │
Phase 5 (Frontend):
  health-dashboard (3000) ─────┘  (depends on admin-api)

Phase 6 (Parallel -- all other services):
  All data-collectors, ml-engine, automation-core, blueprints,
  energy-analytics, device-management, pattern-analysis services
  (depend on InfluxDB and/or data-api being available on the network)
```

### Manual Startup Sequence

```bash
# Phase 1
docker compose up -d influxdb postgres
sleep 30  # wait for health checks to pass

# Phase 2
docker compose up -d data-api
sleep 15

# Phase 3
docker compose up -d websocket-ingestion
sleep 10

# Phase 4
docker compose up -d admin-api
sleep 10

# Phase 5
docker compose up -d health-dashboard

# Phase 6 (all remaining)
docker compose up -d
```

---

## Troubleshooting Guide by Service Tier

### Tier 1 Troubleshooting

**InfluxDB not starting:**
```bash
docker logs homeiq-influxdb --tail 50
# Common: port conflict, volume permission issue, OOM
# Fix: Check port 8086, increase memory limit, check volume mounts
```

**PostgreSQL not starting:**
```bash
docker logs homeiq-postgres --tail 50
# Common: data directory corruption, port conflict, wrong credentials
# Fix: Check port 5432, verify POSTGRES_PASSWORD, check volume
```

**data-api unhealthy:**
```bash
docker logs homeiq-data-api --tail 50
# Common: InfluxDB/PostgreSQL not reachable, wrong credentials
# Fix: Verify DATABASE_URL, INFLUXDB_URL, ensure databases started first
```

**websocket-ingestion unhealthy:**
```bash
docker logs homeiq-websocket --tail 50
# Common: data-api not ready, Home Assistant not reachable
# Fix: Verify data-api is healthy, check HA_HTTP_URL and HA_TOKEN
# Note: Expected "degraded" if Home Assistant is offline
```

**admin-api unhealthy:**
```bash
docker logs homeiq-admin --tail 50
# Common: Depends on multiple services, any failure cascades
# Fix: Verify all Tier 1 dependencies are healthy first
```

### Tier 2-3 Troubleshooting

**"Connection refused" to InfluxDB:**
- Service started before InfluxDB was healthy
- Fix: `docker compose restart <service>`

**"API key" or "authentication" errors:**
- Token mismatch between service config and InfluxDB
- Fix: Verify `INFLUXDB_TOKEN` matches in `.env`

**Service starts then exits immediately:**
```bash
docker logs <container> --tail 100
# Look for ImportError, ModuleNotFoundError, or config errors
# Common: Missing shared library, wrong Python version
```

### HA-Dependent Services

These services show "degraded" status when Home Assistant is offline:

- websocket-ingestion (expected -- it retries connection)
- ha-ai-agent-service (needs HA for entity resolution)
- smart-meter (needs HA for energy sensor data)
- calendar (needs HA for calendar entities)
- ha-setup-service (needs HA for setup validation)

**This is normal behavior when HA is not connected.** These services are healthy if they respond to `/health` and report the HA dependency as unavailable.

---

## Batch Health Check Commands

```bash
# Check all Tier 1 services (critical)
for url in \
    "http://localhost:8086/health" \
    "http://localhost:8006/health" \
    "http://localhost:8001/health" \
    "http://localhost:8004/api/v1/health" \
    "http://localhost:3000"; do
    echo -n "$url: "
    curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" || echo "UNREACHABLE"
    echo ""
done

# Check all services with JSON output
./scripts/check-service-health.sh --json --output health-report.json

# Quick port scan to see what is running
for port in 8086 5432 8006 8001 8004 3000 8080 8009 8014 8005 8017 8018 8019; do
    echo -n "Port $port: "
    curl -s -o /dev/null -w "%{http_code}" --max-time 2 "http://localhost:$port/health" 2>/dev/null || echo "closed"
    echo ""
done
```

---

## Health Check Response Formats

### Standard Service Response

Most Python services follow this format:

```json
{
  "service": "<service-name>",
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2026-02-24T12:00:00Z",
  "uptime_seconds": 86400,
  "version": "1.0.0",
  "dependencies": [
    {"name": "influxdb", "status": "healthy"},
    {"name": "database", "status": "healthy"},
    {"name": "home_assistant", "status": "degraded"}
  ],
  "metrics": {
    "events_processed": 12345,
    "errors_last_hour": 0
  }
}
```

### InfluxDB Response

```json
{
  "name": "influxdb",
  "message": "ready for queries and writes",
  "status": "pass",
  "checks": [],
  "version": "2.7.12"
}
```

### Status Enum

| Status | Meaning | Action |
|--------|---------|--------|
| `healthy` / `pass` | All systems operational | None |
| `degraded` | Running but a dependency is unavailable | Investigate the failed dependency |
| `unhealthy` | Critical failure, service cannot function | Immediate investigation required |

---

## Related Documentation

- [PostgreSQL Runbook](postgresql-runbook.md)
- [Monitoring Setup](monitoring-setup.md)
- [Disaster Recovery Procedures](disaster-recovery.md)
- [check-service-health.sh](../../scripts/check-service-health.sh)

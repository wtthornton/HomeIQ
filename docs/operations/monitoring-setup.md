# Monitoring Setup Guide

**Version:** 1.0
**Last Updated:** 2026-02-24
**Maintainer:** HomeIQ Platform Team

---

## Overview

HomeIQ uses a Prometheus + Grafana monitoring stack alongside service-native health endpoints and InfluxDB for time-series metrics. This guide covers how to configure, extend, and troubleshoot the monitoring infrastructure.

---

## Service Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           HomeIQ Monitoring Stack                            │
│                                                                              │
│  ┌─────────────────┐     ┌──────────────┐     ┌─────────────────────────┐  │
│  │   Prometheus     │────>│   Grafana    │     │   Jaeger (Tracing)      │  │
│  │   (port 9090)   │     │  (port 3001) │     │   (port 16686)          │  │
│  └────────┬────────┘     └──────────────┘     └─────────────────────────┘  │
│           │ scrapes                                                          │
│           │                                                                  │
│  ┌────────┼──────────────────────────────────────────────────────────────┐  │
│  │        ▼           Service Metrics Endpoints                          │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐             │  │
│  │  │ WS-Ingest│  │ Data-API │  │ Admin-API│  │ AI-Core  │  ...        │  │
│  │  │ :8001    │  │ :8006    │  │ :8004    │  │ :8033    │             │  │
│  │  │ /metrics │  │ /metrics │  │ /metrics │  │ /metrics │             │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────┐     ┌──────────────────────────────────────┐     │
│  │  InfluxDB (port 8086) │     │  health-dashboard (port 3000)       │     │
│  │  Time-series storage  │     │  Built-in health aggregation        │     │
│  └───────────────────────┘     └──────────────────────────────────────┘     │
│                                                                              │
│  ┌───────────────────────┐                                                  │
│  │  PostgreSQL (5432)    │                                                  │
│  │  pg_stat_statements   │                                                  │
│  └───────────────────────┘                                                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Prometheus** scrapes `/metrics` endpoints from all services at a configurable interval (default: 15 seconds)
2. **Grafana** queries Prometheus and InfluxDB to render dashboards
3. **health-dashboard** (port 3000) provides a real-time view by querying admin-api and data-api
4. **Jaeger** collects distributed traces via OpenTelemetry
5. **InfluxDB** stores high-resolution time-series data from websocket-ingestion

---

## Adding New Scrape Targets

### Step 1: Expose a /metrics Endpoint

If your service uses FastAPI with `prometheus-fastapi-instrumentator`:

```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

If your service uses aiohttp:

```python
from aiohttp import web
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

async def metrics_handler(request):
    return web.Response(body=generate_latest(), content_type=CONTENT_TYPE_LATEST)

app.router.add_get('/metrics', metrics_handler)
```

### Step 2: Add to Prometheus Configuration

Edit `infrastructure/prometheus/prometheus.yml` (or the equivalent mounted config):

```yaml
scrape_configs:
  # ... existing targets ...

  - job_name: 'my-new-service'
    static_configs:
      - targets: ['my-new-service:8099']
    scrape_interval: 15s
    metrics_path: /metrics
```

### Step 3: Reload Prometheus

```bash
# Hot reload (no downtime)
curl -X POST http://localhost:9090/-/reload

# Or restart the container
docker compose restart prometheus
```

### Step 4: Verify

```bash
# Check targets page
curl -s http://localhost:9090/api/v1/targets | python -m json.tool

# Query a metric
curl -s 'http://localhost:9090/api/v1/query?query=up{job="my-new-service"}'
```

---

## Creating Grafana Dashboards

### Accessing Grafana

- URL: `http://localhost:3001`
- Default credentials: `admin` / `admin` (change on first login)

### Adding a Data Source

1. Navigate to **Configuration > Data Sources**
2. Click **Add data source**
3. For Prometheus: Select "Prometheus", set URL to `http://prometheus:9090`
4. For InfluxDB: Select "InfluxDB", set URL to `http://influxdb:8086`, set organization and token

### Dashboard Creation Steps

1. Click **+ > Dashboard > Add visualization**
2. Select the appropriate data source
3. Write your PromQL or Flux query
4. Configure visualization type (time series, gauge, stat, table, etc.)
5. Set panel title and description
6. Click **Apply**, then **Save dashboard**

### Recommended Dashboard Panels

#### System Overview

```promql
# Service uptime
up{job=~"websocket-ingestion|data-api|admin-api"}

# Request rate (per service)
rate(http_requests_total[5m])

# Request latency (p95)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
```

#### PostgreSQL Monitoring

```promql
# Active connections
pg_stat_activity_count{datname="homeiq"}

# Transaction rate
rate(pg_stat_database_xact_commit{datname="homeiq"}[5m])

# Cache hit ratio (should be > 99%)
pg_stat_database_blks_hit{datname="homeiq"} /
(pg_stat_database_blks_hit{datname="homeiq"} + pg_stat_database_blks_read{datname="homeiq"})
```

#### InfluxDB Monitoring

```promql
# Write throughput
rate(influxdb_write_points_total[5m])

# Query latency
histogram_quantile(0.95, rate(influxdb_query_duration_seconds_bucket[5m]))
```

### Exporting/Importing Dashboards

```bash
# Export a dashboard as JSON
curl -H "Authorization: Bearer <api-key>" \
  http://localhost:3001/api/dashboards/uid/<dashboard-uid> > dashboard.json

# Import a dashboard
curl -X POST -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d @dashboard.json \
  http://localhost:3001/api/dashboards/db
```

---

## Alert Rule Configuration

### Prometheus Alerting Rules

Create or edit `infrastructure/prometheus/alert-rules.yml`:

```yaml
groups:
  - name: homeiq-critical
    rules:
      - alert: ServiceDown
        expr: up == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} is down"
          description: "{{ $labels.job }} has been down for more than 2 minutes."

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate on {{ $labels.job }}"
          description: "{{ $labels.job }} has >5% error rate for 5 minutes."

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency on {{ $labels.job }}"
          description: "p95 latency on {{ $labels.job }} exceeds 5 seconds."

      - alert: PostgreSQLConnectionsHigh
        expr: pg_stat_activity_count{datname="homeiq"} > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "PostgreSQL connections approaching limit"
          description: "{{ $value }} active connections (max_connections is typically 100)."

      - alert: PostgreSQLCacheHitLow
        expr: >
          pg_stat_database_blks_hit{datname="homeiq"} /
          (pg_stat_database_blks_hit{datname="homeiq"} + pg_stat_database_blks_read{datname="homeiq"}) < 0.95
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "PostgreSQL cache hit ratio below 95%"

      - alert: DiskSpaceLow
        expr: node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} < 0.10
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Less than 10% disk space remaining"

  - name: homeiq-ingestion
    rules:
      - alert: IngestionStopped
        expr: rate(influxdb_write_points_total[10m]) == 0
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "No data being written to InfluxDB"
          description: "websocket-ingestion has not written data for 10 minutes."

      - alert: WebSocketDisconnected
        expr: homeiq_websocket_connected == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "WebSocket connection to Home Assistant lost"
```

### Loading Alert Rules

Reference the rules file in `prometheus.yml`:

```yaml
rule_files:
  - /etc/prometheus/alert-rules.yml
```

Reload Prometheus:

```bash
curl -X POST http://localhost:9090/-/reload
```

### Grafana Alert Rules (Alternative)

For alerts that fire through Grafana rather than Prometheus:

1. Open a dashboard panel
2. Click **Alert** tab
3. Define conditions (e.g., `WHEN avg() OF query(A) IS ABOVE 5`)
4. Configure notification channel (Slack, email, webhook)
5. Save

---

## Troubleshooting Common Monitoring Issues

### Prometheus Target Shows "DOWN"

```bash
# Check if the service is actually running
docker compose ps | grep <service-name>

# Check if the metrics endpoint responds
curl -s http://localhost:<port>/metrics | head -5

# Check Prometheus target page for error message
curl -s http://localhost:9090/api/v1/targets | python -m json.tool | grep -A5 <service-name>
```

**Common causes:**
- Service container not running
- Network name mismatch (service not on `homeiq-network`)
- Wrong port in scrape config
- `/metrics` endpoint not implemented

### Grafana Shows "No Data"

1. Verify data source connection: **Configuration > Data Sources > Test**
2. Check time range (top-right corner) -- is it set to a period with data?
3. Run the query directly in Prometheus: `http://localhost:9090/graph`
4. Check Grafana server logs: `docker logs homeiq-grafana --tail 50`

### Metrics Missing After Restart

Prometheus stores data in a persistent volume. If data is lost:

1. Check the volume: `docker volume inspect homeiq_prometheus_data`
2. Verify the retention period in `prometheus.yml`: `--storage.tsdb.retention.time=30d`
3. If volume was deleted, historical data is lost -- only new data will appear

### High Memory Usage in Prometheus

```bash
# Check cardinality (too many unique time series)
curl -s http://localhost:9090/api/v1/status/tsdb | python -m json.tool

# If cardinality is > 1M, reduce labels or drop high-cardinality metrics
# Add relabeling rules to prometheus.yml:
scrape_configs:
  - job_name: 'high-cardinality-service'
    metric_relabel_configs:
      - source_labels: [__name__]
        regex: 'unwanted_metric_.*'
        action: drop
```

### Jaeger Traces Not Appearing

```bash
# Check if the Jaeger collector is running
curl -s http://localhost:16686/api/services

# Verify services are exporting traces
docker logs homeiq-data-api 2>&1 | grep -i "otel\|trace\|jaeger"

# Check OTEL environment variables in the service
docker inspect homeiq-data-api | grep -i "otel"
```

Required environment variables for tracing:

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
OTEL_SERVICE_NAME=data-api
OTEL_TRACES_EXPORTER=otlp
```

---

## Maintenance Tasks

### Prometheus Data Cleanup

```bash
# Check current disk usage
docker exec homeiq-prometheus du -sh /prometheus

# Force a compaction (if supported)
curl -X POST http://localhost:9090/api/v1/admin/tsdb/clean_tombstones

# Delete specific time series (use with caution)
curl -X POST 'http://localhost:9090/api/v1/admin/tsdb/delete_series?match[]={job="old-service"}'
```

### Grafana Backup

```bash
# Backup Grafana database (contains dashboards, users, data sources)
docker cp homeiq-grafana:/var/lib/grafana/grafana.db ./backups/grafana.db

# Backup provisioned dashboards
docker cp homeiq-grafana:/etc/grafana/provisioning ./backups/grafana-provisioning
```

---

## Related Documentation

- [PostgreSQL Runbook](postgresql-runbook.md)
- [Disaster Recovery Procedures](disaster-recovery.md)
- [Service Health Checks](service-health-checks.md)
- [Agent Evaluation Runbook](agent-evaluation-runbook.md)

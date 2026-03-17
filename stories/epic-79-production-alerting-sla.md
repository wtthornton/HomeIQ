# Epic 79: Production Alerting & SLA Monitoring

## Overview
Implements tiered SLA definitions, Prometheus recording/alert rules, AlertManager deployment,
Grafana SLA dashboards, Zeek security alert routing, and admin-api webhook integration.

## Service Tier SLA Targets

| Tier | Availability | P95 Latency | Error Rate | Services |
|------|-------------|-------------|------------|----------|
| 1 (Critical) | 99.9% | < 500ms | < 0.1% | websocket-ingestion, data-api, admin-api |
| 2 (Essential) | 99.5% | < 1s | < 1% | data-retention, ha-setup-service, weather-api, smart-meter, energy-correlator |
| 3+ (Features) | 99.0% | < 2s | < 5% | All other services |

## Stories

### Story 79.1: SLA Definitions & Prometheus Recording Rules
**File:** `infrastructure/prometheus/sla-rules.yml`
**Status:** Complete

Recording rules evaluated every 15s:
- `service:availability:ratio_1h` — per-service availability (1h rolling)
- `service:latency:p95_5m` / `p99_5m` — latency percentiles (5m rolling)
- `service:error_rate:ratio_5m` — error rate (5m rolling)
- `service:error_budget:remaining_30d` — error budget burn per tier
- `service:requests:rate_5m` — request throughput
- `tier:availability:ratio_1h` / `tier:latency:p95_5m` — tier-aggregated metrics

### Story 79.2: SLA Alert Rules
**File:** `infrastructure/prometheus/alerts.yml` (updated — added `sla_alerts` and `cross_cutting_alerts` groups)
**Status:** Complete

Alerts added:
- `Tier1SLABreach` — availability < 99.9% (critical, page)
- `Tier1LatencySLABreach` — p95 > 500ms (warning, page)
- `Tier1ErrorRateSLABreach` — error rate > 0.1% (critical, page)
- `Tier2SLABreach` — availability < 99.5% (warning)
- `Tier2LatencySLABreach` — p95 > 1s (warning)
- `Tier3SLABreach` — availability < 99.0% (warning)
- `ErrorBudgetBurnRateCritical` — budget < 10% (critical)
- `ErrorBudgetBurnRateWarning` — budget < 25% (warning)
- `ZeekAlertEscalation` — > 5 active Zeek alerts (critical)
- `MemoryBrainEmbeddingDown` — rag-service down (warning)
- `CircuitBreakerOpen` — any CB open > 5 min (warning)

### Story 79.3: AlertManager Configuration
**Files:**
- `infrastructure/alertmanager/alertmanager.yml` (new)
- `domains/core-platform/compose.yml` (updated)
- `infrastructure/prometheus/prometheus.yml` (updated)
**Status:** Complete

- AlertManager v0.28.1 deployed on port 9093
- Routes: critical (30m repeat) / security (1h repeat) / default (4h repeat)
- All receivers POST to `admin-api:8004/api/alerts/webhook`
- Inhibition: critical suppresses warning for same alert+service
- Prometheus updated with `alerting.alertmanagers` config
- New rule files mounted in Prometheus container

### Story 79.4: Grafana SLA Dashboard
**File:** `infrastructure/grafana/dashboards/sla-overview.json`
**Status:** Complete

Panels:
1. Availability by Tier — 3 gauge panels (Tier 1/2/3+)
2. Error Budget Remaining — time series with 10%/25% threshold lines
3. Latency P95 by Service — split Tier 1-2 and Tier 3+ panels
4. Active Alerts — table of currently firing alerts with severity coloring
5. SLA Compliance History — time series with SLA threshold bands

### Story 79.5: Zeek Security Alert Routing
**File:** `infrastructure/prometheus/zeek-alerts.yml`
**Status:** Complete

Recording rules:
- `zeek:anomalies:rate_5m` — anomaly detection rate
- `zeek:connections:active` — active connections by protocol
- `zeek:tls_failures:rate_5m` — TLS handshake failures
- `zeek:dns:query_rate_5m` — DNS query throughput

Alert rules:
- `ZeekNewDeviceDetected` — new MAC address (warning)
- `ZeekBeaconingDetected` — C2 beaconing (critical)
- `ZeekDGADetected` — domain generation algorithm (critical)
- `ZeekWeakTLS` — TLS < 1.2 (warning)
- `ZeekExpiredCert` — expired certificates (warning)
- `ZeekRogueMQTTClient` — unknown MQTT client (critical)
- `ZeekHighAnomalyRate` — anomaly rate > 10/s (critical)
- `ZeekServiceDown` — zeek-network-service unreachable (critical)

### Story 79.6: Admin API Alert Webhook Endpoint
**File:** `domains/core-platform/admin-api/src/alertmanager_webhook.py` (new)
**File:** `domains/core-platform/admin-api/src/routes.py` (updated)
**Status:** Complete

Endpoints:
- `POST /api/alerts/webhook` — receives AlertManager v4 webhook payloads
- `GET /api/alerts/active` — returns currently firing alerts (with severity filter)
- `GET /api/alerts/active/count` — returns alert counts by severity

Features:
- In-memory AlertStore with 15-minute TTL expiry
- Structured logging for all firing/resolved alerts
- No auth required on webhook (called by AlertManager container)
- `get_active_alert_count()` function available for /health enrichment

## Architecture

```
Prometheus (9090)
  ├── sla-rules.yml (recording rules)
  ├── alerts.yml (SLA + cross-cutting alerts)
  └── zeek-alerts.yml (security alerts)
      │
      ▼
AlertManager (9093)
  ├── critical → admin-api webhook (30m repeat)
  ├── security → admin-api webhook (1h repeat)
  └── default → admin-api webhook (4h repeat)
      │
      ▼
Admin API (8004)
  ├── POST /api/alerts/webhook (receive)
  ├── GET /api/alerts/active (query)
  └── GET /api/alerts/active/count
      │
      ▼
Health Dashboard (3000) / Grafana (3002)
```

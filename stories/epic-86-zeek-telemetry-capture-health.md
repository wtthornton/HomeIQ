# Epic 86: Zeek 8.x Native Telemetry & Capture Health Dashboard

<!-- docsmcp:start:metadata -->
**Status:** Proposed
**Priority:** P2 — Medium
**Estimated LOE:** ~1 week (1 developer)
**Dependencies:** Epic 79 (Production Alerting & SLA — COMPLETE), Epic 72 (Zeek Core Network Ingestion — COMPLETE), Epic 82 (Zeek Container Docker Healthcheck — COMPLETE)

<!-- docsmcp:end:metadata -->

---

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

We are doing this so that the HomeIQ observability stack gains direct visibility into Zeek's packet capture engine health — not just the zeek-network-service application metrics, but the underlying capture process metrics (packet drops, memory usage, event queue depth, connection stats). This closes the gap between "is the Python service alive?" and "is Zeek actually capturing packets reliably?" — enabling proactive alerting before packet loss degrades network security monitoring.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:goal -->
## Goal

Enable Zeek 8.x's built-in telemetry framework to expose Prometheus-format metrics on port 9911, integrate those metrics into the existing Prometheus/Grafana/AlertManager pipeline from Epic 79, and create a Grafana dashboard panel for Zeek capture health alongside existing SLA monitoring.

<!-- docsmcp:end:goal -->

<!-- docsmcp:start:motivation -->
## Motivation

Today, Epic 79's zeek-alerts.yml monitors the zeek-network-service Python application (anomaly rates, TLS failures, DNS throughput) but has no visibility into the Zeek capture engine itself. If Zeek drops packets due to memory pressure, AF_PACKET ring buffer exhaustion, or event queue saturation, the alerting pipeline is blind until downstream log parsing gaps appear — minutes to hours later. Zeek 8.x ships a built-in telemetry framework (`@load frameworks/telemetry`) that exposes real-time Prometheus-format metrics, giving us sub-second visibility into capture health.

<!-- docsmcp:end:motivation -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Zeek process exposes Prometheus metrics on port 9911 via `@load frameworks/telemetry`
- [ ] Prometheus scrapes Zeek telemetry endpoint at 30s interval with correct labels
- [ ] Recording rules compute 5m rolling averages for packet drops and event queue depth
- [ ] Alert rules fire on packet drop rate >0.1% and event queue depth >10000
- [ ] Grafana dashboard displays Zeek capture health panels (packets received/dropped/memory/event queue/connections)
- [ ] Dashboard is auto-provisioned alongside existing SLA dashboard
- [ ] All changes work with Zeek's `network_mode: host` constraint
- [ ] zeek-alerts.yml updated to include capture-level alert rules

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:stories -->
## Stories

| Story | Title | Points | Story Doc |
|-------|-------|--------|-----------|
| 86.1 | Enable Zeek Telemetry Framework in local.zeek | 2 | [epic-86-story-1.md](epic-86-story-1.md) |
| 86.2 | Docker Networking — Expose Telemetry Port to Prometheus | 3 | [epic-86-story-2.md](epic-86-story-2.md) |
| 86.3 | Prometheus Scrape Config for Zeek Telemetry | 2 | [epic-86-story-3.md](epic-86-story-3.md) |
| 86.4 | Zeek Capture Health Recording Rules | 2 | [epic-86-story-4.md](epic-86-story-4.md) |
| 86.5 | Zeek Capture Health Alert Rules | 3 | [epic-86-story-5.md](epic-86-story-5.md) |
| 86.6 | Grafana Zeek Capture Health Dashboard | 3 | [epic-86-story-6.md](epic-86-story-6.md) |
| 86.7 | Integration Verification & Documentation | 2 | [epic-86-story-7.md](epic-86-story-7.md) |

**Total: 17 points across 7 stories**

<!-- docsmcp:end:stories -->

<!-- docsmcp:start:implementation-order -->
## Implementation Order

1. **Story 86.1** — Enable Zeek Telemetry Framework in local.zeek *(foundation — all else depends on this)*
2. **Story 86.2** — Docker Networking — Expose Telemetry Port to Prometheus *(unblocks scraping)*
3. **Story 86.3** — Prometheus Scrape Config for Zeek Telemetry *(unblocks rules & dashboard)*
4. **Story 86.4** — Zeek Capture Health Recording Rules *(pre-compute metrics for alerts & dashboard)*
5. **Story 86.5** — Zeek Capture Health Alert Rules *(depends on recording rules)*
6. **Story 86.6** — Grafana Zeek Capture Health Dashboard *(depends on recording rules)*
7. **Story 86.7** — Integration Verification & Documentation *(final validation)*

> Stories 86.5 and 86.6 can be parallelized after 86.4 completes.

<!-- docsmcp:end:implementation-order -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- **Zeek 8.x telemetry** uses `@load frameworks/telemetry` — built-in framework, no zkg package needed
- **`Telemetry::metrics_port = 9911`** opens an HTTP endpoint serving Prometheus text format (`text/plain; version=0.0.4`)
- **Networking challenge:** Zeek container uses `network_mode: host` — port 9911 is on the host, not the Docker bridge. Prometheus (on `homeiq-network` bridge) must reach it via `host.docker.internal` or `extra_hosts`
- **Key Zeek 8.x telemetry metric families:**
  - `zeek_packets_received_total` (counter) — packets received by capture engine
  - `zeek_packets_dropped_total` (counter) — packets dropped by kernel/AF_PACKET
  - `zeek_active_connections` (gauge) — currently tracked connections
  - `zeek_event_queue_length` (gauge) — pending events in event queue
  - `zeek_memory_usage_bytes` (gauge) — Zeek process RSS
  - `zeek_timers_pending` (gauge) — scheduled timers waiting to fire
- **Existing zeek-alerts.yml** already has app-level alerts from `zeek-network-service:8048/metrics` — this epic adds *capture-engine-level* alerts from Zeek itself on `:9911`
- **Port 9911** not yet assigned in TECH_STACK.md — reserve for Zeek telemetry

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:non-goals -->
## Out of Scope / Future Considerations

- Modifying zeek-network-service Python application metrics (already handled by Epic 72)
- Adding OpenTelemetry or OTLP export from Zeek (native Prometheus is sufficient)
- Custom Zeek scripts for additional metric instrumentation beyond built-in telemetry
- Alerting on individual connection-level events (handled by existing zeek-alerts.yml)

<!-- docsmcp:end:non-goals -->

<!-- docsmcp:start:success-metrics -->
## Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Packet drop visibility | Blind | Sub-30s | Prometheus scrape |
| Alert MTTR for capture issues | Hours (log gap detection) | Minutes (direct metric alert) | AlertManager |
| Dashboard load time | N/A | <3s | Grafana |
| Metric cardinality | 0 Zeek-native | ~20 metric families | Prometheus |

<!-- docsmcp:end:success-metrics -->

<!-- docsmcp:start:stakeholders -->
## Stakeholders

| Role | Person | Responsibility |
|------|--------|----------------|
| Owner | Platform Team | Implementation and testing |
| Consumer | Security Monitoring | Zeek capture health visibility |
| Consumer | SRE/Oncall | Alert response for capture degradation |

<!-- docsmcp:end:stakeholders -->

<!-- docsmcp:start:risk-assessment -->
## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Zeek 8.1.1 telemetry may expose fewer metrics than documented in dev builds | Medium | Medium | Validate available metric families in Story 86.1 before writing rules |
| Host-to-bridge network connectivity may need platform-specific workarounds | Medium | Medium | Story 86.2 tests both Docker Desktop (Windows) and native Linux approaches |
| Telemetry endpoint adds ~2MB RSS to Zeek process | Low | Low | Within existing 4GB limit; monitor via the new dashboard |
| Under extreme load, telemetry HTTP server may become unresponsive | Low | Low | Prometheus scrape timeout (10s) handles gracefully; `ZeekCaptureStalled` alert covers this |

<!-- docsmcp:end:risk-assessment -->

<!-- docsmcp:start:files-affected -->
## Files Affected

| File | Change Type | Story |
|------|-------------|-------|
| `domains/data-collectors/zeek-network-service/zeek-config/local.zeek` | Modify | 86.1 |
| `domains/data-collectors/zeek-network-service/Dockerfile.zeek` | Modify (expose port) | 86.2 |
| `domains/data-collectors/compose.yml` | Modify (networking) | 86.2 |
| `domains/core-platform/compose.yml` | Modify (Prometheus extra_hosts) | 86.2 |
| `infrastructure/prometheus/prometheus.yml` | Modify (add scrape job) | 86.3 |
| `infrastructure/prometheus/zeek-alerts.yml` | Modify (recording + alert rules) | 86.4, 86.5 |
| `infrastructure/grafana/dashboards/zeek-capture-health.json` | **New file** | 86.6 |
| `docs/TECH_STACK.md` | Modify (port 9911) | 86.7 |

<!-- docsmcp:end:files-affected -->

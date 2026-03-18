# Story 86.6 -- Grafana Zeek Capture Health Dashboard

<!-- docsmcp:start:user-story -->

> **As a** SRE/oncall engineer, **I want** a Grafana dashboard showing Zeek capture health metrics (packets, drops, memory, event queue, connections), **so that** I can visually assess capture engine health at a glance and correlate capture issues with downstream alert patterns

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that operators have a visual overview of Zeek capture engine health alongside the existing SLA monitoring, enabling quick assessment of whether the network security monitoring pipeline is healthy from packet capture through to alerting.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Create a new `zeek-capture-health.json` Grafana dashboard provisioned alongside the existing SLA and PostgreSQL dashboards. The dashboard includes:

| Row | Panel | Query | Type |
|-----|-------|-------|------|
| 1 | Packets Received/Dropped | `zeek:packets:received_rate_5m`, `zeek:packets:dropped_rate_5m` | Time series |
| 1 | Drop Ratio | `zeek:packets:drop_ratio_5m` | Gauge (green <0.01%, yellow <0.1%, red >0.1%) |
| 2 | Memory Usage | `zeek:memory:usage_bytes` | Gauge (max 4GB, thresholds at 60%/80%) |
| 2 | Event Queue Depth | `zeek:event_queue:depth_avg_5m` | Time series (threshold line at 10000) |
| 3 | Active Connections | `zeek:connections:active` | Time series |
| 3 | Capture Health Status | Derived from alert states | Stat panel |

Use the existing Prometheus datasource. Dashboard auto-provisions via the existing `/var/lib/grafana/dashboards` directory mount. Include a link to the SLA overview dashboard for cross-reference.

See [Epic 86](epic-86-zeek-telemetry-capture-health.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `infrastructure/grafana/dashboards/zeek-capture-health.json` **(new file)**

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create `zeek-capture-health.json` dashboard with `uid=zeek-capture-health` (`infrastructure/grafana/dashboards/zeek-capture-health.json`)
- [ ] Add Row 1: Packets panel — time series of `zeek:packets:received_rate_5m` and `zeek:packets:dropped_rate_5m`
- [ ] Add Row 1: Drop Ratio gauge — `zeek:packets:drop_ratio_5m` with thresholds: green <0.01%, yellow <0.1%, red >0.1%
- [ ] Add Row 2: Memory Usage gauge — `zeek:memory:usage_bytes` against 4GB limit, thresholds at 60%/80%
- [ ] Add Row 2: Event Queue Depth — time series with 10000 threshold line
- [ ] Add Row 3: Active Connections — `zeek:connections:active` by protocol
- [ ] Add Capture Health Status stat panel — overall status derived from alert states
- [ ] Add dashboard link to existing SLA overview dashboard (`/d/sla-overview`)
- [ ] Verify dashboard auto-loads in Grafana after container restart

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] `zeek-capture-health.json` exists in `infrastructure/grafana/dashboards/`
- [ ] Dashboard auto-provisions when Grafana starts (no manual import needed)
- [ ] All 6+ panels render data from Prometheus Zeek telemetry metrics
- [ ] Drop Ratio gauge shows correct color thresholds (green/yellow/red)
- [ ] Memory gauge shows usage relative to 4GB container limit
- [ ] Event Queue panel has a 10000 threshold line
- [ ] Dashboard loads in under 3 seconds
- [ ] Dashboard has a link to the existing SLA overview dashboard for cross-reference

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 86](epic-86-zeek-telemetry-capture-health.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_dashboard_json_exists` -- zeek-capture-health.json exists in infrastructure/grafana/dashboards/
2. `test_ac2_auto_provisioning` -- Dashboard auto-provisions when Grafana starts
3. `test_ac3_panels_render_data` -- All 6+ panels render data from Prometheus Zeek telemetry metrics
4. `test_ac4_drop_ratio_thresholds` -- Drop Ratio gauge shows correct color thresholds
5. `test_ac5_memory_gauge_limit` -- Memory gauge shows usage relative to 4GB container limit
6. `test_ac6_event_queue_threshold` -- Event Queue panel has a 10000 threshold line
7. `test_ac7_load_time` -- Dashboard loads in under 3 seconds
8. `test_ac8_sla_dashboard_link` -- Dashboard has a link to the existing SLA overview dashboard

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Use Grafana dashboard JSON model version 38+ (compatible with Grafana 11.5.2 deployed in the stack)
- The Prometheus datasource UID must match the provisioned datasource — use `${DS_PROMETHEUS}` variable for portability
- Dashboard UID `zeek-capture-health` enables stable deep-linking from other dashboards and alerts
- The SLA dashboard link uses `/d/sla-overview` based on the existing sla-overview.json UID
- Gauge panels should use `last()` reducer for current value display
- The Capture Health Status panel can use `ALERTS{alertname=~"Zeek.*", alertstate="firing"}` to show active capture alerts

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 86.4 (recording rules must exist for dashboard queries)
- Can be parallelized with Story 86.5

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [ ] **I**ndependent -- Depends on 86.4
- [x] **N**egotiable -- Panel layout and thresholds can be adjusted
- [x] **V**aluable -- Visual capture health overview for operators
- [x] **E**stimable -- Team can estimate the effort
- [x] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->

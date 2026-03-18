# Story 86.4 -- Zeek Capture Health Recording Rules

<!-- docsmcp:start:user-story -->

> **As a** platform engineer, **I want** to add Prometheus recording rules that compute rolling capture health metrics from Zeek telemetry, **so that** alert rules and dashboards can reference pre-computed metrics like packet drop ratio and event queue depth averages

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2 | **Size:** S

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that raw Zeek telemetry counters are pre-computed into meaningful derived metrics (rates, ratios, averages) that alert rules and Grafana dashboards can use efficiently without expensive real-time PromQL.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Add a `zeek_capture_health` recording rule group to zeek-alerts.yml with 15s evaluation interval (matching existing rule groups). Compute:

| Recording Rule | Expression | Type |
|---------------|------------|------|
| `zeek:packets:received_rate_5m` | `rate(zeek_packets_received_total[5m])` | Gauge |
| `zeek:packets:dropped_rate_5m` | `rate(zeek_packets_dropped_total[5m])` | Gauge |
| `zeek:packets:drop_ratio_5m` | `dropped_rate / (received_rate + dropped_rate)` | Gauge |
| `zeek:memory:usage_bytes` | `zeek_memory_usage_bytes` | Gauge |
| `zeek:event_queue:depth_avg_5m` | `avg_over_time(zeek_event_queue_length[5m])` | Gauge |
| `zeek:connections:active` | `zeek_active_connections` | Gauge |

See [Epic 86](epic-86-zeek-telemetry-capture-health.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `infrastructure/prometheus/zeek-alerts.yml`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Add `zeek_capture_health` recording rule group with `interval: 15s` (`infrastructure/prometheus/zeek-alerts.yml`)
- [ ] Add rule: `zeek:packets:received_rate_5m` = `rate(zeek_packets_received_total[5m])` (`infrastructure/prometheus/zeek-alerts.yml`)
- [ ] Add rule: `zeek:packets:dropped_rate_5m` = `rate(zeek_packets_dropped_total[5m])` (`infrastructure/prometheus/zeek-alerts.yml`)
- [ ] Add rule: `zeek:packets:drop_ratio_5m` = `zeek:packets:dropped_rate_5m / (zeek:packets:received_rate_5m + zeek:packets:dropped_rate_5m)` with `clamp_max(..., 1)` for safety (`infrastructure/prometheus/zeek-alerts.yml`)
- [ ] Add rules for memory, event queue depth avg, and active connections (`infrastructure/prometheus/zeek-alerts.yml`)
- [ ] Reload Prometheus config and verify recording rules evaluate without errors

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] zeek-alerts.yml contains `zeek_capture_health` recording rule group
- [ ] All 6 recording rules evaluate without errors in Prometheus
- [ ] `zeek:packets:drop_ratio_5m` returns a value between 0 and 1
- [ ] Recording rules use consistent naming convention matching existing sla-rules.yml patterns (`namespace:metric:aggregation_window`)
- [ ] Rules handle the cold-start case gracefully (no division by zero when `received_rate` is 0)

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 86](epic-86-zeek-telemetry-capture-health.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_recording_rule_group_exists` -- zeek-alerts.yml contains zeek_capture_health recording rule group
2. `test_ac2_all_rules_evaluate` -- All 6 recording rules evaluate without errors in Prometheus
3. `test_ac3_drop_ratio_bounded` -- zeek:packets:drop_ratio_5m returns a value between 0 and 1
4. `test_ac4_naming_convention` -- Recording rules follow `namespace:metric:aggregation_window` pattern
5. `test_ac5_cold_start_safe` -- Rules handle the cold-start case gracefully (no division by zero)

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Use `clamp_max(x, 1)` on the drop ratio to handle edge cases where counter resets could cause ratios > 1
- The drop ratio formula uses `dropped / (received + dropped)` rather than `dropped / received` to avoid division by zero when there's no traffic
- When both received and dropped are 0, PromQL will return NaN — this is expected and won't trigger alerts (which use `>` comparison)
- The `zeek:memory:usage_bytes` and `zeek:connections:active` rules are simple aliases for naming consistency — they add no computation but enable consistent PromQL patterns

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 86.3 (Prometheus must be scraping Zeek telemetry)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [ ] **I**ndependent -- Depends on 86.3
- [x] **N**egotiable -- Window sizes and naming can be adjusted
- [x] **V**aluable -- Enables efficient alerting and dashboard queries
- [x] **E**stimable -- Team can estimate the effort
- [x] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->

# Story 86.5 -- Zeek Capture Health Alert Rules

<!-- docsmcp:start:user-story -->

> **As a** SRE/oncall engineer, **I want** to receive alerts when Zeek capture health degrades (packet drops, memory pressure, queue saturation, capture stall), **so that** I can respond to capture issues within minutes instead of discovering them hours later through log parsing gaps

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that capture-level degradation triggers alerts through the existing Epic 79 AlertManager pipeline, enabling proactive response before packet loss impacts network security monitoring.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Add a `zeek_capture_alerts` alert rule group to zeek-alerts.yml with four alerts:

| Alert | Expression | For | Severity | Domain |
|-------|-----------|-----|----------|--------|
| `ZeekPacketDropHigh` | `zeek:packets:drop_ratio_5m > 0.001` | 5m | critical | security |
| `ZeekMemoryPressure` | `zeek:memory:usage_bytes > 3.2e9` | 5m | warning | — |
| `ZeekEventQueueSaturated` | `zeek:event_queue:depth_avg_5m > 10000` | 2m | warning | — |
| `ZeekCaptureStalled` | `zeek:packets:received_rate_5m == 0` | 2m | critical | security |

All alerts include `service=zeek`, `tier=2`, `group=data-collectors` labels for correct AlertManager routing via Epic 79's configuration.

See [Epic 86](epic-86-zeek-telemetry-capture-health.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `infrastructure/prometheus/zeek-alerts.yml`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Add `zeek_capture_alerts` alert group to zeek-alerts.yml (`infrastructure/prometheus/zeek-alerts.yml`)
- [ ] Add `ZeekPacketDropHigh`: `zeek:packets:drop_ratio_5m > 0.001`, severity=critical, domain=security, for=5m
- [ ] Add `ZeekMemoryPressure`: `zeek:memory:usage_bytes > 3.2e9` (80% of 4GB limit), severity=warning, for=5m
- [ ] Add `ZeekEventQueueSaturated`: `zeek:event_queue:depth_avg_5m > 10000`, severity=warning, for=2m
- [ ] Add `ZeekCaptureStalled`: `zeek:packets:received_rate_5m == 0`, severity=critical, domain=security, for=2m
- [ ] Add descriptive annotations (`summary`, `description`, `runbook_url`) to each alert
- [ ] Verify alerts appear in Prometheus /alerts page with correct labels

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Four capture health alerts are defined in zeek-alerts.yml
- [ ] `ZeekPacketDropHigh` fires at >0.1% drop ratio with `severity=critical` and `domain=security`
- [ ] `ZeekMemoryPressure` fires at >80% of 4GB container limit with `severity=warning`
- [ ] `ZeekEventQueueSaturated` fires at queue depth >10000 with `severity=warning`
- [ ] `ZeekCaptureStalled` fires when received rate drops to 0 for 2m with `severity=critical`
- [ ] All alerts include `service=zeek` `tier=2` `group=data-collectors` labels for correct AlertManager routing
- [ ] Alerts route correctly through existing AlertManager config (critical -> 30m repeat, security -> 1h repeat)

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 86](epic-86-zeek-telemetry-capture-health.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_four_capture_alerts_defined` -- Four capture health alerts are defined in zeek-alerts.yml
2. `test_ac2_packet_drop_high_alert` -- ZeekPacketDropHigh fires at >0.1% drop ratio with severity=critical
3. `test_ac3_memory_pressure_alert` -- ZeekMemoryPressure fires at >80% of 4GB limit
4. `test_ac4_event_queue_saturated_alert` -- ZeekEventQueueSaturated fires at queue depth >10000
5. `test_ac5_capture_stalled_alert` -- ZeekCaptureStalled fires when received rate drops to 0 for 2m
6. `test_ac6_alert_labels_correct` -- All alerts include correct service/tier/group labels
7. `test_ac7_alertmanager_routing` -- Alerts route correctly through existing AlertManager config

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- The 0.1% drop ratio threshold is based on industry best practice for IDS/IPS systems — above this, analysis gaps become significant
- Memory threshold (3.2GB) is 80% of the 4GB container limit set in compose.yml
- `ZeekCaptureStalled` uses `== 0` which requires the rate to be exactly zero for the full `for` duration — this avoids false positives from brief traffic lulls
- All alerts use the `domain: security` label for security-relevant alerts, which routes them through the security webhook receiver with 1h repeat interval
- The `for` durations balance between early detection and false positive avoidance

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 86.4 (recording rules must exist for alert expressions)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [ ] **I**ndependent -- Depends on 86.4
- [x] **N**egotiable -- Thresholds and severities can be tuned
- [x] **V**aluable -- Core alerting capability for capture health
- [x] **E**stimable -- Team can estimate the effort
- [x] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->

# Story 86.1 -- Enable Zeek Telemetry Framework in local.zeek

<!-- docsmcp:start:user-story -->

> **As a** platform engineer, **I want** to enable Zeek 8.x's built-in telemetry framework with Prometheus metrics on port 9911, **so that** the capture engine exposes real-time health metrics (packet counts, memory, event queue depth) in a format Prometheus can scrape

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2 | **Size:** S

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that Zeek's built-in telemetry framework is activated, exposing native Prometheus-format metrics from the capture engine. This is the foundation for all subsequent observability work in the epic — without it, no capture-level metrics exist.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Add `@load frameworks/telemetry` and `redef Telemetry::metrics_port = 9911` to the Zeek site configuration (local.zeek). The telemetry framework is built into Zeek 8.x and requires no additional packages. Once loaded, it opens an HTTP endpoint on the specified port that serves metrics in Prometheus text exposition format (text/plain; version=0.0.4). Since Zeek runs with network_mode: host, port 9911 will be directly accessible on the host.

See [Epic 86](epic-86-zeek-telemetry-capture-health.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/data-collectors/zeek-network-service/zeek-config/local.zeek`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Add `@load frameworks/telemetry` to local.zeek before the homeiq.zeek load (`domains/data-collectors/zeek-network-service/zeek-config/local.zeek`)
- [ ] Add `redef Telemetry::metrics_port = 9911;` with comment explaining the port choice (`domains/data-collectors/zeek-network-service/zeek-config/local.zeek`)
- [ ] Add `redef Telemetry::metrics_endpoint_name = "/metrics";` for explicit path (`domains/data-collectors/zeek-network-service/zeek-config/local.zeek`)
- [ ] Rebuild Zeek container and verify `curl http://localhost:9911/metrics` returns Prometheus text format
- [ ] Document which metric families are actually available in Zeek 8.1.1 (may differ from dev docs)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] local.zeek contains `@load frameworks/telemetry` directive
- [ ] `Telemetry::metrics_port` is set to 9911
- [ ] After Zeek container restart `curl http://localhost:9911/metrics` returns HTTP 200 with Content-Type text/plain
- [ ] Response contains at least `zeek_packets_received_total` and `zeek_packets_dropped_total` metric families
- [ ] Zeek process starts without errors related to telemetry framework loading
- [ ] No regression in existing Zeek log output or capture behavior

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 86](epic-86-zeek-telemetry-capture-health.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_localzeek_contains_load_frameworks_telemetry` -- local.zeek contains @load frameworks/telemetry directive
2. `test_ac2_telemetry_metrics_port_set_9911` -- Telemetry::metrics_port is set to 9911
3. `test_ac3_metrics_endpoint_returns_http_200` -- After Zeek container restart curl http://localhost:9911/metrics returns HTTP 200 with Content-Type text/plain
4. `test_ac4_response_contains_packet_counter_metrics` -- Response contains at least zeek_packets_received_total and zeek_packets_dropped_total metric families
5. `test_ac5_zeek_starts_without_telemetry_errors` -- Zeek process starts without errors related to telemetry framework loading
6. `test_ac6_no_regression_in_log_output` -- No regression in existing Zeek log output or capture behavior

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- The telemetry framework is built into Zeek 8.x — no zkg install needed
- The `@load` directive must come before any scripts that might register custom metrics
- Port 9911 is on the host (`network_mode: host`) so it's immediately testable with curl from the host machine
- If `Telemetry::metrics_endpoint_name` is not available in 8.1.1, the default path is `/metrics` anyway
- Expected metric families in Zeek 8.x: `zeek_packets_received_total`, `zeek_packets_dropped_total`, `zeek_active_connections`, `zeek_event_queue_length`, `zeek_memory_usage_bytes`, `zeek_timers_pending`

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- None — this is the first story in the epic

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Can be developed and delivered independently
- [x] **N**egotiable -- Details can be refined during implementation
- [x] **V**aluable -- Delivers value to a user or the system
- [x] **E**stimable -- Team can estimate the effort
- [x] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->

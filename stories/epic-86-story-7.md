# Story 86.7 -- Integration Verification & Documentation

<!-- docsmcp:start:user-story -->

> **As a** platform engineer, **I want** to verify the complete Zeek telemetry -> Prometheus -> AlertManager -> Grafana pipeline and update documentation, **so that** the epic's acceptance criteria are fully validated and future engineers can find and maintain this integration

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2 | **Size:** S

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that the full end-to-end telemetry pipeline is verified working and documented, ensuring the work is sustainable and discoverable by future engineers.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Run an end-to-end verification:
1. Zeek exposes metrics on `:9911`
2. Prometheus scrapes and stores them
3. Recording rules evaluate correctly
4. Alert rules can fire (simulate by temporarily lowering thresholds)
5. Grafana dashboard renders all panels

Update TECH_STACK.md with port 9911 assignment. Add a telemetry health check to the existing healthcheck.sh (curl `:9911/metrics` or fall back gracefully). Update OPEN-EPICS-INDEX.md with Epic 86 entry.

See [Epic 86](epic-86-zeek-telemetry-capture-health.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `docs/TECH_STACK.md`
- `domains/data-collectors/zeek-network-service/healthcheck.sh`
- `stories/OPEN-EPICS-INDEX.md`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Verify Zeek `:9911/metrics` returns HTTP 200 with expected metric families
- [ ] Verify Prometheus target `zeek-telemetry` shows UP with last scrape <30s ago
- [ ] Verify all 6 recording rules evaluate without errors in Prometheus `/rules`
- [ ] Verify all 4 alert rules appear in Prometheus `/alerts` (may be inactive — that's OK)
- [ ] Verify Grafana dashboard renders all panels with live data
- [ ] Add port 9911 (Zeek Telemetry) to TECH_STACK.md port table (`docs/TECH_STACK.md`)
- [ ] Add optional telemetry endpoint check to Zeek healthcheck.sh (`domains/data-collectors/zeek-network-service/healthcheck.sh`)
- [ ] Update OPEN-EPICS-INDEX.md with Epic 86 entry (`stories/OPEN-EPICS-INDEX.md`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] End-to-end pipeline verified: Zeek metrics -> Prometheus -> recording rules -> alerts -> Grafana
- [ ] TECH_STACK.md updated with port 9911 = Zeek Telemetry
- [ ] healthcheck.sh includes optional telemetry endpoint check
- [ ] OPEN-EPICS-INDEX.md updated with Epic 86 entry
- [ ] All 8 epic acceptance criteria are checked off

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 86](epic-86-zeek-telemetry-capture-health.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_end_to_end_pipeline` -- End-to-end pipeline verified: Zeek metrics -> Prometheus -> recording rules -> alerts -> Grafana
2. `test_ac2_tech_stack_port_9911` -- TECH_STACK.md updated with port 9911 = Zeek Telemetry
3. `test_ac3_healthcheck_telemetry` -- healthcheck.sh includes optional telemetry endpoint check
4. `test_ac4_epic_index_updated` -- OPEN-EPICS-INDEX.md updated with Epic 86 entry
5. `test_ac5_all_epic_ac_checked` -- All 8 epic acceptance criteria are checked off

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- The telemetry healthcheck in healthcheck.sh should be optional (non-blocking) — if the telemetry endpoint is down, the Zeek process may still be capturing packets. Use `curl --max-time 2 http://localhost:9911/metrics > /dev/null 2>&1 || true`
- When updating OPEN-EPICS-INDEX.md, add Epic 86 to the P2 Backlog section with status "Proposed"
- TECH_STACK.md port table entry: `9911 | Zeek Telemetry | zeek | Native Prometheus metrics endpoint`

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Stories 86.1-86.6 (all prior stories must be complete)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [ ] **I**ndependent -- Depends on all prior stories
- [x] **N**egotiable -- Documentation scope can be adjusted
- [x] **V**aluable -- Validates the epic and ensures maintainability
- [x] **E**stimable -- Team can estimate the effort
- [x] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->

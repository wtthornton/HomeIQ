# Story 86.3 -- Prometheus Scrape Config for Zeek Telemetry

<!-- docsmcp:start:user-story -->

> **As a** platform engineer, **I want** to add a Prometheus scrape job targeting Zeek's native telemetry endpoint on port 9911, **so that** Zeek capture metrics are stored in Prometheus and available for PromQL queries, recording rules, and alert evaluation

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2 | **Size:** S

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that Prometheus actively scrapes Zeek's native telemetry endpoint, making capture-level metrics available for recording rules, alerts, and Grafana dashboards.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Add a new `zeek-telemetry` scrape job to prometheus.yml that targets `host.docker.internal:9911`. This is separate from the existing `data-collectors` job that scrapes `zeek-network-service:8048` (Python app metrics). Use 30s scrape interval to match the data-collectors group. Apply labels: `service=zeek`, `group=data-collectors`, `tier=2`, `metrics_source=native-telemetry`.

See [Epic 86](epic-86-zeek-telemetry-capture-health.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `infrastructure/prometheus/prometheus.yml`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Add `zeek-telemetry` scrape job to prometheus.yml with target `host.docker.internal:9911` (`infrastructure/prometheus/prometheus.yml`)
- [ ] Set `scrape_interval: 30s` and `scrape_timeout: 10s` matching data-collectors group (`infrastructure/prometheus/prometheus.yml`)
- [ ] Apply labels: `service=zeek`, `group=data-collectors`, `tier=2`, `metrics_source=native-telemetry` (`infrastructure/prometheus/prometheus.yml`)
- [ ] Restart Prometheus and verify target shows as UP in Prometheus UI (http://localhost:9090/targets)
- [ ] Verify `zeek_packets_received_total` metric is queryable in Prometheus expression browser

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] prometheus.yml contains a `zeek-telemetry` scrape job
- [ ] Target `host.docker.internal:9911` appears as UP in Prometheus targets page
- [ ] Zeek native metrics are queryable via PromQL (e.g. `zeek_packets_received_total`)
- [ ] Scrape interval is 30s with 10s timeout
- [ ] Labels correctly identify the source as zeek native telemetry
- [ ] Existing scrape jobs are unaffected

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 86](epic-86-zeek-telemetry-capture-health.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_prometheus_yml_contains_zeek_telemetry_job` -- prometheus.yml contains a zeek-telemetry scrape job
2. `test_ac2_target_shows_up_in_prometheus` -- Target host.docker.internal:9911 appears as UP
3. `test_ac3_metrics_queryable_via_promql` -- Zeek native metrics are queryable via PromQL
4. `test_ac4_scrape_interval_and_timeout` -- Scrape interval is 30s with 10s timeout
5. `test_ac5_labels_correct` -- Labels correctly identify zeek native telemetry
6. `test_ac6_existing_jobs_unaffected` -- Existing scrape jobs are unaffected

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- The `zeek-telemetry` job is intentionally separate from the `data-collectors` job because it targets a different host (`host.docker.internal` vs Docker container names)
- The `metrics_source=native-telemetry` label distinguishes Zeek-native metrics from the zeek-network-service Python app metrics
- Prometheus config reload can be triggered via `POST /-/reload` or container restart

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 86.2 (networking must be configured first)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [ ] **I**ndependent -- Depends on 86.2
- [x] **N**egotiable -- Label names can be adjusted
- [x] **V**aluable -- Makes Zeek metrics available to all downstream consumers
- [x] **E**stimable -- Team can estimate the effort
- [x] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->

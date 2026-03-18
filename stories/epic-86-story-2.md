# Story 86.2 -- Docker Networking — Expose Telemetry Port to Prometheus

<!-- docsmcp:start:user-story -->

> **As a** platform engineer, **I want** to configure Docker networking so Prometheus can scrape Zeek's host-bound telemetry port 9911, **so that** the bridge-to-host connectivity gap is resolved and Prometheus can reach Zeek's native metrics endpoint

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 3 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that Prometheus (running on the Docker bridge network) can reach Zeek's telemetry endpoint (running on the host network). Without solving this networking gap, the metrics exist but can't be scraped.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

The Zeek container runs with `network_mode: host` for physical NIC access, which means port 9911 is on the host. Prometheus runs on the `homeiq-network` Docker bridge. To bridge this gap, add `extra_hosts: ["host.docker.internal:host-gateway"]` to the Prometheus service in the core-platform compose.yml. This allows Prometheus to reach host-bound ports via the `host.docker.internal` hostname. Also add an `EXPOSE 9911` directive to Dockerfile.zeek for documentation purposes (it has no effect with host networking but documents the contract).

See [Epic 86](epic-86-zeek-telemetry-capture-health.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/core-platform/compose.yml`
- `domains/data-collectors/zeek-network-service/Dockerfile.zeek`
- `domains/data-collectors/compose.yml`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Add `extra_hosts: ["host.docker.internal:host-gateway"]` to Prometheus service in core-platform compose.yml (`domains/core-platform/compose.yml`)
- [ ] Add `EXPOSE 9911` to Dockerfile.zeek — documentation only, no effect with host networking (`domains/data-collectors/zeek-network-service/Dockerfile.zeek`)
- [ ] Add `ZEEK_TELEMETRY_PORT=9911` environment variable to zeek service in compose.yml for configurability (`domains/data-collectors/compose.yml`)
- [ ] Verify from inside Prometheus container: `curl http://host.docker.internal:9911/metrics` returns Zeek metrics
- [ ] Test on Docker Desktop (Windows) and document any Linux-specific differences

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Prometheus container has `extra_hosts` entry for `host.docker.internal`
- [ ] From inside Prometheus container `curl http://host.docker.internal:9911/metrics` returns Zeek metrics
- [ ] Dockerfile.zeek documents `EXPOSE 9911`
- [ ] No disruption to existing Prometheus scrape targets
- [ ] Docker compose up succeeds without networking errors

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 86](epic-86-zeek-telemetry-capture-health.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_prometheus_extra_hosts_entry` -- Prometheus container has extra_hosts entry for host.docker.internal
2. `test_ac2_prometheus_can_reach_zeek_metrics` -- From inside Prometheus container curl returns Zeek metrics
3. `test_ac3_dockerfile_expose_9911` -- Dockerfile.zeek documents EXPOSE 9911
4. `test_ac4_no_existing_scrape_disruption` -- No disruption to existing Prometheus scrape targets
5. `test_ac5_compose_up_succeeds` -- Docker compose up succeeds without networking errors

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Docker Desktop on Windows/macOS automatically resolves `host.docker.internal`
- On native Linux Docker 20.10+, the `extra_hosts: host-gateway` directive maps it correctly
- The homeiq stack runs on Docker Desktop for Windows so this should work out of the box
- If the deployment target changes to native Linux, ensure Docker version >= 20.10
- The `ZEEK_TELEMETRY_PORT` env var allows overriding the port without rebuilding the Zeek config

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Story 86.1 (telemetry must be enabled first)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [ ] **I**ndependent -- Depends on 86.1
- [x] **N**egotiable -- Networking approach can be adjusted
- [x] **V**aluable -- Bridges the critical host-to-bridge gap
- [x] **E**stimable -- Team can estimate the effort
- [x] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->

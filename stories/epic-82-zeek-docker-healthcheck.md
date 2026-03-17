# Epic 82: Zeek Container Docker Healthcheck

**Priority:** P3 Low | **Effort:** 1 session | **Dependencies:** Epic 72 (Zeek Core Network Ingestion) | **Status:** IN PROGRESS (3/5 stories complete)
**Affects:** `homeiq-zeek` container (only container in the stack without a Docker healthcheck)
**Domain:** `domains/data-collectors/`

## Background

HomeIQ runs 58 production containers across 9 domain groups. As of Sprint 37, **57 of 58** report
`healthy` status via Docker healthchecks. The sole exception is `homeiq-zeek`, which shows only
`Up` — it has no `healthcheck:` block in compose.

The Zeek container is architecturally unique: it runs with `network_mode: host` for raw packet
capture (CAP_NET_RAW/CAP_NET_ADMIN), has no HTTP server, and runs a single `zeek -i af_packet::eth0`
process. Traditional HTTP health endpoints don't apply here.

### Why This Matters

- **Docker restart policy:** Without a healthcheck, `restart: unless-stopped` can only detect
  process exit, not a hung or degraded Zeek process (e.g., interface down, log stall)
- **Compose dependency:** `zeek-network-service` uses `condition: service_started` — with a
  healthcheck it could upgrade to `condition: service_healthy` for safer startup ordering
- **Observability gap:** `docker ps` shows 57 healthy + 1 unknown — the gap creates uncertainty
  during incident triage
- **Consistency:** All other HomeIQ containers follow the standard healthcheck pattern
  (`interval: 30s, timeout: 10s, retries: 3, start_period: 40s`)

### Research: Zeek 8.x Health Monitoring (Mar 2026)

**No community Zeek Docker image implements a HEALTHCHECK directive.** Official `zeek/zeek`,
`activecm/docker-zeek`, `blacktop/docker-zeek`, and Security Onion all rely on external
monitoring or `zeekctl cron` for self-healing. HomeIQ would be leading best practice here.

**Key constraint:** Since `homeiq-zeek` uses `exec zeek -i af_packet::...` directly (standalone
mode, not zeekctl cluster mode), `zeekctl status/netstats/cron` commands are NOT available.
The healthcheck must rely on OS-level signals.

**Available tools in `zeek/zeek:8.1.1` base image:** `pgrep`, `find`, `sh` are all present.
`curl` is NOT installed — HTTP-based checks would require adding it to the Dockerfile.

**Zeek 8.x health signals available in standalone mode:**

1. **Process alive:** `pgrep -x zeek` — single process in standalone mode
2. **Log freshness:** Zeek writes `conn.log` continuously; stale logs indicate capture failure.
   5-minute log rotation configured in `local.zeek`, so a fresh log = active packet processing
3. **Capture stats:** `/proc/net/dev` counters on the capture interface confirm packets are flowing
4. **Log directory:** `/zeek/logs/` should contain active log files (conn.log, dns.log, etc.)
5. **Telemetry framework (future):** Zeek 8.x supports `@load frameworks/telemetry` with
   `Telemetry::metrics_port` for Prometheus-format metrics at an HTTP endpoint — could be
   enabled in a future epic for richer observability (packet counts, memory, event queue depth)

### Existing HomeIQ Healthcheck Patterns

| Container | Check Type | Command |
|-----------|-----------|---------|
| influxdb | HTTP | `curl -f http://localhost:8086/health` |
| postgres | CLI | `pg_isready -U homeiq -d homeiq` |
| data-api | Python urllib | `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8006/health')"` |
| alertmanager | HTTP | `curl -f http://localhost:9093/-/healthy` |
| zeek-network-service | HTTP | `curl -f http://localhost:8048/health` |

For Zeek, the appropriate pattern is a **process + log freshness** shell check, similar to
how `postgres` uses `pg_isready` (CLI tool, not HTTP).

## Stories

| Story | Description | Status |
|-------|-------------|--------|
| 82.1 | **Design healthcheck script** — Create `/usr/local/bin/healthcheck.sh` for the Zeek container. Two-phase check: (1) `pgrep -x zeek` confirms process alive, (2) verify any `.log` file in `/zeek/logs/` was modified within the last 10 minutes (2x rotation period for safety margin). Exit 0 = healthy, exit 1 = unhealthy. Script must be POSIX-compatible (Zeek base image is Debian). `pgrep` and `find` are confirmed available in `zeek/zeek:8.1.1` — no extra packages needed | COMPLETE |
| 82.2 | **Update Dockerfile.zeek** — Add `COPY` for `healthcheck.sh` into the image, `chmod +x`. Add `HEALTHCHECK` instruction as a Dockerfile default: `HEALTHCHECK --interval=60s --timeout=10s --retries=3 --start-period=120s CMD /usr/local/bin/healthcheck.sh`. Use 120s start period (Zeek needs time to initialize af_packet capture, begin processing, and write first log rotation). Use 60s interval (less aggressive than the standard 30s since log freshness check has a 10-min window) | COMPLETE |
| 82.3 | **Add compose healthcheck block** — Add `healthcheck:` to the `zeek` service in `domains/data-collectors/compose.yml` matching HomeIQ standard pattern. Update `zeek-network-service` depends_on from `condition: service_started` to `condition: service_healthy` so the sidecar waits for confirmed packet capture before starting log parsing | COMPLETE |
| 82.4 | **Build, deploy & verify** — Rebuild Zeek image (`docker compose build zeek`), restart both Zeek containers, verify `docker ps` shows `homeiq-zeek` as `healthy`. Confirm `zeek-network-service` starts only after Zeek healthcheck passes. Verify 58/58 containers now report healthy status | TODO |
| 82.5 | **Regression test — Zeek-down scenario** — Validate the healthcheck correctly detects failure: (1) `docker exec homeiq-zeek pkill zeek` and confirm container transitions to `unhealthy` within 90s (3 retries x 30s), (2) confirm Docker restart policy brings Zeek back to `healthy`, (3) confirm `zeek-network-service` continues operating in degraded mode during the restart window (existing behavior from Story 72.7) | TODO |

## Acceptance Criteria

- [ ] `docker ps` shows `homeiq-zeek` as `healthy` during normal operation
- [ ] Healthcheck detects process death within 3 minutes (3 retries x 60s interval)
- [ ] Healthcheck detects log stall (Zeek alive but not writing) within 10 minutes
- [ ] `zeek-network-service` depends_on `condition: service_healthy`
- [ ] All 58/58 containers report healthy status
- [ ] No false positives during Zeek's startup phase (120s grace period)
- [ ] No additional packages required in `zeek/zeek:8.1.1` base image

## Healthcheck Script (Reference Design)

```bash
#!/bin/sh
# Zeek Docker healthcheck — process alive + log freshness
# No community Zeek Docker image implements a healthcheck (as of Mar 2026);
# this is a HomeIQ-original pattern for standalone-mode Zeek.

# Phase 1: Zeek process must be running
pgrep -x zeek > /dev/null 2>&1 || exit 1

# Phase 2: At least one log file must have been written within 10 minutes
# (2x the 5-min rotation interval configured in local.zeek for safety margin)
# During startup, no logs exist yet — the 120s start_period covers this window.
test -n "$(find /zeek/logs -name '*.log' -mmin -10 2>/dev/null)" || exit 1
```

## Dependency Graph

```
82.1 (healthcheck script)
  │
82.2 (Dockerfile update)
  │
82.3 (compose update)
  │
82.4 (build & deploy)
  │
82.5 (regression test)
```

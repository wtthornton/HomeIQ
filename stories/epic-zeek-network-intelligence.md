# Zeek Network Intelligence — Epics 72-75

**Created:** 2026-03-16
**PRD:** [zeek-network-intelligence-prd.md](../docs/architecture/zeek-network-intelligence-prd.md)
**Target Domain:** `domains/data-collectors/zeek-network-service/`
**Port:** 8048
**Total:** 4 Epics, 25 Stories

> Implements passive network monitoring for all IoT devices using Zeek Network Security Monitor.
> Two containers: `zeek` (packet capture, `--net=host`) + `zeek-network-service` (Python sidecar, FastAPI, port 8048).
> Follows existing data-collector pattern: BaseServiceSettings + ServiceLifespan + InfluxDB writes.

---

## Epic 72: Zeek Core Network Ingestion (Phase 1 — MVP)

**Priority:** P1 | **Effort:** 1-2 weeks | **Dependencies:** None (greenfield service)
**Goal:** Deploy Zeek, parse conn.log and dns.log, write to InfluxDB, expose REST API.

| Story | Description | Status |
|-------|-------------|--------|
| 72.1 | **Zeek Docker image & config files** — Custom `Dockerfile.zeek` (FROM `zeek/zeek:8.1.1`), `local.zeek` + `homeiq.zeek` configs (JSON output, 5-min rotation, MQTT enabled). Entrypoint script for `ZEEK_INTERFACE` env var expansion (exec form `CMD` cannot expand shell variables). Verify image builds and Zeek starts with default config | **DONE** |
| 72.2 | **Compose integration & shared volume** — Add `zeek` + `zeek-network-service` to `domains/data-collectors/compose.yml`. `--net=host`, `NET_RAW`/`NET_ADMIN` caps, BPF filter excluding Docker bridge (`not net 172.18.0.0/16`), shared `zeek-logs` volume (local driver, read-only mount for sidecar), port 8048. Note: Zeek container uses `network_mode: host` so is not reachable by service name — health is monitored indirectly via log freshness in the sidecar | **DONE** |
| 72.3 | **Python service scaffold** — `zeek-network-service` with `BaseServiceSettings`, `ServiceLifespan`, `StandardHealthCheck`. Multi-stage Alpine Dockerfile installing all 6 homeiq libs (including `homeiq-memory`). Health endpoint reporting Zeek process status, log freshness, InfluxDB write counts. `requirements.txt` with fastapi, uvicorn, influxdb-client, asyncpg, httpx. Initialize Alembic environment (empty migration head — first migration in Epic 73) | **DONE** |
| 72.4 | **conn.log parser + InfluxDB writer** — Background polling loop (30s) parsing `conn.log` JSON → `network_connections` InfluxDB measurement. Log file position tracking via JSON state file on persistent volume (`/app/state/offsets.json`) to avoid re-processing on restart. Handles Zeek's 5-min log rotation gracefully (detect renamed file via inode or file-size reset, open new file). In-memory buffer (5 min max) when InfluxDB is unavailable, flush on recovery | **DONE** |
| 72.5 | **dns.log parser + InfluxDB writer** — Background polling loop parsing `dns.log` JSON → `network_dns` InfluxDB measurement. Tags: device_ip, query_domain, query_type, rcode_name. Fields: rtt, answers_count, ttl, rejected. Reuses log_tracker from 72.4 for seek offset persistence and rotation handling | **DONE** |
| 72.6 | **Per-device metric aggregation** — 60s aggregation window computing `network_device_metrics` measurement from parsed conn.log data. Fields: total_bytes_sent/recv, connection_count, unique_destinations, unique_domains, avg_conn_duration, active_services | **DONE** |
| 72.7 | **REST API + integration tests** — `GET /health`, `GET /current-stats` (connections/min, bytes/min, top talkers), `GET /devices` (all discovered), `GET /devices/{ip}` (detail), `GET /cache/stats`. Tests: health endpoint, BPF filter exclusion (no Docker bridge IPs in parsed data), restart recovery (no duplicate writes after offset restore), Zeek-down degraded mode, InfluxDB-down buffering. 25 tests passing | **DONE** |

**Dependency graph:**
```
72.1 (Zeek image) ── parallel ── 72.3 (Python scaffold)
        │                              │
  72.2 (Compose)                       │
        └───────────────┬──────────────┘
                  72.4 (conn.log) ← 72.5 (dns.log)
                        │
                  72.6 (aggregation)
                        │
                  72.7 (API + tests)
```

---

## Epic 73: Zeek Device Fingerprinting (Phase 2)

**Priority:** P1 | **Effort:** 2-3 weeks | **Dependencies:** Epic 72 complete
**Goal:** Auto-discover devices via DHCP, fingerprint via JA3/JA4/HASSH, feed device-intelligence-service.

| Story | Description | Status |
|-------|-------------|--------|
| 73.1 | **Custom Zeek image with fingerprinting packages** — Extend `Dockerfile.zeek` with `zkg install` for `zeek/ja3`, `foxio-n/ja4`, `salesforce/hassh`, `corelight/KYD` (DHCP fingerprinting). Pin package versions for reproducibility | **DONE** |
| 73.2 | **DHCP parsing + PostgreSQL fingerprints** — Parse `dhcp.log` + `dhcpfp.log` → `devices.network_device_fingerprints` table (MAC, IP, hostname, vendor, DHCP fingerprint). Alembic migration. Device deduplication: MAC is primary key, IP updates on DHCP renewal, `times_seen` increments, `last_seen` updates | **DONE** |
| 73.3 | **TLS fingerprinting** — Parse `ssl.log` + `ja3.log` + `ja4.log` → update `network_device_fingerprints` with `ja3_hash`, `ja3s_hash`, `ja4_hash`. Correlate by source IP to existing MAC-based records | **DONE** |
| 73.4 | **SSH + software fingerprinting** — Parse `hassh.log` → `hassh_hash`, `hassh_server`. Parse `software.log` → `user_agent`, `server_software`, `os_guess`. Update existing fingerprint records by IP→MAC correlation | **DONE** |
| 73.5 | **MAC OUI vendor lookup** — Bundle IEEE OUI database (CSV or SQLite). Lookup `vendor` from first 3 octets of MAC address. Auto-populate on DHCP discovery. Fallback to "Unknown" for unrecognized OUIs | **DONE** |
| 73.6 | **Fingerprint REST API + cross-service feeds** — `GET /devices/{ip}/fingerprint`, `GET /devices/discovered` (last 24h), `GET /devices/new` (not in baseline). Feed `device-intelligence-service` with JA3/JA4→device type mapping via data-api. Feed `device-database-client` with auto-discovered MAC/vendor/hostname. Integration tests | **DONE** |

**Dependency graph:**
```
73.1 (Zeek packages) → 73.2 (DHCP + PG table)
                              │
              ┌───────────────┼───────────────┐
        73.3 (TLS)      73.4 (SSH/SW)    73.5 (OUI)
              └───────────────┼───────────────┘
                              │
                        73.6 (API + feeds)
```

---

## Epic 74: Zeek MQTT & Protocol Intelligence (Phase 3)

**Priority:** P2 | **Effort:** 1-2 weeks | **Dependencies:** Epic 72 complete (Epic 73 recommended)
**Goal:** Monitor HA MQTT backbone, track TLS certificates, build DNS behavior profiles.

| Story | Description | Status |
|-------|-------------|--------|
| 74.1 | **MQTT log parsing → InfluxDB** — Parse `mqtt_connect.log`, `mqtt_publish.log`, `mqtt_subscribe.log` → `network_mqtt` measurement. Tags: client_id, client_ip, topic, action, qos. Fields: payload_size, retain, connect_ok, proto_version. 30s batch writes | **DONE** |
| 74.2 | **TLS certificate tracking** — Parse `x509.log` + `ssl.log` → `devices.network_tls_certificates` PostgreSQL table. Track subject, issuer, validity dates, key type/length, TLS version, cipher suite, self-signed flag. Alembic migration. Detect expired certs → `network_anomalies` | **DONE** |
| 74.3 | **DNS behavior profiles** — Build `devices.network_device_dns_profiles` from dns.log — per-device domain query frequency with category classification (cloud_api, ntp, update_check, ad_tracker, social_media, unknown). Domain suffix matching for categorization. Alembic migration. Rolling 7-day query counts | **DONE** |
| 74.4 | **Protocol intelligence REST API** — `GET /mqtt/topics` (active topics + message counts), `GET /mqtt/clients` (connected clients), `GET /tls/certificates` (tracked certs + expiry status), `GET /dns/profiles/{ip}` (per-device DNS profile) | **DONE** |
| 74.5 | **Alerting + cross-service feeds** — Alert on: rogue MQTT clients (unknown client_id), expired TLS certificates, TLS < 1.2 negotiation. Feed `automation-trace-service` with MQTT message metadata for end-to-end automation tracing. Integration tests | **DONE** |

**Dependency graph:**
```
74.1 (MQTT) ── parallel ── 74.2 (TLS certs) ── parallel ── 74.3 (DNS profiles)
        └────────────────────────┬────────────────────────────┘
                           74.4 (REST API)
                                 │
                           74.5 (Alerts + feeds)
```

---

## Epic 75: Zeek Anomaly Detection & Security Baseline (Phase 4)

**Priority:** P2 | **Effort:** 2-3 weeks | **Dependencies:** Epics 72 + 73 complete
**Goal:** Establish network baseline, detect anomalies, feed proactive-agent-service.

| Story | Description | Status |
|-------|-------------|--------|
| 75.1 | **Anomaly log parsing** — Parse `weird.log` → `network_anomalies` InfluxDB measurement (protocol violations). Parse `notice.log` → `network_anomalies` (Zeek-generated alerts). Tags: source_ip, anomaly_type, severity, source_log. Fields: name, message, peer, suppress_for. On-occurrence writes (not batched) | **DONE** |
| 75.2 | **Network baseline** — Parse `known_hosts.log` + `known_services.log` → `devices.network_baseline_hosts` PostgreSQL table. Track IP, MAC, hostname, first/last seen, is_baseline flag, approved_by, services JSONB. Alembic migration. `POST /baseline/approve/{ip}` to mark devices as known | **DONE** |
| 75.3 | **New device detection** — Alert when a previously unseen MAC address appears on the network. Write `network_anomalies` with `anomaly_type=new_device`, `severity=warning`. Suppress after baseline approval. Cross-reference with `network_device_fingerprints` for enriched alerts | **DONE** |
| 75.4 | **Beaconing + DNS anomaly detection** — Beaconing: identify connections with regular intervals to external IPs (C2 indicator, >1h persistence, ±5s jitter threshold). DNS anomalies: DGA domain detection (high entropy names), DNS tunneling (large TXT records). Configurable thresholds via env vars | **DONE** |
| 75.5 | **zeek-flowmeter ML features** — Install `SuperCowPowers/zeek-flowmeter` package. Parse `flowmeter.log` → feed `ml-service` with ML-ready traffic features for network-based anomaly detection models | **DONE** |
| 75.6 | **Cross-service security feeds** — Feed `proactive-agent-service` with security events (anomalies, new devices, beaconing) via data-api or direct HTTP. Feed `ai-pattern-service` with network behavioral patterns (DNS profiles, connection graphs) for automation enrichment | **DONE** |
| 75.7 | **Security REST API + integration tests** — `GET /anomalies` (filterable by type/severity), `GET /baseline/devices`, `GET /security/alerts` (active alerts). Configurable alert thresholds. Tests: new device detection, beaconing detection, baseline approval, proactive-agent feed, Zeek-down degradation | **DONE** |

**Dependency graph:**
```
75.1 (weird/notice) ── parallel ── 75.2 (baseline)
        │                                │
        │                          75.3 (new device)
        │                                │
        ├──────── 75.4 (beaconing/DNS) ──┤
        │                                │
        └──── 75.5 (flowmeter) ──────────┤
                                         │
                                   75.6 (cross-service)
                                         │
                                   75.7 (API + tests)
```

---

## Execution Plan

| Sprint | Epic | Stories | Effort | Notes |
|--------|------|---------|--------|-------|
| 30 | 72: Core Ingestion | 7 | **COMPLETE** | 7/7 stories, 22 files, 25 tests. Review fixes applied |
| 31 | 73: Fingerprinting | 6 | **COMPLETE** | 6/6 stories, 7 new files, 32 tests. OUI database (~200 vendors), asyncpg fingerprint service |
| 32 | 74: MQTT/Protocol | 5 | **COMPLETE** | 5/5 stories, 8 new files, 39 tests. MQTT parsing, cert tracking, DNS profiling, security alerts |
| 33 | 75: Anomaly/Security | 7 | **COMPLETE** | 7/7 stories, 7 new files, 37 tests. Anomaly parsing, network baseline, beaconing/DGA/DNS tunneling detection, flowmeter ML features, security feeds |

**Total:** 25 stories across 4 epics (Epics 72-75) — 25 complete, 0 planned

---

## New Files Created

### Epic 72
- `domains/data-collectors/zeek-network-service/Dockerfile`
- `domains/data-collectors/zeek-network-service/Dockerfile.zeek`
- `domains/data-collectors/zeek-network-service/docker-entrypoint.sh`
- `domains/data-collectors/zeek-network-service/requirements.txt`
- `domains/data-collectors/zeek-network-service/src/main.py`
- `domains/data-collectors/zeek-network-service/src/config.py`
- `domains/data-collectors/zeek-network-service/src/parsers/conn_parser.py`
- `domains/data-collectors/zeek-network-service/src/parsers/dns_parser.py`
- `domains/data-collectors/zeek-network-service/src/services/influx_writer.py`
- `domains/data-collectors/zeek-network-service/src/services/log_tracker.py`
- `domains/data-collectors/zeek-network-service/src/services/device_aggregator.py`
- `domains/data-collectors/zeek-network-service/zeek-config/local.zeek`
- `domains/data-collectors/zeek-network-service/zeek-config/homeiq.zeek`
- `domains/data-collectors/zeek-network-service/alembic.ini`
- `domains/data-collectors/zeek-network-service/alembic/env.py`

### Epic 73
- `domains/data-collectors/zeek-network-service/src/models/__init__.py`
- `domains/data-collectors/zeek-network-service/src/models/fingerprints.py`
- `domains/data-collectors/zeek-network-service/src/parsers/dhcp_parser.py`
- `domains/data-collectors/zeek-network-service/src/parsers/tls_parser.py`
- `domains/data-collectors/zeek-network-service/src/parsers/ssh_parser.py`
- `domains/data-collectors/zeek-network-service/src/services/fingerprint_service.py`
- `domains/data-collectors/zeek-network-service/src/services/oui_lookup.py`
- `domains/data-collectors/zeek-network-service/alembic/versions/001_fingerprints.py`
- `domains/data-collectors/zeek-network-service/tests/test_fingerprinting.py`

### Epic 74
- `domains/data-collectors/zeek-network-service/src/parsers/mqtt_parser.py`
- `domains/data-collectors/zeek-network-service/src/parsers/x509_parser.py`
- `domains/data-collectors/zeek-network-service/src/services/dns_profiler.py`
- `domains/data-collectors/zeek-network-service/src/services/cert_tracker.py`
- `domains/data-collectors/zeek-network-service/src/models/dns_profiles.py`
- `domains/data-collectors/zeek-network-service/src/models/tls_certificates.py`
- `domains/data-collectors/zeek-network-service/alembic/versions/002_dns_profiles.py`
- `domains/data-collectors/zeek-network-service/alembic/versions/003_tls_certificates.py`
- `domains/data-collectors/zeek-network-service/tests/test_protocol_intelligence.py`

### Epic 75
- `domains/data-collectors/zeek-network-service/src/parsers/anomaly_parser.py`
- `domains/data-collectors/zeek-network-service/src/services/baseline_service.py`
- `domains/data-collectors/zeek-network-service/src/services/anomaly_detector.py`
- `domains/data-collectors/zeek-network-service/src/models/baseline_hosts.py`
- `domains/data-collectors/zeek-network-service/alembic/versions/004_baseline_hosts.py`

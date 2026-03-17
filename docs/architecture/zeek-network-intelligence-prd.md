# PRD & Architecture: Zeek Network Intelligence Service

**Document Type:** Combined Product Requirements Document + Architecture Specification
**Status:** Complete (All 4 phases delivered — 25/25 stories, 133 tests)
**Created:** 2026-03-16
**Author:** HomeIQ Engineering
**Epics:** 72 (Core Ingestion), 73 (Fingerprinting), 74 (MQTT/Protocol), 75 (Anomaly/Security)
**Stories:** [epic-zeek-network-intelligence.md](../../stories/epic-zeek-network-intelligence.md)
**Target Domain:** `domains/data-collectors/zeek-network-service/`

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [User Personas](#user-personas)
4. [Solution Overview](#solution-overview)
5. [Architecture](#architecture)
6. [Zeek Technology Profile](#zeek-technology-profile)
7. [Data Model](#data-model)
8. [Phased Requirements](#phased-requirements)
9. [API Specification](#api-specification)
10. [Integration Map](#integration-map)
11. [Docker & Infrastructure](#docker--infrastructure)
12. [Zeek Configuration](#zeek-configuration)
13. [Security Considerations](#security-considerations)
14. [Acceptance Criteria](#acceptance-criteria)
15. [Non-Goals](#non-goals)
16. [Risk Assessment](#risk-assessment)
17. [Appendix: Zeek Log Reference](#appendix-zeek-log-reference)

---

## Executive Summary

HomeIQ monitors 50+ smart home services across 9 domain groups but has **zero visibility into the network layer** — the transport medium connecting every IoT device, Home Assistant, and cloud service. This document specifies a new **zeek-network-service** that leverages the [Zeek Network Security Monitor](https://zeek.org/) to passively analyze all network traffic flowing through the HomeIQ host, producing structured metadata about connections, DNS queries, MQTT messages, device fingerprints, TLS certificates, and network anomalies.

The service follows HomeIQ's established data-collector pattern (FastAPI + `BaseServiceSettings` + `ServiceLifespan` + InfluxDB writes) and deploys as two containers: the official Zeek image for packet capture and a Python sidecar for log parsing, enrichment, and data routing.

**Key value propositions:**
- **Device intelligence enrichment** — JA3/JA4 + DHCP + DNS fingerprinting feeds `device-intelligence-service` (6,000+ device mappings)
- **Energy-network correlation** — per-device bandwidth metrics correlated with power consumption via `energy-correlator`
- **MQTT backbone visibility** — Zeek's native MQTT analyzer monitors the HA message bus end-to-end
- **Passive security monitoring** — anomaly detection, new device alerts, and TLS posture assessment feed `proactive-agent-service`
- **Behavioral pattern enrichment** — DNS and connection patterns feed `ai-pattern-service` for richer automation suggestions
- **Greenfield opportunity** — As of March 2026, no Zeek + Home Assistant integration exists anywhere; HomeIQ would be first-to-market with deep network intelligence for smart homes

---

## Problem Statement

### Current State

HomeIQ's data pipeline captures Home Assistant events (websocket-ingestion), external data (8 data collectors), and device metadata (device-management group). However, it operates **above the network layer** — it knows *what* devices do in HA but not *how* they communicate:

| Capability | Current State | With Zeek |
|---|---|---|
| Device inventory | HA entity registry only | + DHCP/DNS auto-discovery of all network devices |
| Device identification | HA integration labels | + JA3/JA4/HASSH/DHCP fingerprinting |
| Network bandwidth | None | Per-device connection metrics (bytes, duration, frequency) |
| MQTT monitoring | None (HA events only) | Full topic/client/payload visibility |
| DNS behavior | None | Per-device DNS query profiles |
| TLS security posture | None | Certificate validity, cipher strength, TLS version per device |
| Network anomalies | None | Protocol violations, beaconing, new device alerts |
| Cloud endpoint mapping | None | Which devices talk to which cloud services |

### Impact of the Gap

1. **device-intelligence-service** has 6,000+ device capability mappings but no network-layer signals to validate or enrich them
2. **energy-correlator** correlates power consumption with HA events but misses network activity as a causal signal (e.g., firmware update causing power spike)
3. **proactive-agent-service** generates recommendations but cannot detect network-level security issues (compromised devices, data exfiltration, DNS tunneling)
4. **activity-recognition** uses HA state changes for presence detection but misses network-based signals (phone connecting to WiFi, device wake patterns)
5. **ai-pattern-service** builds behavioral patterns from HA events only — network communication patterns would significantly enrich pattern quality

---

## User Personas

### 1. HomeIQ Platform Administrator
- Manages the Docker stack (50+ containers) and Home Assistant instance
- Needs: Easy deployment (two containers), minimal configuration, resource-aware sizing
- Pain point: No way to audit what IoT devices are actually doing on the network
- Key features: Device discovery, network baseline, health dashboard integration

### 2. Smart Home Power User
- Runs 50-200 IoT devices across multiple protocols (Zigbee, Z-Wave, WiFi, Thread)
- Needs: Comprehensive device inventory, MQTT traffic insights, device behavior profiles
- Pain point: Devices appear in HA but their network behavior is opaque
- Key features: Device fingerprinting, DNS profiling, MQTT topic monitoring

### 3. Energy-Conscious Homeowner
- Uses HomeIQ's energy analytics to optimize consumption
- Needs: Correlation between network activity and power usage
- Pain point: Unexplained power consumption spikes with no network activity context
- Key features: Per-device bandwidth metrics in InfluxDB, energy-correlator integration

### 4. Security-Aware User
- Concerned about IoT device security and privacy
- Needs: Alerts on suspicious behavior, TLS posture visibility, new device detection
- Pain point: No way to know if a device is compromised or phoning home to unexpected servers
- Key features: Anomaly detection, certificate monitoring, beaconing detection, DNS anomaly alerts

---

## Solution Overview

### Two-Container Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  HomeIQ Docker Host (--net=host for zeek container)                  │
│                                                                     │
│  ┌───────────────────────┐    ┌────────────────────────────────┐   │
│  │  zeek                  │    │  zeek-network-service           │   │
│  │  (official image)      │    │  (Python 3.12 + FastAPI)        │   │
│  │                        │    │                                  │   │
│  │  - Packet capture      │    │  - JSON log parser               │   │
│  │  - Protocol analysis   │    │  - InfluxDB writer               │   │
│  │  - JSON log output     │──▶│  - PostgreSQL writer             │   │
│  │  - JA3/JA4/HASSH/KYD  │    │  - REST API (:8048)             │   │
│  │  - MQTT analyzer       │    │  - Health endpoint               │   │
│  │  - zeek-flowmeter      │    │  - Device enrichment             │   │
│  │  - BPF filter          │    │  - Anomaly detection             │   │
│  │                        │    │                                  │   │
│  │  Volume: /zeek-logs    │    │  Volume: /zeek-logs (read-only) │   │
│  └───────────────────────┘    └──────────┬───────────────────────┘   │
│                                          │                           │
│                    ┌─────────────────────┼──────────────────┐       │
│                    ▼                     ▼                  ▼       │
│             ┌──────────┐         ┌────────────┐    ┌──────────┐    │
│             │ InfluxDB  │         │ PostgreSQL  │    │ Existing │    │
│             │ :8086     │         │ (devices    │    │ Services │    │
│             │           │         │  schema)    │    │          │    │
│             │ Metrics:  │         │             │    │ device-  │    │
│             │ - conns   │         │ Metadata:   │    │ intel    │    │
│             │ - dns     │         │ - fingerprts│    │ energy-  │    │
│             │ - mqtt    │         │ - profiles  │    │ corr     │    │
│             │ - anomaly │         │ - certs     │    │ proactive│    │
│             └──────────┘         └────────────┘    └──────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Follow existing patterns** — Same lifecycle, settings, health, and data flow as weather-api, smart-meter-service, and other data collectors
2. **Passive only** — Zeek observes traffic; it never injects, blocks, or modifies packets
3. **File-based coupling** — Zeek writes JSON logs to a shared volume; the Python service tails them on a 30s interval (no Kafka dependency)
4. **Enrich, don't duplicate** — Feed existing services (device-intelligence, energy-correlator, proactive-agent) rather than building parallel analysis
5. **BPF-filtered** — Exclude Docker bridge traffic (`homeiq-network`) to avoid monitoring HomeIQ's own inter-service chatter

---

## Zeek Technology Profile

### What Is Zeek

[Zeek](https://zeek.org/) (formerly "Bro", renamed 2018) is an open-source, BSD-licensed **programmable network analysis framework**. Unlike signature-based IDS tools (Snort, Suricata), Zeek passively observes network traffic and produces **rich, structured metadata logs** — one per protocol. It has a layered architecture:

1. **Event Engine (C++ core)** — Packet capture → protocol parsing → session reassembly → file analysis → event generation
2. **Script Interpreter** — Event-driven domain-specific language for defining logging, detection, and correlation logic
3. **Spicy Integration** — Modern parser generator for adding new protocol analyzers without modifying C++ core

### Key Capabilities for HomeIQ

| Capability | Relevance |
|---|---|
| **40+ protocol analyzers** | HTTP, DNS, TLS/SSL, SSH, DHCP, NTP, MQTT, Modbus, WebSocket, RADIUS, and more |
| **Native MQTT support** | Directly monitors the HA MQTT backbone (Zigbee2MQTT, Tasmota, ESPHome) |
| **JSON log output** | `redef LogAscii::use_json = T;` — one JSON object per line, easy to parse |
| **Device fingerprinting ecosystem** | JA3/JA4 (TLS), HASSH (SSH), KYD (DHCP) — mature community packages |
| **Zeek scripting language** | Custom detectors, log enrichment, stateful cross-connection correlation |
| **Docker support** | Official `zeek/zeek` image on Docker Hub with `zkg` package manager |
| **Low resource footprint (home scale)** | ~2 cores, 4GB RAM for <100 Mbps sustained traffic |

### Zeek Packages Required

| Package | Purpose | Log Files Added |
|---|---|---|
| **ja3** | TLS client fingerprinting (MD5 hash of Client Hello) — legacy, kept for backwards compatibility | `ja3.log` |
| **ja4** (foxio-n/ja4) | Next-gen multi-method fingerprinting suite (see JA4+ details below) | Multiple (see below) |
| **hassh** | SSH client/server fingerprinting | `hassh.log` |
| **KYD** (corelight/KYD) | DHCP client fingerprint hashing | `dhcpfp.log` |
| **zeek-flowmeter** | ML-ready traffic features (timing, volume, metadata) | `flowmeter.log` |

### JA4+ Fingerprint Suite (2026 State of the Art)

The JA4 package provides **11 fingerprint methods** — the combination of 3-5 signals achieves **92-97% IoT device identification accuracy** (vs ~50-60% for JA3 alone):

| Method | What It Fingerprints | IoT Value | Zeek Support |
|---|---|---|---|
| **JA4** | TLS Client Hello (ciphers, extensions, ALPN) | High — embedded TLS stacks are distinctive | Yes |
| **JA4S** | TLS Server Hello response | Medium — cloud backend identification | Yes |
| **JA4H** | HTTP client (headers, cookies, accept-encoding) | Medium — decreasing as TLS adoption grows | Yes |
| **JA4T** | TCP client fingerprint (window size, options, timestamps) | **Very high** — embedded OS TCP stacks are distinctive | Yes |
| **JA4TS** | TCP server response fingerprint | Medium | Yes |
| **JA4D** | DHCP client fingerprint (option order, requested options) | **Very high** — best single signal for IoT device ID | Yes (v0.18.8+) |
| **JA4D6** | DHCPv6 client fingerprint | Medium — growing with IPv6 IoT | Yes (v0.18.8+) |
| **JA4X** | X.509 certificate structure | Medium — identifies cert issuers | Yes |
| **JA4SSH** | SSH traffic patterns (packet sizes, timing) | Low for consumer IoT | Yes |
| **JA4L** | Network latency (client-to-server) | Low | Yes |
| **JA4LS** | Network latency (server-to-client) | Low | Yes |

**Key insight:** The combination of **JA4 + JA4T + JA4D** is the most reliable fingerprinting strategy for IoT devices. Each embedded platform (ESP32/FreeRTOS, Raspberry Pi/Linux, Tuya, Shelly) has distinctive fingerprints across all three signals simultaneously.

### Multi-Signal Device Identification Accuracy

| Signal Combination | Accuracy | Notes |
|---|---|---|
| MAC OUI only | ~70-80% | Manufacturer only, not device type |
| JA3 only | ~50-60% | High collision rate, especially TLS 1.3 |
| JA4 only | ~70% | Better than JA3 but insufficient alone |
| DHCP option 55 / JA4D | ~78% | Best single signal for device class |
| mDNS/DNS-SD patterns | ~85% | `_matter._tcp`, `_hap._tcp`, `_googlecast._tcp` |
| DNS query patterns | ~85% | Domains contacted, timing, NXDOMAIN rate |
| **JA4 + JA4T + JA4D** | **92-97%** | Recommended minimum for production |
| **All signals combined** | **97%+** | Diminishing returns above 5 signals |

### Version and Compatibility (as of March 2026)

| Component | Version | Notes |
|---|---|---|
| Zeek | **8.1.1** (Jan 29, 2025 — latest stable) | Security fix for HTTP analyzer MIME header evasion |
| Docker image | `zeek/zeek:latest` or `zeek/zeek:8.1.1` | Debian 13 base (since v8.0.1), includes `zkg` |
| Spicy | **1.15.0** (Jan 2025, bundled) | Control-flow optimization enabled by default |
| zkg | Bundled | Package manager for community packages |
| af_packet | **Built into core** (since v8.1.0) | No separate plugin install needed — high-perf packet capture |
| Python | 3.10+ required | Zeek 8.x minimum requirement |

### Key v8.x Features Relevant to HomeIQ

| Feature | Version | Impact |
|---|---|---|
| **af_packet integrated into core** | v8.1.0 | No separate plugin install; native high-perf packet capture in Docker |
| **Redis protocol analyzer** | v8.0.0 | Built-in — can monitor HA Redis if used |
| **PostgreSQL protocol analyzer** | v8.0.0 | Built-in — can monitor DB traffic |
| **Log field truncation controls** | v8.1.0 | Cap string/container field lengths to control log size |
| **SSH/Kerberos SHA256 fingerprints** | v8.1.0 | Replaces MD5 — better security fingerprinting |
| **MQTT analyzer** | Native (all versions) | Full MQTT 3.1/3.1.1 support |
| **~50 protocol analyzers** | v8.1.1 | HTTP, DNS, TLS, SSH, DHCP, NTP, MQTT, Modbus, WebSocket, QUIC, LDAP, RDP, and more |

---

## Data Model

### InfluxDB Measurements

All time-series data writes to the existing `home_assistant_events` bucket (or a dedicated `network_data` bucket if retention differs).

#### Measurement: `network_connections`

Source: `conn.log` (every TCP/UDP/ICMP connection)

```yaml
Tags:
  src_ip:         # Source IP address
    cardinality: ~100 (home network devices)
  dst_ip:         # Destination IP address
    cardinality: ~1000 (cloud endpoints)
  proto:          # Transport protocol (tcp, udp, icmp)
    cardinality: 3
  service:        # Application protocol detected (http, dns, ssl, mqtt, ssh, etc.)
    cardinality: ~20
  conn_state:     # Connection state (S0, S1, SF, REJ, RSTO, etc.)
    cardinality: ~12
  direction:      # inbound, outbound, internal
    cardinality: 3

Fields:
  duration:       float   # Connection duration in seconds
  orig_bytes:     int     # Bytes sent by originator
  resp_bytes:     int     # Bytes sent by responder
  orig_pkts:      int     # Packets sent by originator
  resp_pkts:      int     # Packets sent by responder
  missed_bytes:   int     # Bytes missed (gaps in content)

Write Interval: 30 seconds (batch from parsed conn.log entries)
Retention: 7 days (Layer 1), aggregated to daily in Layer 2
```

#### Measurement: `network_dns`

Source: `dns.log` (every DNS query/response)

```yaml
Tags:
  device_ip:      # IP of the device making the query
    cardinality: ~100
  query_domain:   # Domain name queried (e.g., "api.tuya.com")
    cardinality: ~500
  query_type:     # DNS record type (A, AAAA, CNAME, MX, TXT, SRV, PTR)
    cardinality: ~10
  rcode_name:     # Response code (NOERROR, NXDOMAIN, SERVFAIL, REFUSED)
    cardinality: ~5

Fields:
  rtt:            float   # Round-trip time for query (seconds)
  answers_count:  int     # Number of answers in response
  ttl:            int     # TTL of first answer
  rejected:       bool    # Whether query was rejected

Write Interval: 30 seconds
Retention: 7 days (Layer 1)
```

#### Measurement: `network_mqtt`

Source: `mqtt_connect.log`, `mqtt_publish.log`, `mqtt_subscribe.log`

```yaml
Tags:
  client_id:      # MQTT client identifier
    cardinality: ~50
  client_ip:      # IP of MQTT client
    cardinality: ~50
  topic:          # MQTT topic (e.g., "zigbee2mqtt/living_room_light")
    cardinality: ~200
  action:         # connect, publish, subscribe, disconnect
    cardinality: 4
  qos:            # Quality of Service level (0, 1, 2)
    cardinality: 3

Fields:
  payload_size:   int     # Size of message payload in bytes
  retain:         bool    # Whether message was retained
  connect_ok:     bool    # Whether connection was accepted (connect action)
  proto_version:  string  # MQTT protocol version

Write Interval: 30 seconds
Retention: 7 days (Layer 1)
```

#### Measurement: `network_anomalies`

Source: `weird.log`, `notice.log`

```yaml
Tags:
  source_ip:      # IP associated with the anomaly
    cardinality: ~100
  anomaly_type:   # Category (protocol_violation, beaconing, new_device, cert_expired, dns_anomaly)
    cardinality: ~15
  severity:       # info, warning, critical
    cardinality: 3
  source_log:     # Which Zeek log generated this (weird, notice)
    cardinality: 2

Fields:
  name:           string  # Zeek anomaly name (e.g., "bad_TCP_checksum")
  message:        string  # Human-readable description
  peer:           string  # Destination IP/port if applicable
  suppress_for:   float   # Suppression interval (notice.log)

Write Interval: On occurrence (not batched)
Retention: 30 days
```

#### Measurement: `network_device_metrics`

Aggregated from `conn.log` — per-device summaries computed by the Python service

```yaml
Tags:
  device_ip:      # Device IP address
    cardinality: ~100
  device_mac:     # Device MAC address (from DHCP correlation)
    cardinality: ~100

Fields:
  total_bytes_sent:     int     # Total bytes sent in window
  total_bytes_recv:     int     # Total bytes received in window
  connection_count:     int     # Number of connections in window
  unique_destinations:  int     # Unique destination IPs contacted
  unique_domains:       int     # Unique DNS domains queried
  avg_conn_duration:    float   # Average connection duration
  active_services:      int     # Unique application protocols used

Write Interval: 60 seconds (aggregated)
Retention: 30 days (Layer 1), 365 days (Layer 2 daily aggregates)
```

### PostgreSQL Tables (Schema: `devices`)

#### Table: `network_device_fingerprints`

```sql
CREATE TABLE devices.network_device_fingerprints (
    id              SERIAL PRIMARY KEY,
    mac_address     VARCHAR(17) NOT NULL,           -- "AA:BB:CC:DD:EE:FF"
    ip_address      INET NOT NULL,                  -- Current IP (updated on DHCP renewal)
    hostname        VARCHAR(255),                    -- From DHCP or mDNS
    vendor          VARCHAR(255),                    -- OUI lookup from MAC

    -- DHCP Fingerprint
    dhcp_fingerprint    VARCHAR(512),               -- DHCP parameter request list hash
    dhcp_vendor_class   VARCHAR(255),               -- DHCP vendor class identifier

    -- TLS Fingerprints
    ja3_hash        VARCHAR(32),                    -- JA3 MD5 hash (most recent)
    ja3s_hash       VARCHAR(32),                    -- JA3S server hash
    ja4_hash        VARCHAR(64),                    -- JA4 fingerprint string

    -- SSH Fingerprint
    hassh_hash      VARCHAR(32),                    -- HASSH client hash
    hassh_server    VARCHAR(32),                    -- HASSH server hash

    -- Software Detection
    user_agent      TEXT,                           -- HTTP User-Agent string
    server_software TEXT,                           -- Server header
    os_guess        VARCHAR(100),                   -- Inferred OS

    -- Metadata
    first_seen      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    times_seen      INTEGER DEFAULT 1,
    is_active       BOOLEAN DEFAULT TRUE,

    -- Constraints
    UNIQUE(mac_address)
);

CREATE INDEX idx_fingerprints_ip ON devices.network_device_fingerprints(ip_address);
CREATE INDEX idx_fingerprints_ja3 ON devices.network_device_fingerprints(ja3_hash);
CREATE INDEX idx_fingerprints_ja4 ON devices.network_device_fingerprints(ja4_hash);
CREATE INDEX idx_fingerprints_vendor ON devices.network_device_fingerprints(vendor);
```

#### Table: `network_device_dns_profiles`

```sql
CREATE TABLE devices.network_device_dns_profiles (
    id              SERIAL PRIMARY KEY,
    mac_address     VARCHAR(17) NOT NULL REFERENCES devices.network_device_fingerprints(mac_address),
    domain          VARCHAR(255) NOT NULL,          -- Domain queried
    query_count     INTEGER DEFAULT 1,              -- Times queried (rolling 7 days)
    first_queried   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_queried    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    category        VARCHAR(50),                    -- cloud_api, ntp, update_check, ad_tracker, unknown

    UNIQUE(mac_address, domain)
);

CREATE INDEX idx_dns_profiles_mac ON devices.network_device_dns_profiles(mac_address);
CREATE INDEX idx_dns_profiles_domain ON devices.network_device_dns_profiles(domain);
```

#### Table: `network_tls_certificates`

```sql
CREATE TABLE devices.network_tls_certificates (
    id                  SERIAL PRIMARY KEY,
    server_ip           INET NOT NULL,
    server_name         VARCHAR(255),               -- SNI from TLS handshake
    serial_number       VARCHAR(128),               -- Certificate serial
    subject             TEXT,                        -- Certificate subject
    issuer              TEXT,                        -- Certificate issuer
    not_valid_before    TIMESTAMPTZ,
    not_valid_after     TIMESTAMPTZ,
    key_type            VARCHAR(20),                -- RSA, EC, etc.
    key_length          INTEGER,                    -- Key size in bits
    sig_algorithm       VARCHAR(50),                -- Signature algorithm
    tls_version         VARCHAR(10),                -- TLS 1.0, 1.1, 1.2, 1.3
    cipher_suite        VARCHAR(100),               -- Negotiated cipher
    is_self_signed      BOOLEAN DEFAULT FALSE,
    first_seen          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(server_ip, serial_number)
);

CREATE INDEX idx_certs_expiry ON devices.network_tls_certificates(not_valid_after);
CREATE INDEX idx_certs_server ON devices.network_tls_certificates(server_name);
```

#### Table: `network_baseline_hosts`

```sql
CREATE TABLE devices.network_baseline_hosts (
    id              SERIAL PRIMARY KEY,
    ip_address      INET NOT NULL UNIQUE,
    mac_address     VARCHAR(17),
    hostname        VARCHAR(255),
    first_seen      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_baseline     BOOLEAN DEFAULT FALSE,          -- TRUE = known/approved device
    approved_by     VARCHAR(100),                   -- "auto" or admin username
    approved_at     TIMESTAMPTZ,
    services        JSONB DEFAULT '[]',             -- [{port, protocol, service_name}]
    notes           TEXT
);
```

---

## Phased Requirements

### Phase 1: Core Network Ingestion (MVP) — COMPLETE (Sprint 30)

**Goal:** Deploy Zeek, parse `conn.log` and `dns.log`, write to InfluxDB, expose REST API.
**Stories:** 7 (Epic 72) — all complete
**Dependencies:** None (new service)

#### Requirements

| ID | Requirement | Priority |
|---|---|---|
| P1.1 | Zeek Docker image (`Dockerfile.zeek`) with entrypoint script for `ZEEK_INTERFACE` env var expansion | Must |
| P1.2 | Zeek `local.zeek` + `homeiq.zeek` configuration: JSON output, log rotation (5 min), MQTT enabled | Must |
| P1.3 | Compose integration: `--net=host`, `NET_RAW`/`NET_ADMIN` caps, BPF filter excluding `homeiq-network` bridge. Note: Zeek container health monitored indirectly via log freshness (not reachable by service name due to host network mode) | Must |
| P1.4 | Shared Docker volume (`zeek-logs`) mounted read-write in Zeek, read-only in sidecar | Must |
| P1.5 | Python `zeek-network-service` using `BaseServiceSettings`, `ServiceLifespan`, `StandardHealthCheck` | Must |
| P1.6 | Dockerfile following multi-stage Alpine pattern, all 6 homeiq libs installed (including `homeiq-memory`) | Must |
| P1.7 | Initialize Alembic environment (empty migration head — first migration in Phase 2) | Must |
| P1.8 | Background polling loop (30s) parsing `conn.log` JSON → `network_connections` InfluxDB measurement | Must |
| P1.9 | Background polling loop parsing `dns.log` JSON → `network_dns` InfluxDB measurement | Must |
| P1.10 | Log file position tracking via JSON state file (`/app/state/offsets.json`) on persistent volume. Handles Zeek's 5-min log rotation (detect renamed file via inode or file-size reset) | Must |
| P1.11 | In-memory buffer (5 min max) when InfluxDB is unavailable, flush on recovery | Must |
| P1.12 | Per-device aggregation computing `network_device_metrics` measurement (60s window) | Must |
| P1.13 | Health endpoint reporting: Zeek process status, log freshness (seconds since last log line), InfluxDB write counts | Must |
| P1.14 | REST API: `GET /health`, `GET /current-stats`, `GET /devices` | Must |
| P1.15 | Port 8048 assignment in `domains/data-collectors/compose.yml` | Must |

#### Acceptance Criteria

```gherkin
Feature: Core network ingestion
  Scenario: Zeek captures and service parses connection data
    Given the zeek container is running with --net=host
    And the zeek-network-service container is running
    When a device on the network makes an HTTP connection
    Then a conn.log JSON entry is written to the shared volume
    And the service parses it within 30 seconds
    And a network_connections point is written to InfluxDB
    And GET /devices returns the device IP in the response

  Scenario: Health endpoint reflects system status
    Given both containers are running
    When GET /health is called
    Then status is "healthy"
    And zeek_process_running is true
    And log_freshness_seconds is less than 60
    And influxdb_writes_total is greater than 0

  Scenario: BPF filter excludes Docker traffic
    Given Zeek is running with the BPF filter
    When inter-container traffic flows on homeiq-network (172.18.0.0/16)
    Then no conn.log entries are generated for that traffic

  Scenario: Service recovers from restart
    Given the service has been processing logs
    When the zeek-network-service container is restarted
    Then it resumes from the last known log file position
    And no duplicate entries are written to InfluxDB
```

---

### Phase 2: Device Fingerprinting — COMPLETE (Sprint 31)

**Goal:** Auto-discover devices via DHCP, fingerprint via JA3/JA4/HASSH, feed device-intelligence-service.
**Stories:** 6 (Epic 73) — all complete
**Dependencies:** Phase 1 complete

#### Requirements

| ID | Requirement | Priority |
|---|---|---|
| P2.1 | Custom Zeek Docker image (FROM `zeek/zeek`) with `zkg install` for ja3, ja4, hassh, KYD packages | Must |
| P2.2 | Parse `dhcp.log` + `dhcpfp.log` → `network_device_fingerprints` PostgreSQL table (MAC, IP, hostname, vendor, DHCP fingerprint) | Must |
| P2.3 | Parse `ssl.log` + `ja3.log` + `ja4.log` → update `network_device_fingerprints` with TLS fingerprints | Must |
| P2.4 | Parse `hassh.log` → update `network_device_fingerprints` with SSH fingerprints | Should |
| P2.5 | Parse `software.log` → update `network_device_fingerprints` with user-agent and server software | Should |
| P2.6 | MAC address OUI vendor lookup (IEEE OUI database, bundled or API) | Must |
| P2.7 | Device deduplication across DHCP renewals (MAC is primary key, IP updates on renewal) | Must |
| P2.8 | REST API: `GET /devices/{ip}/fingerprint`, `GET /devices/discovered`, `GET /devices/new` (since last baseline) | Must |
| P2.9 | Feed `device-intelligence-service` via data-api with fingerprint data (JA3/JA4 → device type mapping) | Should |
| P2.10 | Feed `device-database-client` with auto-discovered MAC/vendor/hostname for device registry enrichment | Should |
| P2.11 | Alembic migration for `network_device_fingerprints` table in `devices` schema | Must |

#### Acceptance Criteria

```gherkin
Feature: Device fingerprinting
  Scenario: New device discovered via DHCP
    Given Zeek is monitoring the network
    When a new device sends a DHCP request
    Then a record is created in network_device_fingerprints
    And mac_address, ip_address, hostname, and vendor are populated
    And GET /devices/discovered includes the device

  Scenario: TLS fingerprint captured
    Given a device has been discovered via DHCP
    When the device makes a TLS connection
    Then ja3_hash and ja4_hash are updated in network_device_fingerprints
    And the fingerprint is available via GET /devices/{ip}/fingerprint

  Scenario: DHCP renewal updates IP
    Given a device exists in network_device_fingerprints with IP 192.168.1.50
    When the device renews its DHCP lease and gets IP 192.168.1.75
    Then the ip_address is updated to 192.168.1.75
    And mac_address remains unchanged
    And times_seen is incremented
    And last_seen is updated
```

#### Implementation Notes (Sprint 31)

- **Zeek packages** already installed in `Dockerfile.zeek` from Phase 1 (ja3, ja4, hassh, KYD, zeek-flowmeter)
- **DHCP parser** (`dhcp_parser.py`) — parses `dhcp.log` + `dhcpfp.log`, upserts via `FingerprintService`
- **TLS parser** (`tls_parser.py`) — parses `ja3.log`, `ja4.log`, `ssl.log` (with embedded JA3/JA4 fallback)
- **SSH/software parser** (`ssh_parser.py`) — parses `hassh.log` + `software.log`, maps software_type to correct DB field
- **OUI lookup** (`oui_lookup.py`) — curated dictionary of ~200 IoT/networking vendor OUI prefixes
- **Fingerprint service** (`fingerprint_service.py`) — asyncpg with upsert (ON CONFLICT MAC), COALESCE for partial updates
- **Alembic migration 001** — `devices.network_device_fingerprints` table with 4 indexes
- **REST API** — 3 new endpoints: `GET /devices/{ip}/fingerprint`, `GET /devices/discovered`, `GET /devices/new`
- **Tests** — 32 new tests (57 total), all passing
- **Bug fix** — `version_minor=0` was falsy in ssh_parser, fixed with explicit None check

---

### Phase 3: MQTT & Protocol Intelligence

**Goal:** Monitor HA MQTT backbone, track TLS certificates, build DNS behavior profiles.
**Estimated stories:** 5-6
**Dependencies:** Phase 1 complete (Phase 2 recommended)

#### Requirements

| ID | Requirement | Priority |
|---|---|---|
| P3.1 | Enable Zeek MQTT analyzer in `local.zeek` configuration | Must |
| P3.2 | Parse `mqtt_connect.log`, `mqtt_publish.log`, `mqtt_subscribe.log` → `network_mqtt` InfluxDB measurement | Must |
| P3.3 | Parse `x509.log` + `ssl.log` → `network_tls_certificates` PostgreSQL table | Must |
| P3.4 | Build `network_device_dns_profiles` from `dns.log` — per-device domain query frequency with category classification | Must |
| P3.5 | REST API: `GET /mqtt/topics`, `GET /mqtt/clients`, `GET /tls/certificates`, `GET /dns/profiles/{ip}` | Must |
| P3.6 | Alert generation: rogue MQTT clients (client_id not in known list), expired certificates, TLS < 1.2 | Should |
| P3.7 | Feed `automation-trace-service` with MQTT message metadata for end-to-end automation tracing | Should |
| P3.8 | DNS domain categorization (cloud_api, ntp, update_check, ad_tracker, social_media, unknown) using domain suffix matching | Should |
| P3.9 | Alembic migrations for `network_device_dns_profiles` and `network_tls_certificates` tables | Must |

#### Acceptance Criteria

```gherkin
Feature: MQTT monitoring
  Scenario: MQTT publish captured
    Given Zeek is monitoring the network with MQTT analyzer enabled
    When Zigbee2MQTT publishes a message to "zigbee2mqtt/living_room_light"
    Then a network_mqtt point is written to InfluxDB
    And topic is "zigbee2mqtt/living_room_light"
    And client_id matches the Zigbee2MQTT client

  Scenario: Expired certificate detected
    Given a device presents a TLS certificate
    When the certificate's not_valid_after is in the past
    Then an alert is generated in network_anomalies measurement
    And anomaly_type is "cert_expired"
    And severity is "warning"
```

---

### Phase 4: Anomaly Detection & Security Baseline

**Goal:** Establish network baseline, detect anomalies, feed proactive-agent-service.
**Estimated stories:** 6-8
**Dependencies:** Phase 1 + Phase 2 complete

#### Requirements

| ID | Requirement | Priority |
|---|---|---|
| P4.1 | Parse `weird.log` → `network_anomalies` InfluxDB measurement (protocol violations) | Must |
| P4.2 | Parse `notice.log` → `network_anomalies` InfluxDB measurement (Zeek-generated alerts) | Must |
| P4.3 | Network baseline from `known_hosts.log`, `known_services.log` → `network_baseline_hosts` PostgreSQL table | Must |
| P4.4 | New device detection: alert when a device appears that is not in the baseline | Must |
| P4.5 | Beaconing detection: identify connections with regular intervals to external IPs (C2 indicator) | Should |
| P4.6 | DNS anomaly detection: DGA domain patterns (high entropy domain names), DNS tunneling (large TXT records) | Should |
| P4.7 | Install `zeek-flowmeter` package for ML-ready traffic features → feed `ml-service` | Should |
| P4.8 | Feed `proactive-agent-service` with security events via data-api or direct HTTP | Must |
| P4.9 | Feed `ai-pattern-service` with network behavioral patterns for automation enrichment | Should |
| P4.10 | REST API: `GET /anomalies`, `GET /baseline/devices`, `GET /security/alerts`, `POST /baseline/approve/{ip}` | Must |
| P4.11 | Configurable alert thresholds via environment variables | Should |
| P4.12 | Alembic migration for `network_baseline_hosts` table | Must |

#### Acceptance Criteria

```gherkin
Feature: Anomaly detection
  Scenario: New device detected
    Given the network baseline has been established
    When a previously unseen MAC address appears on the network
    Then a network_anomalies point is written with anomaly_type "new_device"
    And severity is "warning"
    And the device appears in GET /baseline/devices with is_baseline=false

  Scenario: Beaconing detected
    Given a device makes connections to the same external IP
    When the connections occur at regular intervals (e.g., every 60s ± 5s)
    And this pattern persists for more than 1 hour
    Then a network_anomalies point is written with anomaly_type "beaconing"
    And severity is "critical"

  Scenario: Baseline approval
    Given a new device has been detected
    When POST /baseline/approve/{ip} is called
    Then the device's is_baseline is set to true
    And no further new_device alerts are generated for this device
```

---

## API Specification

### Port: 8048

### Endpoints

| Method | Path | Phase | Description |
|---|---|---|---|
| `GET` | `/` | P1 | Service info and endpoint list |
| `GET` | `/health` | P1 | Health status (zeek process, log freshness, write counts) |
| `GET` | `/metrics` | P1 | Operational metrics (connections parsed, bytes processed, errors) |
| `GET` | `/current-stats` | P1 | Current network statistics (connections/min, bytes/min, top talkers) |
| `GET` | `/devices` | P1 | All discovered devices with latest metrics |
| `GET` | `/devices/{ip}` | P1 | Device detail (connections, DNS, bandwidth) |
| `GET` | `/devices/{ip}/fingerprint` | P2 | Device fingerprint data (JA3, JA4, DHCP, HASSH) |
| `GET` | `/devices/discovered` | P2 | Recently discovered devices (last 24h) |
| `GET` | `/devices/new` | P2 | Devices not yet in baseline |
| `GET` | `/mqtt/topics` | P3 | Active MQTT topics with message counts |
| `GET` | `/mqtt/clients` | P3 | Connected MQTT clients |
| `GET` | `/tls/certificates` | P3 | Tracked TLS certificates with expiry status |
| `GET` | `/dns/profiles/{ip}` | P3 | DNS query profile for a device |
| `GET` | `/anomalies` | P4 | Recent anomaly events (filterable by type, severity) |
| `GET` | `/baseline/devices` | P4 | Network baseline device list |
| `POST` | `/baseline/approve/{ip}` | P4 | Approve a device into the baseline |
| `GET` | `/security/alerts` | P4 | Active security alerts |
| `GET` | `/cache/stats` | P1 | Cache performance statistics |

### Response Format

Follows HomeIQ convention — direct Pydantic model or dict, no JSON wrapper:

```json
// GET /devices
[
  {
    "ip": "192.168.1.42",
    "mac": "AA:BB:CC:DD:EE:FF",
    "hostname": "shelly-plug-livingroom",
    "vendor": "Shelly (Allterco Robotics)",
    "last_seen": "2026-03-16T14:30:00Z",
    "connections_1h": 47,
    "bytes_sent_1h": 125400,
    "bytes_recv_1h": 89200,
    "top_destinations": ["api.shelly.cloud", "time.google.com"],
    "fingerprints": {
      "ja3": "e7d705a3286e19ea42f587b344ee6865",
      "ja4": "t13d1516h2_8daaf6152771_02713d6af862"
    }
  }
]
```

---

## Integration Map

### Downstream Consumers (services that receive data from zeek-network-service)

```
zeek-network-service (:8048)
    │
    ├──▶ InfluxDB (:8086)                    [Direct write — time-series metrics]
    │     └── network_connections, network_dns, network_mqtt,
    │         network_anomalies, network_device_metrics
    │
    ├──▶ PostgreSQL (devices schema)         [Direct write — device metadata]
    │     └── network_device_fingerprints, network_device_dns_profiles,
    │         network_tls_certificates, network_baseline_hosts
    │
    ├──▶ device-intelligence-service (:8028) [Via data-api — fingerprint enrichment]
    │     └── JA3/JA4 hashes → device type classification
    │
    ├──▶ device-database-client (:8022)      [Via data-api — device registry]
    │     └── Auto-discovered MAC/vendor/hostname
    │
    ├──▶ energy-correlator (:8017)           [Via InfluxDB — reads network_device_metrics]
    │     └── Per-device bandwidth correlated with power consumption
    │
    ├──▶ proactive-agent-service (:8031)     [Via data-api — security events]
    │     └── Anomalies, new devices, beaconing alerts
    │
    ├──▶ ai-pattern-service (:8034)          [Via data-api — behavioral patterns]
    │     └── DNS profiles, connection patterns, device communication graphs
    │
    ├──▶ automation-trace-service (:8044)    [Via data-api — MQTT traces]
    │     └── MQTT publish/subscribe events for automation tracing
    │
    ├──▶ activity-recognition (:8043)        [Via InfluxDB — presence signals]
    │     └── Network activity patterns as presence indicators
    │
    └──▶ health-dashboard (:3000)            [Via data-api — dashboard data]
          └── Network overview tab, device list, security alerts
```

### Upstream Dependencies (services that zeek-network-service depends on)

| Service | Purpose | Circuit Breaker |
|---|---|---|
| InfluxDB (:8086) | Time-series data writes | `core-platform` |
| data-api (:8006) | Device metadata queries, cross-service data routing | `core-platform` |
| PostgreSQL | Direct metadata writes (fingerprints, baselines) | `core-platform` |

### Degradation Behavior

| Upstream Down | Behavior |
|---|---|
| InfluxDB unavailable | Buffer metrics in memory (5 min max), log warning, continue parsing |
| PostgreSQL unavailable | Skip fingerprint/baseline writes, cache in memory, retry on recovery |
| data-api unavailable | Skip cross-service enrichment feeds, service remains healthy |
| Zeek container stopped | Health → "degraded", log_freshness increases, no new data |

---

## Docker & Infrastructure

### Compose Configuration

Added to `domains/data-collectors/compose.yml`:

```yaml
  # Zeek network monitor — packet capture
  zeek:
    image: homeiq/zeek:latest  # Custom image with packages pre-installed
    build:
      context: ../..
      dockerfile: domains/data-collectors/zeek-network-service/Dockerfile.zeek
    network_mode: host  # Required for physical NIC access
    cap_add:
      - NET_RAW           # Required for packet capture
      - NET_ADMIN         # Required for interface configuration
    volumes:
      - zeek-logs:/zeek/logs
    environment:
      - ZEEK_INTERFACE=${ZEEK_INTERFACE:-eth0}
      - ZEEK_BPF_FILTER=not net 172.18.0.0/16  # Exclude homeiq-network bridge
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 4096M
        reservations:
          cpus: "1.0"
          memory: 2048M
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
        labels: "service"
    labels:
      - "service=zeek"

  # Zeek network service — log parser and data router
  zeek-network-service:
    build:
      context: ../..
      dockerfile: domains/data-collectors/zeek-network-service/Dockerfile
    ports:
      - "8048:8048"
    volumes:
      - zeek-logs:/zeek/logs:ro  # Read-only access to Zeek logs
      - zeek-state:/app/state    # Persistent seek offset state
    environment:
      - SERVICE_NAME=zeek-network-service
      - SERVICE_PORT=8048
      - INFLUXDB_URL=${INFLUXDB_URL:-http://influxdb:8086}
      - INFLUXDB_TOKEN=${INFLUXDB_TOKEN}
      - INFLUXDB_ORG=${INFLUXDB_ORG:-home_assistant}
      - INFLUXDB_BUCKET=${INFLUXDB_BUCKET:-home_assistant_events}
      - DATABASE_URL=${DATABASE_URL}
      - DATABASE_SCHEMA=devices
      - DATA_API_URL=${DATA_API_URL:-http://data-api:8006}
      - DATA_API_KEY=${DATA_API_KEY}
      - ZEEK_LOG_DIR=/zeek/logs
      - POLL_INTERVAL_SECONDS=30
      - DEVICE_METRICS_INTERVAL_SECONDS=60
    env_file:
      - ../../.env
    networks:
      - homeiq-network
    depends_on:
      zeek:
        condition: service_started
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 384M
        reservations:
          cpus: "0.25"
          memory: 192M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8048/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
        labels: "service"
    labels:
      - "service=zeek-network-service"

volumes:
  zeek-logs:
    driver: local
  zeek-state:
    driver: local
```

### Dockerfile (Python Sidecar)

```dockerfile
# Stage 1: Builder
FROM python:3.12-alpine AS builder

RUN apk add --no-cache gcc musl-dev libffi-dev

WORKDIR /app

# Install shared libs
COPY libs/ /tmp/libs/
RUN pip install --no-cache-dir --user \
    /tmp/libs/homeiq-patterns/ \
    /tmp/libs/homeiq-resilience/ \
    /tmp/libs/homeiq-observability/ \
    /tmp/libs/homeiq-data/ \
    /tmp/libs/homeiq-ha/ \
    /tmp/libs/homeiq-memory/

COPY domains/data-collectors/zeek-network-service/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Production
FROM python:3.12-alpine

RUN adduser -D -u 1001 appuser
WORKDIR /app

# Persistent state directory for log seek offsets
RUN mkdir -p /app/state && chown appuser:root /app/state

COPY --from=builder /root/.local /home/appuser/.local
COPY domains/data-collectors/zeek-network-service/src/ ./src/

ENV PATH="/home/appuser/.local/bin:$PATH"
ENV PYTHONPATH="/app"

USER 1001
EXPOSE 8048

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8048"]
```

### Dockerfile.zeek (Custom Zeek Image)

```dockerfile
FROM zeek/zeek:8.1.1

# af_packet is now built into core (v8.1.0+) — no separate install needed
# Install community packages for device fingerprinting and ML features
RUN zkg autoconfig && \
    zkg install --force \
        zeek/ja3 \
        foxio-n/ja4 \
        salesforce/hassh \
        corelight/KYD \
        SuperCowPowers/zeek-flowmeter

# Copy custom Zeek configuration
COPY domains/data-collectors/zeek-network-service/zeek-config/local.zeek /usr/local/zeek/share/zeek/site/local.zeek
COPY domains/data-collectors/zeek-network-service/zeek-config/homeiq.zeek /usr/local/zeek/share/zeek/site/homeiq.zeek

# Log output directory
RUN mkdir -p /zeek/logs && chown -R zeek:zeek /zeek

USER zeek
WORKDIR /zeek

# Entrypoint script handles ZEEK_INTERFACE env var expansion
# (exec form CMD cannot expand shell variables)
COPY domains/data-collectors/zeek-network-service/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
```

**docker-entrypoint.sh:**
```bash
#!/bin/bash
set -e
# Use af_packet for high-performance capture (built into core since v8.1.0)
# Falls back to libpcap if af_packet unavailable (e.g., non-Linux hosts)
exec zeek -i "af_packet::${ZEEK_INTERFACE:-eth0}" local
```

### Resource Budget

| Container | CPU Limit | CPU Reserve | Memory Limit | Memory Reserve |
|---|---|---|---|---|
| zeek | 2.0 cores | 1.0 core | 4096 MB | 2048 MB |
| zeek-network-service | 0.5 cores | 0.25 cores | 384 MB | 192 MB |
| **Total** | **2.5 cores** | **1.25 cores** | **4480 MB** | **2240 MB** |

For context, existing data collectors use 0.5/0.25 CPU and 384/192 MB each. The Zeek container is the heavier component due to packet processing. On a home network (<100 Mbps), actual usage will be well below limits.

---

## Zeek Configuration

### local.zeek (Primary Configuration)

```zeek
# HomeIQ Zeek Configuration
# JSON output for all logs
redef LogAscii::use_json = T;

# Log rotation: 5 minutes (matches polling interval)
redef Log::default_rotation_interval = 5 min;

# Log directory
redef Log::default_logdir = "/zeek/logs";

# Enable MQTT analyzer
@load protocols/mqtt

# Load community packages
@load packages

# Load HomeIQ custom scripts
@load homeiq.zeek

# Reduce noise: disable rarely-needed logs for home networks
redef Log::disable_rotation_ifaces = set("reporter");
```

### homeiq.zeek (Custom HomeIQ Scripts)

```zeek
# HomeIQ-specific Zeek scripts

module HomeIQ;

# Track local network (configurable)
redef Site::local_nets += { 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12 };

# Increase connection tracking for long-lived IoT connections
redef tcp_inactivity_timeout = 30 min;
redef udp_inactivity_timeout = 10 min;

# Lower thresholds for scan detection (home networks are small)
redef Scan::addr_scan_threshold = 10;
redef Scan::port_scan_threshold = 15;

# Enable notices for new connections to external IPs
# (useful for detecting devices phoning home)
redef Notice::policy += {
    [$action = Notice::ACTION_LOG,
     $pred(n: Notice::Info) = { return n$note == Weird::Activity; }]
};
```

---

## Security Considerations

### Network Access

- Zeek container runs with `--net=host` and `NET_RAW`/`NET_ADMIN` capabilities — **required for packet capture** but increases attack surface
- Mitigation: Zeek container runs as non-root `zeek` user, read-only filesystem except `/zeek/logs`
- The Python sidecar does NOT require elevated capabilities — normal container networking

### Data Sensitivity

- `conn.log` contains IP addresses of all devices and their communication partners — **PII-adjacent data**
- MQTT payloads may contain sensor readings, device states — **potentially sensitive**
- DNS queries reveal browsing behavior — **privacy-sensitive**
- Mitigation: All data stays within the HomeIQ Docker host, no external transmission
- Mitigation: InfluxDB retention policies limit data lifetime (7-30 days)

### BPF Filter

- The BPF filter `not net 172.18.0.0/16` excludes Docker bridge traffic
- **Critical:** If the Docker bridge subnet changes, the BPF filter must be updated
- Mitigation: Make BPF filter configurable via `ZEEK_BPF_FILTER` environment variable

### Secrets

- No external API keys required (Zeek is passive)
- InfluxDB token and data-api key follow existing `SecretStr` pattern
- PostgreSQL connection string handled via `DATABASE_URL` environment variable

---

## Non-Goals

| Item | Reason |
|---|---|
| **Replacing IDS/IPS** | Zeek is passive monitoring; it does not block or modify traffic |
| **Docker inter-container traffic monitoring** | Excluded by BPF filter; internal HomeIQ traffic is not useful IoT data |
| **Kafka or message queue infrastructure** | No existing Kafka in HomeIQ; file-based log transfer matches the data-collector pattern |
| **Active network scanning** | Zeek is passive only; active scanning would conflict with home network devices |
| **PCAP retention** | Storing raw packet captures requires significant storage; metadata logs are sufficient |
| **Sub-second alerting** | 30s polling interval is consistent with existing collectors; real-time alerting is out of scope |
| **Custom Spicy parsers for Matter/Thread/Zigbee** | These protocols have limited IP visibility; defer to a future epic if needed |
| **External SIEM integration** | HomeIQ is the SIEM; forwarding to Splunk/Elastic is not in scope |
| **VPN/encrypted tunnel deep inspection** | Cannot inspect encrypted payloads; metadata analysis only |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `--net=host` breaks Docker network isolation for Zeek container | Low | Medium | Zeek runs as non-root, read-only FS, no outbound connections |
| Zeek resource usage exceeds budget on busy networks | Low | Medium | BPF filter reduces traffic, resource limits in compose, monitoring via `/metrics` |
| High-cardinality InfluxDB tags (dst_ip) cause performance issues | Medium | Medium | Limit dst_ip cardinality with top-N aggregation, use fields for high-cardinality data |
| Log file rotation race condition (Zeek rotates while sidecar reads) | Medium | Low | Use inotify/file position tracking, handle truncated reads gracefully |
| Docker bridge subnet changes break BPF filter | Low | High | Configurable BPF filter via env var, health check detects zero-traffic condition |
| Zeek package compatibility issues across versions | Low | Medium | Pin Zeek version in Dockerfile, test package installation in CI |
| MQTT payload capture may include sensitive data | Medium | Medium | Log metadata only (topic, size, QoS), not payload content |
| PostgreSQL devices schema migration conflicts with existing tables | Low | Medium | Use unique table names with `network_` prefix, standard Alembic migration |

---

## Appendix: Zeek Log Reference

### Logs Consumed by Phase

| Log File | Phase | InfluxDB Measurement | PostgreSQL Table | Description |
|---|---|---|---|---|
| `conn.log` | P1 | `network_connections`, `network_device_metrics` | — | Connection summaries (IP, port, bytes, duration) |
| `dns.log` | P1 | `network_dns` | P3: `network_device_dns_profiles` | DNS queries and responses |
| `dhcp.log` | P2 | — | `network_device_fingerprints` | DHCP assignments (MAC, IP, hostname) |
| `dhcpfp.log` | P2 | — | `network_device_fingerprints` | DHCP client fingerprints (KYD) |
| `ssl.log` | P2/P3 | — | `network_device_fingerprints`, `network_tls_certificates` | TLS handshake details |
| `ja3.log` | P2 | — | `network_device_fingerprints` | JA3 TLS client fingerprints |
| `ja4.log` | P2 | — | `network_device_fingerprints` | JA4 multi-protocol fingerprints |
| `hassh.log` | P2 | — | `network_device_fingerprints` | SSH client/server fingerprints |
| `software.log` | P2 | — | `network_device_fingerprints` | Detected software versions |
| `mqtt_connect.log` | P3 | `network_mqtt` | — | MQTT client connections |
| `mqtt_publish.log` | P3 | `network_mqtt` | — | MQTT publish messages |
| `mqtt_subscribe.log` | P3 | `network_mqtt` | — | MQTT subscribe requests |
| `x509.log` | P3 | — | `network_tls_certificates` | X.509 certificate details |
| `weird.log` | P4 | `network_anomalies` | — | Protocol anomalies |
| `notice.log` | P4 | `network_anomalies` | — | Zeek-generated alerts |
| `known_hosts.log` | P4 | — | `network_baseline_hosts` | Known network hosts |
| `known_services.log` | P4 | — | `network_baseline_hosts` (services JSONB) | Known services per host |
| `flowmeter.log` | P4 | — | — (feed to ml-service) | ML-ready traffic features |

### Logs Not Consumed (Available for Future Use)

| Log File | Potential Use |
|---|---|
| `http.log` | HTTP request/response analysis (URLs, user-agents, status codes) |
| `ssh.log` | SSH authentication tracking |
| `ntp.log` | NTP server usage per device |
| `sip.log` | VoIP detection (if applicable) |
| `modbus.log` | ICS/SCADA device monitoring (smart meters with Modbus TCP) |
| `radius.log` | RADIUS authentication (enterprise WiFi) |
| `tunnel.log` | VPN/tunnel detection |
| `traceroute.log` | Network path discovery |
| `capture_loss.log` | Zeek performance diagnostics |
| `stats.log` | Zeek resource usage metrics |

---

## 2026 Landscape & Greenfield Opportunity

### No Existing Zeek + Home Assistant Integration

As of March 2026, **no integration exists** between Zeek and Home Assistant — no HA add-on, no HACS component, no community project. This makes `zeek-network-service` a **greenfield opportunity** with no prior art to follow or conflict with.

### Home Assistant Native Network Capabilities (Limited)

| HA Integration | Method | Limitation vs Zeek |
|---|---|---|
| `nmap_tracker` | Active scanning | Disruptive; no traffic analysis |
| DHCP Discovery | Passive DHCP | New device alerts only; no fingerprinting |
| Router integrations (UniFi, Fritz!Box) | Router API polling | Router-specific; no protocol-level detail |
| Pi-hole (HACS) | DNS query logging | DNS only; no connection/TLS/MQTT analysis |
| Ping | ICMP | Binary presence only |

Zeek provides **10-100x the network visibility** of any existing HA integration.

### Comparable Products (and Why Zeek is Better for HomeIQ)

| Product | Strength | Why Zeek is Better for HomeIQ |
|---|---|---|
| **ntopng v6.6** (Nov 2025) | Web UI, NetFlow/IPFIX | No programmable analysis, no MQTT, no fingerprinting ecosystem |
| **Fing / FingBox** | Large device fingerprint DB | Closed-source, commercial, no InfluxDB integration |
| **Pi-hole** | DNS-level blocking + logging | DNS only; complementary, not a replacement |
| **RITA v5.1.1** (Jan 2026) | Threat analytics on Zeek logs | Analytics layer, not a data collector — could be Phase 5 |
| **Suricata** | Signature-based IDS | Alert-focused, not metadata-focused; less IoT fingerprinting |

### No Direct Zeek → InfluxDB Writer

No maintained Zeek log writer plugin for InfluxDB exists. Our approach (Python sidecar parsing JSON logs) is the correct pattern for HomeIQ because:
1. It follows the existing data-collector architecture
2. It allows enrichment logic (device deduplication, DNS categorization, anomaly detection) before writing
3. It avoids adding Telegraf, Vector, or Kafka as new infrastructure dependencies
4. The Python service can simultaneously write to both InfluxDB (time-series) and PostgreSQL (metadata)

**Alternative considered:** Telegraf `tail` input → InfluxDB output (zero custom code). Rejected because it cannot write to PostgreSQL or perform cross-log correlation (e.g., linking `conn.log` IPs to `dhcp.log` MACs).

### Matter/Thread Protocol Visibility

- **Matter** runs over IP (Wi-Fi or Thread) with CASE session establishment
- **Thread** uses IPv6 over 802.15.4 — not directly visible on Ethernet
- **Primary passive surface:** mDNS commissioning announcements (`_matter._tcp.local`) visible in `dns.log`
- **Thread border router** IPv6 traffic is observable at the IP level
- **No Zeek analyzer exists** for Matter application layer — defer custom Spicy parser to future epic

---

## Related Documents

- [Service Groups Architecture](service-groups.md) — Domain group structure and communication rules
- [InfluxDB Schema Documentation](influxdb-schema.md) — Existing measurement schemas and retention policies
- [Database Schema](database-schema.md) — PostgreSQL schema-per-domain design
- [Event Flow Architecture](event-flow-architecture.md) — Data flow with group boundary annotations
- [AI Agent Classification](ai-agent-classification.md) — Service tier labels (this service = T4 Non-AI)

---

**Document History:**

| Date | Author | Change |
|---|---|---|
| 2026-03-16 | HomeIQ Engineering | Initial draft — combined PRD + Architecture |

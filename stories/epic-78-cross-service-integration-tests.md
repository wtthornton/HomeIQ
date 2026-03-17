# Epic 78: Cross-Service Integration Tests

**Status:** Complete
**Sprint:** 34
**Priority:** High
**Stories:** 6 (23 tests across 4 new test files + 3 tests added to existing file)

## Overview

Expands the cross-group integration test suite from 15 tests (3 files) to 41 tests (7 files), covering Tier 1 data flow, Zeek pipeline, agent chains, Memory Brain, and cross-group auth validation. All tests use `pytest.mark.integration` and mock external services while exercising real client/library code paths.

## Stories

### Story 78.1: Tier 1 Data Flow Chain Tests
**File:** `tests/integration/cross_group/test_tier1_data_flow.py`
**Tests:** 5

| # | Test | Description |
|---|------|-------------|
| 1 | `test_influxdb_manager_write_and_query` | Write a point via InfluxDBManager, query it back |
| 2 | `test_data_api_client_entity_fetch_schema` | StandardDataAPIClient returns correct entity schema |
| 3 | `test_data_api_bearer_auth_required` | Requests without auth token have no Authorization header |
| 4 | `test_influxdb_write_retry_on_transient_failure` | InfluxDBManager retries on transient write errors |
| 5 | `test_data_flow_event_to_query_roundtrip` | End-to-end event write -> query result validation |

### Story 78.2: Zeek Pipeline Integration Tests
**File:** `tests/integration/cross_group/test_zeek_pipeline.py`
**Tests:** 5

| # | Test | Description |
|---|------|-------------|
| 1 | `test_conn_log_parser_produces_influxdb_points` | Parse conn.log line, verify Point schema |
| 2 | `test_dns_log_parser_produces_influxdb_points` | Parse dns.log line, verify Point schema |
| 3 | `test_fingerprint_service_stores_to_pg_schema` | NetworkDeviceFingerprint model matches PG schema |
| 4 | `test_anomaly_detection_alert_lifecycle` | Anomaly -> alert generated -> queryable via API |
| 5 | `test_zeek_health_endpoint_schema` | Health response matches expected format |

### Story 78.3: Agent Chain Integration Tests
**File:** `tests/integration/cross_group/test_agent_chains.py`
**Tests:** 5

| # | Test | Description |
|---|------|-------------|
| 1 | `test_cross_group_client_retry_on_connection_error` | CrossGroupClient retries on ConnectError |
| 2 | `test_cross_group_client_circuit_breaker_opens_on_failures` | CircuitBreaker opens after threshold |
| 3 | `test_proactive_agent_confidence_scoring_contract` | ActionScore model schema validation |
| 4 | `test_agent_chain_auth_token_propagation` | Bearer tokens propagate across calls |
| 5 | `test_safety_guardrails_block_restricted_domains` | lock/alarm/camera always blocked |

### Story 78.4: Memory Brain Integration Tests
**File:** `tests/integration/cross_group/test_memory_brain.py`
**Tests:** 6

| # | Test | Description |
|---|------|-------------|
| 1 | `test_memory_brain_save_and_search` | Save memory, verify search returns it |
| 2 | `test_memory_brain_semantic_search_relevance` | Relevant results rank higher |
| 3 | `test_memory_brain_decay_tier_assignment` | HALF_LIVES mapping and decay calculation |
| 4 | `test_memory_brain_consolidation_merges_related` | Cosine similarity and reinforce logic |
| 5 | `test_memory_brain_domain_scoping` | Domain classification and scoping |
| 6 | `test_memory_brain_should_archive_logic` | Archive threshold evaluation |

### Story 78.5: Cross-Group Auth Validation Tests
**File:** `tests/integration/cross_group/test_cross_domain_api.py` (added to existing)
**Tests:** 3

| # | Test | Description |
|---|------|-------------|
| 1 | `test_service_auth_validator_rejects_invalid_token` | Invalid tokens get 401 |
| 2 | `test_service_auth_validator_accepts_valid_token` | Valid tokens pass |
| 3 | `test_cross_group_client_injects_auth_header` | Auth header set correctly |

### Story 78.6: Update conftest.py and CI
**Files:** `tests/integration/cross_group/conftest.py`, `.github/workflows/integration-tests.yml`

- Added sys.path setup for all 6 shared libraries and 2 domain service source directories
- Added fixtures: `zeek_service_url`, `influxdb_url`, `ha_agent_url`, `proactive_agent_url`, `device_control_url`, `memory_database_url`
- Added 4 new CI jobs: `tier1-data-flow`, `zeek-pipeline`, `agent-chains`, `memory-brain`
- Updated workflow_dispatch scope options and summary job

## Test Summary

| File | Tests | Async | Marker |
|------|-------|-------|--------|
| test_tier1_data_flow.py | 5 | 5 | integration |
| test_zeek_pipeline.py | 5 | 1 | integration |
| test_agent_chains.py | 5 | 4 | integration |
| test_memory_brain.py | 6 | 2 | integration |
| test_cross_domain_api.py (new tests) | 3 | 2 | integration |
| **Total new** | **24** | **14** | |

## Dependencies

- homeiq-resilience: CircuitBreaker, CrossGroupClient, ServiceAuthValidator
- homeiq-data: InfluxDBManager, StandardDataAPIClient
- homeiq-memory: MemoryClient, MemorySearch, MemoryConsolidator, decay functions
- homeiq-observability: setup_logging
- zeek-network-service: ConnLogParser, DnsLogParser, fingerprints model, AnomalyDetector
- proactive-agent-service: ConfidenceScorer, SAFETY_BLOCKED_DOMAINS

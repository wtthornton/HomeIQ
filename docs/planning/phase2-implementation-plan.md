# Phase 2: Standard Library Updates - Implementation Plan

**Created:** February 5, 2026
**Framework:** TappsCodingAgents with Context7 MCP
**Status:** Ready for Execution
**Based On:** Phase 1 Success (38/40 services, 95% success rate)

---

## Executive Summary

Phase 2 focuses on standard library updates across 30+ Python services, handling 5 breaking changes systematically. Building on Phase 1's automation framework, this phase introduces comprehensive breaking change management with automated migration scripts, extensive testing, and zero-downtime deployment.

### Key Objectives

- ✅ Update 30+ services with Phase 2 library upgrades
- ✅ Handle 5 breaking changes systematically
- ✅ Maintain 95%+ success rate from Phase 1
- ✅ Zero-downtime deployment for all services
- ✅ Comprehensive testing for each breaking change
- ✅ Automated rollback support

### Success Criteria

- [ ] All 30+ services updated successfully
- [ ] 100% test pass rate after breaking changes
- [ ] Health checks pass for all services
- [ ] Zero production incidents
- [ ] Documentation updated for all breaking changes
- [ ] Rollback tested and verified

---

## Phase 2 Library Updates

### Overview

| Library | From | To | Change Type | Services | Risk |
|---------|------|-----|-------------|----------|------|
| **pytest** | 8.3.x | 9.0.2 | MINOR | 30+ | LOW |
| **pytest-asyncio** | 0.23.0 | 1.3.0 | **BREAKING** | 25+ | HIGH |
| **tenacity** | 8.2.3 | 9.1.2 | **BREAKING** | 20+ | MEDIUM |
| **asyncio-mqtt → aiomqtt** | N/A | 2.4.0 | **BREAKING** | 5-8 | HIGH |
| **influxdb3-python** | 0.3.0 | 0.17.0 | **BREAKING** | 10+ | HIGH |
| **python-dotenv** | Current | 1.2.1 | PATCH | 30+ | LOW |

### Breaking Changes Summary

**5 Breaking Changes to Handle:**

1. **pytest-asyncio 1.3.0** - Test fixture patterns changed
2. **tenacity 9.1.2** - Retry decorator API updated
3. **asyncio-mqtt → aiomqtt 2.4.0** - Complete library replacement
4. **influxdb3-python 0.17.0** - Client API redesigned
5. **pytest 9.0.2** - Minor breaking changes in plugins

---

## Story Breakdown

### Epic: Phase 2 Standard Library Updates

**Epic ID:** PHASE2-STDLIB-001
**Priority:** HIGH
**Story Points:** 55
**Estimated Duration:** 5-7 days

---

### Story 1: Service Dependency Analysis & Risk Assessment

**Story ID:** PHASE2-001
**Priority:** CRITICAL
**Story Points:** 5
**Estimated Effort:** 4-6 hours

#### Description

As a DevOps engineer, I want to analyze all service dependencies and assess migration risks, so that we can identify which services are affected by each breaking change and plan the migration order.

#### Acceptance Criteria

1. ✅ Complete dependency map created for all 30+ services
2. ✅ Services categorized by breaking change impact
3. ✅ Risk assessment completed for each service
4. ✅ Migration order determined based on dependencies
5. ✅ Service groups identified for parallel processing

#### Tasks

- [ ] Scan all `requirements.txt` files for Phase 2 libraries
- [ ] Identify services using pytest-asyncio (async tests)
- [ ] Find services using tenacity (retry logic)
- [ ] Locate services using asyncio-mqtt/MQTT
- [ ] Find services using influxdb-client (InfluxDB writes)
- [ ] Create dependency graph with networkx
- [ ] Generate risk matrix (Low/Medium/High)
- [ ] Document migration order with justification

#### Implementation Commands

```bash
# Scan for pytest-asyncio usage
grep -r "pytest-asyncio" services/*/requirements.txt

# Find async test patterns
find services -name "test_*.py" -exec grep -l "@pytest.mark.asyncio" {} \;

# Scan for tenacity usage
grep -r "tenacity" services/*/requirements.txt
grep -r "from tenacity import" services/*/src/

# Find MQTT services
grep -r "asyncio_mqtt" services/*/requirements.txt
grep -r "import asyncio_mqtt" services/*/src/

# Find InfluxDB services
grep -r "influxdb-client\|influxdb3-python" services/*/requirements.txt
grep -r "from influxdb_client import" services/*/src/
```

#### Deliverables

- `docs/planning/phase2-dependency-analysis.md` - Dependency map
- `docs/planning/phase2-risk-assessment.md` - Risk matrix
- `docs/planning/phase2-migration-order.md` - Service migration order
- `.phase2_service_groups.json` - Service categorization

---

### Story 2: pytest-asyncio 1.3.0 Migration Script

**Story ID:** PHASE2-002
**Priority:** HIGH
**Story Points:** 8
**Estimated Effort:** 1-2 days

#### Description

As a developer, I want an automated migration script for pytest-asyncio 1.3.0, so that all async test patterns are updated correctly without manual intervention.

#### Acceptance Criteria

1. ✅ Migration script handles all breaking changes
2. ✅ `@pytest.mark.asyncio` patterns updated
3. ✅ `pytest.ini` configurations updated
4. ✅ Fixture scope changes handled
5. ✅ All tests pass after migration
6. ✅ Rollback script created

#### Breaking Changes to Handle

**pytest-asyncio 1.3.0 Changes:**
- `asyncio_mode = "auto"` is now default (remove from pytest.ini)
- `@pytest.mark.asyncio` required for all async tests
- Fixture scope changes: `scope="function"` → `scope="function", loop_scope="function"`
- Event loop fixture now auto-closed

#### Tasks

- [ ] Create `scripts/phase2-migrate-pytest-asyncio.py`
- [ ] Scan all test files for async patterns
- [ ] Update `@pytest.mark.asyncio` usage
- [ ] Update `pytest.ini` configurations
- [ ] Handle fixture scope changes
- [ ] Test migration on sample service
- [ ] Create rollback script
- [ ] Document migration process

#### Implementation Script Pseudocode

```python
# scripts/phase2-migrate-pytest-asyncio.py

def migrate_pytest_asyncio(service_path):
    """Migrate service to pytest-asyncio 1.3.0"""

    # 1. Update pytest.ini
    update_pytest_ini(service_path)

    # 2. Update test files
    for test_file in find_test_files(service_path):
        # Add @pytest.mark.asyncio to async test functions
        add_asyncio_markers(test_file)

        # Update fixture scopes
        update_fixture_scopes(test_file)

    # 3. Update conftest.py
    update_conftest(service_path)

    # 4. Run tests to verify
    run_tests(service_path)

def update_pytest_ini(service_path):
    """Update pytest.ini configuration"""
    pytest_ini = read_file(f"{service_path}/pytest.ini")

    # Remove asyncio_mode = "auto" (now default)
    pytest_ini = remove_line(pytest_ini, "asyncio_mode = auto")

    write_file(f"{service_path}/pytest.ini", pytest_ini)

def add_asyncio_markers(test_file):
    """Add @pytest.mark.asyncio to async test functions"""
    content = read_file(test_file)

    # Find async test functions without marker
    pattern = r"^async def test_\w+\(.*\):$"

    for match in find_pattern(content, pattern):
        if not has_marker(match, "@pytest.mark.asyncio"):
            add_marker(match, "@pytest.mark.asyncio")

    write_file(test_file, content)
```

#### Deliverables

- `scripts/phase2-migrate-pytest-asyncio.py` - Migration script
- `scripts/phase2-rollback-pytest-asyncio.sh` - Rollback script
- `docs/guides/pytest-asyncio-migration-guide.md` - Migration guide
- Test results for sample services

---

### Story 3: tenacity 9.1.2 Migration Script

**Story ID:** PHASE2-003
**Priority:** MEDIUM
**Story Points:** 5
**Estimated Effort:** 1 day

#### Description

As a developer, I want an automated migration script for tenacity 9.1.2, so that all retry logic is updated to the new API without breaking existing functionality.

#### Acceptance Criteria

1. ✅ Migration script handles all API changes
2. ✅ Retry decorators updated to new syntax
3. ✅ Custom retry logic patterns preserved
4. ✅ Error handling tested in failure scenarios
5. ✅ All services pass retry tests
6. ✅ Rollback script created

#### Breaking Changes to Handle

**tenacity 9.1.2 Changes:**
- `@retry` decorator parameters renamed
- `wait_exponential` → `wait_exponential_multiplier`
- `stop_after_attempt` unchanged (compatible)
- New `retry_error_callback` parameter

#### Tasks

- [ ] Create `scripts/phase2-migrate-tenacity.py`
- [ ] Scan all services for tenacity usage
- [ ] Update retry decorator syntax
- [ ] Update wait strategies
- [ ] Test retry behavior with failures
- [ ] Create rollback script
- [ ] Document migration process

#### Implementation Script Pseudocode

```python
# scripts/phase2-migrate-tenacity.py

def migrate_tenacity(service_path):
    """Migrate service to tenacity 9.1.2"""

    # 1. Find all files using tenacity
    files = find_files_with_tenacity(service_path)

    # 2. Update retry decorators
    for file in files:
        update_retry_decorators(file)

    # 3. Test retry behavior
    test_retry_behavior(service_path)

def update_retry_decorators(file_path):
    """Update retry decorator syntax"""
    content = read_file(file_path)

    # Update wait_exponential → wait_exponential_multiplier
    content = replace(
        content,
        r"wait=wait_exponential\(multiplier=(\d+), min=(\d+), max=(\d+)\)",
        r"wait=wait_exponential_multiplier(multiplier=\1, min=\2, max=\3)"
    )

    write_file(file_path, content)
```

#### Deliverables

- `scripts/phase2-migrate-tenacity.py` - Migration script
- `scripts/phase2-rollback-tenacity.sh` - Rollback script
- `docs/guides/tenacity-migration-guide.md` - Migration guide
- Retry behavior test results

---

### Story 4: asyncio-mqtt → aiomqtt 2.4.0 Migration

**Story ID:** PHASE2-004
**Priority:** HIGH
**Story Points:** 13
**Estimated Effort:** 2-3 days

#### Description

As a developer, I want to migrate all MQTT services from asyncio-mqtt to aiomqtt 2.4.0, so that we use the actively maintained library with better async support.

#### Acceptance Criteria

1. ✅ All MQTT services identified
2. ✅ Import statements updated
3. ✅ Connection patterns migrated
4. ✅ Subscribe/publish logic updated
5. ✅ Error handling preserved
6. ✅ MQTT connectivity tested
7. ✅ Rollback script created

#### Breaking Changes to Handle

**asyncio-mqtt → aiomqtt Migration:**
- Package name: `asyncio_mqtt` → `aiomqtt`
- Class name: `Client` → `Client` (same)
- Context manager: `async with Client(...) as client:` (same pattern)
- Subscribe: `await client.subscribe(topic)` (compatible)
- Publish: `await client.publish(topic, payload)` (compatible)
- Connection parameters slightly different

#### Tasks

- [ ] Identify all MQTT services (5-8 services)
- [ ] Create `scripts/phase2-migrate-mqtt.py`
- [ ] Update import statements
- [ ] Update Client initialization
- [ ] Update connection parameters
- [ ] Test MQTT connectivity
- [ ] Verify subscribe/publish functionality
- [ ] Create rollback script
- [ ] Document migration process

#### MQTT Services to Migrate

Likely candidates:
- `homeiq-mqtt-bridge` (if exists)
- `homeiq-device-mqtt-service` (if exists)
- Any service with MQTT in requirements.txt

#### Implementation Script Pseudocode

```python
# scripts/phase2-migrate-mqtt.py

def migrate_mqtt_service(service_path):
    """Migrate service from asyncio-mqtt to aiomqtt"""

    # 1. Update requirements.txt
    update_requirements(service_path)

    # 2. Update import statements
    for file in find_python_files(service_path):
        update_imports(file)

    # 3. Update Client usage
    for file in find_files_with_mqtt_client(service_path):
        update_client_usage(file)

    # 4. Test MQTT connectivity
    test_mqtt_connection(service_path)

def update_imports(file_path):
    """Update import statements"""
    content = read_file(file_path)

    # Replace imports
    content = replace(content, "import asyncio_mqtt", "import aiomqtt")
    content = replace(content, "from asyncio_mqtt import", "from aiomqtt import")

    write_file(file_path, content)

def update_requirements(service_path):
    """Update requirements.txt"""
    req_file = f"{service_path}/requirements.txt"
    content = read_file(req_file)

    # Replace package
    content = replace(content, "asyncio-mqtt==", "aiomqtt==2.4.0")

    write_file(req_file, content)
```

#### Deliverables

- `scripts/phase2-migrate-mqtt.py` - Migration script
- `scripts/phase2-rollback-mqtt.sh` - Rollback script
- `docs/guides/mqtt-migration-guide.md` - Migration guide
- MQTT connectivity test results
- List of migrated services

---

### Story 5: influxdb3-python 0.17.0 Migration

**Story ID:** PHASE2-005
**Priority:** HIGH
**Story Points:** 13
**Estimated Effort:** 2-3 days

#### Description

As a developer, I want to migrate all InfluxDB services to influxdb3-python 0.17.0, so that we use the latest client with improved performance and new features.

#### Acceptance Criteria

1. ✅ All InfluxDB services identified (10+ services)
2. ✅ Client initialization updated
3. ✅ Write API calls migrated
4. ✅ Query API calls migrated
5. ✅ Bucket configuration updated
6. ✅ Data ingestion tested
7. ✅ Rollback script created

#### Breaking Changes to Handle

**influxdb3-python 0.17.0 Changes:**
- Package: `influxdb-client` → `influxdb3-python`
- Client: `InfluxDBClient3` → simplified API
- Write API: `write_api.write()` → `client.write()`
- Query API: New Polars/Pandas integration
- Batch writes: Improved performance

#### Tasks

- [ ] Identify all InfluxDB services (10+ services)
- [ ] Create `scripts/phase2-migrate-influxdb.py`
- [ ] Update import statements
- [ ] Update Client initialization
- [ ] Migrate write API calls
- [ ] Migrate query API calls
- [ ] Update bucket configurations
- [ ] Test data ingestion
- [ ] Verify query results
- [ ] Create rollback script
- [ ] Document migration process

#### InfluxDB Services to Migrate

Known services using InfluxDB:
- `homeiq-websocket-ingestion` - Event ingestion
- `homeiq-data-api` - Query API
- `homeiq-energy-correlator` - Energy data
- `homeiq-energy-forecasting` - Forecasting
- `homeiq-device-health-monitor` - Device metrics
- Additional services TBD from dependency scan

#### Implementation Script Pseudocode

```python
# scripts/phase2-migrate-influxdb.py

def migrate_influxdb_service(service_path):
    """Migrate service to influxdb3-python 0.17.0"""

    # 1. Update requirements.txt
    update_requirements(service_path)

    # 2. Update imports
    for file in find_python_files(service_path):
        update_imports(file)

    # 3. Update Client initialization
    for file in find_files_with_influx_client(service_path):
        update_client_init(file)
        update_write_calls(file)
        update_query_calls(file)

    # 4. Test data operations
    test_influxdb_operations(service_path)

def update_imports(file_path):
    """Update import statements"""
    content = read_file(file_path)

    # Replace imports
    content = replace(
        content,
        "from influxdb_client import InfluxDBClient",
        "from influxdb3_python import InfluxDB3Client"
    )

    write_file(file_path, content)

def update_client_init(file_path):
    """Update Client initialization"""
    content = read_file(file_path)

    # Old pattern:
    # client = InfluxDBClient(url=url, token=token, org=org)
    # write_api = client.write_api(write_options=SYNCHRONOUS)

    # New pattern:
    # client = InfluxDB3Client(host=host, token=token, database=database)
    # (write_api not needed - direct writes)

    # Replace patterns
    content = replace_client_pattern(content)

    write_file(file_path, content)
```

#### Deliverables

- `scripts/phase2-migrate-influxdb.py` - Migration script
- `scripts/phase2-rollback-influxdb.sh` - Rollback script
- `docs/guides/influxdb-migration-guide.md` - Migration guide
- Data ingestion test results
- Query performance comparison

---

### Story 6: Phase 2 Batch Rebuild Orchestration

**Story ID:** PHASE2-006
**Priority:** CRITICAL
**Story Points:** 13
**Estimated Effort:** 2-3 days

#### Description

As a DevOps engineer, I want an automated batch rebuild orchestrator for Phase 2, so that all 30+ services are updated systematically with proper testing and rollback support.

#### Acceptance Criteria

1. ✅ Orchestration script extends Phase 1 framework
2. ✅ Service groups processed in parallel batches
3. ✅ Breaking change migrations automated
4. ✅ Health checks validate each service
5. ✅ Rollback support for failed migrations
6. ✅ Progress tracking and reporting
7. ✅ Zero-downtime deployment achieved

#### Tasks

- [ ] Create `scripts/phase2-batch-rebuild.sh`
- [ ] Extend Phase 1 orchestration framework
- [ ] Integrate migration scripts
- [ ] Add breaking change validation
- [ ] Implement parallel batch processing
- [ ] Add health check validation
- [ ] Create rollback mechanism
- [ ] Add progress monitoring
- [ ] Test on sample service group
- [ ] Document orchestration process

#### Implementation Architecture

```bash
# scripts/phase2-batch-rebuild.sh

#!/bin/bash
# Phase 2 Batch Rebuild Orchestrator
# Extends Phase 1 framework with breaking change management

PHASE2_LIBS=(
    "pytest>=9.0.2,<10.0.0"
    "pytest-asyncio>=1.3.0,<2.0.0"
    "tenacity>=9.1.2,<10.0.0"
    "aiomqtt>=2.4.0,<3.0.0"
    "influxdb3-python>=0.17.0,<1.0.0"
    "python-dotenv>=1.2.1,<2.0.0"
)

# Service groups (based on breaking changes)
GROUP_PYTEST_ASYNCIO=(
    "api-automation-edge"
    "ml-service"
    "ai-core-service"
    # ... services with async tests
)

GROUP_TENACITY=(
    "websocket-ingestion"
    "device-health-monitor"
    # ... services with retry logic
)

GROUP_MQTT=(
    # ... services using MQTT
)

GROUP_INFLUXDB=(
    "websocket-ingestion"
    "data-api"
    "energy-correlator"
    # ... services using InfluxDB
)

main() {
    log_info "Starting Phase 2 Batch Rebuild"

    # 1. Load Phase 1 framework
    source scripts/phase1-batch-rebuild.sh

    # 2. Run dependency analysis
    run_dependency_analysis

    # 3. Process service groups
    for group in "${SERVICE_GROUPS[@]}"; do
        process_service_group "$group"
    done

    # 4. Validate all services
    validate_all_services

    # 5. Generate completion report
    generate_phase2_report
}

process_service_group() {
    local group=$1

    log_info "Processing group: $group"

    # Get services in group
    local services=$(get_services_for_group "$group")

    # Process in parallel batches
    for batch in $(split_into_batches "$services" 5); do
        process_batch "$batch"
    done
}

process_batch() {
    local batch=$1

    for service in $batch; do
        (
            log_info "Processing service: $service"

            # 1. Apply breaking change migrations
            apply_migrations "$service"

            # 2. Update requirements.txt
            update_requirements "$service"

            # 3. Rebuild service
            rebuild_service "$service"

            # 4. Run tests
            run_tests "$service"

            # 5. Health check
            health_check "$service"

            # 6. Record success
            record_success "$service"
        ) &
    done

    wait
}

apply_migrations() {
    local service=$1

    log_info "Applying migrations for: $service"

    # Apply pytest-asyncio migration
    if service_uses_pytest_asyncio "$service"; then
        python scripts/phase2-migrate-pytest-asyncio.py "$service"
    fi

    # Apply tenacity migration
    if service_uses_tenacity "$service"; then
        python scripts/phase2-migrate-tenacity.py "$service"
    fi

    # Apply MQTT migration
    if service_uses_mqtt "$service"; then
        python scripts/phase2-migrate-mqtt.py "$service"
    fi

    # Apply InfluxDB migration
    if service_uses_influxdb "$service"; then
        python scripts/phase2-migrate-influxdb.py "$service"
    fi
}
```

#### Deliverables

- `scripts/phase2-batch-rebuild.sh` - Main orchestration script
- `scripts/phase2-service-config.yaml` - Service configuration
- `scripts/phase2-monitor-rebuild.sh` - Monitoring dashboard
- `scripts/phase2-validate-services.sh` - Validation script
- `docs/planning/phase2-batch-rebuild-guide.md` - Comprehensive guide

---

### Story 7: Phase 2 Testing & Validation

**Story ID:** PHASE2-007
**Priority:** CRITICAL
**Story Points:** 8
**Estimated Effort:** 1-2 days

#### Description

As a QA engineer, I want comprehensive testing and validation for Phase 2, so that all breaking changes are verified and no regressions are introduced.

#### Acceptance Criteria

1. ✅ Test suite covers all breaking changes
2. ✅ Async test patterns validated
3. ✅ Retry behavior tested with failures
4. ✅ MQTT connectivity verified
5. ✅ InfluxDB data operations tested
6. ✅ Integration tests pass
7. ✅ Performance benchmarks collected

#### Tasks

- [ ] Create Phase 2 test suite
- [ ] Test pytest-asyncio patterns
- [ ] Test tenacity retry behavior
- [ ] Test MQTT connectivity
- [ ] Test InfluxDB operations
- [ ] Run integration tests
- [ ] Collect performance metrics
- [ ] Generate test report

#### Test Categories

**1. Unit Tests**
- pytest-asyncio async test patterns
- tenacity retry decorators
- MQTT client initialization
- InfluxDB client operations

**2. Integration Tests**
- End-to-end async workflows
- Retry behavior in failure scenarios
- MQTT publish/subscribe flow
- InfluxDB write/query operations

**3. Performance Tests**
- Test execution time (pytest 9.x)
- Retry overhead (tenacity 9.x)
- MQTT throughput (aiomqtt 2.4.0)
- InfluxDB write performance (influxdb3-python 0.17.0)

#### Deliverables

- `tests/phase2/` - Phase 2 test suite
- `scripts/phase2-run-tests.sh` - Test runner
- `docs/testing/phase2-test-report.md` - Test results
- Performance benchmark report

---

## Implementation Timeline

### Day 1: Analysis & Planning (Story 1)

**Duration:** 4-6 hours

- ✅ Run dependency analysis
- ✅ Create risk assessment
- ✅ Determine migration order
- ✅ Categorize services by breaking change
- ✅ Generate service groups

### Day 2-3: Migration Scripts (Stories 2-5)

**Duration:** 2-3 days

**Day 2:**
- ✅ Create pytest-asyncio migration script (Story 2)
- ✅ Create tenacity migration script (Story 3)
- ✅ Test migration scripts on sample services

**Day 3:**
- ✅ Create MQTT migration script (Story 4)
- ✅ Create InfluxDB migration script (Story 5)
- ✅ Test all migration scripts

### Day 4-5: Orchestration & Testing (Stories 6-7)

**Duration:** 2-3 days

**Day 4:**
- ✅ Create batch rebuild orchestrator (Story 6)
- ✅ Integrate migration scripts
- ✅ Test orchestration on pilot group

**Day 5:**
- ✅ Create test suite (Story 7)
- ✅ Run full Phase 2 rebuild
- ✅ Validate all services
- ✅ Generate completion report

### Total Duration: 5-7 days

---

## Risk Assessment

### High-Risk Changes

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **pytest-asyncio test failures** | HIGH | MEDIUM | Extensive testing, rollback support |
| **MQTT connectivity issues** | HIGH | LOW | Test on non-prod first, verify brokers |
| **InfluxDB data loss** | CRITICAL | LOW | Backup before migration, verify writes |
| **Service downtime** | HIGH | LOW | Blue-green deployment, health checks |

### Medium-Risk Changes

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **Tenacity retry behavior** | MEDIUM | MEDIUM | Test failure scenarios |
| **pytest plugin compatibility** | MEDIUM | LOW | Check plugin versions |
| **Performance degradation** | MEDIUM | LOW | Benchmark before/after |

### Low-Risk Changes

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **python-dotenv updates** | LOW | LOW | Standard patch update |
| **pytest 9.x minor changes** | LOW | LOW | Well-documented upgrade path |

---

## Rollback Strategy

### Automatic Rollback Triggers

- Migration script failures
- Test suite failures (>10% tests failing)
- Health check failures
- Critical service downtime

### Rollback Procedure

```bash
# Per-service rollback
scripts/phase2-rollback.sh <service_name>

# Breaking change rollback
scripts/phase2-rollback-pytest-asyncio.sh
scripts/phase2-rollback-tenacity.sh
scripts/phase2-rollback-mqtt.sh
scripts/phase2-rollback-influxdb.sh

# Full Phase 2 rollback
scripts/phase2-rollback-all.sh
```

### Rollback Validation

- Verify service health
- Run regression tests
- Check data integrity
- Validate performance metrics

---

## Monitoring & Validation

### Real-Time Monitoring

```bash
# Launch Phase 2 monitoring dashboard
scripts/phase2-monitor-rebuild.sh
```

**Dashboard Metrics:**
- Services processed / total
- Migration success rate
- Test pass rate
- Health check status
- Performance metrics
- Error count by type

### Post-Migration Validation

```bash
# Validate all Phase 2 services
scripts/phase2-validate-services.sh
```

**Validation Checks:**
- All services running
- Health endpoints responding
- Tests passing
- No error spikes in logs
- Performance within baseline

---

## Documentation Deliverables

### Migration Guides

1. `docs/guides/pytest-asyncio-migration-guide.md`
2. `docs/guides/tenacity-migration-guide.md`
3. `docs/guides/mqtt-migration-guide.md`
4. `docs/guides/influxdb-migration-guide.md`

### Planning Documents

1. `docs/planning/phase2-dependency-analysis.md`
2. `docs/planning/phase2-risk-assessment.md`
3. `docs/planning/phase2-migration-order.md`
4. `docs/planning/phase2-batch-rebuild-guide.md`

### Reports

1. `docs/planning/phase2-execution-complete.md`
2. `docs/testing/phase2-test-report.md`
3. `docs/performance/phase2-benchmark-report.md`

---

## Success Metrics

### Quantitative Metrics

- **Success Rate:** ≥95% (maintain Phase 1 rate)
- **Test Pass Rate:** 100% after migration
- **Health Check Pass Rate:** 100%
- **Migration Time:** <8 hours for all services
- **Downtime:** 0 seconds (zero-downtime deployment)
- **Rollback Rate:** <5%

### Qualitative Metrics

- Breaking changes handled systematically
- Documentation comprehensive and clear
- Migration scripts reusable for future phases
- Team confidence in automation framework
- Production stability maintained

---

## Dependencies

### Prerequisite

- ✅ Phase 1 Complete (38/40 services, 95% success)
- ✅ Phase 1 automation framework functional
- ✅ BuildKit optimization enabled
- ✅ Health check system operational

### External Dependencies

- Docker 29.1.3+
- Docker Compose 2.40.3+
- Python 3.10+ on all services
- InfluxDB 2.x (for influxdb3-python)
- MQTT broker (for aiomqtt)

---

## Next Steps After Phase 2

### Phase 3: ML/AI Library Upgrades

- NumPy 2.x migration
- Pandas 3.x migration
- TensorFlow/PyTorch updates
- Scikit-learn updates

### Continuous Improvement

- Enhance automation framework
- Improve migration scripts
- Expand test coverage
- Optimize performance

---

**Status:** Ready for Execution
**Estimated Start:** February 5-6, 2026
**Estimated Completion:** February 10-12, 2026
**Framework:** TappsCodingAgents with Context7 MCP

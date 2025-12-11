# Epic 50: WebSocket Ingestion Service Code Review Improvements

**Status:** 🔄 **IN PROGRESS** (Critical Items Complete)  
**Type:** Quality & Security Enhancement  
**Priority:** High  
**Effort:** 7 Stories (15-20 hours estimated)  
**Created:** December 2025  
**Target Completion:** December 2025  
**Related:** Code Review - `docs/qa/code-review-websocket-ingestion-2025.md`

---

## Epic Goal

Address security, testing, and code quality improvements identified in the comprehensive 2025 code review of the websocket-ingestion service. This epic enhances production readiness by implementing timezone standardization, security hardening, comprehensive integration tests, and documentation improvements while maintaining the service's excellent architectural patterns and performance optimizations.

**Value:** High - Improves consistency, security, and test coverage for the most critical service in the HomeIQ architecture.

**Complexity:** Medium - Focused improvements to existing working service with well-defined scope.

---

## Existing System Context

### Current Service Status

**Service:** websocket-ingestion (Port 8001)  
**Status:** ✅ Production Ready (with concerns identified)  
**Quality Score:** 82/100  
**Code Review Date:** December 2025

### Current Strengths

- ✅ Epic 31 architecture compliance (perfect alignment)
- ✅ Sophisticated async-first design
- ✅ State machine patterns for robust state management
- ✅ Circuit breaker and retry logic
- ✅ Batch processing with overflow protection
- ✅ Comprehensive error handling
- ✅ Memory management for NUC constraints

### Code Review Findings

**14 Issues Identified:**
- 0 HIGH: No critical blocking issues
- 7 MEDIUM: Timezone standardization, integration tests, security hardening, test coverage
- 7 LOW: Code organization, documentation, type hints

**Review Reference:** `docs/qa/code-review-websocket-ingestion-2025.md`

---

## Enhancement Details

### High Priority Improvements

1. **Timezone Standardization (Story 50.1)**
   - Standardize all datetime operations to timezone-aware
   - Replace 107 instances of `datetime.now()` with `datetime.now(timezone.utc)`

2. **Security Hardening (Story 50.2)**
   - Add WebSocket message input validation
   - Enable SSL verification by default
   - Add rate limiting

### Medium Priority Improvements

3. **Integration Test Suite (Story 50.3)**
   - End-to-end WebSocket connection tests
   - Full event processing pipeline tests
   - Discovery service integration tests

4. **Error Scenario Testing (Story 50.4)**
   - Connection failure and retry tests
   - InfluxDB write failure tests
   - Network timeout scenarios

5. **WebSocket Handler Tests (Story 50.5)**
   - WebSocket connection/disconnection tests
   - Message handling tests
   - Invalid message handling

6. **Test Coverage Improvement (Story 50.6)**
   - Increase coverage from 70% to 80%
   - Update pytest.ini configuration
   - Add missing test cases

7. **Code Organization & Documentation (Story 50.7)**
   - Move archive files
   - Move test file to tests directory
   - Add architecture diagram
   - Enhance component documentation

### Success Criteria

- ✅ All timezone operations standardized (107 instances)
- ✅ Security hardening implemented
- ✅ Integration test suite implemented and passing
- ✅ Test coverage ≥80% achieved
- ✅ Error scenarios comprehensively tested
- ✅ WebSocket handler tests implemented
- ✅ Code organization improved
- ✅ All tests passing in CI/CD pipeline

---

## Stories

### Story 50.1: Timezone Standardization

**Priority:** High  
**Effort:** 2-3 hours  
**Status:** ✅ **COMPLETE**  
**Story Type:** Code Quality Enhancement

#### Goal

Standardize all datetime operations to use timezone-aware datetimes consistently throughout the service, replacing 107 instances of timezone-naive `datetime.now()` calls.

#### Background

Code review identified:
- 107 instances of `datetime.now()` without timezone across 22 files
- Inconsistent timezone handling can cause issues with time-based operations
- Should use `datetime.now(timezone.utc)` consistently

#### Acceptance Criteria

**Functional Requirements:**
- [x] All `datetime.now()` calls replaced with `datetime.now(timezone.utc)`
- [x] All timestamp operations use timezone-aware datetimes
- [x] No regression in existing functionality
- [x] All tests continue to pass

**Technical Requirements:**
- [x] Add `from datetime import timezone` import where needed
- [x] Replace all `datetime.now()` with `datetime.now(timezone.utc)`
- [x] Replace all `datetime.utcnow()` with `datetime.now(timezone.utc)` (if any)
- [x] Update timestamp comparisons to use timezone-aware datetimes
- [x] Verify all datetime operations work correctly

**Quality Requirements:**
- [x] All existing tests continue to pass
- [x] No breaking changes to API contracts
- [x] Timestamps remain ISO 8601 format

#### Tasks

1. Identify all datetime.now() instances
   - Run grep to find all instances
   - Document which files need changes
   - Create change list

2. Add timezone import
   - Add `from datetime import datetime, timezone` to all affected files
   - Remove deprecated `datetime.utcnow()` if present

3. Replace datetime.now() calls
   - Replace with `datetime.now(timezone.utc)`
   - Update timestamp comparisons
   - Verify ISO format maintained

4. Test timezone changes
   - Run full test suite
   - Verify timestamp behavior
   - Check health check timestamps

5. Update documentation
   - Document timezone standardization
   - Update any timezone-related docs

#### File List

**Files to Update (22 files):**
- `src/connection_manager.py`
- `src/main.py`
- `src/health_check.py`
- `src/batch_processor.py`
- `src/influxdb_batch_writer.py`
- `src/async_event_processor.py`
- `src/event_processor.py`
- `src/event_queue.py`
- `src/event_rate_monitor.py`
- `src/event_subscription.py`
- `src/discovery_service.py`
- `src/influxdb_wrapper.py`
- `src/memory_manager.py`
- `src/http_client.py`
- `src/error_handler.py`
- `src/historical_event_counter.py`
- `src/token_validator.py`
- `src/websocket_client.py`
- `src/entity_filter.py`
- `src/influxdb_schema.py`
- `src/weather_cache.py` (if present)
- `src/weather_client.py` (if present)

---

### Story 50.2: Security Hardening

**Priority:** High  
**Effort:** 1-2 hours  
**Status:** ✅ **COMPLETE**  
**Story Type:** Security Enhancement

#### Goal

Implement security hardening measures including WebSocket message input validation, SSL verification enablement, and rate limiting to address MEDIUM priority security concerns.

#### Background

Code review identified:
- WebSocket handler accepts messages without input validation
- SSL verification disabled in discovery service
- No rate limiting on WebSocket messages

#### Acceptance Criteria

**Functional Requirements:**
- [x] WebSocket messages validated for size limits (64KB max)
- [x] WebSocket messages validated for JSON structure
- [x] Rate limiting implemented for WebSocket connections
- [x] SSL verification enabled by default (configurable)
- [x] No breaking changes to existing functionality

**Technical Requirements:**
- [x] Add message size validation (MAX_MESSAGE_SIZE = 64KB)
- [x] Add JSON structure validation
- [x] Implement rate limiting (60 messages/minute per connection)
- [x] Enable SSL verification with configuration option
- [x] Add security tests

**Quality Requirements:**
- [x] All existing tests continue to pass
- [x] New security tests added and passing
- [x] Error messages are clear and actionable

#### Tasks

1. Add WebSocket message validation
   - Add size limit check (64KB)
   - Add JSON structure validation
   - Add error responses for invalid messages

2. Implement rate limiting
   - Add rate limiter per connection
   - Track message count per minute
   - Return rate limit error when exceeded

3. Enable SSL verification
   - Make SSL verification configurable
   - Default to enabled (ssl=True)
   - Allow disabling for local/internal networks

4. Add security tests
   - Test message size limits
   - Test rate limiting
   - Test SSL verification

5. Update documentation
   - Document security features
   - Document configuration options

#### File List

- `services/websocket-ingestion/src/main.py` - Add WebSocket validation
- `services/websocket-ingestion/src/discovery_service.py` - Enable SSL verification
- `services/websocket-ingestion/tests/unit/test_websocket_security.py` - New security tests
- `services/websocket-ingestion/README.md` - Update security documentation

---

### Story 50.3: Integration Test Suite

**Priority:** Medium  
**Effort:** 4-6 hours  
**Status:** ✅ **COMPLETE**  
**Story Type:** Testing Foundation

#### Goal

Implement comprehensive integration tests for end-to-end WebSocket connections, full event processing pipeline, and discovery service integration.

#### Background

Code review identified:
- Only unit tests exist
- Missing integration tests for:
  - End-to-end WebSocket connection flow
  - Full event processing pipeline (HA → InfluxDB)
  - Discovery service integration with data-api
  - Batch processing integration

#### Acceptance Criteria

**Functional Requirements:**
- [x] Integration tests for WebSocket connection flow
- [x] Integration tests for event processing pipeline
- [x] Integration tests for discovery service
- [x] Integration tests for batch processing
- [x] All integration tests passing

**Technical Requirements:**
- [x] Create `tests/integration/` directory
- [x] Use testcontainers or mocks for external services
- [x] Tests are independent and parallel-safe
- [x] Test data is self-contained

**Quality Requirements:**
- [x] Tests document expected behavior
- [x] Tests use appropriate test levels
- [x] Integration tests don't block unit tests

#### Tasks

1. Set up integration test infrastructure
   - Create `tests/integration/` directory
   - Configure testcontainers or mock services
   - Create shared fixtures

2. Implement WebSocket connection integration tests
   - Test connection establishment
   - Test authentication flow
   - Test reconnection logic
   - Test event subscription

3. Implement event processing pipeline tests
   - Test end-to-end event flow (HA → InfluxDB)
   - Test batch processing
   - Test error handling in pipeline

4. Implement discovery service integration tests
   - Test device discovery
   - Test entity discovery
   - Test data-api integration
   - Test cache refresh

5. Add integration test documentation
   - Document test setup requirements
   - Document how to run integration tests

#### File List

- `services/websocket-ingestion/tests/integration/test_websocket_connection.py` - New
- `services/websocket-ingestion/tests/integration/test_event_pipeline.py` - New
- `services/websocket-ingestion/tests/integration/test_discovery_integration.py` - New
- `services/websocket-ingestion/tests/integration/test_batch_processing.py` - New
- `services/websocket-ingestion/tests/integration/conftest.py` - New (shared fixtures)

---

### Story 50.4: Error Scenario Testing

**Priority:** Medium  
**Effort:** 2-3 hours  
**Status:** 📋 Planning  
**Story Type:** Testing Enhancement

#### Goal

Add comprehensive error scenario tests to ensure robust error handling and graceful degradation under all failure conditions.

#### Background

Code review identified:
- Tests focus on happy path scenarios
- Missing tests for:
  - WebSocket connection failures and retries
  - InfluxDB write failures
  - Discovery service failures
  - Network timeout scenarios
  - Queue overflow scenarios

#### Acceptance Criteria

**Functional Requirements:**
- [ ] Tests for WebSocket connection failures
- [ ] Tests for InfluxDB write failures
- [ ] Tests for discovery service failures
- [ ] Tests for network timeouts
- [ ] Tests for queue overflow scenarios
- [ ] Tests for retry logic

**Technical Requirements:**
- [ ] Use pytest.raises() for exception testing
- [ ] Mock external dependencies for failure scenarios
- [ ] Test error recovery and fallback logic
- [ ] Test circuit breaker behavior

**Quality Requirements:**
- [ ] All error scenarios documented
- [ ] Tests verify graceful degradation
- [ ] Error messages are clear and actionable

#### Tasks

1. Add WebSocket failure tests
   - Test connection failures
   - Test reconnection logic
   - Test infinite retry behavior
   - Test circuit breaker

2. Add InfluxDB failure tests
   - Test write failures
   - Test connection failures
   - Test error recovery
   - Test batch write failures

3. Add discovery service failure tests
   - Test HTTP API failures
   - Test WebSocket fallback
   - Test cache behavior on failures

4. Add network timeout tests
   - Test timeout scenarios
   - Test timeout recovery
   - Test timeout handling

5. Add queue overflow tests
   - Test queue at capacity
   - Test overflow strategies
   - Test dropped events handling

#### File List

- `services/websocket-ingestion/tests/unit/test_error_scenarios.py` - New
- `services/websocket-ingestion/tests/unit/test_connection_failures.py` - New
- `services/websocket-ingestion/tests/unit/test_influxdb_failures.py` - New

---

### Story 50.5: WebSocket Handler Tests

**Priority:** Medium  
**Effort:** 1-2 hours  
**Status:** 📋 Planning  
**Story Type:** Testing Enhancement

#### Goal

Add comprehensive tests for the WebSocket handler to ensure proper connection management, message handling, and error scenarios.

#### Background

Code review identified:
- WebSocket handler (`websocket_handler()`) has no dedicated tests
- Critical functionality should be thoroughly tested

#### Acceptance Criteria

**Functional Requirements:**
- [ ] Tests for WebSocket connection establishment
- [ ] Tests for connection/disconnection scenarios
- [ ] Tests for ping/pong message handling
- [ ] Tests for subscribe message handling
- [ ] Tests for invalid JSON handling
- [ ] Tests for error scenarios

**Technical Requirements:**
- [ ] Use aiohttp test utilities for WebSocket testing
- [ ] Mock WebSocket connections
- [ ] Test message sending and receiving
- [ ] Test error handling

**Quality Requirements:**
- [ ] Tests are maintainable and readable
- [ ] Tests document expected behavior
- [ ] All scenarios covered

#### Tasks

1. Set up WebSocket test infrastructure
   - Create WebSocket test fixtures
   - Set up mock WebSocket connections
   - Create test utilities

2. Add connection tests
   - Test connection establishment
   - Test disconnection handling
   - Test connection state management

3. Add message handling tests
   - Test ping/pong messages
   - Test subscribe messages
   - Test unknown message types
   - Test echo functionality

4. Add error handling tests
   - Test invalid JSON handling
   - Test WebSocket errors
   - Test exception handling

#### File List

- `services/websocket-ingestion/tests/unit/test_websocket_handler.py` - New
- `services/websocket-ingestion/tests/conftest.py` - Add WebSocket fixtures

---

### Story 50.6: Test Coverage Improvement

**Priority:** Medium  
**Effort:** 3-4 hours  
**Status:** 📋 Planning  
**Story Type:** Testing Enhancement

#### Goal

Increase test coverage from 70% to 80% target by adding missing test cases and updating pytest configuration.

#### Background

Code review identified:
- Current coverage target is 70% (below project standard ≥80% target)
- Service is large and complex, should target higher coverage
- Missing coverage in some areas

#### Acceptance Criteria

**Functional Requirements:**
- [ ] Test coverage ≥80% achieved
- [ ] All critical paths have test coverage
- [ ] Edge cases comprehensively tested
- [ ] pytest.ini fail_under updated to 80%

**Technical Requirements:**
- [ ] Run coverage report to identify gaps
- [ ] Add missing unit tests for uncovered functions
- [ ] Add edge case tests (boundary conditions)
- [ ] Update pytest.ini coverage settings

**Quality Requirements:**
- [ ] All new tests are maintainable and readable
- [ ] Test names clearly describe what's being tested
- [ ] Tests follow AAA pattern

#### Tasks

1. Run coverage analysis
   - Generate coverage report
   - Identify uncovered functions/methods
   - Identify low-coverage areas
   - Document coverage gaps

2. Add missing unit tests
   - Test all public methods
   - Test helper functions
   - Test edge cases
   - Test boundary conditions

3. Update pytest configuration
   - Set fail_under = 80 in pytest.ini
   - Verify coverage report generation
   - Update coverage exclusion patterns if needed

4. Verify coverage target met
   - Run full test suite with coverage
   - Verify ≥80% coverage achieved
   - Document coverage improvements

#### File List

- `services/websocket-ingestion/tests/unit/test_edge_cases.py` - New
- `services/websocket-ingestion/tests/unit/test_*.py` - Extend existing
- `services/websocket-ingestion/pytest.ini` - Update coverage settings

---

### Story 50.7: Code Organization & Documentation

**Priority:** Medium  
**Effort:** 1-2 hours  
**Status:** ✅ **COMPLETE**  
**Story Type:** Code Quality Enhancement

#### Goal

Improve code organization by moving archive files, relocating misplaced test files, and enhancing documentation with architecture diagrams and detailed component documentation.

#### Background

Code review identified:
- Archive files in source directory
- Test file in source directory
- Missing architecture diagram
- Complex components need better documentation

#### Acceptance Criteria

**Functional Requirements:**
- [x] Archive files moved to appropriate location
- [x] Test file moved to tests/ directory
- [x] Architecture diagram added or referenced
- [x] Complex components have detailed docstrings
- [x] No breaking changes

**Technical Requirements:**
- [x] Move `src/archive/` files to archive location
- [x] Move `src/test_state_machine_integration.py` to tests/
- [x] Add architecture diagram or reference
- [x] Enhance docstrings for complex components

**Quality Requirements:**
- [x] Code organization follows standards
- [x] Documentation is clear and comprehensive
- [x] No functional changes

#### Tasks

1. Reorganize archive files
   - Move archive directory to appropriate location
   - Or remove if no longer needed
   - Update any references

2. Move test file
   - Move `src/test_state_machine_integration.py` to `tests/integration/`
   - Update imports if needed
   - Verify tests still pass

3. Add architecture diagram
   - Create or reference architecture diagram
   - Show component relationships
   - Show data flow

4. Enhance documentation
   - Add detailed docstrings to complex components
   - Document state machine transitions
   - Document batch processing algorithms
   - Document retry logic patterns

#### File List

- `services/websocket-ingestion/src/archive/` - Move or remove
- `services/websocket-ingestion/src/test_state_machine_integration.py` - Move to tests/
- `services/websocket-ingestion/src/connection_manager.py` - Enhance docstrings
- `services/websocket-ingestion/src/batch_processor.py` - Enhance docstrings
- `services/websocket-ingestion/src/state_machine.py` - Enhance docstrings
- `services/websocket-ingestion/README.md` - Add architecture diagram reference

---

## Timeline

**Estimated Duration:** 15-20 hours (3-4 days)

**Phase 1: Critical Improvements (Stories 50.1, 50.2)** - 3-5 hours
- Timezone standardization and security hardening

**Phase 2: Testing Foundation (Stories 50.3, 50.4, 50.5)** - 7-11 hours
- Integration tests, error scenarios, WebSocket handler tests

**Phase 3: Quality & Organization (Stories 50.6, 50.7)** - 4-5 hours
- Test coverage improvement and code organization

---

## Risk Mitigation

### Primary Risks

**Risk 1: Timezone changes break existing functionality**
- **Mitigation:** Comprehensive test coverage before changes, verify all timestamp operations
- **Rollback:** Revert timezone changes if issues found

**Risk 2: Integration test setup complexity**
- **Mitigation:** Use testcontainers or mock services (simpler setup)
- **Rollback:** Skip integration tests if setup too complex (document for future)

**Risk 3: Test coverage target not achievable**
- **Mitigation:** Focus on critical paths first, document acceptable gaps
- **Rollback:** Set realistic target (75% minimum, 80% stretch goal)

---

## Definition of Done

- [ ] All 7 stories completed with acceptance criteria met
- [ ] All timezone operations standardized (107 instances)
- [ ] Security hardening implemented
- [ ] Integration test suite implemented and passing
- [ ] Test coverage ≥80% achieved
- [ ] All error scenarios tested
- [ ] WebSocket handler tests implemented
- [ ] Code organization improved
- [ ] All tests passing in CI/CD pipeline
- [ ] Documentation updated
- [ ] Code review findings addressed (MEDIUM priorities)
- [ ] No regression in existing functionality

---

## References

- **Code Review:** `docs/qa/code-review-websocket-ingestion-2025.md`
- **Service README:** `services/websocket-ingestion/README.md`
- **Code Review Guide:** `docs/architecture/code-review-guide-2025.md`
- **Epic 31 Architecture:** `.cursor/rules/epic-31-architecture.mdc`
- **Similar Epics:** 
  - `docs/prd/epic-48-energy-correlator-code-review-improvements.md`
  - `docs/prd/epic-49-electricity-pricing-service-code-review-improvements.md`

---

**Epic Created:** December 2025  
**Last Updated:** December 2025  
**Status:** 📋 Planning


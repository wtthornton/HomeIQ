# Epic 48: Energy Correlator Code Review Improvements

**Status:** 🔄 **IN PROGRESS** (Critical Items Complete)  
**Type:** Quality & Security Enhancement  
**Priority:** High  
**Effort:** 5 Stories (14-18 hours estimated)  
**Created:** December 2025  
**Target Completion:** December 2025  
**Related:** Code Review - `docs/qa/code-review-energy-correlator-2025.md`

---

## Epic Goal

Address critical security, testing, and code quality improvements identified in the comprehensive 2025 code review of the energy-correlator service. This epic enhances production readiness by implementing security hardening, comprehensive test coverage, and performance optimizations while maintaining the service's excellent architectural patterns.

**Value:** High - Addresses security vulnerabilities, improves reliability through comprehensive testing, and optimizes resource usage.

**Complexity:** Medium - Focused improvements to existing working service with well-defined scope.

---

## Existing System Context

### Current Service Status

**Service:** energy-correlator (Port 8017)  
**Status:** ✅ Production Ready (with concerns identified)  
**Quality Score:** 78/100  
**Code Review Date:** December 2025

### Current Strengths

- ✅ Epic 31 architecture compliance (direct InfluxDB writes)
- ✅ Async-first design with proper batch processing
- ✅ Power cache optimization (eliminates N+1 queries)
- ✅ Clean separation of concerns
- ✅ Comprehensive configuration via environment variables

### Code Review Findings

**12 Issues Identified:**
- 1 HIGH: API endpoint authentication/validation
- 5 MEDIUM: Integration tests, error scenarios, test coverage, performance optimizations
- 6 LOW: Timezone handling, type hints, observability (deferred to future epic)

**Review Reference:** `docs/qa/code-review-energy-correlator-2025.md`

---

## Enhancement Details

### High Priority Improvements

1. **Security Hardening (Story 48.1)**
   - Add API endpoint validation/authentication
   - Validate InfluxDB bucket name format
   - Sanitize Flux query inputs

2. **Integration Test Suite (Story 48.2)**
   - Implement InfluxDB query integration tests
   - Add API endpoint integration tests
   - Test end-to-end event processing flow

### Medium Priority Improvements

3. **Error Scenario Testing (Story 48.3)**
   - Test connection failures and timeouts
   - Test invalid data formats
   - Test retry queue overflow scenarios

4. **Test Coverage & Quality (Story 48.4)**
   - Increase test coverage to 70% (from 40%)
   - Update pytest.ini fail_under setting
   - Add missing edge case tests

5. **Performance & Memory Optimization (Story 48.5)**
   - Optimize retry queue memory usage (dataclasses)
   - Add monitoring for queue capacity
   - Standardize timezone handling

### Success Criteria

- ✅ All HIGH priority security issues resolved
- ✅ Integration test suite implemented and passing
- ✅ Test coverage ≥70% achieved
- ✅ Error scenarios comprehensively tested
- ✅ Retry queue memory optimized
- ✅ All tests passing in CI/CD pipeline

---

## Stories

### Story 48.1: Security Hardening & Input Validation

**Priority:** High  
**Effort:** 2-3 hours  
**Status:** ✅ **COMPLETE**  
**Story Type:** Security Enhancement

#### Goal

Implement security hardening measures including API endpoint authentication, input validation for InfluxDB bucket names, and Flux query sanitization to address HIGH priority security concerns.

#### Background

Code review identified:
- API endpoints (`/statistics`, `/statistics/reset`) have no authentication or rate limiting
- Flux queries constructed with f-strings without validation
- Bucket names from environment variables not validated

#### Acceptance Criteria

**Functional Requirements:**
- [x] Reset statistics endpoint (`POST /statistics/reset`) requires internal network validation or API key
- [x] Get statistics endpoint (`GET /statistics`) remains publicly accessible (read-only)
- [x] Bucket name format validated (alphanumeric, hyphens, underscores only)
- [x] Invalid bucket names raise ValueError with clear error message
- [x] Service fails fast on startup if bucket name invalid

**Technical Requirements:**
- [x] Add `validate_bucket_name()` function with regex validation
- [x] Add `validate_internal_request()` middleware for reset endpoint
- [x] Update `EnergyCorrelatorService.__init__()` to validate bucket name
- [x] Add unit tests for validation functions
- [x] Error messages are clear and actionable

**Quality Requirements:**
- [x] No breaking changes to existing API contracts
- [x] All existing tests continue to pass
- [x] New security tests added and passing
- [x] Documentation updated with security practices

#### Tasks

1. Implement bucket name validation function
   - Create `validate_bucket_name()` with regex pattern
   - Add unit tests for valid/invalid bucket names
   - Update service initialization to use validation

2. Add internal network validation for reset endpoint
   - Create `validate_internal_request()` middleware
   - Apply to `POST /statistics/reset` endpoint
   - Test with valid/invalid IP addresses

3. Update service configuration
   - Validate bucket name on startup
   - Add clear error messages for invalid configuration

4. Add security tests
   - Test invalid bucket names rejected
   - Test reset endpoint blocks external requests
   - Test statistics endpoint remains accessible

5. Update documentation
   - Document security practices in README.md
   - Add security configuration section

#### File List

- `services/energy-correlator/src/main.py` - Add validation middleware
- `services/energy-correlator/src/correlator.py` - Add bucket validation
- `services/energy-correlator/tests/unit/test_security.py` - New security tests
- `services/energy-correlator/README.md` - Update security documentation

---

### Story 48.2: Integration Test Suite

**Priority:** High  
**Effort:** 4-6 hours  
**Status:** ✅ **COMPLETE**  
**Story Type:** Testing Foundation

#### Goal

Implement comprehensive integration tests for InfluxDB queries, API endpoints, and end-to-end event processing flow as outlined in TEST_PLAN.md but currently missing.

#### Background

Code review identified:
- Test plan outlines integration tests but files don't exist
- Only unit tests currently present
- Missing: InfluxDB query integration, API endpoint integration, E2E event processing

#### Acceptance Criteria

**Functional Requirements:**
- [x] Integration tests for InfluxDB query operations
- [x] Integration tests for API endpoints (`/health`, `/statistics`, `/statistics/reset`)
- [x] End-to-end event processing flow tests
- [x] Tests use testcontainers or mock InfluxDB server
- [x] All integration tests passing in CI/CD

**Technical Requirements:**
- [x] Create `tests/integration/` directory structure
- [x] Implement `test_influxdb_queries.py` with query tests
- [x] Implement `test_api_endpoints.py` with endpoint tests
- [x] Implement `test_event_processing.py` with E2E flow tests
- [x] Use pytest fixtures for test setup/teardown
- [x] Tests are independent and parallel-safe

**Quality Requirements:**
- [x] Tests follow TEST_PLAN.md specifications
- [x] Tests use appropriate test levels (integration vs E2E)
- [x] Test data is self-contained and cleaned up
- [x] Tests document expected behavior clearly

#### Tasks

1. Set up integration test infrastructure
   - Create `tests/integration/` directory
   - Configure testcontainers or mock InfluxDB
   - Create shared fixtures for InfluxDB connection

2. Implement InfluxDB query integration tests
   - Test event query with various filters
   - Test power cache query and windowing
   - Test write operations and batch writes
   - Test error handling for connection failures

3. Implement API endpoint integration tests
   - Test `/health` endpoint response format
   - Test `/statistics` endpoint with various states
   - Test `/statistics/reset` endpoint (with security)
   - Test error responses and status codes

4. Implement end-to-end event processing tests
   - Test complete correlation flow (events → correlations)
   - Test retry queue integration
   - Test batch processing limits
   - Test power cache efficiency

5. Add integration test documentation
   - Document test setup requirements
   - Document how to run integration tests
   - Update TEST_PLAN.md with implementation status

#### File List

- `services/energy-correlator/tests/integration/test_influxdb_queries.py` - New
- `services/energy-correlator/tests/integration/test_api_endpoints.py` - New
- `services/energy-correlator/tests/integration/test_event_processing.py` - New
- `services/energy-correlator/tests/integration/conftest.py` - New (shared fixtures)
- `services/energy-correlator/TEST_PLAN.md` - Update implementation status

---

### Story 48.3: Error Scenario Testing

**Priority:** Medium  
**Effort:** 2-3 hours  
**Status:** 📋 Planning  
**Story Type:** Testing Enhancement

#### Goal

Add comprehensive error scenario tests to ensure robust error handling and graceful degradation under failure conditions.

#### Background

Code review identified:
- Unit tests focus on happy path scenarios
- Missing tests for: connection failures, timeouts, invalid data, retry queue overflow

#### Acceptance Criteria

**Functional Requirements:**
- [ ] Tests for InfluxDB connection failures
- [ ] Tests for query timeouts
- [ ] Tests for invalid data formats
- [ ] Tests for missing power data scenarios
- [ ] Tests for retry queue overflow scenarios
- [ ] Tests for cache lookup failures

**Technical Requirements:**
- [ ] Use pytest.raises() for exception testing
- [ ] Mock InfluxDB client for failure scenarios
- [ ] Test error recovery and retry logic
- [ ] Test error statistics tracking
- [ ] Test graceful degradation

**Quality Requirements:**
- [ ] All error scenarios documented
- [ ] Error messages are clear and actionable
- [ ] Tests verify error handling doesn't crash service
- [ ] Error statistics correctly tracked

#### Tasks

1. Add connection failure tests
   - Test InfluxDB connection refused
   - Test connection timeout
   - Test authentication failures
   - Verify service handles gracefully

2. Add query failure tests
   - Test query timeout scenarios
   - Test malformed query responses
   - Test empty result sets
   - Test invalid data format responses

3. Add data validation tests
   - Test missing required fields
   - Test invalid datetime formats
   - Test invalid power values (None, negative, NaN)
   - Test event deduplication edge cases

4. Add retry queue overflow tests
   - Test queue at maximum capacity
   - Test events dropped when queue full
   - Test queue retention policy enforcement
   - Test old events properly trimmed

5. Add cache failure tests
   - Test cache miss scenarios
   - Test cache lookup with invalid timestamps
   - Test cache with empty power data

#### File List

- `services/energy-correlator/tests/unit/test_error_scenarios.py` - New
- `services/energy-correlator/tests/unit/test_retry_queue.py` - New (extend existing)
- `services/energy-correlator/src/correlator.py` - May need minor error handling improvements

---

### Story 48.4: Test Coverage & Quality Improvements

**Priority:** Medium  
**Effort:** 3-4 hours  
**Status:** 📋 Planning  
**Story Type:** Testing Enhancement

#### Goal

Increase test coverage from 40% to 70% target by adding missing test cases and updating pytest configuration.

#### Background

Code review identified:
- Current coverage target is 40% (below project standard ≥80% target)
- Test plan targets >70% coverage
- Missing edge case coverage

#### Acceptance Criteria

**Functional Requirements:**
- [ ] Test coverage ≥70% achieved
- [ ] All critical paths have test coverage
- [ ] Edge cases comprehensively tested
- [ ] pytest.ini fail_under updated to 70%

**Technical Requirements:**
- [ ] Run coverage report to identify gaps
- [ ] Add missing unit tests for uncovered functions
- [ ] Add edge case tests (boundary conditions)
- [ ] Update pytest.ini coverage settings
- [ ] Coverage report generated in CI/CD

**Quality Requirements:**
- [ ] All new tests are maintainable and readable
- [ ] Test names clearly describe what's being tested
- [ ] Tests follow AAA pattern (Arrange, Act, Assert)
- [ ] No flaky tests

#### Tasks

1. Run coverage analysis
   - Generate coverage report
   - Identify uncovered functions/methods
   - Identify low-coverage areas
   - Document coverage gaps

2. Add missing unit tests
   - Test all public methods in correlator.py
   - Test all helper functions
   - Test configuration validation
   - Test statistics calculations

3. Add edge case tests
   - Test boundary conditions (empty lists, None values)
   - Test configuration limits (min/max values)
   - Test concurrent operations (if applicable)
   - Test memory limits

4. Update pytest configuration
   - Set fail_under = 70 in pytest.ini
   - Verify coverage report generation
   - Update coverage exclusion patterns if needed

5. Verify coverage target met
   - Run full test suite with coverage
   - Verify ≥70% coverage achieved
   - Document coverage improvements

#### File List

- `services/energy-correlator/tests/unit/test_correlator_logic.py` - Extend existing
- `services/energy-correlator/tests/unit/test_statistics.py` - Extend existing
- `services/energy-correlator/tests/unit/test_edge_cases.py` - New
- `services/energy-correlator/pytest.ini` - Update coverage settings

---

### Story 48.5: Performance & Memory Optimization

**Priority:** Medium  
**Effort:** 1-2 hours  
**Status:** ✅ **COMPLETE**  
**Story Type:** Performance Enhancement

#### Goal

Optimize retry queue memory usage, add queue capacity monitoring, and standardize timezone handling for better performance and consistency.

#### Background

Code review identified:
- Retry queue uses dictionaries (can be more memory-efficient)
- No monitoring when queue approaches capacity
- Mixed timezone handling (datetime.utcnow() deprecated)

#### Acceptance Criteria

**Functional Requirements:**
- [x] Retry queue uses dataclasses instead of dictionaries
- [x] Monitoring/logging when queue approaches capacity (≥80%)
- [x] All datetime operations use timezone-aware datetimes
- [x] Replace all datetime.utcnow() calls
- [x] Error retry interval configurable

**Technical Requirements:**
- [x] Create DeferredEvent dataclass
- [x] Update retry queue to use dataclasses
- [x] Add queue capacity monitoring
- [x] Standardize on datetime.now(timezone.utc)
- [x] Add ERROR_RETRY_INTERVAL environment variable

**Quality Requirements:**
- [x] Memory usage improved (measurable)
- [x] No breaking changes to existing functionality
- [x] All tests continue to pass
- [x] Code is more maintainable

#### Tasks

1. Create DeferredEvent dataclass
   - Define dataclass with required fields
   - Add to_dict() method for compatibility
   - Add unit tests for dataclass

2. Update retry queue to use dataclasses
   - Replace dictionary usage with DeferredEvent
   - Update merge and trim functions
   - Verify compatibility with existing code

3. Add queue capacity monitoring
   - Log warning when queue ≥80% capacity
   - Add queue size to statistics endpoint
   - Test monitoring triggers correctly

4. Standardize timezone handling
   - Replace datetime.utcnow() with datetime.now(timezone.utc)
   - Update all datetime operations
   - Test timezone handling correctness

5. Make error retry interval configurable
   - Add ERROR_RETRY_INTERVAL environment variable
   - Update default to use configuration
   - Update documentation

#### File List

- `services/energy-correlator/src/correlator.py` - Update retry queue, timezone handling
- `services/energy-correlator/src/main.py` - Add error retry interval config
- `services/energy-correlator/tests/unit/test_retry_queue.py` - Update for dataclasses
- `services/energy-correlator/README.md` - Update configuration documentation

---

## Timeline

**Estimated Duration:** 14-18 hours (2-3 days)

**Phase 1: Security (Story 48.1)** - 2-3 hours
- Immediate security hardening

**Phase 2: Testing Foundation (Story 48.2)** - 4-6 hours
- Integration test suite implementation

**Phase 3: Testing Enhancement (Stories 48.3, 48.4)** - 5-7 hours
- Error scenarios and coverage improvements

**Phase 4: Optimization (Story 48.5)** - 1-2 hours
- Performance and memory improvements

---

## Risk Mitigation

### Primary Risks

**Risk 1: Integration test setup complexity**
- **Mitigation:** Use testcontainers or mock InfluxDB (simpler setup)
- **Rollback:** Skip integration tests if setup too complex (document for future)

**Risk 2: Test coverage target not achievable**
- **Mitigation:** Focus on critical paths first, document acceptable gaps
- **Rollback:** Set realistic target (65% minimum, 70% stretch goal)

**Risk 3: Breaking changes during optimization**
- **Mitigation:** Comprehensive test coverage before optimization
- **Rollback:** Revert dataclass changes if compatibility issues

---

## Definition of Done

- [ ] All 5 stories completed with acceptance criteria met
- [ ] All HIGH priority security issues resolved
- [ ] Integration test suite implemented and passing
- [ ] Test coverage ≥70% achieved
- [ ] All error scenarios tested
- [ ] Performance optimizations implemented
- [ ] All tests passing in CI/CD pipeline
- [ ] Documentation updated
- [ ] Code review findings addressed (HIGH and MEDIUM priorities)
- [ ] No regression in existing functionality

---

## References

- **Code Review:** `docs/qa/code-review-energy-correlator-2025.md`
- **Test Plan:** `services/energy-correlator/TEST_PLAN.md`
- **Service README:** `services/energy-correlator/README.md`
- **Code Review Guide:** `docs/architecture/code-review-guide-2025.md`
- **Epic 31 Architecture:** `.cursor/rules/epic-31-architecture.mdc`

---

**Epic Created:** December 2025  
**Last Updated:** December 2025  
**Status:** 📋 Planning


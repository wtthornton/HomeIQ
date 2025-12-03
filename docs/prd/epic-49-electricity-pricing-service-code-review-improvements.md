# Epic 49: Electricity Pricing Service Code Review Improvements

**Status:** 📋 **PLANNING**  
**Type:** Quality & Security Enhancement  
**Priority:** High  
**Effort:** 6 Stories (12-16 hours estimated)  
**Created:** December 2025  
**Target Completion:** December 2025  
**Related:** Code Review - `docs/qa/code-review-electricity-pricing-service-2025.md`

---

## Epic Goal

Address critical security, testing, and performance improvements identified in the comprehensive 2025 code review of the electricity-pricing-service. This epic enhances production readiness by implementing security hardening, comprehensive test coverage, performance optimizations, and batch write improvements while maintaining the service's excellent architectural patterns.

**Value:** High - Addresses security vulnerabilities, improves reliability through comprehensive testing, and optimizes performance with batch writes.

**Complexity:** Medium - Focused improvements to existing working service with well-defined scope.

---

## Existing System Context

### Current Service Status

**Service:** electricity-pricing-service (Port 8011)  
**Status:** ✅ Production Ready (with concerns identified)  
**Quality Score:** 75/100  
**Code Review Date:** December 2025

### Current Strengths

- ✅ Epic 31 architecture compliance (direct InfluxDB writes)
- ✅ Async-first design with proper HTTP client usage
- ✅ Provider abstraction pattern (easy to extend)
- ✅ Smart caching with graceful fallback
- ✅ Clean separation of concerns

### Code Review Findings

**11 Issues Identified:**
- 1 HIGH: API endpoint input validation
- 6 MEDIUM: Authentication, batch writes, integration tests, error scenarios, test coverage, provider tests
- 4 LOW: Timezone handling, type hints (deferred to future epic)

**Review Reference:** `docs/qa/code-review-electricity-pricing-service-2025.md`

---

## Enhancement Details

### High Priority Improvements

1. **Security Hardening (Story 49.1)**
   - Add API endpoint input validation
   - Validate query parameter bounds
   - Add basic authentication or network restrictions

2. **Performance Optimization (Story 49.2)**
   - Implement batch InfluxDB writes
   - Wrap synchronous writes in async context

### Medium Priority Improvements

3. **Integration Test Suite (Story 49.3)**
   - Implement InfluxDB write integration tests
   - Add API endpoint integration tests
   - Test provider integration

4. **Error Scenario Testing (Story 49.4)**
   - Test provider API failures
   - Test InfluxDB connection failures
   - Test network timeouts
   - Test cache expiration

5. **Test Coverage & Quality (Story 49.5)**
   - Increase test coverage to 70% (from 50%)
   - Update pytest.ini fail_under setting
   - Add missing edge case tests

6. **Provider-Specific Testing (Story 49.6)**
   - Add Awattar provider parsing tests
   - Test price calculation logic
   - Test forecast building

### Success Criteria

- ✅ All HIGH priority security issues resolved
- ✅ Batch writes implemented for performance
- ✅ Integration test suite implemented and passing
- ✅ Test coverage ≥70% achieved
- ✅ Error scenarios comprehensively tested
- ✅ Provider-specific tests implemented
- ✅ All tests passing in CI/CD pipeline

---

## Stories

### Story 49.1: Security Hardening & Input Validation

**Priority:** High  
**Effort:** 2-3 hours  
**Status:** 📋 Planning  
**Story Type:** Security Enhancement

#### Goal

Implement security hardening measures including API endpoint input validation, query parameter bounds checking, and basic authentication to address HIGH priority security concerns.

#### Background

Code review identified:
- API endpoint `/cheapest-hours` has no input validation
- Query parameter `hours` directly converted to int without bounds checking
- No authentication/authorization on endpoints

#### Acceptance Criteria

**Functional Requirements:**
- [ ] `/cheapest-hours` endpoint validates `hours` parameter (1-24 range)
- [ ] Invalid `hours` parameter returns 400 error with clear message
- [ ] Non-integer `hours` parameter handled gracefully
- [ ] Endpoints have basic authentication or network restrictions
- [ ] Health endpoint remains publicly accessible (read-only)

**Technical Requirements:**
- [ ] Add input validation for `hours` query parameter
- [ ] Add bounds checking (1-24 hours)
- [ ] Add error handling for invalid parameter types
- [ ] Add authentication middleware or network restrictions
- [ ] Add unit tests for validation logic

**Quality Requirements:**
- [ ] No breaking changes to existing API contracts
- [ ] All existing tests continue to pass
- [ ] New security tests added and passing
- [ ] Error messages are clear and actionable

#### Tasks

1. Add input validation for `/cheapest-hours` endpoint
   - Validate `hours` parameter is integer
   - Check bounds (1-24 hours)
   - Return appropriate error responses

2. Add authentication or network restrictions
   - Implement basic API key or network-based validation
   - Apply to write/sensitive endpoints only
   - Keep health endpoint publicly accessible

3. Add validation tests
   - Test invalid parameter types
   - Test out-of-bounds values
   - Test authentication failures

4. Update documentation
   - Document security practices in README.md
   - Add authentication configuration section

#### File List

- `services/electricity-pricing-service/src/main.py` - Add validation and auth
- `services/electricity-pricing-service/tests/unit/test_security.py` - New security tests
- `services/electricity-pricing-service/README.md` - Update security documentation

---

### Story 49.2: Performance Optimization - Batch Writes

**Priority:** High  
**Effort:** 1-2 hours  
**Status:** 📋 Planning  
**Story Type:** Performance Enhancement

#### Goal

Implement batch InfluxDB writes for forecast data and wrap synchronous writes in async context to improve performance and follow async best practices.

#### Background

Code review identified:
- Forecast data written individually in loop (24+ writes)
- InfluxDB client `write()` called synchronously in async function
- Should batch writes and use async context

#### Acceptance Criteria

**Functional Requirements:**
- [ ] All InfluxDB writes use batch operations
- [ ] Current pricing and forecast written in single batch
- [ ] Writes wrapped in async context (asyncio.to_thread)
- [ ] No performance regression

**Technical Requirements:**
- [ ] Collect all points before writing
- [ ] Use single batch write operation
- [ ] Wrap synchronous writes in asyncio.to_thread()
- [ ] Maintain backward compatibility

**Quality Requirements:**
- [ ] All existing tests continue to pass
- [ ] Performance improvement measurable
- [ ] Error handling preserved

#### Tasks

1. Refactor write operations to batch
   - Collect current pricing and forecast points
   - Use single batch write call
   - Verify batch write syntax

2. Wrap writes in async context
   - Use asyncio.to_thread() for synchronous writes
   - Test async write behavior

3. Add batch write tests
   - Test batch write success
   - Test batch write with errors
   - Verify all points written

#### File List

- `services/electricity-pricing-service/src/main.py` - Update store_in_influxdb()
- `services/electricity-pricing-service/tests/unit/test_influxdb_storage.py` - Add batch write tests

---

### Story 49.3: Integration Test Suite

**Priority:** Medium  
**Effort:** 3-4 hours  
**Status:** 📋 Planning  
**Story Type:** Testing Foundation

#### Goal

Implement comprehensive integration tests for InfluxDB writes, API endpoints, and provider integration as outlined in pytest.ini markers but currently missing.

#### Background

Code review identified:
- Only unit tests exist
- Missing integration tests for:
  - InfluxDB write operations
  - API endpoint integration
  - Provider API integration
  - End-to-end data flow

#### Acceptance Criteria

**Functional Requirements:**
- [ ] Integration tests for InfluxDB write operations
- [ ] Integration tests for API endpoints
- [ ] Integration tests for provider API calls
- [ ] Tests use testcontainers or mock InfluxDB
- [ ] All integration tests passing

**Technical Requirements:**
- [ ] Create `tests/integration/` directory
- [ ] Implement `test_influxdb_writes.py`
- [ ] Implement `test_api_endpoints.py`
- [ ] Implement `test_provider_integration.py`
- [ ] Use pytest fixtures for setup/teardown

**Quality Requirements:**
- [ ] Tests are independent and parallel-safe
- [ ] Tests document expected behavior
- [ ] Test data is self-contained

#### Tasks

1. Set up integration test infrastructure
   - Create `tests/integration/` directory
   - Configure testcontainers or mock InfluxDB
   - Create shared fixtures

2. Implement InfluxDB write integration tests
   - Test batch write operations
   - Test write with various data formats
   - Test error handling

3. Implement API endpoint integration tests
   - Test `/health` endpoint
   - Test `/cheapest-hours` endpoint
   - Test error responses

4. Implement provider integration tests
   - Test Awattar API integration
   - Test response parsing
   - Test error scenarios

5. Add integration test documentation
   - Document test setup requirements
   - Document how to run integration tests

#### File List

- `services/electricity-pricing-service/tests/integration/test_influxdb_writes.py` - New
- `services/electricity-pricing-service/tests/integration/test_api_endpoints.py` - New
- `services/electricity-pricing-service/tests/integration/test_provider_integration.py` - New
- `services/electricity-pricing-service/tests/integration/conftest.py` - New (shared fixtures)

---

### Story 49.4: Error Scenario Testing

**Priority:** Medium  
**Effort:** 2-3 hours  
**Status:** 📋 Planning  
**Story Type:** Testing Enhancement

#### Goal

Add comprehensive error scenario tests to ensure robust error handling and graceful degradation under failure conditions.

#### Background

Code review identified:
- Unit tests focus on happy path scenarios
- Missing tests for:
  - Provider API failures
  - InfluxDB connection failures
  - Invalid API responses
  - Network timeouts
  - Cache expiration

#### Acceptance Criteria

**Functional Requirements:**
- [ ] Tests for provider API failures
- [ ] Tests for InfluxDB connection failures
- [ ] Tests for invalid API responses
- [ ] Tests for network timeouts
- [ ] Tests for cache expiration scenarios

**Technical Requirements:**
- [ ] Use pytest.raises() for exception testing
- [ ] Mock external dependencies for failure scenarios
- [ ] Test error recovery and fallback logic
- [ ] Test error statistics tracking

**Quality Requirements:**
- [ ] All error scenarios documented
- [ ] Error messages are clear and actionable
- [ ] Tests verify graceful degradation

#### Tasks

1. Add provider API failure tests
   - Test API connection failures
   - Test invalid response formats
   - Test timeout scenarios
   - Verify cached data fallback

2. Add InfluxDB failure tests
   - Test connection failures
   - Test write failures
   - Test error recovery

3. Add network timeout tests
   - Test HTTP timeout scenarios
   - Test connection timeout
   - Verify error handling

4. Add cache expiration tests
   - Test cache expiration logic
   - Test stale cache handling

#### File List

- `services/electricity-pricing-service/tests/unit/test_error_scenarios.py` - New
- `services/electricity-pricing-service/tests/unit/test_pricing_service.py` - Extend existing

---

### Story 49.5: Test Coverage & Quality Improvements

**Priority:** Medium  
**Effort:** 2-3 hours  
**Status:** 📋 Planning  
**Story Type:** Testing Enhancement

#### Goal

Increase test coverage from 50% to 70% target by adding missing test cases and updating pytest configuration.

#### Background

Code review identified:
- Current coverage target is 50% (below project standard ≥80% target)
- Service has good unit test coverage but missing integration tests
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

3. Update pytest configuration
   - Set fail_under = 70 in pytest.ini
   - Verify coverage report generation

4. Verify coverage target met
   - Run full test suite with coverage
   - Verify ≥70% coverage achieved
   - Document coverage improvements

#### File List

- `services/electricity-pricing-service/tests/unit/test_pricing_service.py` - Extend existing
- `services/electricity-pricing-service/tests/unit/test_edge_cases.py` - New
- `services/electricity-pricing-service/pytest.ini` - Update coverage settings

---

### Story 49.6: Provider-Specific Testing

**Priority:** Medium  
**Effort:** 1-2 hours  
**Status:** 📋 Planning  
**Story Type:** Testing Enhancement

#### Goal

Add comprehensive tests for AwattarProvider parsing logic, price calculations, and forecast building to ensure provider reliability.

#### Background

Code review identified:
- No tests for AwattarProvider parsing logic
- Provider-specific tests should cover:
  - API response parsing
  - Price calculation (marketprice / 10000)
  - Forecast building logic
  - Cheapest hours calculation

#### Acceptance Criteria

**Functional Requirements:**
- [ ] Tests for API response parsing
- [ ] Tests for price calculation logic
- [ ] Tests for forecast building
- [ ] Tests for cheapest hours calculation
- [ ] Tests for edge cases (empty data, invalid formats)

**Technical Requirements:**
- [ ] Create `tests/unit/test_awattar_provider.py`
- [ ] Mock Awattar API responses
- [ ] Test parsing with various data formats
- [ ] Test error handling

**Quality Requirements:**
- [ ] Tests are maintainable and readable
- [ ] Tests document expected behavior
- [ ] Edge cases covered

#### Tasks

1. Create provider test file
   - Create `tests/unit/test_awattar_provider.py`
   - Set up test fixtures for API responses

2. Add parsing tests
   - Test valid API response parsing
   - Test price calculation (marketprice / 10000)
   - Test forecast building logic

3. Add calculation tests
   - Test cheapest hours calculation
   - Test most expensive hours calculation
   - Test peak period detection

4. Add error scenario tests
   - Test empty data handling
   - Test invalid response formats
   - Test missing fields

#### File List

- `services/electricity-pricing-service/tests/unit/test_awattar_provider.py` - New
- `services/electricity-pricing-service/tests/conftest.py` - Add provider fixtures

---

## Timeline

**Estimated Duration:** 12-16 hours (2-3 days)

**Phase 1: Security & Performance (Stories 49.1, 49.2)** - 3-5 hours
- Immediate security hardening and performance optimization

**Phase 2: Testing Foundation (Story 49.3)** - 3-4 hours
- Integration test suite implementation

**Phase 3: Testing Enhancement (Stories 49.4, 49.5, 49.6)** - 5-7 hours
- Error scenarios, coverage improvements, provider tests

---

## Risk Mitigation

### Primary Risks

**Risk 1: Integration test setup complexity**
- **Mitigation:** Use testcontainers or mock InfluxDB (simpler setup)
- **Rollback:** Skip integration tests if setup too complex (document for future)

**Risk 2: Test coverage target not achievable**
- **Mitigation:** Focus on critical paths first, document acceptable gaps
- **Rollback:** Set realistic target (65% minimum, 70% stretch goal)

**Risk 3: Batch write breaking changes**
- **Mitigation:** Comprehensive test coverage before optimization
- **Rollback:** Revert to individual writes if compatibility issues

---

## Definition of Done

- [ ] All 6 stories completed with acceptance criteria met
- [ ] All HIGH priority security issues resolved
- [ ] Batch writes implemented for performance
- [ ] Integration test suite implemented and passing
- [ ] Test coverage ≥70% achieved
- [ ] All error scenarios tested
- [ ] Provider-specific tests implemented
- [ ] All tests passing in CI/CD pipeline
- [ ] Documentation updated
- [ ] Code review findings addressed (HIGH and MEDIUM priorities)
- [ ] No regression in existing functionality

---

## References

- **Code Review:** `docs/qa/code-review-electricity-pricing-service-2025.md`
- **Service README:** `services/electricity-pricing-service/README.md`
- **Code Review Guide:** `docs/architecture/code-review-guide-2025.md`
- **Epic 31 Architecture:** `.cursor/rules/epic-31-architecture.mdc`
- **Similar Epic:** `docs/prd/epic-48-energy-correlator-code-review-improvements.md`

---

**Epic Created:** December 2025  
**Last Updated:** December 2025  
**Status:** 📋 Planning


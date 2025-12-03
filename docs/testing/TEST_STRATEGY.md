# HomeIQ Test Strategy

**Last Updated:** December 3, 2025  
**Status:** Active

---

## Overview

This document outlines the testing strategy for HomeIQ, including test types, coverage goals, and execution procedures.

---

## Test Pyramid

```
        /\
       /  \      E2E Tests (5%)
      /____\     - Full user journeys
     /      \    - Critical workflows
    /________\   Integration Tests (15%)
   /          \  - Service interactions
  /____________\ Unit Tests (80%)
                 - Fast, isolated tests
```

---

## Test Types

### 1. Unit Tests (80% of tests)

**Purpose:** Test individual functions and classes in isolation.

**Location:** `services/*/tests/test_*.py`

**Characteristics:**
- Fast execution (< 1 second per test)
- No external dependencies
- High code coverage (target: 80%+)
- Mock external services

**Example:**
```python
def test_sanitize_flux_value():
    assert sanitize_flux_value("test") == "test"
    assert sanitize_flux_value("test'; DROP--") == "test DROP"
```

**Coverage Target:** 80%+ for critical services

---

### 2. Integration Tests (15% of tests)

**Purpose:** Test service interactions and data flow.

**Location:** `tests/integration/`

**Characteristics:**
- May require external services (InfluxDB, Home Assistant)
- Test service-to-service communication
- Verify data transformations
- Use test containers when possible

**Example:**
```python
def test_event_ingestion_to_influxdb():
    # Send event via websocket-ingestion
    # Verify it appears in InfluxDB
    # Query via data-api
```

**Coverage Target:** Critical paths only

---

### 3. Smoke Tests (5% of tests)

**Purpose:** Verify critical production paths work end-to-end.

**Location:** `tests/test_smoke_critical_paths.py`, `tests/smoke_tests.py`

**Characteristics:**
- Test critical user-facing functionality
- Run before every deployment
- Fast execution (< 2 minutes total)
- Must pass for production deployment

**Critical Paths:**
1. Health checks for all services
2. Event ingestion → InfluxDB → data-api query
3. Authentication on protected endpoints
4. Dashboard accessibility
5. API endpoint responses

**Execution:**
```bash
# Run smoke tests
python tests/smoke_tests.py

# Or with pytest
pytest tests/test_smoke_critical_paths.py -v
```

---

## Test Infrastructure

### Pytest Configuration

**Root:** `pytest-unit.ini`

**Service-level:** `services/*/pytest.ini`

**Key Settings:**
- Coverage reporting enabled
- Async test support (pytest-asyncio)
- Test markers for categorization
- Coverage fail-under: 70%

### Test Runners

1. **Simple Unit Test Runner:** `scripts/simple-unit-tests.py`
   - Visual progress indicators
   - Coverage reporting
   - Python and TypeScript support

2. **Smoke Test Runner:** `tests/smoke_tests.py`
   - Service health checks
   - Critical path verification
   - JSON/text output

3. **Pytest:** Standard pytest execution
   ```bash
   pytest services/data-api/tests/ -v --cov=src
   ```

---

## Coverage Goals

### Critical Services (80%+ coverage required)

- `websocket-ingestion` - Event ingestion pipeline
- `data-api` - Data query endpoints
- `ai-automation-service` - AI automation logic
- `admin-api` - System administration

### Standard Services (70%+ coverage required)

- All other services

### Coverage Reporting

**Location:** `test-results/coverage/`

**Formats:**
- HTML: `test-results/coverage/python/index.html`
- XML: `test-results/coverage/python/coverage.xml`
- Terminal: Missing lines shown

**View Coverage:**
```bash
# Open HTML report
open test-results/coverage/python/index.html
```

---

## Test Markers

### Standard Markers

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.smoke` - Smoke tests
- `@pytest.mark.slow` - Slow tests (> 1 second)
- `@pytest.mark.asyncio` - Async tests

### Service-Specific Markers

- `@pytest.mark.requires_ha` - Requires Home Assistant
- `@pytest.mark.requires_openai` - Requires OpenAI API
- `@pytest.mark.requires_db` - Requires database
- `@pytest.mark.requires_influxdb` - Requires InfluxDB

### Running Tests by Marker

```bash
# Run only unit tests
pytest -m unit

# Run only smoke tests
pytest -m smoke

# Skip slow tests
pytest -m "not slow"
```

---

## Security Tests

**Location:** 
- `services/data-api/tests/test_flux_security.py`
- `services/ai-code-executor/tests/test_sandbox_security.py`
- `services/ai-automation-service/tests/test_authentication.py`

**Coverage:**
- SQL/Flux injection prevention
- Authentication enforcement
- Sandbox isolation
- Input validation

**Execution:**
```bash
pytest services/*/tests/test_*security*.py -v
```

---

## CI/CD Integration

### Pre-commit

- Run unit tests for changed files
- Check code quality (ruff, mypy)
- Verify no critical test failures

### Pre-deployment

- Run full smoke test suite
- Verify all critical services healthy
- Check coverage thresholds

### Post-deployment

- Run smoke tests against production
- Monitor service health
- Verify critical paths

---

## Test Data Management

### Test Fixtures

**Location:** `services/*/tests/fixtures/`

**Guidelines:**
- Use minimal, representative data
- Generate data programmatically when possible
- Clean up after tests

### Test Databases

- Use separate test databases
- Reset between test runs
- Use transactions for isolation

---

## Best Practices

### 1. Test Naming

```python
def test_function_name_condition_expected_result():
    """Test that function_name handles condition and returns expected_result."""
    pass
```

### 2. Test Organization

- One test class per module
- Group related tests together
- Use fixtures for common setup

### 3. Test Independence

- Tests should not depend on each other
- Use fixtures for shared state
- Clean up after each test

### 4. Mock External Services

- Mock HTTP requests
- Mock database calls
- Mock file system operations

### 5. Test Documentation

- Document test purpose
- Explain complex test logic
- Note any assumptions

---

## Troubleshooting

### Tests Failing Intermittently

- Check for race conditions
- Verify test isolation
- Check for shared state

### Slow Tests

- Profile test execution
- Identify slow operations
- Use mocks for external calls

### Coverage Gaps

- Review coverage reports
- Add tests for uncovered code
- Focus on critical paths first

---

## Metrics and Reporting

### Test Metrics

- Total tests: Track over time
- Pass rate: Target 95%+
- Coverage: Track by service
- Execution time: Monitor for regressions

### Reporting

- Coverage reports: HTML + XML
- Test results: JSON + text
- CI/CD integration: Automated reporting

---

## Future Improvements

1. **Performance Tests:** Add performance benchmarks
2. **Load Tests:** Test under load conditions
3. **Chaos Tests:** Test failure scenarios
4. **Mutation Testing:** Verify test quality
5. **Property-Based Testing:** Test edge cases

---

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Test Strategy Best Practices](https://martinfowler.com/articles/practical-test-pyramid.html)

---

**Maintainer:** Development Team  
**Review Frequency:** Quarterly


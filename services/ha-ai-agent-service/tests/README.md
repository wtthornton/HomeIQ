# HA AI Agent Service - Test Documentation

**Epic AI-20 Story AI20.11: Comprehensive Testing**

This directory contains comprehensive tests for the HA AI Agent Service, including unit tests, integration tests, end-to-end tests, and performance tests.

## Test Structure

```
tests/
├── __init__.py
├── README.md                          # This file
├── integration/                       # Integration and E2E tests
│   ├── __init__.py
│   ├── test_context_integration.py   # Context builder integration tests
│   └── test_chat_flow_e2e.py         # End-to-end chat flow tests
├── test_*.py                          # Unit and integration tests for services
├── test_chat_performance.py          # Chat endpoint performance tests
└── test_performance.py               # Context building performance tests
```

## Test Categories

### Unit Tests

Unit tests test individual components in isolation with mocked dependencies.

**Coverage Target:** >90% for all services

**Test Files:**
- `test_openai_client.py` - OpenAI client wrapper tests
- `test_conversation_service.py` - Conversation management tests
- `test_prompt_assembly_service.py` - Prompt assembly tests
- `test_tool_service.py` - Tool execution tests
- `test_context_builder.py` - Context builder tests
- `test_ha_client.py` - Home Assistant client tests
- `test_data_api_client.py` - Data API client tests
- `test_device_intelligence_client.py` - Device Intelligence client tests
- `test_entity_inventory_service.py` - Entity inventory service tests
- `test_areas_service.py` - Areas service tests
- `test_services_summary_service.py` - Services summary tests
- `test_capability_patterns_service.py` - Capability patterns tests
- `test_helpers_scenes_service.py` - Helpers & scenes service tests

**Run Unit Tests:**
```bash
pytest tests/ -m "not integration" -v
```

### Integration Tests

Integration tests test components working together with mocked external services.

**Test Files:**
- `test_chat_endpoints.py` - Chat API endpoint tests
- `test_conversation_endpoints.py` - Conversation management API tests
- `test_main.py` - Service initialization tests
- `integration/test_context_integration.py` - Context builder integration tests

**Run Integration Tests:**
```bash
pytest tests/ -m "not integration" -v  # API endpoint tests
pytest tests/integration/ -v            # Full integration tests
```

### End-to-End Tests

End-to-end tests test complete user workflows from API request to response.

**Test Files:**
- `integration/test_chat_flow_e2e.py` - Complete chat flow tests

**E2E Test Scenarios:**
- Simple message flow
- Chat with tool calls
- Multi-turn conversations
- Automation creation via chat
- Error handling
- Conversation persistence
- Context refresh

**Run E2E Tests:**
```bash
pytest tests/integration/test_chat_flow_e2e.py -v
```

### Performance Tests

Performance tests verify that the service meets performance requirements.

**Test Files:**
- `test_performance.py` - Context building performance tests
- `test_chat_performance.py` - Chat endpoint performance tests

**Performance Targets:**
- Chat response time: <3 seconds
- Concurrent users: 10+ simultaneous requests
- Context building: <100ms (cached), <500ms (first call)
- System prompt retrieval: <10ms

**Run Performance Tests:**
```bash
pytest tests/test_performance.py -v
pytest tests/test_chat_performance.py -v
```

## Running Tests

### Run All Tests

```bash
# From service directory
cd services/ha-ai-agent-service
pytest tests/ -v
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/ -m "not integration" -v

# Integration tests only
pytest tests/integration/ -v

# E2E tests only
pytest tests/integration/test_chat_flow_e2e.py -v

# Performance tests only
pytest tests/test_performance.py tests/test_chat_performance.py -v
```

### Run Specific Test File

```bash
pytest tests/test_openai_client.py -v
```

### Run Specific Test Function

```bash
pytest tests/test_openai_client.py::test_chat_completion_success -v
```

### Run Tests with Coverage

```bash
# HTML coverage report
pytest tests/ --cov=src --cov-report=html

# Terminal coverage report
pytest tests/ --cov=src --cov-report=term-missing

# XML coverage report (for CI)
pytest tests/ --cov=src --cov-report=xml
```

### Run Tests with Verbose Output

```bash
pytest tests/ -v -s  # -s shows print statements
```

## Test Dependencies

### Required Packages

All test dependencies are included in `requirements.txt`:
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking support
- `httpx` - HTTP client for async tests
- `unittest.mock` - Mocking utilities

### External Service Mocks

All external services are mocked in tests:
- OpenAI API - Mocked OpenAI client responses
- Home Assistant API - Mocked HA client responses
- Data API - Mocked Data API client responses
- Device Intelligence Service - Mocked device intelligence responses
- SQLite Database - In-memory database for tests

## Mocking Strategies

### OpenAI Client Mocking

```python
from unittest.mock import AsyncMock, MagicMock

mock_openai_client = MagicMock(spec=OpenAIClient)
mock_openai_client.chat_completion = AsyncMock(
    return_value=mock_completion_response
)
```

### FastAPI Test Client

```python
from httpx import AsyncClient
from src.main import app

async with AsyncClient(app=app, base_url="http://test") as client:
    response = await client.post("/api/v1/chat", json={...})
```

### Service Dependency Injection

```python
from src.api.dependencies import set_services

set_services(
    settings=settings,
    context_builder=mock_context_builder,
    conversation_service=mock_conversation_service,
    # ... other services
)
```

## Test Data and Fixtures

### Common Fixtures

- `settings` - Test configuration settings
- `mock_context_builder` - Mocked context builder
- `mock_openai_client` - Mocked OpenAI client
- `mock_tool_service` - Mocked tool service
- `conversation_service` - Real conversation service instance
- `test_client` - FastAPI async test client

### Test Data Files

Test data is generated programmatically in fixtures. No external test data files are required.

## Continuous Integration

### CI Test Command

```bash
# Run all tests with coverage
pytest tests/ \
    --cov=src \
    --cov-report=xml \
    --cov-report=term-missing \
    --junitxml=junit.xml \
    -v
```

### Coverage Requirements

- **Minimum Coverage:** 90% for all services
- **Coverage Reporting:** XML format for CI integration
- **Coverage Threshold:** Fail build if coverage drops below 90%

## Writing New Tests

### Unit Test Template

```python
"""
Unit tests for [Service Name]
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.example_service import ExampleService


@pytest.fixture
def example_service():
    """Create service instance"""
    return ExampleService(...)


@pytest.mark.asyncio
async def test_service_method(example_service):
    """Test service method"""
    result = await example_service.method()
    assert result is not None
```

### Integration Test Template

```python
"""
Integration tests for [Feature]
"""

import pytest
from httpx import AsyncClient
from src.main import app


@pytest.fixture
async def test_client():
    """Create test client"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_feature_endpoint(test_client):
    """Test feature endpoint"""
    response = await test_client.post("/api/v1/feature", json={...})
    assert response.status_code == 200
```

### Performance Test Template

```python
"""
Performance tests for [Feature]
"""

import pytest
import time


@pytest.mark.asyncio
async def test_feature_performance(test_client):
    """Test feature performance"""
    start_time = time.perf_counter()
    response = await test_client.post("/api/v1/feature", json={...})
    elapsed_time = time.perf_counter() - start_time
    
    assert response.status_code == 200
    assert elapsed_time < 3.0, f"Feature took {elapsed_time:.2f}s, expected <3.0s"
```

## Test Best Practices

### 1. Test Isolation

- Each test should be independent
- Use fixtures to set up and tear down test data
- Mock external dependencies

### 2. Test Naming

- Use descriptive test names: `test_service_method_scenario`
- Follow pattern: `test_[what]_[condition]_[expected_result]`

### 3. Test Organization

- Group related tests in the same file
- Use test classes for logical grouping (optional)
- Keep test files focused on one component

### 4. Async Testing

- Always use `@pytest.mark.asyncio` for async tests
- Use `AsyncMock` for async function mocks
- Use `AsyncClient` for async HTTP requests

### 5. Assertions

- Use specific assertions: `assert response.status_code == 200`
- Include helpful error messages: `assert elapsed_time < 3.0, f"Took {elapsed_time:.2f}s"`
- Test both success and error scenarios

### 6. Performance Tests

- Set realistic performance targets
- Use `time.perf_counter()` for accurate timing
- Account for network latency in mocked responses
- Test both single requests and concurrent load

## Troubleshooting

### Tests Hanging

If tests hang, check:
- Async fixtures are properly closed
- Mock async functions return properly
- Database connections are closed
- Event loops are properly managed

### Import Errors

If you get import errors:
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify Python path includes service directory
- Check for circular imports

### Mock Issues

If mocks aren't working:
- Verify mock is applied before the code under test runs
- Check that async mocks use `AsyncMock`
- Ensure mock spec matches the real object

## Test Coverage Report

View coverage report after running tests:

```bash
# Generate HTML report
pytest tests/ --cov=src --cov-report=html

# Open in browser
open htmlcov/index.html
```

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [Python Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)


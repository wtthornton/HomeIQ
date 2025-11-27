# AI Automation Service Tests

Epic 39, Story 39.12: Query & Automation Service Testing

## Test Structure

```
tests/
├── conftest.py                    # Pytest fixtures and configuration
├── test_health_router.py         # Health endpoint tests (to be created)
├── test_suggestion_router.py     # Suggestion generation tests (to be created)
├── test_deployment_router.py     # Deployment endpoint tests (to be created)
├── test_yaml_generation.py       # YAML generation tests (to be created)
└── test_performance.py           # Performance tests (to be created)
```

## Running Tests

### All Tests
```bash
cd services/ai-automation-service-new
pytest
```

### With Coverage
```bash
pytest --cov=src --cov-report=html
```

### Specific Test Categories
```bash
# Unit tests only
pytest -m unit

# Integration tests
pytest -m integration

# Deployment tests
pytest -m deployment

# YAML generation tests
pytest -m yaml

# Performance tests
pytest -m performance
```

## Test Coverage Goals

- **Unit Tests**: >80% coverage for core modules
- **Integration Tests**: All critical paths
- **Deployment Tests**: All deployment scenarios
- **YAML Generation Tests**: All generation paths validated

## Test Fixtures

### Database Fixtures
- `test_db` - In-memory SQLite database session (fresh for each test)

### Sample Data Fixtures
- `sample_suggestion_data` - Sample suggestion dictionary
- `sample_yaml_content` - Sample automation YAML

### Mock Fixtures
- `mock_ha_client` - Mock Home Assistant client
- `mock_openai_client` - Mock OpenAI client for YAML generation

## Notes

- Tests use in-memory SQLite for isolation
- Suggestion and Deployment router tests will be added after routers are created
- YAML generation tests will validate YAML syntax and structure
- Deployment tests will verify HA integration

## Status

- ✅ Test infrastructure created
- ⏳ Tests to be added as routers are implemented


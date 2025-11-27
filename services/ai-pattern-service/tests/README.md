# Pattern Service Tests

Epic 39, Story 39.8: Pattern Service Testing & Validation

## Test Structure

### Unit Tests
- `test_health_router.py` - Health endpoint tests
- `test_crud_patterns.py` - Pattern CRUD operation tests
- `test_crud_synergies.py` - Synergy CRUD operation tests
- `test_pattern_analyzer.py` - Pattern analyzer module tests
- `test_learning.py` - Learning and quality scoring tests
- `test_clients.py` - Client module tests

### Integration Tests
- `test_scheduler.py` - Scheduler functionality tests

## Running Tests

### Run all tests
```bash
cd services/ai-pattern-service
pytest
```

### Run specific test categories
```bash
# Unit tests only
pytest -m unit

# Integration tests
pytest -m integration

# Scheduler tests
pytest -m scheduler

# Async tests
pytest -m asyncio
```

### Run with coverage
```bash
pytest --cov=src --cov-report=html
```

## Test Fixtures

### Database Fixtures
- `test_db` - In-memory SQLite database session (fresh for each test)

### Sample Data Fixtures
- `sample_pattern_data` - Sample pattern dictionary
- `sample_synergy_data` - Sample synergy dictionary

### Mock Fixtures
- `mock_data_api_client` - Mock DataAPIClient with sample data
- `mock_mqtt_client` - Mock MQTTNotificationClient

## Test Coverage Goals

- **Unit Tests**: >80% coverage for core modules
- **Integration Tests**: Critical paths covered
- **Scheduler Tests**: All scheduler functionality verified

## Notes

- Pattern and SynergyOpportunity models are in shared database
- Tests use in-memory SQLite with minimal schema
- Some tests may require external services (marked with `@pytest.mark.requires_data_api` or `@pytest.mark.requires_mqtt`)


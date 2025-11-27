# AI Query Service Tests

Epic 39, Story 39.12: Query & Automation Service Testing

## Test Structure

```
tests/
├── conftest.py                    # Pytest fixtures and configuration
├── test_health_router.py         # Health endpoint tests
├── test_query_router.py          # Query API endpoint tests
├── test_query_processor.py       # Query processor service tests
└── test_performance.py           # Performance and latency tests
```

## Running Tests

### All Tests
```bash
cd services/ai-query-service
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

# Performance tests
pytest -m performance

# Latency tests
pytest -m latency

# Integration tests
pytest -m integration

# Async tests
pytest -m asyncio
```

## Test Coverage Goals

- **Unit Tests**: >80% coverage for core modules
- **Integration Tests**: Critical paths covered
- **Performance Tests**: <500ms P95 latency validated

## Test Fixtures

### Database Fixtures
- `test_db` - In-memory SQLite database session (fresh for each test)

### Sample Data Fixtures
- `sample_query_request` - Sample query request dictionary
- `sample_entities` - Sample extracted entities list

### Mock Fixtures
- `mock_openai_client` - Mock OpenAI client
- `mock_data_api_client` - Mock DataAPIClient
- `mock_entity_extractor` - Mock entity extractor

## Performance Targets

- **Query Latency**: <500ms P95
- **Health Check**: <10ms
- **Cache Hit Rate**: >80% (when cache implemented)

## Notes

- Tests use in-memory SQLite for isolation
- Query endpoint tests currently expect 501 (not implemented yet)
- Performance tests will be enabled after full implementation
- Integration tests verify service-to-service communication


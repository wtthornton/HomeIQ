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
- `test_integration_synergy_improvements.py` - End-to-end integration tests for 2025 synergy improvements:
  - Multi-modal context integration
  - Explainable AI (XAI) explanations
  - Reinforcement Learning feedback loop
  - Transformer-based sequence modeling (optional)
  - Graph Neural Network (GNN) integration (optional)
  - API endpoint testing with enhanced features
  - Error handling and edge cases
  - Performance testing with large device sets

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
- **Integration Tests**: Critical paths covered, including 2025 enhancements
- **Scheduler Tests**: All scheduler functionality verified
- **2025 Enhancement Tests**: End-to-end flow with all improvements (multi-modal context, XAI, RL, transformer, GNN)

## Notes

- Pattern and SynergyOpportunity models are in shared database
- Tests use in-memory SQLite with minimal schema
- Some tests may require external services (marked with `@pytest.mark.requires_data_api` or `@pytest.mark.requires_mqtt`)
- Integration tests for 2025 enhancements include:
  - Mocked external context data (weather, energy)
  - XAI explanation generation testing
  - RL feedback loop validation
  - Optional transformer/GNN framework testing (requires dependencies)


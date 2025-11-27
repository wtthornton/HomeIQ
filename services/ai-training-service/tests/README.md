# AI Training Service Tests

Epic 39, Story 39.4: Training Service Testing & Validation

## Test Structure

```
tests/
├── conftest.py                    # Pytest fixtures and configuration
├── test_health_router.py         # Health endpoint tests
├── test_training_router.py       # Training API endpoint tests
├── test_crud_training.py         # CRUD operation tests
└── training/                      # Synthetic data generator tests
    ├── test_synthetic_weather_generator.py
    ├── test_synthetic_calendar_generator.py
    └── ... (other generator tests)
```

## Running Tests

### All Tests
```bash
cd services/ai-training-service
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

# Async tests
pytest -m asyncio
```

## Test Coverage Goals

- **Unit Tests**: >80% coverage
- **Integration Tests**: All critical paths
- **Performance Tests**: Validate NUC deployment targets

## Test Fixtures

- `test_db`: In-memory SQLite database for each test
- `sample_training_run_data`: Sample training run data
- `client`: FastAPI test client with database override

## Notes

- Tests use in-memory SQLite for isolation
- Synthetic data generator tests migrated from ai-automation-service
- Integration tests verify service-to-service communication
- Performance tests validate memory and latency targets


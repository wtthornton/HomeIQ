# Calendar Service Tests

Unit tests for the Home Assistant Calendar Service integration.

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

### Run All Tests

```bash
pytest tests/
```

### Run with Coverage

```bash
pytest tests/ --cov=src --cov-report=html --cov-report=term
```

### Run Specific Test File

```bash
pytest tests/test_ha_client.py -v
pytest tests/test_event_parser.py -v
```

### Run Specific Test

```bash
pytest tests/test_ha_client.py::test_client_initialization -v
```

## Test Structure

```
tests/
├── __init__.py
├── test_ha_client.py       # Tests for Home Assistant REST client
├── test_event_parser.py    # Tests for calendar event parser
└── README.md               # This file
```

## Test Coverage Goals

- **ha_client.py**: 80%+ coverage
- **event_parser.py**: 90%+ coverage

## Writing New Tests

Follow these patterns:

1. **Async Tests**: Use `@pytest.mark.asyncio` decorator
2. **Mocking**: Use `unittest.mock.AsyncMock` for async functions
3. **Fixtures**: Define reusable fixtures in conftest.py (if needed)
4. **Naming**: Use descriptive test names (test_<what>_<condition>)

## Example Test

```python
import pytest
from unittest.mock import AsyncMock
from ha_client import HomeAssistantCalendarClient

@pytest.mark.asyncio
async def test_get_calendars():
    """Test getting calendar list"""
    client = HomeAssistantCalendarClient("http://localhost:8123", "token")
    # ... test implementation
```

## CI/CD Integration

These tests run automatically in the CI/CD pipeline on:
- Pull requests
- Main branch commits
- Release tags


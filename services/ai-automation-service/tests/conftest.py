from tests.path_setup import add_service_src

add_service_src(__file__)
"""
Shared pytest fixtures for AI Automation Service tests

Following Context7 KB best practices from /pytest-dev/pytest
"""

import os
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

# ✅ Context7 Best Practice: Conditional test skipping
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY") and not os.getenv("CI"),
    reason="OPENAI_API_KEY not set and not in CI environment",
)


# ✅ Context7 Best Practice: Shared async HTTP client
@pytest.fixture
async def client():
    """
    Async HTTP client for AI Automation API endpoints

    Automatically closes after test completes.
    """
    from src.api.main import app

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# ✅ Context7 Best Practice: Mock OpenAI client
@pytest.fixture
def mock_openai():
    """
    Mock OpenAI client to avoid API costs in tests

    Provides realistic responses without making actual API calls.
    """
    with patch("src.llm.openai_client.OpenAI") as mock:
        # Configure mock to return realistic responses
        mock_instance = AsyncMock()
        mock_instance.chat.completions.create.return_value = AsyncMock(
            choices=[
                AsyncMock(
                    message=AsyncMock(
                        content='{"suggestion": "Test automation suggestion", "confidence": 0.85}',
                    ),
                ),
            ],
        )
        mock.return_value = mock_instance
        yield mock


# ✅ Context7 Best Practice: Mock database fixture
@pytest.fixture
def mock_pattern_db():
    """Mock pattern database for testing"""
    with patch("src.database.get_session") as mock:
        yield mock


# ✅ Context7 Best Practice: Mock data API client
@pytest.fixture
def mock_data_api():
    """Mock Data API client for testing"""
    with patch("src.clients.data_api_client.DataAPIClient") as mock:
        mock_instance = AsyncMock()
        mock_instance.get_patterns.return_value = []
        mock_instance.get_device_info.return_value = {"name": "Test Device"}
        mock.return_value = mock_instance
        yield mock


# ✅ Context7 Best Practice: Sample test data fixtures
@pytest.fixture
def sample_pattern():
    """Sample AI-detected pattern for testing"""
    return {
        "id": 1,
        "pattern_type": "time_of_day",
        "device_id": "light.living_room",
        "confidence": 0.92,
        "occurrences": 45,
        "metadata": {
            "time_range": "18:00-19:00",
            "days_of_week": ["Monday", "Tuesday", "Wednesday"],
        },
        "last_occurrence": datetime.utcnow(),
    }


@pytest.fixture
def sample_automation_suggestion():
    """Sample automation suggestion for testing"""
    return {
        "id": 1,
        "pattern_id": 1,
        "description": "Turn on living room light at 6 PM on weekdays",
        "automation_yaml": """
alias: "Evening Light Automation"
trigger:
  - platform: time
    at: "18:00:00"
condition:
  - condition: time
    weekday: [mon, tue, wed, thu, fri]
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
""",
        "confidence": 0.92,
        "status": "pending",
    }


@pytest.fixture
def sample_device_context():
    """Sample device context for AI analysis"""
    return {
        "device_id": "light.living_room",
        "name": "Living Room Light",
        "device_class": "light",
        "capabilities": ["brightness", "color_temp"],
        "recent_states": [
            {"state": "on", "timestamp": datetime.utcnow()},
            {"state": "off", "timestamp": datetime.utcnow()},
        ],
    }


# ✅ Context7 Best Practice: Test markers
def pytest_configure(config):
    """Register custom pytest markers for AI tests"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests (AI processing)")
    config.addinivalue_line("markers", "openai: Tests requiring OpenAI API")
    config.addinivalue_line("markers", "pattern: Pattern detection tests")
    config.addinivalue_line("markers", "suggestion: Suggestion generation tests")


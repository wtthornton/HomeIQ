"""
Pytest Configuration and Shared Fixtures
"""
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add parent directory to path for shared module imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Set test environment
os.environ['ENVIRONMENT'] = 'test'
os.environ['LOG_LEVEL'] = 'DEBUG'


@pytest.fixture(scope='session')
def event_loop_policy():
    """Set event loop policy for async tests"""
    import asyncio
    return asyncio.get_event_loop_policy()


@pytest.fixture
def mock_ha_client():
    """Mock Home Assistant client"""
    mock = AsyncMock()
    mock.get_version.return_value = "2024.10.0"
    mock.test_connection.return_value = {"status": "ok"}
    mock.health_check.return_value = {"healthy": True}
    return mock


@pytest.fixture
def mock_influxdb_client():
    """Mock InfluxDB client"""
    mock = MagicMock()
    mock.fetch_events.return_value = []
    return mock


@pytest.fixture
def mock_data_api_client():
    """Mock Data API client"""
    mock = AsyncMock()
    mock.fetch_devices.return_value = []
    mock.fetch_entities.return_value = []
    mock.health_check.return_value = {"status": "healthy"}
    return mock


@pytest.fixture
def mock_mqtt_client():
    """Mock MQTT client"""
    mock = AsyncMock()
    mock.connect.return_value = None
    mock.publish.return_value = None
    mock.disconnect.return_value = None
    return mock


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    mock = AsyncMock()
    mock.generate_automation_suggestion.return_value = {
        "alias": "Test Automation",
        "description": "Test description",
        "yaml_content": "test: yaml",
        "category": "convenience",
        "priority": "medium"
    }
    return mock


@pytest.fixture
def sample_events():
    """Sample Home Assistant events for testing"""
    return [
        {
            "entity_id": "light.living_room",
            "state": "on",
            "timestamp": "2024-10-20T10:00:00Z",
            "attributes": {"brightness": 255}
        },
        {
            "entity_id": "sensor.temperature",
            "state": "22.5",
            "timestamp": "2024-10-20T10:05:00Z",
            "attributes": {"unit": "°C"}
        }
    ]


@pytest.fixture
def sample_devices():
    """Sample device data for testing"""
    return [
        {
            "device_id": "device_1",
            "name": "Living Room Light",
            "area": "living_room",
            "domain": "light",
            "capabilities": ["brightness", "color"]
        },
        {
            "device_id": "device_2",
            "name": "Bedroom Thermostat",
            "area": "bedroom",
            "domain": "climate",
            "capabilities": ["temperature", "mode"]
        }
    ]


@pytest.fixture
def sample_pattern():
    """Sample pattern for testing"""
    return {
        "pattern_type": "time_of_day",
        "entity_id": "light.living_room",
        "hour": 18,
        "confidence": 0.85,
        "occurrences": 25
    }


@pytest.fixture
def sample_suggestion():
    """Sample automation suggestion for testing"""
    return {
        "id": 1,
        "alias": "Evening Light Automation",
        "description": "Turn on living room light at 6 PM",
        "category": "convenience",
        "priority": "medium",
        "confidence": 0.85,
        "yaml_content": """
automation:
  - alias: "Evening Light"
    trigger:
      - platform: time
        at: "18:00:00"
    action:
      - service: light.turn_on
        entity_id: light.living_room
""",
        "status": "pending"
    }


# Pytest hooks for better test output
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    # Add markers automatically based on test location
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)


# Environment variable validation - Context7 recommended approach
def pytest_sessionstart(session):
    """Load test environment - Context7 recommended approach"""
    # Try loading .env.test from multiple locations
    env_files = [
        Path('.env.test'),
        Path(__file__).parent / '.env.test',
        Path(__file__).parent.parent / '.env.test'
    ]

    loaded_from = None
    for env_file in env_files:
        if env_file.exists():
            from dotenv import load_dotenv
            load_dotenv(env_file)
            loaded_from = env_file
            break

    if loaded_from:
        print(f"[OK] Loaded test environment from {loaded_from}")
    else:
        print("[WARN] No .env.test file found - using system environment")

    # Validate required test variables
    required_vars = {
        'HA_URL': 'Home Assistant test URL',
        'HA_TOKEN': 'Home Assistant test token',
        'MQTT_BROKER': 'MQTT test broker',
        'OPENAI_API_KEY': 'OpenAI test API key'
    }

    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"{var} ({description})")

    if missing_vars:
        print(f"[ERROR] Missing required test variables: {', '.join(missing_vars)}")
        print("   Create a .env.test file with test values")
    else:
        print("[OK] All required test environment variables present")


@pytest.fixture
def test_config():
    """Simple test configuration fixture - Context7 pattern"""
    return {
        'ha_url': os.getenv('HA_URL', 'http://localhost:8123'),
        'ha_token': os.getenv('HA_TOKEN', 'test_token'),
        'mqtt_broker': os.getenv('MQTT_BROKER', 'localhost:1883'),
        'openai_api_key': os.getenv('OPENAI_API_KEY', 'test_key'),
        'influxdb_url': os.getenv('INFLUXDB_URL', 'http://localhost:8086'),
        'influxdb_token': os.getenv('INFLUXDB_TOKEN', 'test_token'),
    }


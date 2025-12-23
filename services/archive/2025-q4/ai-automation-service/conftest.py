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
    # Use generate_with_unified_prompt instead of deprecated generate_automation_suggestion
    mock.generate_with_unified_prompt.return_value = {
        "alias": "Test Automation",
        "description": "Test description",
        "automation_yaml": "test: yaml",
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
    from dotenv import load_dotenv
    
    # Try loading .env from multiple locations (primary source)
    # Then fall back to .env.test if it exists
    env_files = [
        Path('.env'),  # Project root .env (primary)
        Path(__file__).parent.parent.parent / '.env',  # Project root from service
        Path(__file__).parent / '.env',  # Service directory
        Path('.env.test'),  # Fallback to .env.test
        Path(__file__).parent / '.env.test',
        Path(__file__).parent.parent / '.env.test'
    ]

    loaded_from = None
    for env_file in env_files:
        if env_file.exists():
            load_dotenv(env_file, override=False)  # Don't override existing env vars
            if not loaded_from:  # Only set first found file
                loaded_from = env_file

    if loaded_from:
        print(f"[OK] Loaded test environment from {loaded_from}")
    else:
        print("[WARN] No .env or .env.test file found - using system environment")

    # Validate required test variables with alternative names
    # Check for alternative variable names used in the codebase
    def get_env_var(*names):
        """Get environment variable trying multiple alternative names"""
        for name in names:
            value = os.getenv(name)
            if value:
                return value
        return None

    # Check required variables with alternatives
    ha_url = get_env_var('HA_URL', 'HA_HTTP_URL', 'HOME_ASSISTANT_URL')
    ha_token = get_env_var('HA_TOKEN', 'HOME_ASSISTANT_TOKEN')
    mqtt_broker = get_env_var('MQTT_BROKER')
    openai_api_key = get_env_var('OPENAI_API_KEY')

    missing_vars = []
    if not ha_url:
        missing_vars.append("HA_URL/HA_HTTP_URL/HOME_ASSISTANT_URL (Home Assistant URL)")
    if not ha_token:
        missing_vars.append("HA_TOKEN/HOME_ASSISTANT_TOKEN (Home Assistant token)")
    if not mqtt_broker:
        missing_vars.append("MQTT_BROKER (MQTT broker)")
    if not openai_api_key:
        missing_vars.append("OPENAI_API_KEY (OpenAI API key)")

    if missing_vars:
        print(f"[ERROR] Missing required test variables: {', '.join(missing_vars)}")
        print("   Add these to your .env file")
    else:
        print("[OK] All required test environment variables present")


@pytest.fixture
def test_config():
    """Simple test configuration fixture - Context7 pattern"""
    # Support alternative variable names
    ha_url = (os.getenv('HA_URL') or 
              os.getenv('HA_HTTP_URL') or 
              os.getenv('HOME_ASSISTANT_URL') or 
              'http://localhost:8123')
    ha_token = (os.getenv('HA_TOKEN') or 
                os.getenv('HOME_ASSISTANT_TOKEN') or 
                'test_token')
    
    return {
        'ha_url': ha_url,
        'ha_token': ha_token,
        'mqtt_broker': os.getenv('MQTT_BROKER', 'localhost:1883'),
        'openai_api_key': os.getenv('OPENAI_API_KEY', 'test_key'),
        'influxdb_url': os.getenv('INFLUXDB_URL', 'http://localhost:8086'),
        'influxdb_token': os.getenv('INFLUXDB_TOKEN', 'test_token'),
    }


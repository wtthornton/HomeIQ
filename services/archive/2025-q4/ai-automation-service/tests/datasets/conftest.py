"""
Pytest fixtures for dataset-based testing

Phase 1: Foundation - Test Infrastructure
"""

import os
from pathlib import Path
from typing import Any, AsyncGenerator

import pytest

# Add src to path for imports
from tests.path_setup import add_service_src
add_service_src(__file__)

from src.testing.dataset_loader import HomeAssistantDatasetLoader
from src.testing.event_injector import EventInjector


@pytest.fixture(scope="session")
def dataset_root() -> Path:
    """
    Get the root directory for datasets.
    
    Checks multiple possible locations:
    1. tests/datasets/datasets/ (git submodule)
    2. Environment variable DATASET_ROOT
    3. ../home-assistant-datasets/datasets/ (relative)
    """
    # Try git submodule location first
    project_root = Path(__file__).parent.parent.parent.parent.parent
    dataset_root = project_root / "tests" / "datasets" / "datasets"
    
    # Check environment variable
    env_root = os.getenv("DATASET_ROOT")
    if env_root and Path(env_root).exists():
        dataset_root = Path(env_root)
    
    # Check relative location
    if not dataset_root.exists():
        relative_root = project_root.parent / "home-assistant-datasets" / "datasets"
        if relative_root.exists():
            dataset_root = relative_root
    
    if not dataset_root.exists():
        pytest.skip(
            f"Dataset root not found at {dataset_root}. "
            "Please clone home-assistant-datasets repository or set DATASET_ROOT environment variable."
        )
    
    return dataset_root


@pytest.fixture
def dataset_loader(dataset_root: Path) -> HomeAssistantDatasetLoader:
    """Create dataset loader instance"""
    return HomeAssistantDatasetLoader(dataset_root=dataset_root)


@pytest.fixture
def event_injector() -> AsyncGenerator[EventInjector, None]:
    """
    Create event injector instance.
    
    Uses test InfluxDB configuration from environment variables:
    - INFLUXDB_URL (default: http://localhost:8086)
    - INFLUXDB_TOKEN (default: ha-ingestor-token - matches docker-compose init)
    - INFLUXDB_ORG (default: ha-ingestor - matches docker-compose init)
    - INFLUXDB_BUCKET (default: home_assistant_events_test for test isolation)
    """
    import os
    
    # Use test bucket for isolation
    test_bucket = os.getenv("INFLUXDB_TEST_BUCKET", "home_assistant_events_test")
    
    # Match docker-compose InfluxDB initialization
    injector = EventInjector(
        influxdb_url=os.getenv("INFLUXDB_URL", "http://localhost:8086"),
        influxdb_token=os.getenv("INFLUXDB_TOKEN", "ha-ingestor-token"),
        influxdb_org=os.getenv("INFLUXDB_ORG", "ha-ingestor"),
        influxdb_bucket=test_bucket
    )
    
    try:
        injector.connect()
        yield injector
    finally:
        injector.disconnect()


@pytest.fixture
async def loaded_dataset(dataset_loader: HomeAssistantDatasetLoader) -> dict:
    """
    Load assist-mini dataset (smallest, fastest for testing).
    
    Override in tests to load different datasets:
    
    @pytest.fixture
    async def loaded_dataset(dataset_loader):
        return await dataset_loader.load_synthetic_home("assist")
    """
    return await dataset_loader.load_synthetic_home("assist-mini")


@pytest.fixture
def ha_test_url() -> str:
    """Get test HA URL from environment"""
    return os.getenv("HA_TEST_URL", "http://localhost:8124")


@pytest.fixture
def ha_test_token() -> str | None:
    """Get test HA token from environment"""
    return os.getenv("HA_TEST_TOKEN")


@pytest.fixture
def use_ha_container() -> bool:
    """
    Check if HA container integration should be used.
    
    Controlled by:
    - ENABLE_HA_INTEGRATION environment variable (default: false)
    - --use-ha-container pytest flag
    """
    # Check environment variable
    env_enabled = os.getenv("ENABLE_HA_INTEGRATION", "false").lower() == "true"
    
    # Check pytest flag (would need to be set via pytest.ini or command line)
    # For now, just use environment variable
    return env_enabled


@pytest.fixture
async def ha_test_loader(
    ha_test_url: str,
    ha_test_token: str | None,
    use_ha_container: bool
) -> Any | None:
    """
    Create HA test loader if HA integration is enabled.
    
    Returns:
        HATestLoader instance or None if HA integration disabled
    """
    if not use_ha_container:
        return None
    
    if not ha_test_token:
        pytest.skip("HA_TEST_TOKEN not set. Cannot use HA container integration.")
    
    from src.testing.ha_test_loader import HATestLoader
    
    return HATestLoader(ha_url=ha_test_url, ha_token=ha_test_token)

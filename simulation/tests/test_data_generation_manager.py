"""
Unit tests for DataGenerationManager.
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from src.data_generation.config import DataGenerationConfig
from src.data_generation.data_generation_manager import DataGenerationManager


class MockHomeGenerator:
    """Mock home generator for testing."""
    
    async def generate_home(
        self,
        home_type: str,
        event_days: int,
        home_index: int
    ) -> dict:
        """Generate mock home."""
        return {
            "home_id": f"home_{home_index}",
            "home_type": home_type,
            "devices": [{"device_id": f"device_{i}"} for i in range(15)],
            "events": [{"event_id": f"event_{i}"} for i in range(200)]
        }


@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def config(temp_cache_dir):
    """Create test configuration."""
    return DataGenerationConfig(
        cache_directory=temp_cache_dir,
        cache_enabled=True,
        default_home_count=5,
        default_event_days=7,
        max_parallel_generations=2
    )


@pytest.fixture
def manager(config):
    """Create data generation manager."""
    home_generator = MockHomeGenerator()
    return DataGenerationManager(config=config, home_generator=home_generator)


@pytest.mark.asyncio
async def test_generate_homes(manager):
    """Test home generation."""
    homes = await manager.generate_homes(home_count=5, event_days=7)
    
    assert len(homes) == 5
    assert all("home_id" in h for h in homes)
    assert all("devices" in h for h in homes)
    assert all("events" in h for h in homes)


@pytest.mark.asyncio
async def test_cache_usage(manager):
    """Test cache usage."""
    # First generation
    homes1 = await manager.generate_homes(home_count=3, event_days=7)
    assert len(homes1) == 3
    assert manager.generation_stats["total_generated"] == 3
    
    # Second generation (should use cache)
    homes2 = await manager.generate_homes(home_count=3, event_days=7)
    assert len(homes2) == 3
    assert manager.generation_stats["total_cached"] == 3


@pytest.mark.asyncio
async def test_validation(manager):
    """Test data validation."""
    # Create invalid home generator
    class InvalidHomeGenerator:
        async def generate_home(self, home_type, event_days, home_index):
            return {
                "home_id": "invalid",
                "home_type": home_type,
                "devices": [],  # Too few devices
                "events": []  # Too few events
            }
    
    invalid_manager = DataGenerationManager(
        config=manager.config,
        home_generator=InvalidHomeGenerator()
    )
    
    homes = await invalid_manager.generate_homes(home_count=1)
    assert len(homes) == 0
    assert invalid_manager.generation_stats["total_failed"] == 1


@pytest.mark.asyncio
async def test_parallel_generation(manager):
    """Test parallel generation."""
    homes = await manager.generate_homes(home_count=10, event_days=7)
    assert len(homes) == 10
    
    # Check that generation times are reasonable
    report = manager.get_progress_report()
    assert report["total_generated"] > 0


@pytest.mark.asyncio
async def test_progress_report(manager):
    """Test progress report."""
    await manager.generate_homes(home_count=3)
    
    report = manager.get_progress_report()
    assert "total_generated" in report
    assert "total_cached" in report
    assert "total_failed" in report
    assert "average_generation_time" in report
    assert "cache_enabled" in report


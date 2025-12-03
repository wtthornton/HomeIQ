"""
Unit tests for Simulation Engine Core Framework

Tests for:
- SimulationEngine class
- Configuration management
- Dependency injection framework
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

import sys
from pathlib import Path

# Add simulation/src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from engine.simulation_engine import SimulationEngine
from engine.config import SimulationConfig
from engine.dependency_injection import (
    DependencyContainer,
    ServiceFactory
)


class TestSimulationConfig:
    """Tests for SimulationConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = SimulationConfig()
        assert config.mode == "standard"
        assert config.model_mode == "pretrained"
        assert config.synthetic_homes_count == 100
        assert config.max_parallel_homes == 10

    def test_custom_config(self):
        """Test custom configuration values."""
        config = SimulationConfig(
            mode="quick",
            model_mode="train_during",
            synthetic_homes_count=50,
            max_parallel_homes=5
        )
        assert config.mode == "quick"
        assert config.model_mode == "train_during"
        assert config.synthetic_homes_count == 50
        assert config.max_parallel_homes == 5

    def test_get_synthetic_home_path(self):
        """Test synthetic home path generation."""
        config = SimulationConfig(synthetic_data_directory=Path("/test/data"))
        path = config.get_synthetic_home_path("001")
        assert path == Path("/test/data/home_001.json")

    def test_get_results_path(self, tmp_path):
        """Test results path generation."""
        config = SimulationConfig(results_directory=tmp_path)
        path = config.get_results_path("test.json")
        assert path == tmp_path / "test.json"
        assert path.parent.exists()  # Directory should be created


class MockService:
    """Mock service for testing."""
    def __init__(self, value: str):
        self.value = value


class MockFactory(ServiceFactory[MockService]):
    """Mock factory for testing."""
    def __init__(self, value: str):
        self.value = value
        self.created_count = 0

    def create(self) -> MockService:
        self.created_count += 1
        return MockService(self.value)

    def cleanup(self, service: MockService) -> None:
        pass


class TestDependencyContainer:
    """Tests for DependencyContainer."""

    def test_register_and_get_factory(self):
        """Test factory registration and retrieval."""
        container = DependencyContainer()
        factory = MockFactory("test_value")
        
        container.register_factory("test_service", factory)
        assert container.has("test_service")
        
        service = container.get("test_service")
        assert isinstance(service, MockService)
        assert service.value == "test_value"
        assert factory.created_count == 1

    def test_singleton_behavior(self):
        """Test singleton service behavior."""
        container = DependencyContainer()
        factory = MockFactory("test_value")
        
        container.register_factory("test_service", factory, singleton=True)
        
        service1 = container.get("test_service")
        service2 = container.get("test_service")
        
        assert service1 is service2  # Same instance
        assert factory.created_count == 1  # Created only once

    def test_non_singleton_behavior(self):
        """Test non-singleton service behavior."""
        container = DependencyContainer()
        factory = MockFactory("test_value")
        
        container.register_factory("test_service", factory, singleton=False)
        
        service1 = container.get("test_service")
        service2 = container.get("test_service")
        
        assert service1 is not service2  # Different instances
        assert factory.created_count == 2  # Created twice

    def test_register_instance(self):
        """Test direct instance registration."""
        container = DependencyContainer()
        instance = MockService("direct_value")
        
        container.register_instance("test_service", instance)
        assert container.has("test_service")
        
        retrieved = container.get("test_service")
        assert retrieved is instance
        assert retrieved.value == "direct_value"

    def test_get_nonexistent_service(self):
        """Test getting non-existent service raises KeyError."""
        container = DependencyContainer()
        
        with pytest.raises(KeyError, match="Service 'nonexistent' not registered"):
            container.get("nonexistent")

    def test_clear(self):
        """Test container cleanup."""
        container = DependencyContainer()
        factory = MockFactory("test_value")
        
        container.register_factory("test_service", factory)
        service = container.get("test_service")
        
        container.clear()
        
        assert not container.has("test_service")
        with pytest.raises(KeyError):
            container.get("test_service")

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager."""
        async with DependencyContainer() as container:
            factory = MockFactory("test_value")
            container.register_factory("test_service", factory)
            service = container.get("test_service")
            assert service is not None
        
        # After context exit, container should be cleared
        assert not container.has("test_service")


class TestSimulationEngine:
    """Tests for SimulationEngine."""

    @pytest.mark.asyncio
    async def test_initialization(self, tmp_path):
        """Test engine initialization."""
        config = SimulationConfig(
            results_directory=tmp_path / "results",
            synthetic_data_directory=tmp_path / "data"
        )
        engine = SimulationEngine(config)
        
        await engine.initialize()
        
        assert engine._initialized
        assert (tmp_path / "results").exists()
        assert (tmp_path / "data").exists()

    @pytest.mark.asyncio
    async def test_double_initialization(self, tmp_path):
        """Test that double initialization is safe."""
        config = SimulationConfig(results_directory=tmp_path)
        engine = SimulationEngine(config)
        
        await engine.initialize()
        await engine.initialize()  # Should not raise
        
        assert engine._initialized

    @pytest.mark.asyncio
    async def test_run_3am_simulation_placeholder(self, tmp_path):
        """Test 3 AM simulation placeholder."""
        config = SimulationConfig(results_directory=tmp_path)
        engine = SimulationEngine(config)
        
        result = await engine.run_3am_simulation()
        
        assert result["status"] == "not_implemented"
        assert "message" in result
        assert result["mode"] == "standard"

    @pytest.mark.asyncio
    async def test_run_ask_ai_simulation_placeholder(self, tmp_path):
        """Test Ask AI simulation placeholder."""
        config = SimulationConfig(results_directory=tmp_path)
        engine = SimulationEngine(config)
        
        result = await engine.run_ask_ai_simulation()
        
        assert result["status"] == "not_implemented"
        assert "message" in result
        assert result["mode"] == "standard"

    @pytest.mark.asyncio
    async def test_cleanup(self, tmp_path):
        """Test engine cleanup."""
        config = SimulationConfig(results_directory=tmp_path)
        engine = SimulationEngine(config)
        
        await engine.initialize()
        assert engine._initialized
        
        await engine.cleanup()
        assert not engine._initialized

    @pytest.mark.asyncio
    async def test_async_context_manager(self, tmp_path):
        """Test async context manager."""
        config = SimulationConfig(results_directory=tmp_path)
        
        async with SimulationEngine(config) as engine:
            assert engine._initialized
        
        # After context exit, engine should be cleaned up
        assert not engine._initialized


"""
Unit tests for Device Mapping Library (Epic AI-24).

Tests for base handler interface, registry, and configuration loader.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.device_mappings.base import DeviceHandler, DeviceType
from src.device_mappings.config_loader import ConfigLoader
from src.device_mappings.registry import DeviceMappingRegistry


class MockHandler(DeviceHandler):
    """Mock handler for testing."""
    
    def __init__(self, name: str, can_handle_result: bool = True):
        self.name = name
        self.can_handle_result = can_handle_result
        self.identify_type_called = False
        self.get_relationships_called = False
        self.enrich_context_called = False
    
    def can_handle(self, device: dict) -> bool:
        return self.can_handle_result
    
    def identify_type(self, device: dict, entity: dict) -> DeviceType:
        self.identify_type_called = True
        return DeviceType.INDIVIDUAL
    
    def get_relationships(self, device: dict, entities: list) -> dict:
        self.get_relationships_called = True
        return {}
    
    def enrich_context(self, device: dict, entity: dict) -> dict:
        self.enrich_context_called = True
        return {}


class TestDeviceHandler:
    """Tests for DeviceHandler abstract base class."""
    
    def test_device_handler_is_abstract(self):
        """Test that DeviceHandler cannot be instantiated directly."""
        with pytest.raises(TypeError):
            DeviceHandler()  # type: ignore
    
    def test_mock_handler_implements_interface(self):
        """Test that MockHandler correctly implements the interface."""
        handler = MockHandler("test")
        device = {"id": "test_device"}
        entity = {"entity_id": "test_entity"}
        
        assert handler.can_handle(device) is True
        assert handler.identify_type(device, entity) == DeviceType.INDIVIDUAL
        assert handler.get_relationships(device, []) == {}
        assert handler.enrich_context(device, entity) == {}


class TestDeviceMappingRegistry:
    """Tests for DeviceMappingRegistry."""
    
    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = DeviceMappingRegistry()
        assert len(registry.get_all_handlers()) == 0
    
    def test_register_handler(self):
        """Test registering a handler."""
        registry = DeviceMappingRegistry()
        handler = MockHandler("test")
        
        registry.register("test", handler)
        
        assert registry.get_handler("test") == handler
        assert len(registry.get_all_handlers()) == 1
    
    def test_register_invalid_handler(self):
        """Test that registering a non-DeviceHandler raises TypeError."""
        registry = DeviceMappingRegistry()
        
        with pytest.raises(TypeError):
            registry.register("test", "not a handler")  # type: ignore
    
    def test_get_handler_not_found(self):
        """Test getting a handler that doesn't exist."""
        registry = DeviceMappingRegistry()
        
        assert registry.get_handler("nonexistent") is None
    
    def test_find_handler(self):
        """Test finding a handler that can handle a device."""
        registry = DeviceMappingRegistry()
        handler1 = MockHandler("handler1", can_handle_result=False)
        handler2 = MockHandler("handler2", can_handle_result=True)
        
        registry.register("handler1", handler1)
        registry.register("handler2", handler2)
        
        device = {"id": "test_device"}
        found = registry.find_handler(device)
        
        assert found == handler2
    
    def test_find_handler_not_found(self):
        """Test finding a handler when none can handle the device."""
        registry = DeviceMappingRegistry()
        handler = MockHandler("handler1", can_handle_result=False)
        
        registry.register("handler1", handler)
        
        device = {"id": "test_device"}
        found = registry.find_handler(device)
        
        assert found is None
    
    def test_get_all_handlers(self):
        """Test getting all registered handlers."""
        registry = DeviceMappingRegistry()
        handler1 = MockHandler("handler1")
        handler2 = MockHandler("handler2")
        
        registry.register("handler1", handler1)
        registry.register("handler2", handler2)
        
        all_handlers = registry.get_all_handlers()
        
        assert len(all_handlers) == 2
        assert "handler1" in all_handlers
        assert "handler2" in all_handlers
        assert all_handlers["handler1"] == handler1
        assert all_handlers["handler2"] == handler2
    
    def test_clear_registry(self):
        """Test clearing the registry."""
        registry = DeviceMappingRegistry()
        handler = MockHandler("test")
        
        registry.register("test", handler)
        assert len(registry.get_all_handlers()) == 1
        
        registry.clear()
        assert len(registry.get_all_handlers()) == 0
    
    @patch("src.device_mappings.registry.importlib.import_module")
    def test_discover_handlers_success(self, mock_import):
        """Test handler discovery with successful imports."""
        # Mock module with register function
        mock_module = MagicMock()
        mock_module.register = MagicMock()
        mock_import.return_value = mock_module
        
        registry = DeviceMappingRegistry()
        registry.discover_handlers()
        
        # Should attempt to import handler modules
        assert mock_import.called
    
    @patch("src.device_mappings.registry.importlib.import_module")
    def test_discover_handlers_import_error(self, mock_import):
        """Test handler discovery with import errors (expected for new handlers)."""
        mock_import.side_effect = ImportError("No module named 'device_mappings.hue'")
        
        registry = DeviceMappingRegistry()
        # Should not raise exception
        registry.discover_handlers()
        
        assert mock_import.called


class TestConfigLoader:
    """Tests for ConfigLoader."""
    
    def test_config_loader_initialization(self):
        """Test config loader initialization."""
        loader = ConfigLoader()
        assert loader.base_path is not None
    
    def test_config_loader_custom_path(self):
        """Test config loader with custom path."""
        from pathlib import Path
        custom_path = Path("/custom/path")
        loader = ConfigLoader(custom_path)
        assert loader.base_path == custom_path
    
    @patch("src.device_mappings.config_loader.Path.exists")
    @patch("builtins.open", create=True)
    @patch("src.device_mappings.config_loader.yaml")
    def test_load_config_success(self, mock_yaml, mock_open, mock_exists):
        """Test loading a configuration file."""
        mock_exists.return_value = True
        mock_yaml.safe_load.return_value = {"device_type": "hue", "manufacturer": "signify"}
        
        loader = ConfigLoader()
        config = loader.load_config("hue")
        
        assert config == {"device_type": "hue", "manufacturer": "signify"}
    
    @patch("src.device_mappings.config_loader.Path.exists")
    def test_load_config_not_found(self, mock_exists):
        """Test loading a configuration file that doesn't exist."""
        mock_exists.return_value = False
        
        loader = ConfigLoader()
        config = loader.load_config("nonexistent")
        
        assert config == {}
    
    @patch("src.device_mappings.config_loader.Path.exists")
    @patch("builtins.open", create=True)
    @patch("src.device_mappings.config_loader.yaml")
    def test_load_config_yaml_none(self, mock_yaml, mock_open, mock_exists):
        """Test loading a configuration file that returns None."""
        mock_exists.return_value = True
        mock_yaml.safe_load.return_value = None
        
        loader = ConfigLoader()
        config = loader.load_config("hue")
        
        assert config == {}
    
    @patch("src.device_mappings.config_loader.Path.exists")
    def test_config_exists_true(self, mock_exists):
        """Test checking if config exists when it does."""
        mock_exists.return_value = True
        
        loader = ConfigLoader()
        assert loader.config_exists("hue") is True
    
    @patch("src.device_mappings.config_loader.Path.exists")
    def test_config_exists_false(self, mock_exists):
        """Test checking if config exists when it doesn't."""
        mock_exists.return_value = False
        
        loader = ConfigLoader()
        assert loader.config_exists("hue") is False
    
    @patch("src.device_mappings.config_loader.yaml", None)
    @patch("src.device_mappings.config_loader.Path.exists")
    def test_load_config_no_yaml(self, mock_exists):
        """Test loading config when PyYAML is not installed."""
        mock_exists.return_value = True
        
        loader = ConfigLoader()
        config = loader.load_config("hue")
        
        assert config == {}


class TestDeviceType:
    """Tests for DeviceType enum."""
    
    def test_device_type_values(self):
        """Test DeviceType enum values."""
        assert DeviceType.MASTER.value == "master"
        assert DeviceType.SEGMENT.value == "segment"
        assert DeviceType.GROUP.value == "group"
        assert DeviceType.INDIVIDUAL.value == "individual"


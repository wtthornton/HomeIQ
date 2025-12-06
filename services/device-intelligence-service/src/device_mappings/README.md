# Device Mapping Library - Handler Development Guide

**Epic:** AI-24 - Device Mapping Library Architecture  
**Purpose:** Enable rapid addition of device-specific mappings without modifying core code

---

## Overview

The Device Mapping Library provides a plugin-based architecture for device-specific intelligence. Handlers can be added quickly (< 1 hour) without modifying core code, enabling rapid support for new device types.

---

## Architecture

### Core Components

1. **Base Handler Interface** (`base.py`)
   - Abstract base class that all handlers must implement
   - Defines standard methods for device intelligence

2. **Registry** (`registry.py`)
   - Simple dictionary-based registry for handlers
   - Auto-discovers handlers via imports
   - Finds handlers that can process specific devices

3. **Configuration Loader** (`config_loader.py`)
   - Loads YAML configuration files for handlers
   - Supports device-specific settings

---

## Creating a New Handler

### Step 1: Create Handler Module

Create a new directory for your device type:

```
src/device_mappings/
└── your_device_type/
    ├── __init__.py
    ├── handler.py
    └── config.yaml
```

### Step 2: Implement Handler Class

Create `handler.py`:

```python
from typing import Any
from ..base import DeviceHandler, DeviceType

class YourDeviceHandler(DeviceHandler):
    """Handler for Your Device Type."""
    
    def can_handle(self, device: dict[str, Any]) -> bool:
        """Check if this handler can process the device."""
        manufacturer = device.get("manufacturer", "").lower()
        model = device.get("model", "").lower()
        return manufacturer == "your_manufacturer" and "your_model" in model
    
    def identify_type(self, device: dict[str, Any], entity: dict[str, Any]) -> DeviceType:
        """Identify device type."""
        # Your logic here
        return DeviceType.INDIVIDUAL
    
    def get_relationships(self, device: dict[str, Any], entities: list[dict[str, Any]]) -> dict[str, Any]:
        """Get device relationships."""
        # Your logic here
        return {}
    
    def enrich_context(self, device: dict[str, Any], entity: dict[str, Any]) -> dict[str, Any]:
        """Add device-specific context."""
        return {
            "description": "Your device description",
            "capabilities": ["feature1", "feature2"]
        }
```

### Step 3: Register Handler

Create `__init__.py`:

```python
from .handler import YourDeviceHandler

def register(registry):
    """Register this handler with the device mapping registry."""
    registry.register("your_device_type", YourDeviceHandler())
```

### Step 4: Create Configuration File

Create `config.yaml`:

```yaml
device_type: your_device_type
manufacturer_patterns:
  - "your_manufacturer"
model_patterns:
  - "your_model"
detection_rules:
  is_individual: "device.manufacturer.lower() == 'your_manufacturer'"
context_template: |
  {name} ({entity_id}, Your Device Type - {description})
```

### Step 5: Add to Discovery List

Update `registry.py` to include your handler in the discovery list:

```python
handler_modules = [
    "device_mappings.hue",
    "device_mappings.wled",
    "device_mappings.your_device_type",  # Add your handler here
]
```

---

## Handler Interface Methods

### `can_handle(device: dict) -> bool`

**Purpose:** Check if this handler can process the given device.

**Parameters:**
- `device`: Device dictionary from Device Registry (includes `manufacturer`, `model`, `id`, etc.)

**Returns:**
- `True` if this handler can process the device, `False` otherwise

**Example:**
```python
def can_handle(self, device: dict[str, Any]) -> bool:
    manufacturer = device.get("manufacturer", "").lower()
    return manufacturer in ["signify", "philips"]
```

### `identify_type(device: dict, entity: dict) -> DeviceType`

**Purpose:** Identify the device type (master, segment, group, individual).

**Parameters:**
- `device`: Device dictionary from Device Registry
- `entity`: Entity dictionary from Entity Registry or States

**Returns:**
- `DeviceType` enum value (`MASTER`, `SEGMENT`, `GROUP`, or `INDIVIDUAL`)

**Example:**
```python
def identify_type(self, device: dict[str, Any], entity: dict[str, Any]) -> DeviceType:
    model = device.get("model", "").lower()
    if model in ["room", "zone"]:
        return DeviceType.GROUP
    return DeviceType.INDIVIDUAL
```

### `get_relationships(device: dict, entities: list) -> dict`

**Purpose:** Get device relationships (e.g., segments to master, lights to room).

**Parameters:**
- `device`: Device dictionary from Device Registry
- `entities`: List of related entities

**Returns:**
- Dictionary with relationship information

**Example:**
```python
def get_relationships(self, device: dict[str, Any], entities: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "master_id": device.get("id"),
        "segments": [e.get("entity_id") for e in entities if "_segment_" in e.get("entity_id", "")]
    }
```

### `enrich_context(device: dict, entity: dict) -> dict`

**Purpose:** Add device-specific context for AI agent.

**Parameters:**
- `device`: Device dictionary from Device Registry
- `entity`: Entity dictionary from Entity Registry or States

**Returns:**
- Dictionary with enriched context information

**Example:**
```python
def enrich_context(self, device: dict[str, Any], entity: dict[str, Any]) -> dict[str, Any]:
    return {
        "description": f"{device.get('model')} device",
        "capabilities": ["rgb", "brightness", "color_temp"],
        "manufacturer": device.get("manufacturer")
    }
```

---

## Configuration File Format

Configuration files are YAML and should be placed in `device_mappings/{device_type}/config.yaml`.

### Required Fields

- `device_type`: Device type identifier (e.g., "hue", "wled")

### Optional Fields

- `manufacturer_patterns`: List of manufacturer name patterns to match
- `model_patterns`: List of model name patterns to match
- `detection_rules`: Python expressions for device detection
- `context_template`: Template for context description

### Example Configuration

```yaml
device_type: hue
manufacturer_patterns:
  - "signify"
  - "philips"
group_models:
  - "room"
  - "zone"
individual_models:
  - "hue go"
  - "hue color downlight"
detection_rules:
  is_group: "device.model.lower() in ['room', 'zone']"
  is_individual: "device.model.lower() not in ['room', 'zone']"
context_template: |
  {name} ({entity_id}, {device_type} - {description})
```

---

## Testing Your Handler

### Unit Tests

Create tests in `tests/test_device_mappings_{device_type}.py`:

```python
import pytest
from src.device_mappings.your_device_type.handler import YourDeviceHandler
from src.device_mappings.base import DeviceType

def test_can_handle():
    handler = YourDeviceHandler()
    device = {"manufacturer": "Your Manufacturer", "model": "Your Model"}
    assert handler.can_handle(device) is True

def test_identify_type():
    handler = YourDeviceHandler()
    device = {"manufacturer": "Your Manufacturer", "model": "Your Model"}
    entity = {"entity_id": "test.entity"}
    assert handler.identify_type(device, entity) == DeviceType.INDIVIDUAL
```

### Integration Tests

Test your handler with the registry:

```python
from src.device_mappings.registry import DeviceMappingRegistry
from src.device_mappings.your_device_type.handler import YourDeviceHandler

def test_handler_registration():
    registry = DeviceMappingRegistry()
    handler = YourDeviceHandler()
    registry.register("your_device_type", handler)
    
    device = {"manufacturer": "Your Manufacturer", "model": "Your Model"}
    found = registry.find_handler(device)
    assert found == handler
```

---

## Best Practices

1. **Keep Handlers Simple:** Focus on device-specific logic only
2. **Use Configuration:** Put device patterns in `config.yaml`, not code
3. **Handle Edge Cases:** Always check for missing keys in device/entity dicts
4. **Document Your Handler:** Add docstrings explaining detection logic
5. **Test Thoroughly:** Write unit tests for all handler methods
6. **Follow Naming Conventions:** Use lowercase with underscores for handler names

---

## Examples

### Hue Handler (Room/Zone Groups)

See `device_mappings/hue/` for a complete example of:
- Room/Zone group detection
- Individual light identification
- Relationship mapping

### WLED Handler (Master/Segments)

See `device_mappings/wled/` for a complete example of:
- Master entity detection
- Segment entity detection
- Relationship mapping

---

## API Endpoints

Once your handler is registered, it's available via:

- `GET /api/device-mappings/status` - Get registry status
- `POST /api/device-mappings/reload` - Reload registry (after config changes)
- `GET /api/device-mappings/{device_id}/type` - Get device type (Story AI24.3)
- `GET /api/device-mappings/{device_id}/relationships` - Get relationships (Story AI24.3)
- `GET /api/device-mappings/{device_id}/context` - Get enriched context (Story AI24.3)

---

## Troubleshooting

### Handler Not Discovered

- Check that `__init__.py` has a `register(registry)` function
- Verify handler is in discovery list in `registry.py`
- Check import errors in logs

### Handler Not Selected

- Verify `can_handle()` returns `True` for your device
- Check device dictionary structure matches expectations
- Add debug logging to `can_handle()` method

### Configuration Not Loaded

- Verify `config.yaml` exists in handler directory
- Check YAML syntax is valid
- Ensure PyYAML is installed (`pip install PyYAML`)

---

## Support

For questions or issues:
- Check existing handlers (`hue/`, `wled/`) for examples
- Review unit tests in `tests/test_device_mappings.py`
- See Epic AI-24 documentation for architecture details

---

**Last Updated:** 2025-01-XX  
**Version:** 1.0.0


"""
Pytest configuration for spec validator tests
"""

import pytest
from unittest.mock import MagicMock, patch

# Mock schema for testing
MOCK_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["id", "version", "name", "enabled", "triggers", "actions", "policy"],
    "properties": {
        "id": {"type": "string", "minLength": 3},
        "version": {"type": "string"},
        "name": {"type": "string", "minLength": 3},
        "enabled": {"type": "boolean"},
        "triggers": {"type": "array", "minItems": 1},
        "actions": {"type": "array", "minItems": 1},
        "policy": {"type": "object", "required": ["risk"]}
    }
}

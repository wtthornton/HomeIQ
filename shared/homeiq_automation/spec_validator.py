"""
HomeIQ Automation Spec Validator

Epic C1: JSON Schema validation for Automation Spec with semver enforcement
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import jsonschema
from jsonschema import ValidationError

# Optional YAML support
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logger = logging.getLogger(__name__)

# Load schema from file
SCHEMA_PATH = Path(__file__).parent.parent.parent / "implementation" / "HomeIQ_API_Driven_Automations_Docs" / "HomeIQ_AutomationSpec_v1.schema.json"

# Cache for schema
_schema_cache: Optional[Dict[str, Any]] = None


def load_schema() -> Dict[str, Any]:
    """
    Load JSON Schema from file.
    
    Uses caching to avoid repeated file I/O. The schema is loaded once
    and cached for subsequent calls.
    
    Returns:
        Dictionary containing the JSON Schema
        
    Raises:
        FileNotFoundError: If schema file does not exist
        json.JSONDecodeError: If schema file contains invalid JSON
        OSError: If file cannot be read
    """
    global _schema_cache
    
    if _schema_cache is not None:
        return _schema_cache
    
    try:
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            _schema_cache = json.load(f)
        logger.info(f"Loaded Automation Spec schema from {SCHEMA_PATH}")
        return _schema_cache
    except FileNotFoundError as e:
        logger.error(f"Schema file not found: {SCHEMA_PATH}")
        raise FileNotFoundError(
            f"Automation Spec schema file not found at {SCHEMA_PATH}. "
            "Please ensure the schema file exists."
        ) from e
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in schema file: {e}")
        raise json.JSONDecodeError(
            f"Schema file contains invalid JSON: {e.msg}",
            e.doc,
            e.pos
        ) from e
    except OSError as e:
        logger.error(f"Failed to read schema file: {e}")
        raise OSError(f"Cannot read schema file {SCHEMA_PATH}: {e}") from e


def validate_semver(version: str) -> bool:
    """
    Validate semantic version string.
    
    Pattern: ^\\d+\\.\\d+\\.\\d+(-[0-9A-Za-z\\.-]+)?$
    Examples: "1.0.0", "1.2.3-beta.1", "2.0.0-rc.2"
    
    Args:
        version: Version string to validate
    
    Returns:
        True if valid semver format
    """
    pattern = r'^\d+\.\d+\.\d+(-[0-9A-Za-z\.-]+)?$'
    return bool(re.match(pattern, version))


class SpecValidationError(Exception):
    """Exception for spec validation errors"""
    
    def __init__(self, message: str, errors: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message)
        self.errors = errors or []


class SpecValidator:
    """
    Validator for HomeIQ Automation Specs.
    
    This class provides comprehensive validation for automation specifications,
    combining JSON Schema validation with custom business logic rules. It
    ensures specs are well-formed, semantically correct, and ready for execution.
    
    Features:
    - JSON Schema validation (structural correctness)
    - Semver enforcement (version format validation)
    - Custom business rules (trigger/action requirements)
    - Detailed error reporting (structured error messages)
    - File format support (JSON and YAML)
    
    Usage:
        >>> validator = SpecValidator()
        >>> is_valid, errors = validator.validate(spec_dict)
        >>> if not is_valid:
        ...     print(validator.format_errors(errors))
    
    Performance:
    - Schema is loaded once and cached
    - Validation is efficient for large specs
    - Error collection stops at first critical failure (configurable)
    """
    
    def __init__(self, schema: Optional[Dict[str, Any]] = None):
        """
        Initialize validator.
        
        Creates a new validator instance. If no schema is provided, loads
        the default schema from the implementation directory. The schema
        is cached globally to avoid repeated file I/O.
        
        Args:
            schema: Optional schema dictionary. If not provided, loads from
                the default schema file path. Useful for testing with mock
                schemas or custom validation rules.
        
        Raises:
            FileNotFoundError: If schema file not found (when loading default)
            json.JSONDecodeError: If schema file contains invalid JSON
            OSError: If schema file cannot be read
        """
        if schema is not None:
            if not isinstance(schema, dict):
                raise TypeError(f"schema must be dict, got {type(schema).__name__}")
            self.schema = schema
        else:
            self.schema = load_schema()
        
        try:
            self.validator = jsonschema.Draft202012Validator(self.schema)
        except jsonschema.SchemaError as e:
            raise ValueError(f"Invalid JSON Schema: {e}") from e
    
    def validate(self, spec: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Validate automation spec.
        
        Args:
            spec: Automation spec dictionary
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate semver
        version = spec.get("version")
        if version:
            if not validate_semver(version):
                errors.append({
                    "field": "version",
                    "message": f"Invalid semver format: {version}",
                    "value": version
                })
        
        # Validate JSON Schema
        try:
            self.validator.validate(spec)
        except ValidationError as e:
            errors.append({
                "field": ".".join(str(p) for p in e.path),
                "message": e.message,
                "value": e.instance,
                "schema_path": list(e.schema_path)
            })
        
        # Additional custom validations
        custom_errors = self._validate_custom_rules(spec)
        errors.extend(custom_errors)
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def _validate_custom_rules(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Apply custom validation rules beyond JSON Schema.
        
        This method enforces business logic rules that cannot be expressed
        in JSON Schema alone, such as:
        - Trigger type-specific required fields
        - Action target validation
        - Cross-field dependencies
        
        Args:
            spec: Automation spec dictionary
        
        Returns:
            List of error dictionaries with field, message, and value keys
            
        Note:
            Errors are returned as dictionaries to provide structured
            feedback for debugging and user-facing error messages.
        """
        errors = []
        
        # Validate triggers exist
        triggers = spec.get("triggers", [])
        if not triggers:
            errors.append({
                "field": "triggers",
                "message": "At least one trigger is required",
                "value": triggers
            })
            return errors  # Early return if no triggers
        
        # Validate actions exist
        actions = spec.get("actions", [])
        if not actions:
            errors.append({
                "field": "actions",
                "message": "At least one action is required",
                "value": actions
            })
            return errors  # Early return if no actions
        
        # Validate trigger types and required fields
        errors.extend(self._validate_trigger_types(triggers))
        
        # Validate action targets
        errors.extend(self._validate_action_targets(actions))
        
        return errors
    
    def _validate_trigger_types(self, triggers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate trigger types and their required fields.
        
        Args:
            triggers: List of trigger dictionaries
        
        Returns:
            List of error dictionaries
        """
        errors = []
        
        for i, trigger in enumerate(triggers):
            trigger_type = trigger.get("type")
            
            if trigger_type == "ha_event":
                if "event_type" not in trigger:
                    errors.append({
                        "field": f"triggers[{i}].event_type",
                        "message": "event_type is required for ha_event triggers",
                        "value": trigger
                    })
            elif trigger_type == "schedule":
                if "cron" not in trigger:
                    errors.append({
                        "field": f"triggers[{i}].cron",
                        "message": "cron is required for schedule triggers",
                        "value": trigger
                    })
            elif trigger_type == "webhook":
                if "webhook_id" not in trigger:
                    errors.append({
                        "field": f"triggers[{i}].webhook_id",
                        "message": "webhook_id is required for webhook triggers",
                        "value": trigger
                    })
            # Note: "manual" trigger type has no required fields
        
        return errors
    
    def _validate_action_targets(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate action targets.
        
        Args:
            actions: List of action dictionaries
        
        Returns:
            List of error dictionaries
        """
        errors = []
        required_target_keys = ["entity_id", "area", "device_class", "user"]
        
        for i, action in enumerate(actions):
            target = action.get("target", {})
            if not any(key in target for key in required_target_keys):
                errors.append({
                    "field": f"actions[{i}].target",
                    "message": f"Target must specify one of: {', '.join(required_target_keys)}",
                    "value": target
                })
        
        return errors
    
    def validate_file(self, file_path: Path) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Validate spec from file.
        
        Args:
            file_path: Path to spec file (JSON or YAML)
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix in ['.yaml', '.yml']:
                    if not YAML_AVAILABLE:
                        return False, [{
                            "field": "file",
                            "message": "YAML support not available (pyyaml not installed)",
                            "value": str(file_path)
                        }]
                    spec = yaml.safe_load(f)
                else:
                    spec = json.load(f)
            
            return self.validate(spec)
        except FileNotFoundError:
            return False, [{
                "field": "file",
                "message": f"File not found: {file_path}",
                "value": str(file_path)
            }]
        except json.JSONDecodeError as e:
            return False, [{
                "field": "file",
                "message": f"Invalid JSON format: {e}",
                "value": str(file_path)
            }]
        except Exception as e:
            if YAML_AVAILABLE and isinstance(e, yaml.YAMLError):
                return False, [{
                    "field": "file",
                    "message": f"Invalid YAML format: {e}",
                    "value": str(file_path)
                }]
            return False, [{
                "field": "file",
                "message": f"Failed to read file: {e}",
                "value": str(file_path)
            }]
    
    def format_errors(self, errors: List[Dict[str, Any]]) -> str:
        """
        Format validation errors as human-readable string.
        
        Creates a formatted error message suitable for logging, user display,
        or debugging. Errors are numbered and include field paths and messages.
        
        Args:
            errors: List of error dictionaries from validate() method
        
        Returns:
            Formatted error string with numbered list of errors.
            Returns "No errors" if errors list is empty.
        
        Example:
            >>> errors = [
            ...     {"field": "version", "message": "Invalid semver format"},
            ...     {"field": "triggers", "message": "At least one trigger required"}
            ... ]
            >>> formatted = validator.format_errors(errors)
            >>> # Returns:
            >>> # "Validation failed with 2 error(s):
            >>> #   1. version: Invalid semver format
            >>> #   2. triggers: At least one trigger required"
        """
        if not errors:
            return "No errors"
        
        if not isinstance(errors, list):
            return f"Invalid errors format: expected list, got {type(errors).__name__}"
        
        error_count = len(errors)
        plural = "error" if error_count == 1 else "errors"
        lines = [f"Validation failed with {error_count} {plural}:"]
        
        for i, error in enumerate(errors, 1):
            if not isinstance(error, dict):
                lines.append(f"  {i}. [Invalid error format: {type(error).__name__}]")
                continue
            
            field = error.get("field", "unknown")
            message = error.get("message", "Unknown error")
            value = error.get("value")
            
            # Include value if it's short and informative
            if value is not None and isinstance(value, (str, int, float, bool)):
                value_str = str(value)
                if len(value_str) <= 50:
                    lines.append(f"  {i}. {field}: {message} (value: {value_str})")
                else:
                    lines.append(f"  {i}. {field}: {message}")
            else:
                lines.append(f"  {i}. {field}: {message}")
        
        return "\n".join(lines)


# Convenience function
def validate_spec(spec: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Validate automation spec (convenience function).
    
    Args:
        spec: Automation spec dictionary
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    validator = SpecValidator()
    return validator.validate(spec)

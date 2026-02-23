"""
Version constants for the HA Automation Lint Engine.
These versions control rule stability and API compatibility.
"""

# Engine version (semantic versioning)
ENGINE_VERSION = "0.1.0"

# Ruleset version (changes when rules are added/modified/removed)
RULESET_VERSION = "2026.02.1"

# Supported automation formats
SUPPORTED_FORMATS = {
    "single_automation",  # Single automation dictionary
    "automation_list",    # List of automations
}


# Severity levels
class Severity:
    """Severity levels for lint findings."""
    ERROR = "error"
    WARN = "warn"
    INFO = "info"


# Rule categories
class RuleCategory:
    """Categories for organizing lint rules."""
    SYNTAX = "syntax"
    SCHEMA = "schema"
    LOGIC = "logic"
    RELIABILITY = "reliability"
    MAINTAINABILITY = "maintainability"


# Fix modes
class FixMode:
    """Auto-fix operation modes."""
    NONE = "none"
    SAFE = "safe"
    OPINIONATED = "opinionated"  # Future use


# Batch limits (security/abuse protection)
MAX_YAML_SIZE_BYTES = 500_000  # 500KB
MAX_AUTOMATIONS_PER_REQUEST = 100
PROCESSING_TIMEOUT_SECONDS = 30

# Common Home Assistant entity ID pattern
ENTITY_ID_PATTERN = r"^[a-z_]+\.[a-z0-9_]+$"

# Valid automation modes
VALID_MODES = {"single", "restart", "queued", "parallel"}

# High-frequency trigger platforms that may need debouncing
HIGH_FREQUENCY_TRIGGERS = {
    "state",
    "time_pattern",
    "event"
}

"""
Version-Aware YAML Renderer

Renders AutomationSpec to YAML based on Home Assistant version capabilities.
Adapts YAML output to match the target Home Assistant version.
"""

import logging
from typing import Any

import yaml

from .renderer import AutomationRenderer
from .schema import AutomationSpec

logger = logging.getLogger(__name__)


class VersionAwareRenderer:
    """
    Renders AutomationSpec to YAML based on HA version.
    
    Features:
    - Version-specific field handling (e.g., initial_state required in 2025.10+)
    - Blueprint pattern application
    - Feature detection (what features are available in target version)
    - Fallback for older versions
    """
    
    def __init__(self, ha_version: str | None = None):
        """
        Initialize version-aware renderer.
        
        Args:
            ha_version: Target Home Assistant version (e.g., "2025.10.3")
        """
        self.ha_version = ha_version
        self.base_renderer = AutomationRenderer()
        
        # Extract major.minor version
        self.major_minor = self._get_major_minor(ha_version) if ha_version else None
        
        # Determine capabilities
        self.capabilities = self._determine_capabilities()
    
    def render(self, spec: AutomationSpec) -> str:
        """
        Render AutomationSpec to YAML based on HA version.
        
        Args:
            spec: AutomationSpec instance
        
        Returns:
            YAML string adapted for target HA version
        """
        # Create version-adapted spec
        adapted_spec = self._adapt_spec_for_version(spec)
        
        # Render using base renderer
        yaml_dict = self.base_renderer._spec_to_dict(adapted_spec)
        
        # Apply version-specific transformations
        yaml_dict = self._apply_version_transformations(yaml_dict)
        
        # Generate YAML
        yaml_str = yaml.safe_dump(
            yaml_dict,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=1000,
            indent=2
        )
        
        return yaml_str.strip()
    
    def _get_major_minor(self, version: str) -> str:
        """Extract major.minor version from full version string."""
        parts = version.split(".")
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}"
        return version
    
    def _determine_capabilities(self) -> dict[str, bool]:
        """Determine capabilities based on version."""
        if not self.major_minor:
            # Default: assume latest features
            return {
                "initial_state_required": True,
                "singular_trigger_action": True,
                "singular_action": True,
                "error_handling": True,
            }
        
        # Version-specific capabilities
        if self.major_minor >= "2025.1":
            return {
                "initial_state_required": True,
                "singular_trigger_action": True,  # trigger: not triggers:
                "singular_action": True,  # action: not actions:
                "error_handling": True,  # error: continue instead of continue_on_error
            }
        elif self.major_minor >= "2024.12":
            return {
                "initial_state_required": False,
                "singular_trigger_action": False,  # Uses triggers: and actions:
                "singular_action": False,
                "error_handling": False,  # Uses continue_on_error
            }
        else:
            # Older versions
            return {
                "initial_state_required": False,
                "singular_trigger_action": False,
                "singular_action": False,
                "error_handling": False,
            }
    
    def _adapt_spec_for_version(self, spec: AutomationSpec) -> AutomationSpec:
        """Adapt AutomationSpec for target version."""
        # Ensure initial_state is set for 2025.10+
        if self.capabilities.get("initial_state_required", True):
            if not hasattr(spec, "initial_state") or spec.initial_state is None:
                spec.initial_state = True
        
        return spec
    
    def _apply_version_transformations(self, yaml_dict: dict[str, Any]) -> dict[str, Any]:
        """Apply version-specific transformations to YAML dictionary."""
        # Handle singular vs plural keys
        if not self.capabilities.get("singular_trigger_action", True):
            # Convert trigger: to triggers:
            if "trigger" in yaml_dict:
                yaml_dict["triggers"] = yaml_dict.pop("trigger")
        
        if not self.capabilities.get("singular_action", True):
            # Convert action: to actions:
            if "action" in yaml_dict:
                yaml_dict["actions"] = yaml_dict.pop("action")
        
        # Handle error handling format
        if not self.capabilities.get("error_handling", True):
            # Convert error: to continue_on_error
            self._convert_error_handling(yaml_dict)
        
        return yaml_dict
    
    def _convert_error_handling(self, yaml_dict: dict[str, Any]):
        """Convert error: to continue_on_error format for older versions."""
        if "action" in yaml_dict:
            actions = yaml_dict["action"]
        elif "actions" in yaml_dict:
            actions = yaml_dict["actions"]
        else:
            return
        
        if not isinstance(actions, list):
            return
        
        for action in actions:
            if isinstance(action, dict):
                if "error" in action:
                    error_value = action.pop("error")
                    if error_value == "continue":
                        action["continue_on_error"] = True
                    elif error_value == "stop":
                        action["continue_on_error"] = False
                    # "abort" doesn't have a direct equivalent in older versions


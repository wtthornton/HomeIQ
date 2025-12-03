"""
Mock Safety Validator

Safety check simulation for simulation.
Maintains same interface as production SafetyValidator.
"""

import logging
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class MockSafetyValidator:
    """
    Mock Safety Validator for simulation.
    
    Provides deterministic safety validation without complex checks.
    Maintains same interface as production SafetyValidator.
    """

    def __init__(self, safety_level: str = "moderate"):
        """
        Initialize mock safety validator.
        
        Args:
            safety_level: Safety level (not used in mock)
        """
        self.safety_level = safety_level
        
        logger.info(f"MockSafetyValidator initialized: safety_level={safety_level}")

    async def validate(
        self,
        automation_yaml: str,
        existing_automations: list[dict] | None = None
    ) -> dict[str, Any]:
        """
        Validate automation safety (mock validation).
        
        Args:
            automation_yaml: Automation YAML string
            existing_automations: List of existing automations (not used)
            
        Returns:
            Safety validation result
        """
        # Basic YAML validation
        try:
            automation = yaml.safe_load(automation_yaml)
            if not automation:
                return {
                    "passed": False,
                    "safety_score": 0.0,
                    "issues": [{
                        "rule": "yaml_syntax",
                        "severity": "critical",
                        "message": "Invalid or empty YAML"
                    }],
                    "can_override": False,
                    "summary": "Cannot validate: Invalid YAML"
                }
        except yaml.YAMLError as e:
            return {
                "passed": False,
                "safety_score": 0.0,
                "issues": [{
                    "rule": "yaml_syntax",
                    "severity": "critical",
                    "message": f"Invalid YAML syntax: {e}"
                }],
                "can_override": False,
                "summary": "Cannot validate: Invalid YAML"
            }

        # Mock validation: always passes for valid YAML
        issues = []
        
        # Check for obvious dangerous patterns (basic mock checks)
        yaml_str = automation_yaml.lower()
        if "disable" in yaml_str and "security" in yaml_str:
            issues.append({
                "rule": "security_disable",
                "severity": "critical",
                "message": "Attempting to disable security automation"
            })
        
        # Calculate safety score
        if issues:
            safety_score = 0.5
            passed = False
        else:
            safety_score = 1.0
            passed = True

        result = {
            "passed": passed,
            "safety_score": safety_score,
            "issues": issues,
            "can_override": len(issues) > 0 and all(i.get("severity") != "critical" for i in issues),
            "summary": f"Safety validation: {'PASSED' if passed else 'FAILED'} (score={safety_score:.2f})"
        }
        
        logger.debug(f"Safety validation: passed={passed}, score={safety_score}, issues={len(issues)}")
        return result

    async def validate_automation(
        self,
        automation_yaml: str,
        automation_id: str | None = None,
        validated_entities: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Validate automation (alternative interface).
        
        Args:
            automation_yaml: Automation YAML string
            automation_id: Optional automation ID
            validated_entities: List of validated entities (not used)
            
        Returns:
            Validation result dictionary
        """
        # Use same validation logic
        result = await self.validate(automation_yaml)
        
        # Convert to alternative format
        return {
            "safe": result["passed"],
            "issues": result["issues"],
            "warnings": [i for i in result["issues"] if i.get("severity") == "warning"],
            "coverage": 0.9 if result["passed"] else 0.5  # Mock coverage
        }


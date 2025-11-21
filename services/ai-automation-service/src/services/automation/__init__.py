"""
Automation Services Module

Consolidates automation-related functionality:
- YAML Generation: Generate automation YAML from suggestions
- Validation: Multi-stage validation pipeline
- Correction: Self-correction for YAML errors
- Testing: Test automation execution
- Deployment: Deploy automations to Home Assistant

Created: Phase 2 - Core Service Refactoring
"""

from .deployer import AutomationDeployer
from .test_executor import AutomationTestExecutor
from .yaml_corrector import AutomationYAMLCorrector
from .yaml_generator import AutomationYAMLGenerator
from .yaml_validator import AutomationYAMLValidator

__all__ = [
    "AutomationDeployer",
    "AutomationTestExecutor",
    "AutomationYAMLCorrector",
    "AutomationYAMLGenerator",
    "AutomationYAMLValidator",
]


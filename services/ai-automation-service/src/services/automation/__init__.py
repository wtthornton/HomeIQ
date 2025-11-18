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

from .yaml_generator import AutomationYAMLGenerator
from .yaml_validator import AutomationYAMLValidator
from .yaml_corrector import AutomationYAMLCorrector
from .test_executor import AutomationTestExecutor
from .deployer import AutomationDeployer

__all__ = [
    'AutomationYAMLGenerator',
    'AutomationYAMLValidator',
    'AutomationYAMLCorrector',
    'AutomationTestExecutor',
    'AutomationDeployer'
]


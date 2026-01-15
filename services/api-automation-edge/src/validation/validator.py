"""
Main Validation Pipeline

Orchestrates all validation stages and produces execution plan
"""

import logging
from typing import Any, Dict, Optional

from ..capability.capability_graph import CapabilityGraph

from .policy_validator import PolicyValidator
from .preflight_checker import PreflightChecker
from .service_validator import ServiceValidator
from .target_resolver import TargetResolver

logger = logging.getLogger(__name__)


class Validator:
    """
    Main validation pipeline.
    
    Orchestrates:
    1. Spec schema validation
    2. Target resolution (capabilities → entities)
    3. Service availability + field validation
    4. Feature compatibility (supported features)
    5. Policy gating (risk level, quiet hours, confirmations)
    6. Dry-run plan output
    7. Optional live preflight (availability/online)
    """
    
    def __init__(
        self,
        capability_graph: CapabilityGraph,
        rest_client: Optional[Any] = None
    ):
        """
        Initialize validator.
        
        Args:
            capability_graph: CapabilityGraph instance
            rest_client: Optional REST client for preflight checks
        """
        self.capability_graph = capability_graph
        
        # Initialize validators
        self.target_resolver = TargetResolver(capability_graph)
        self.service_validator = ServiceValidator(capability_graph)
        self.policy_validator = PolicyValidator()
        self.preflight_checker = PreflightChecker(capability_graph, rest_client)
    
    async def validate(
        self,
        spec: Dict[str, Any],
        perform_preflight: bool = False,
        current_risk_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate automation spec and produce execution plan.
        
        Args:
            spec: Automation spec dictionary
            perform_preflight: Whether to perform live preflight check
            current_risk_state: Optional current risk state
        
        Returns:
            Validation result dictionary with:
            - is_valid: bool
            - errors: list of error messages
            - execution_plan: execution plan (if valid)
            - warnings: list of warnings
        """
        errors = []
        warnings = []
        
        # 1. Target resolution
        try:
            execution_plan = self.target_resolver.create_execution_plan(spec)
        except Exception as e:
            errors.append(f"Target resolution failed: {str(e)}")
            return {
                "is_valid": False,
                "errors": errors,
                "execution_plan": None,
                "warnings": warnings
            }
        
        # 2. Service compatibility
        actions = execution_plan.get("actions", [])
        is_valid_services, service_errors = self.service_validator.validate_actions(actions)
        if not is_valid_services:
            for action_id, action_errors in service_errors.items():
                errors.extend([f"Action {action_id}: {error}" for error in action_errors])
        
        # 3. Policy gates
        is_valid_policy, policy_errors = self.policy_validator.validate_policy(
            spec, current_risk_state
        )
        if not is_valid_policy:
            errors.extend(policy_errors)
        
        # 4. Live preflight (optional)
        if perform_preflight:
            is_valid_preflight, preflight_errors = await self.preflight_checker.preflight_check(spec)
            if not is_valid_preflight:
                errors.extend(preflight_errors)
        
        # Check if spec is enabled
        if not spec.get("enabled", True):
            warnings.append("Spec is disabled")
        
        is_valid = len(errors) == 0
        
        result = {
            "is_valid": is_valid,
            "errors": errors,
            "execution_plan": execution_plan if is_valid else None,
            "warnings": warnings
        }
        
        if is_valid:
            logger.info(
                f"Validation successful for spec {spec.get('id')}: "
                f"{execution_plan['total_actions']} actions, "
                f"{execution_plan['total_entities']} entities"
            )
        else:
            logger.warning(
                f"Validation failed for spec {spec.get('id')}: {len(errors)} errors"
            )
        
        return result

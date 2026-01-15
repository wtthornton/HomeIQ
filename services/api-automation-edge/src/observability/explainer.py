"""
Explainability System

Epic F3: Store decision factors and provide user-facing explanations
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Explainer:
    """
    Explainability system for automation decisions.
    
    Features:
    - Store decision factors (triggers matched, conditions applied, targets resolved)
    - User-facing explanation templates
    - "Why did this happen?" query interface
    """
    
    def __init__(self):
        """Initialize explainer"""
        # Store explanations by correlation_id
        self.explanations: Dict[str, Dict[str, Any]] = {}
    
    def record_decision_factors(
        self,
        correlation_id: str,
        spec_id: str,
        triggers_matched: List[Dict[str, Any]],
        conditions_applied: List[Dict[str, Any]],
        targets_resolved: Dict[str, List[str]],
        policy_checks: Dict[str, Any],
        execution_plan: Dict[str, Any]
    ):
        """
        Record decision factors for an execution.
        
        Args:
            correlation_id: Correlation ID
            spec_id: Spec ID
            triggers_matched: List of matched triggers
            conditions_applied: List of applied conditions
            targets_resolved: Dictionary mapping action IDs to resolved entity IDs
            policy_checks: Policy check results
            execution_plan: Execution plan
        """
        self.explanations[correlation_id] = {
            "spec_id": spec_id,
            "triggers_matched": triggers_matched,
            "conditions_applied": conditions_applied,
            "targets_resolved": targets_resolved,
            "policy_checks": policy_checks,
            "execution_plan": execution_plan
        }
        
        logger.debug(f"Recorded decision factors for {correlation_id}")
    
    def get_explanation(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get explanation for a correlation ID.
        
        Args:
            correlation_id: Correlation ID
        
        Returns:
            Explanation dictionary or None
        """
        return self.explanations.get(correlation_id)
    
    def generate_user_explanation(
        self,
        correlation_id: str
    ) -> Optional[str]:
        """
        Generate user-facing explanation.
        
        Args:
            correlation_id: Correlation ID
        
        Returns:
            Human-readable explanation string
        """
        explanation = self.get_explanation(correlation_id)
        if not explanation:
            return None
        
        spec_id = explanation.get("spec_id", "unknown")
        triggers = explanation.get("triggers_matched", [])
        conditions = explanation.get("conditions_applied", [])
        targets = explanation.get("targets_resolved", {})
        
        lines = [f"Automation '{spec_id}' executed because:"]
        
        # Triggers
        if triggers:
            lines.append("  Triggers:")
            for trigger in triggers:
                trigger_type = trigger.get("type", "unknown")
                lines.append(f"    - {trigger_type} occurred")
        
        # Conditions
        if conditions:
            lines.append("  Conditions met:")
            for condition in conditions:
                condition_type = condition.get("type", "unknown")
                lines.append(f"    - {condition_type}")
        
        # Actions
        if targets:
            lines.append("  Actions executed:")
            for action_id, entity_ids in targets.items():
                lines.append(f"    - {action_id} on {len(entity_ids)} entity(ies)")
        
        return "\n".join(lines)
    
    def explain_why(
        self,
        correlation_id: str,
        question: str = "why"
    ) -> str:
        """
        Answer "Why did this happen?" query.
        
        Args:
            correlation_id: Correlation ID
            question: Question type (default: "why")
        
        Returns:
            Explanation string
        """
        explanation = self.generate_user_explanation(correlation_id)
        if explanation:
            return explanation
        
        return f"No explanation found for correlation ID: {correlation_id}"

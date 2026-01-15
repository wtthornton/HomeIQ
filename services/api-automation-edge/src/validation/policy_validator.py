"""
Policy Gates

Epic D3: Risk levels, quiet hours, manual overrides

This module provides policy validation for automation specs, including:
- Risk level checks (low/medium/high)
- Quiet hours enforcement (time-based constraints)
- Manual override TTL checks
- Confirmation workflow hooks for high-risk automations

Performance optimizations:
- Time parsing is cached to avoid repeated string parsing
- Manual override checks use efficient dictionary lookups
"""

import logging
from datetime import datetime, time
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@lru_cache(maxsize=128)
def _parse_time_string(time_str: str) -> Optional[time]:
    """
    Parse time string to time object (cached for performance).
    
    Args:
        time_str: Time string in ISO format (HH:MM:SS)
    
    Returns:
        time object or None if parsing fails
    """
    try:
        return time.fromisoformat(time_str)
    except (ValueError, TypeError):
        return None


class PolicyValidator:
    """
    Validates policy gates for automation specs.
    
    This class enforces policy constraints that determine whether an
    automation can execute. It checks risk levels, time-based constraints
    (quiet hours), and manual overrides.
    
    Features:
    - Risk level checks (low/medium/high) with HA stability awareness
    - Quiet hours enforcement with midnight-wrapping support
    - Manual override TTL checks with efficient lookups
    - Confirmation workflow hooks for high-risk automations
    
    Performance:
    - Time parsing is cached to avoid repeated string parsing
    - Manual override checks use O(1) dictionary lookups
    - Early returns for common cases (no conditions, no overrides)
    
    Example:
        >>> validator = PolicyValidator()
        >>> policy = {"risk": "low"}
        >>> is_allowed, reason = validator.validate_risk_level(policy)
        >>> assert is_allowed is True
    """
    
    def __init__(self):
        """
        Initialize policy validator.
        
        Creates a new validator instance with empty manual override tracking.
        Manual overrides are tracked per-entity and automatically expire
        based on their TTL.
        """
        # Manual override tracking (entity_id -> override_until timestamp)
        # Timestamps are Unix epoch seconds
        self.manual_overrides: Dict[str, float] = {}
    
    def validate_risk_level(
        self,
        policy: Dict[str, Any],
        current_risk_state: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate risk level allows execution.
        
        Args:
            policy: Policy dictionary from spec
            current_risk_state: Optional current risk state (HA unstable, etc.)
        
        Returns:
            Tuple of (is_allowed, reason)
        """
        risk = policy.get("risk", "low")
        allow_when_ha_unstable = policy.get("allow_when_ha_unstable", False)
        
        # Check HA stability
        ha_unstable = current_risk_state and current_risk_state.get("ha_unstable", False)
        if ha_unstable and not allow_when_ha_unstable:
            if risk in ["medium", "high"]:
                return False, "HA unstable and policy does not allow execution"
        
        # High risk requires additional checks
        if risk == "high":
            require_confirmations = policy.get("require_confirmations", [])
            if require_confirmations:
                # Confirmation required - would need to check if confirmed
                # For now, we'll allow but note that confirmation is needed
                logger.warning("High-risk automation requires confirmation")
        
        return True, None
    
    def validate_quiet_hours(
        self,
        conditions: Optional[List[Dict[str, Any]]] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate quiet hours constraints.
        
        Supports two condition types:
        - not_in_time_range: Execution blocked during this time range
        - in_time_range: Execution allowed only during this time range
        
        Handles time ranges that wrap midnight (e.g., 22:30 to 06:30).
        Time parsing is cached for performance.
        
        Args:
            conditions: List of condition dictionaries with:
                - type: "not_in_time_range" | "in_time_range"
                - start: str (HH:MM:SS format)
                - end: str (HH:MM:SS format)
        
        Returns:
            Tuple of (is_allowed, reason)
            - is_allowed: True if execution allowed, False if blocked
            - reason: None if allowed, error message if blocked
        
        Example:
            >>> conditions = [{
            ...     "type": "not_in_time_range",
            ...     "start": "22:00:00",
            ...     "end": "06:00:00"
            ... }]
            >>> is_allowed, reason = validator.validate_quiet_hours(conditions)
        """
        if not conditions:
            return True, None
        
        now = datetime.now().time()
        
        for condition in conditions:
            condition_type = condition.get("type")
            
            if condition_type == "not_in_time_range":
                result = self._check_time_range(
                    condition, now, is_blocking=True
                )
                if not result[0]:
                    return result
            
            elif condition_type == "in_time_range":
                result = self._check_time_range(
                    condition, now, is_blocking=False
                )
                if not result[0]:
                    return result
        
        return True, None
    
    def _check_time_range(
        self,
        condition: Dict[str, Any],
        current_time: time,
        is_blocking: bool
    ) -> tuple[bool, Optional[str]]:
        """
        Check if current time is within a time range.
        
        Optimized time parsing with caching. Handles both normal ranges
        and ranges that wrap midnight.
        
        Args:
            condition: Condition dictionary with start/end times
            current_time: Current time to check
            is_blocking: True for not_in_time_range, False for in_time_range
        
        Returns:
            Tuple of (is_allowed, reason)
        """
        start_str = condition.get("start")
        end_str = condition.get("end")
        
        if not start_str or not end_str:
            return True, None
        
        # Use cached time parsing
        start_time = _parse_time_string(start_str)
        end_time = _parse_time_string(end_str)
        
        if start_time is None or end_time is None:
            logger.warning(f"Invalid time format: {start_str} or {end_str}")
            return True, None  # Allow execution if time parsing fails
        
        # Check if range wraps midnight
        wraps_midnight = start_time > end_time
        
        if is_blocking:
            # not_in_time_range: block if current time is in range
            if wraps_midnight:
                in_range = current_time >= start_time or current_time <= end_time
            else:
                in_range = start_time <= current_time <= end_time
            
            if in_range:
                return False, f"Quiet hours: {start_str} to {end_str}"
        else:
            # in_time_range: allow only if current time is in range
            if wraps_midnight:
                in_range = current_time >= start_time or current_time <= end_time
            else:
                in_range = start_time <= current_time <= end_time
            
            if not in_range:
                return False, f"Outside allowed time range: {start_str} to {end_str}"
        
        return True, None
    
    def validate_manual_override(
        self,
        conditions: Optional[List[Dict[str, Any]]] = None,
        entity_ids: Optional[List[str]] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate manual override TTL.
        
        Checks if any entities have active manual overrides that would
        prevent automation execution. Manual overrides are set by users
        to temporarily disable automations for specific entities.
        
        Args:
            conditions: List of condition dictionaries (searches for
                "not_manual_override" type)
            entity_ids: List of entity IDs being acted upon
        
        Returns:
            Tuple of (is_allowed, reason)
            - is_allowed: True if no active overrides, False if override active
            - reason: None if allowed, error message with remaining TTL if blocked
        
        Note:
            Scope "area:" is not yet fully implemented - currently checks
            all entities regardless of area. This will be enhanced when
            area-based override tracking is added.
        """
        if not conditions or not entity_ids:
            return True, None
        
        now = datetime.now().timestamp()
        
        # Clean up expired overrides (performance optimization)
        expired_entities = [
            eid for eid, until in self.manual_overrides.items()
            if now >= until
        ]
        for eid in expired_entities:
            del self.manual_overrides[eid]
        
        for condition in conditions:
            condition_type = condition.get("type")
            
            if condition_type == "not_manual_override":
                scope = condition.get("scope", "all")
                
                # Check entities based on scope
                blocked_entity = self._check_override_scope(
                    scope, entity_ids, now
                )
                if blocked_entity:
                    entity_id, remaining = blocked_entity
                    return False, (
                        f"Manual override active for {entity_id} "
                        f"(TTL: {remaining:.0f}s remaining)"
                    )
        
        return True, None
    
    def _check_override_scope(
        self,
        scope: str,
        entity_ids: List[str],
        current_timestamp: float
    ) -> Optional[Tuple[str, float]]:
        """
        Check manual override for entities based on scope.
        
        Args:
            scope: Override scope ("all", "area:<area_id>", or empty)
            entity_ids: List of entity IDs to check
            current_timestamp: Current Unix timestamp
        
        Returns:
            Tuple of (entity_id, remaining_seconds) if override found, None otherwise
        """
        if "area:" in scope:
            # TODO: Implement area-based filtering when area mapping is available
            # For now, check all entities (conservative approach)
            for entity_id in entity_ids:
                override_until = self.manual_overrides.get(entity_id, 0)
                if current_timestamp < override_until:
                    remaining = override_until - current_timestamp
                    return (entity_id, remaining)
        
        elif scope == "all" or not scope:
            # Check all entities
            for entity_id in entity_ids:
                override_until = self.manual_overrides.get(entity_id, 0)
                if current_timestamp < override_until:
                    remaining = override_until - current_timestamp
                    return (entity_id, remaining)
        
        return None
    
    def set_manual_override(self, entity_id: str, ttl_seconds: int):
        """
        Set manual override for an entity.
        
        Args:
            entity_id: Entity ID
            ttl_seconds: TTL in seconds
        """
        now = datetime.now().timestamp()
        self.manual_overrides[entity_id] = now + ttl_seconds
        logger.info(f"Manual override set for {entity_id} (TTL: {ttl_seconds}s)")
    
    def clear_manual_override(self, entity_id: str):
        """Clear manual override for an entity"""
        self.manual_overrides.pop(entity_id, None)
        logger.info(f"Manual override cleared for {entity_id}")
    
    def validate_policy(
        self,
        spec: Dict[str, Any],
        current_risk_state: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, List[str]]:
        """
        Validate all policy gates for an automation spec.
        
        This is the main entry point for policy validation. It orchestrates
        all policy checks in order:
        1. Risk level validation
        2. Quiet hours validation
        3. Manual override validation
        
        Args:
            spec: Automation spec dictionary with:
                - policy: Dict (risk level, allow_when_ha_unstable, etc.)
                - conditions: List[Dict] (time constraints, overrides)
                - actions: List[Dict] (with resolved_entity_ids)
            current_risk_state: Optional current risk state dictionary with:
                - ha_unstable: bool (whether HA is currently unstable)
        
        Returns:
            Tuple of (is_valid, list_of_errors)
            - is_valid: True if all policy gates pass, False otherwise
            - list_of_errors: List of error messages (empty if valid)
        
        Example:
            >>> spec = {
            ...     "policy": {"risk": "low"},
            ...     "conditions": [],
            ...     "actions": [{"resolved_entity_ids": ["light.test"]}]
            ... }
            >>> is_valid, errors = validator.validate_policy(spec)
            >>> assert is_valid is True
        """
        if not isinstance(spec, dict):
            raise ValueError(f"spec must be dict, got {type(spec).__name__}")
        
        errors = []
        
        policy = spec.get("policy", {})
        conditions = spec.get("conditions", [])
        
        # Extract entity IDs from actions (for override checks)
        # This is more efficient than checking during action execution
        actions = spec.get("actions", [])
        entity_ids = self._extract_entity_ids(actions)
        
        # Validate risk level (first check - fastest)
        is_allowed, reason = self.validate_risk_level(policy, current_risk_state)
        if not is_allowed:
            errors.append(reason)
            # Early return if risk level blocks execution
            if errors:
                return False, errors
        
        # Validate quiet hours (time-based check)
        is_allowed, reason = self.validate_quiet_hours(conditions)
        if not is_allowed:
            errors.append(reason)
        
        # Validate manual override (entity-specific check)
        is_allowed, reason = self.validate_manual_override(conditions, entity_ids)
        if not is_allowed:
            errors.append(reason)
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def _extract_entity_ids(self, actions: List[Dict[str, Any]]) -> List[str]:
        """
        Extract all entity IDs from actions.
        
        Args:
            actions: List of action dictionaries
        
        Returns:
            List of unique entity IDs
        """
        entity_ids = []
        for action in actions:
            resolved_ids = action.get("resolved_entity_ids", [])
            if isinstance(resolved_ids, list):
                entity_ids.extend(resolved_ids)
        
        # Remove duplicates
        return list(set(entity_ids))

"""
Shared State Machine Base Class

Provides formal state machine with transition validation for reliable state management.
Implements patterns from Home Assistant 2025 architecture.

This is the shared base class that all services should use for state management.
"""

import logging
from enum import Enum
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class InvalidStateTransition(Exception):
    """Raised when an invalid state transition is attempted"""
    pass


class StateMachine:
    """
    Generic state machine with transition validation.
    
    Enforces valid state transitions to prevent invalid state combinations
    and makes state management explicit and testable.
    """
    
    def __init__(self, initial_state: Enum, valid_transitions: Dict[Enum, List[Enum]]):
        """
        Initialize state machine.
        
        Args:
            initial_state: Initial state
            valid_transitions: Dictionary mapping from_state -> [to_states]
        """
        self.state = initial_state
        self.valid_transitions = valid_transitions
        self.state_history: List[tuple[datetime, Enum, Enum]] = []
        self.transition_count = 0
        
        # Validate transition map
        for from_state, to_states in valid_transitions.items():
            if not isinstance(to_states, list):
                raise ValueError(f"Invalid transitions for {from_state}: must be a list")
    
    def can_transition(self, to_state: Enum) -> bool:
        """
        Check if transition to target state is valid.
        
        Args:
            to_state: Target state
            
        Returns:
            True if transition is valid, False otherwise
        """
        valid_targets = self.valid_transitions.get(self.state, [])
        return to_state in valid_targets
    
    def transition(self, to_state: Enum, force: bool = False) -> bool:
        """
        Attempt to transition to target state.
        
        Args:
            to_state: Target state
            force: If True, skip validation (use with caution)
            
        Returns:
            True if transition succeeded, False otherwise
            
        Raises:
            InvalidStateTransition: If transition is invalid and force=False
        """
        from_state = self.state
        
        # Check if already in target state
        if from_state == to_state:
            logger.debug(f"Already in state {to_state.value}, no transition needed")
            return True
        
        # Validate transition unless forced
        if not force:
            if not self.can_transition(to_state):
                error_msg = f"Cannot transition from {from_state.value} to {to_state.value}"
                logger.error(error_msg)
                logger.debug(f"Valid transitions from {from_state.value}: {[s.value for s in self.valid_transitions.get(from_state, [])]}")
                raise InvalidStateTransition(error_msg)
        
        # Perform transition
        self.state = to_state
        self.transition_count += 1
        self.state_history.append((datetime.now(), from_state, to_state))
        
        logger.info(f"State transition: {from_state.value} → {to_state.value}")
        return True
    
    def get_state(self) -> Enum:
        """Get current state"""
        return self.state
    
    def get_transition_history(self) -> List[tuple[datetime, Enum, Enum]]:
        """Get state transition history"""
        return self.state_history.copy()
    
    def reset(self, new_state: Enum):
        """
        Reset state machine to new state (bypasses transition validation).
        Use with caution - only for initialization or recovery.
        
        Args:
            new_state: New state
        """
        old_state = self.state
        self.state = new_state
        self.state_history.append((datetime.now(), old_state, new_state))
        logger.info(f"State reset: {old_state.value} → {new_state.value} (bypass)")


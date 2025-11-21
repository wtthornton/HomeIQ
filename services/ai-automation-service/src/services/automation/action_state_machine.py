"""
Action Execution State Machine

State machine for tracking action execution states.
Uses shared state machine base class from shared/state_machine.py
"""

import logging
import os
import sys
from enum import Enum
from pathlib import Path

# Add shared directory to path for imports
shared_path_override = os.getenv("HOMEIQ_SHARED_PATH")
try:
    app_root = Path(__file__).resolve().parents[4]  # Go up to project root
except Exception:
    app_root = Path("/app")

candidate_paths = []
if shared_path_override:
    candidate_paths.append(Path(shared_path_override).expanduser())
candidate_paths.extend([
    app_root / "shared",
    Path("/app/shared"),
    Path.cwd() / "shared",
    Path(__file__).parent.parent.parent.parent.parent / "shared",  # Fallback for local dev
])

shared_path = None
for p in candidate_paths:
    if p.exists():
        shared_path = p.resolve()
        break

if shared_path and str(shared_path) not in sys.path:
    sys.path.insert(0, str(shared_path))

# Import shared state machine base class
# Re-export InvalidStateTransition for backward compatibility
from state_machine import StateMachine

logger = logging.getLogger(__name__)


class ActionExecutionState(Enum):
    """Action execution state enumeration"""
    QUEUED = "queued"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class ActionExecutionStateMachine(StateMachine):
    """
    State machine for action execution.

    Valid transitions:
    - QUEUED → EXECUTING, CANCELLED
    - EXECUTING → SUCCESS, FAILED, RETRYING, CANCELLED
    - RETRYING → EXECUTING, FAILED, CANCELLED
    - SUCCESS → (terminal state)
    - FAILED → (terminal state)
    - CANCELLED → (terminal state)
    """

    VALID_TRANSITIONS = {
        ActionExecutionState.QUEUED: [
            ActionExecutionState.EXECUTING,
            ActionExecutionState.CANCELLED,
        ],
        ActionExecutionState.EXECUTING: [
            ActionExecutionState.SUCCESS,
            ActionExecutionState.FAILED,
            ActionExecutionState.RETRYING,
            ActionExecutionState.CANCELLED,
        ],
        ActionExecutionState.RETRYING: [
            ActionExecutionState.EXECUTING,
            ActionExecutionState.FAILED,
            ActionExecutionState.CANCELLED,
        ],
        ActionExecutionState.SUCCESS: [],  # Terminal state
        ActionExecutionState.FAILED: [],  # Terminal state
        ActionExecutionState.CANCELLED: [],  # Terminal state
    }

    def __init__(self, initial_state: ActionExecutionState = ActionExecutionState.QUEUED):
        super().__init__(initial_state, self.VALID_TRANSITIONS)


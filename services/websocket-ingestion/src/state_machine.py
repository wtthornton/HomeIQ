"""
State Machine Pattern for Connection and Service Management
Home Assistant Pattern Improvement #1 (2025)

Provides formal state machine with transition validation for reliable state management.
Implements patterns from Home Assistant 2025 architecture.

Uses shared state machine base class from shared/state_machine.py
"""

import logging
import sys
import os
from enum import Enum
from typing import Dict, List
from pathlib import Path

# Add shared directory to path for imports (same pattern as main.py)
shared_path_override = os.getenv('HOMEIQ_SHARED_PATH')
try:
    app_root = Path(__file__).resolve().parents[1]  # typically /app
except Exception:
    app_root = Path("/app")

candidate_paths = []
if shared_path_override:
    candidate_paths.append(Path(shared_path_override).expanduser())
candidate_paths.extend([
    app_root / "shared",
    Path("/app/shared"),
    Path.cwd() / "shared",
    Path(__file__).parent.parent.parent.parent / "shared",  # Fallback for local dev
])

shared_path = None
for p in candidate_paths:
    if p.exists():
        shared_path = p.resolve()
        break

if shared_path and str(shared_path) not in sys.path:
    sys.path.insert(0, str(shared_path))

# Import shared state machine base class
# Avoid circular import by importing from shared.state_machine explicitly
try:
    from shared.state_machine import StateMachine, InvalidStateTransition
except ImportError:
    # Fallback for different import path
    import importlib.util
    if shared_path:
        spec = importlib.util.spec_from_file_location("shared_state_machine", shared_path / "state_machine.py")
        shared_sm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(shared_sm)
        StateMachine = shared_sm.StateMachine
        InvalidStateTransition = shared_sm.InvalidStateTransition
    else:
        raise ImportError("Cannot find shared state_machine module")

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state enumeration"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class ConnectionStateMachine(StateMachine):
    """
    State machine for connection management.
    
    Valid transitions:
    - DISCONNECTED → CONNECTING
    - CONNECTING → AUTHENTICATING, FAILED
    - AUTHENTICATING → CONNECTED, FAILED
    - CONNECTED → RECONNECTING, DISCONNECTED
    - RECONNECTING → CONNECTING, FAILED
    - FAILED → RECONNECTING
    """
    
    VALID_TRANSITIONS = {
        ConnectionState.DISCONNECTED: [ConnectionState.CONNECTING],
        ConnectionState.CONNECTING: [ConnectionState.AUTHENTICATING, ConnectionState.FAILED],
        ConnectionState.AUTHENTICATING: [ConnectionState.CONNECTED, ConnectionState.FAILED],
        ConnectionState.CONNECTED: [ConnectionState.RECONNECTING, ConnectionState.DISCONNECTED],
        ConnectionState.RECONNECTING: [ConnectionState.CONNECTING, ConnectionState.FAILED],
        ConnectionState.FAILED: [ConnectionState.RECONNECTING]
    }
    
    def __init__(self):
        super().__init__(ConnectionState.DISCONNECTED, self.VALID_TRANSITIONS)


class ProcessingState(Enum):
    """Processing state enumeration"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


class ProcessingStateMachine(StateMachine):
    """
    State machine for batch/event processing.
    
    Valid transitions:
    - STOPPED → STARTING
    - STARTING → RUNNING, ERROR
    - RUNNING → PAUSED, STOPPING, ERROR
    - PAUSED → RUNNING, STOPPING
    - STOPPING → STOPPED
    - ERROR → STOPPED, STARTING
    """
    
    VALID_TRANSITIONS = {
        ProcessingState.STOPPED: [ProcessingState.STARTING],
        ProcessingState.STARTING: [ProcessingState.RUNNING, ProcessingState.ERROR],
        ProcessingState.RUNNING: [ProcessingState.PAUSED, ProcessingState.STOPPING, ProcessingState.ERROR],
        ProcessingState.PAUSED: [ProcessingState.RUNNING, ProcessingState.STOPPING],
        ProcessingState.STOPPING: [ProcessingState.STOPPED],
        ProcessingState.ERROR: [ProcessingState.STOPPED, ProcessingState.STARTING]
    }
    
    def __init__(self):
        super().__init__(ProcessingState.STOPPED, self.VALID_TRANSITIONS)


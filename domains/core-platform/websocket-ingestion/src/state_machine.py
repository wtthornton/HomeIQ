"""
State Machine Pattern for Connection and Service Management
Home Assistant Pattern Improvement #1 (2025)

Provides formal state machine with transition validation for reliable state management.
Implements patterns from Home Assistant 2025 architecture.

Uses shared state machine base class from shared/state_machine.py
"""

import logging
from enum import Enum

from homeiq_data.state_machine import InvalidStateTransition, StateMachine

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
    State machine for connection management with transition validation.

    Provides formal state management for WebSocket connection lifecycle, preventing
    invalid state transitions and ensuring reliable connection handling. Based on
    the shared StateMachine base class from shared/state_machine.py.

    State Flow:
    1. DISCONNECTED → CONNECTING (initial connection attempt)
    2. CONNECTING → AUTHENTICATING (WebSocket established, authenticating)
    3. AUTHENTICATING → CONNECTED (authentication successful)
    4. CONNECTED → RECONNECTING (connection lost, attempting reconnect)
    5. RECONNECTING → CONNECTING (reconnection attempt started)
    6. Any state → FAILED (critical error occurred)
    7. FAILED → RECONNECTING (automatic recovery)

    Valid Transitions:
    - DISCONNECTED → CONNECTING
    - CONNECTING → AUTHENTICATING, FAILED
    - AUTHENTICATING → CONNECTED, FAILED
    - CONNECTED → RECONNECTING, DISCONNECTED
    - RECONNECTING → CONNECTING, FAILED
    - FAILED → RECONNECTING

    Invalid transitions raise InvalidStateTransition exception.

    Example:
        machine = ConnectionStateMachine()
        machine.transition(ConnectionState.CONNECTING)  # Valid
        machine.transition(ConnectionState.CONNECTED)   # Invalid, raises exception
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


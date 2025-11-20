"""
Tests for State Machine Pattern (Home Assistant Pattern Improvement #1 - 2025)
"""


import pytest
from src.state_machine import (
    ConnectionState,
    ConnectionStateMachine,
    InvalidStateTransition,
    ProcessingState,
    ProcessingStateMachine,
)


class TestStateMachine:
    """Test generic state machine functionality"""

    def test_initial_state(self):
        """Test that state machine starts with initial state"""
        machine = ConnectionStateMachine()
        assert machine.get_state() == ConnectionState.DISCONNECTED

    def test_valid_transition(self):
        """Test that valid transitions work"""
        machine = ConnectionStateMachine()
        machine.transition(ConnectionState.CONNECTING)
        assert machine.get_state() == ConnectionState.CONNECTING

    def test_invalid_transition(self):
        """Test that invalid transitions raise exception"""
        machine = ConnectionStateMachine()
        machine.transition(ConnectionState.CONNECTING)

        # Cannot go directly from CONNECTING to CONNECTED (must go through AUTHENTICATING)
        with pytest.raises(InvalidStateTransition):
            machine.transition(ConnectionState.CONNECTED)

    def test_can_transition(self):
        """Test can_transition method"""
        machine = ConnectionStateMachine()
        assert machine.can_transition(ConnectionState.CONNECTING) is True
        assert machine.can_transition(ConnectionState.CONNECTED) is False

    def test_force_transition(self):
        """Test forced transitions bypass validation"""
        machine = ConnectionStateMachine()
        machine.transition(ConnectionState.CONNECTING)

        # Force transition that would normally be invalid
        machine.transition(ConnectionState.CONNECTED, force=True)
        assert machine.get_state() == ConnectionState.CONNECTED

    def test_transition_history(self):
        """Test that transition history is tracked"""
        machine = ConnectionStateMachine()
        machine.transition(ConnectionState.CONNECTING)
        machine.transition(ConnectionState.AUTHENTICATING)

        history = machine.get_transition_history()
        assert len(history) == 2
        assert history[0][1] == ConnectionState.DISCONNECTED
        assert history[0][2] == ConnectionState.CONNECTING
        assert history[1][1] == ConnectionState.CONNECTING
        assert history[1][2] == ConnectionState.AUTHENTICATING

    def test_reset(self):
        """Test reset method"""
        machine = ConnectionStateMachine()
        machine.transition(ConnectionState.CONNECTING)
        machine.reset(ConnectionState.DISCONNECTED)

        assert machine.get_state() == ConnectionState.DISCONNECTED
        history = machine.get_transition_history()
        assert len(history) == 2  # Includes reset transition


class TestConnectionStateMachine:
    """Test connection state machine specific transitions"""

    def test_connection_lifecycle(self):
        """Test full connection lifecycle"""
        machine = ConnectionStateMachine()

        # Start disconnected
        assert machine.get_state() == ConnectionState.DISCONNECTED

        # Begin connection
        machine.transition(ConnectionState.CONNECTING)
        assert machine.get_state() == ConnectionState.CONNECTING

        # Authenticate
        machine.transition(ConnectionState.AUTHENTICATING)
        assert machine.get_state() == ConnectionState.AUTHENTICATING

        # Connected
        machine.transition(ConnectionState.CONNECTED)
        assert machine.get_state() == ConnectionState.CONNECTED

        # Disconnect
        machine.transition(ConnectionState.DISCONNECTED)
        assert machine.get_state() == ConnectionState.DISCONNECTED

    def test_connection_failure(self):
        """Test connection failure path"""
        machine = ConnectionStateMachine()
        machine.transition(ConnectionState.CONNECTING)
        machine.transition(ConnectionState.FAILED)
        assert machine.get_state() == ConnectionState.FAILED

        # Can retry from failed
        machine.transition(ConnectionState.RECONNECTING)
        assert machine.get_state() == ConnectionState.RECONNECTING

    def test_reconnection_cycle(self):
        """Test reconnection cycle"""
        machine = ConnectionStateMachine()
        # Start connected
        machine.transition(ConnectionState.CONNECTING)
        machine.transition(ConnectionState.AUTHENTICATING)
        machine.transition(ConnectionState.CONNECTED)

        # Lose connection, go to reconnecting
        machine.transition(ConnectionState.RECONNECTING)

        # Reconnect
        machine.transition(ConnectionState.CONNECTING)
        machine.transition(ConnectionState.AUTHENTICATING)
        machine.transition(ConnectionState.CONNECTED)
        assert machine.get_state() == ConnectionState.CONNECTED

    def test_invalid_connection_transitions(self):
        """Test invalid connection transitions raise errors"""
        machine = ConnectionStateMachine()

        # Cannot go from disconnected to connected directly
        with pytest.raises(InvalidStateTransition):
            machine.transition(ConnectionState.CONNECTED)

        # Cannot go from disconnected to authenticating
        with pytest.raises(InvalidStateTransition):
            machine.transition(ConnectionState.AUTHENTICATING)

        # Cannot go from connected to failed (must go through reconnecting)
        machine.transition(ConnectionState.CONNECTING)
        machine.transition(ConnectionState.AUTHENTICATING)
        machine.transition(ConnectionState.CONNECTED)

        with pytest.raises(InvalidStateTransition):
            machine.transition(ConnectionState.FAILED)


class TestProcessingStateMachine:
    """Test processing state machine specific transitions"""

    def test_processing_lifecycle(self):
        """Test full processing lifecycle"""
        machine = ProcessingStateMachine()

        # Start stopped
        assert machine.get_state() == ProcessingState.STOPPED

        # Start processing
        machine.transition(ProcessingState.STARTING)
        assert machine.get_state() == ProcessingState.STARTING

        machine.transition(ProcessingState.RUNNING)
        assert machine.get_state() == ProcessingState.RUNNING

        # Stop processing
        machine.transition(ProcessingState.STOPPING)
        assert machine.get_state() == ProcessingState.STOPPING

        machine.transition(ProcessingState.STOPPED)
        assert machine.get_state() == ProcessingState.STOPPED

    def test_pause_resume(self):
        """Test pause and resume functionality"""
        machine = ProcessingStateMachine()
        machine.transition(ProcessingState.STARTING)
        machine.transition(ProcessingState.RUNNING)

        # Pause
        machine.transition(ProcessingState.PAUSED)
        assert machine.get_state() == ProcessingState.PAUSED

        # Resume
        machine.transition(ProcessingState.RUNNING)
        assert machine.get_state() == ProcessingState.RUNNING

    def test_error_recovery(self):
        """Test error state and recovery"""
        machine = ProcessingStateMachine()
        machine.transition(ProcessingState.STARTING)
        machine.transition(ProcessingState.RUNNING)

        # Error occurred
        machine.transition(ProcessingState.ERROR)
        assert machine.get_state() == ProcessingState.ERROR

        # Can restart from error
        machine.transition(ProcessingState.STARTING)
        assert machine.get_state() == ProcessingState.STARTING

    def test_invalid_processing_transitions(self):
        """Test invalid processing transitions raise errors"""
        machine = ProcessingStateMachine()

        # Cannot go from stopped to running directly
        with pytest.raises(InvalidStateTransition):
            machine.transition(ProcessingState.RUNNING)

        # Cannot go from stopped to paused
        with pytest.raises(InvalidStateTransition):
            machine.transition(ProcessingState.PAUSED)

        # Cannot go from stopped to stopping
        with pytest.raises(InvalidStateTransition):
            machine.transition(ProcessingState.STOPPING)

        # Cannot go from stopped to error
        with pytest.raises(InvalidStateTransition):
            machine.transition(ProcessingState.ERROR)


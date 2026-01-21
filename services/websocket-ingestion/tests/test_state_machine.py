"""
Tests for state_machine.py (ConnectionStateMachine, ProcessingStateMachine).

Uses path_setup for imports. Targets 80%+ coverage for src/state_machine.py.
"""

import importlib
import os
import sys
from pathlib import Path
from unittest.mock import patch

from tests.path_setup import add_service_src

add_service_src(__file__)

import pytest

from src.state_machine import (
    ConnectionState,
    ConnectionStateMachine,
    InvalidStateTransition,
    ProcessingState,
    ProcessingStateMachine,
)


def test_import_with_homeiq_shared_path_override():
    """Cover the HOMEIQ_SHARED_PATH branch (state_machine import-time)."""
    shared_dir = Path(__file__).resolve().parents[3] / "shared"
    if not shared_dir.exists():
        pytest.skip("repo shared dir not found")
    with patch.dict(os.environ, {"HOMEIQ_SHARED_PATH": str(shared_dir)}, clear=False):
        if "src.state_machine" in sys.modules:
            del sys.modules["src.state_machine"]
        mod = importlib.import_module("src.state_machine")
    assert hasattr(mod, "ConnectionState")
    assert hasattr(mod, "ProcessingStateMachine")


class TestConnectionStateMachine:
    """Tests for ConnectionStateMachine."""

    def test_init_starts_disconnected(self):
        m = ConnectionStateMachine()
        assert m.get_state() == ConnectionState.DISCONNECTED

    def test_valid_transition_disconnected_to_connecting(self):
        m = ConnectionStateMachine()
        m.transition(ConnectionState.CONNECTING)
        assert m.get_state() == ConnectionState.CONNECTING

    def test_valid_transition_connecting_to_authenticating(self):
        m = ConnectionStateMachine()
        m.transition(ConnectionState.CONNECTING)
        m.transition(ConnectionState.AUTHENTICATING)
        assert m.get_state() == ConnectionState.AUTHENTICATING

    def test_valid_transition_authenticating_to_connected(self):
        m = ConnectionStateMachine()
        m.transition(ConnectionState.CONNECTING)
        m.transition(ConnectionState.AUTHENTICATING)
        m.transition(ConnectionState.CONNECTED)
        assert m.get_state() == ConnectionState.CONNECTED

    def test_valid_transition_connecting_to_failed(self):
        m = ConnectionStateMachine()
        m.transition(ConnectionState.CONNECTING)
        m.transition(ConnectionState.FAILED)
        assert m.get_state() == ConnectionState.FAILED

    def test_valid_transition_failed_to_reconnecting(self):
        m = ConnectionStateMachine()
        m.transition(ConnectionState.CONNECTING)
        m.transition(ConnectionState.FAILED)
        m.transition(ConnectionState.RECONNECTING)
        assert m.get_state() == ConnectionState.RECONNECTING

    def test_invalid_transition_disconnected_to_connected_raises(self):
        m = ConnectionStateMachine()
        with pytest.raises(InvalidStateTransition):
            m.transition(ConnectionState.CONNECTED)

    def test_invalid_transition_connecting_to_connected_raises(self):
        m = ConnectionStateMachine()
        m.transition(ConnectionState.CONNECTING)
        with pytest.raises(InvalidStateTransition):
            m.transition(ConnectionState.CONNECTED)

    def test_can_transition_true(self):
        m = ConnectionStateMachine()
        assert m.can_transition(ConnectionState.CONNECTING) is True

    def test_can_transition_false(self):
        m = ConnectionStateMachine()
        assert m.can_transition(ConnectionState.CONNECTED) is False

    def test_transition_to_same_state_no_op(self):
        m = ConnectionStateMachine()
        m.transition(ConnectionState.CONNECTING)
        assert m.transition(ConnectionState.CONNECTING) is True
        assert m.get_state() == ConnectionState.CONNECTING

    def test_transition_count_increments(self):
        m = ConnectionStateMachine()
        m.transition(ConnectionState.CONNECTING)
        m.transition(ConnectionState.AUTHENTICATING)
        assert m.transition_count == 2


class TestProcessingStateMachine:
    """Tests for ProcessingStateMachine."""

    def test_init_starts_stopped(self):
        m = ProcessingStateMachine()
        assert m.get_state() == ProcessingState.STOPPED

    def test_valid_transition_stopped_to_starting(self):
        m = ProcessingStateMachine()
        m.transition(ProcessingState.STARTING)
        assert m.get_state() == ProcessingState.STARTING

    def test_valid_transition_starting_to_running(self):
        m = ProcessingStateMachine()
        m.transition(ProcessingState.STARTING)
        m.transition(ProcessingState.RUNNING)
        assert m.get_state() == ProcessingState.RUNNING

    def test_valid_transition_running_to_paused(self):
        m = ProcessingStateMachine()
        m.transition(ProcessingState.STARTING)
        m.transition(ProcessingState.RUNNING)
        m.transition(ProcessingState.PAUSED)
        assert m.get_state() == ProcessingState.PAUSED

    def test_valid_transition_stopping_to_stopped(self):
        m = ProcessingStateMachine()
        m.transition(ProcessingState.STARTING)
        m.transition(ProcessingState.RUNNING)
        m.transition(ProcessingState.STOPPING)
        m.transition(ProcessingState.STOPPED)
        assert m.get_state() == ProcessingState.STOPPED

    def test_valid_transition_error_to_starting(self):
        m = ProcessingStateMachine()
        m.transition(ProcessingState.STARTING)
        m.transition(ProcessingState.ERROR)
        m.transition(ProcessingState.STARTING)
        assert m.get_state() == ProcessingState.STARTING

    def test_invalid_transition_stopped_to_running_raises(self):
        m = ProcessingStateMachine()
        with pytest.raises(InvalidStateTransition):
            m.transition(ProcessingState.RUNNING)

    def test_can_transition(self):
        m = ProcessingStateMachine()
        assert m.can_transition(ProcessingState.STARTING) is True
        assert m.can_transition(ProcessingState.RUNNING) is False

    def test_get_transition_history(self):
        m = ProcessingStateMachine()
        m.transition(ProcessingState.STARTING)
        hist = m.get_transition_history()
        assert len(hist) == 1
        assert hist[0][1] == ProcessingState.STOPPED
        assert hist[0][2] == ProcessingState.STARTING

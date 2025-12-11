#!/usr/bin/env python3
"""
Quick integration test for State Machine Pattern
Tests that state machines work in runtime environment
Epic 50 Story 50.7: Code Organization - Moved from src/ to tests/integration/
"""

import sys
from pathlib import Path

# Add src directory to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from state_machine import ConnectionStateMachine, InvalidStateTransition, ProcessingStateMachine


def test_connection_state_machine():
    """Test connection state machine"""
    print("Testing ConnectionStateMachine...")
    machine = ConnectionStateMachine()

    # Test initial state
    assert machine.get_state().value == "disconnected"
    print("  ✓ Initial state: disconnected")

    # Test valid transitions
    machine.transition(machine.VALID_TRANSITIONS[machine.get_state()][0])
    assert machine.get_state().value == "connecting"
    print("  ✓ Transition: disconnected → connecting")

    machine.transition(machine.VALID_TRANSITIONS[machine.get_state()][0])
    assert machine.get_state().value == "authenticating"
    print("  ✓ Transition: connecting → authenticating")

    machine.transition(machine.VALID_TRANSITIONS[machine.get_state()][0])
    assert machine.get_state().value == "connected"
    print("  ✓ Transition: authenticating → connected")

    # Test invalid transition
    try:
        machine.transition(machine.VALID_TRANSITIONS[machine.get_state()][1])  # DISCONNECTED
        print("  ✓ Transition: connected → disconnected")
    except InvalidStateTransition:
        print("  ✗ Invalid transition detected (unexpected)")
        return False

    print("  ✅ ConnectionStateMachine tests passed\n")
    return True


def test_processing_state_machine():
    """Test processing state machine"""
    print("Testing ProcessingStateMachine...")
    machine = ProcessingStateMachine()

    # Test initial state
    assert machine.get_state().value == "stopped"
    print("  ✓ Initial state: stopped")

    # Test valid transitions
    machine.transition(machine.VALID_TRANSITIONS[machine.get_state()][0])
    assert machine.get_state().value == "starting"
    print("  ✓ Transition: stopped → starting")

    machine.transition(machine.VALID_TRANSITIONS[machine.get_state()][0])
    assert machine.get_state().value == "running"
    print("  ✓ Transition: starting → running")

    # Test invalid transition
    try:
        machine.transition(machine.VALID_TRANSITIONS[list(machine.VALID_TRANSITIONS.keys())[0]][0])
        print("  ✓ Valid transition")
    except InvalidStateTransition:
        print("  ✗ Invalid transition (unexpected)")
        return False

    print("  ✅ ProcessingStateMachine tests passed\n")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("State Machine Integration Test")
    print("=" * 60)
    print()

    success = True
    success &= test_connection_state_machine()
    success &= test_processing_state_machine()

    print("=" * 60)
    if success:
        print("✅ All integration tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)


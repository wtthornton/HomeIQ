"""Tests for homeiq_resilience package initialization and public API."""

from __future__ import annotations

import importlib


def test_package_imports() -> None:
    """All public symbols should be importable from the top-level package."""
    import homeiq_resilience

    expected_exports = [
        "CircuitBreaker",
        "CircuitOpenError",
        "CrossGroupClient",
        "DependencyStatus",
        "GroupHealthCheck",
        "ManagedHTTPClient",
        "ServiceAuthValidator",
        "ServiceLifespan",
        "ServiceScheduler",
        "StandardHealthCheck",
        "TaskManager",
        "create_app",
        "require_service_auth",
        "wait_for_dependency",
    ]
    for name in expected_exports:
        assert hasattr(homeiq_resilience, name), f"Missing export: {name}"


def test_all_attribute() -> None:
    """__all__ should contain every public export."""
    import homeiq_resilience

    assert hasattr(homeiq_resilience, "__all__")
    assert len(homeiq_resilience.__all__) == 14


def test_module_reimport() -> None:
    """Re-importing the package should return the cached module."""
    import homeiq_resilience

    mod = importlib.import_module("homeiq_resilience")
    assert mod is homeiq_resilience


def test_circuit_breaker_instantiation() -> None:
    """CircuitBreaker should be constructible with default args."""
    from homeiq_resilience import CircuitBreaker

    breaker = CircuitBreaker()
    assert breaker.allow_request() is True
    assert breaker.name == "default"


def test_circuit_open_error_is_exception() -> None:
    """CircuitOpenError should be a proper Exception subclass."""
    from homeiq_resilience import CircuitOpenError

    assert issubclass(CircuitOpenError, Exception)
    err = CircuitOpenError("test message")
    assert str(err) == "test message"

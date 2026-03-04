"""Tests for homeiq_observability package initialization and public API."""

from __future__ import annotations

import importlib


def test_package_imports() -> None:
    """Package should be importable with all public exports."""
    import homeiq_observability

    assert hasattr(homeiq_observability, "__version__")
    assert homeiq_observability.__version__ == "1.0.0"

    expected_exports = [
        "AlertManager",
        "AlertSeverity",
        "CorrelationMiddleware",
        "FastAPICorrelationMiddleware",
        "MetricsCollector",
        "PerformanceLogger",
        "StructuredFormatter",
        "correlation_context",
        "create_correlation_middleware",
        "generate_correlation_id",
        "get_alert_manager",
        "get_correlation_id",
        "get_logger",
        "get_metrics_collector",
        "propagate_correlation_id",
        "set_correlation_id",
        "setup_logging",
    ]
    for name in expected_exports:
        assert hasattr(homeiq_observability, name), f"Missing export: {name}"


def test_all_attribute() -> None:
    """__all__ should contain every public export."""
    import homeiq_observability

    assert hasattr(homeiq_observability, "__all__")
    assert len(homeiq_observability.__all__) == 17


def test_module_reimport() -> None:
    """Re-importing the package should return the cached module."""
    import homeiq_observability

    mod = importlib.import_module("homeiq_observability")
    assert mod is homeiq_observability


def test_get_logger_returns_logger() -> None:
    """get_logger should return a standard logging.Logger."""
    import logging

    from homeiq_observability import get_logger

    logger = get_logger("test-service")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test-service"


def test_setup_logging_returns_logger() -> None:
    """setup_logging should return a configured Logger."""
    import logging

    from homeiq_observability import setup_logging

    logger = setup_logging("test-obs-service", log_format="text")
    assert isinstance(logger, logging.Logger)


def test_generate_correlation_id_format() -> None:
    """generate_correlation_id should return a string starting with 'req_'."""
    from homeiq_observability import generate_correlation_id

    cid = generate_correlation_id()
    assert isinstance(cid, str)
    assert cid.startswith("req_")

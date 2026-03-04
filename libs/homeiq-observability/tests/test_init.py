"""Tests for homeiq_observability package initialization and public API."""

from __future__ import annotations

import importlib


def test_package_imports() -> None:
    """Package should be importable."""
    import homeiq_observability

    assert hasattr(homeiq_observability, "__version__")
    assert homeiq_observability.__version__ == "1.0.0"


def test_module_reimport() -> None:
    """Re-importing the package should return the cached module."""
    import homeiq_observability

    mod = importlib.import_module("homeiq_observability")
    assert mod is homeiq_observability


def test_logging_config_importable() -> None:
    """logging_config submodule should be importable."""
    from homeiq_observability.logging_config import get_logger, setup_logging

    assert callable(setup_logging)
    assert callable(get_logger)


def test_get_logger_returns_logger() -> None:
    """get_logger should return a standard logging.Logger."""
    import logging

    from homeiq_observability.logging_config import get_logger

    logger = get_logger("test-service")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test-service"


def test_correlation_middleware_importable() -> None:
    """Correlation middleware classes should be importable."""
    from homeiq_observability.correlation_middleware import (
        CorrelationMiddleware,
        FastAPICorrelationMiddleware,
    )

    assert callable(CorrelationMiddleware)
    assert callable(FastAPICorrelationMiddleware)

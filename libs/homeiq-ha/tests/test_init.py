"""Tests for homeiq_ha package initialization and public API."""

from __future__ import annotations

import importlib


def test_package_imports() -> None:
    """Package should be importable."""
    import homeiq_ha

    assert hasattr(homeiq_ha, "__version__")
    assert homeiq_ha.__version__ == "1.0.0"


def test_module_reimport() -> None:
    """Re-importing the package should return the cached module."""
    import homeiq_ha

    mod = importlib.import_module("homeiq_ha")
    assert mod is homeiq_ha


def test_deployment_validation_importable() -> None:
    """deployment_validation submodule should be importable."""
    from homeiq_ha.deployment_validation import (
        get_deployment_mode,
        get_health_check_info,
        validate_deployment_mode,
    )

    assert callable(get_deployment_mode)
    assert callable(validate_deployment_mode)
    assert callable(get_health_check_info)


def test_get_deployment_mode_returns_string() -> None:
    """get_deployment_mode should return a string."""
    from homeiq_ha.deployment_validation import get_deployment_mode

    mode = get_deployment_mode()
    assert isinstance(mode, str)
    assert mode in ("test", "production")


def test_health_check_info_returns_dict() -> None:
    """get_health_check_info should return a dictionary."""
    from homeiq_ha.deployment_validation import get_health_check_info

    info = get_health_check_info()
    assert isinstance(info, dict)
    assert "deployment_mode" in info
    assert "is_test" in info
    assert "is_production" in info

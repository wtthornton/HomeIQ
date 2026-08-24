"""Tests for scripts/check-ha-component-manifest.py (TAP-6483).

The point of this check is that it *fails* on drift. A refactor that quietly
turned it into a no-op would leave CI green while the guarantee evaporated, so
every failure path gets a test asserting a specific message — not merely a
non-zero exit.

Image mode needs a Docker daemon and is exercised by the docker-side CI job;
these cover the static path plus the pure helpers, so they run anywhere.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check-ha-component-manifest.py"


def _load_module():
    """Import the script by path — its filename has hyphens, so no plain import."""
    spec = importlib.util.spec_from_file_location("check_ha_component_manifest", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = _load_module()


@pytest.fixture
def lock() -> dict:
    """The real lock file, so the fixture drifts when the shipped one does."""
    return json.loads((REPO_ROOT / "infrastructure" / "ha-components.lock.json").read_text())


@pytest.fixture
def dockerfile() -> str:
    return (REPO_ROOT / "domains" / "core-platform" / "home-assistant" / "Dockerfile").read_text()


def test_real_lock_and_dockerfile_agree(lock: dict, dockerfile: str) -> None:
    """The shipped pair must pass; this is the check CI actually runs."""
    failures: list[str] = []
    checker.check_static(lock, dockerfile, failures)
    assert failures == []


def test_moving_tag_is_rejected(lock: dict, dockerfile: str) -> None:
    lock["home_assistant"]["version"] = "stable"
    failures: list[str] = []
    checker.check_static(lock, dockerfile, failures)
    assert any("moving tag" in f for f in failures)


def test_component_version_drift_is_caught(lock: dict, dockerfile: str) -> None:
    lock["custom_components"][0]["version"] = "0.0.1"
    failures: list[str] = []
    checker.check_static(lock, dockerfile, failures)
    assert any("Dockerfile ARG" in f for f in failures)


def test_pin_below_declared_floor_is_caught(lock: dict, dockerfile: str) -> None:
    lock["home_assistant"]["version"] = "2026.7.1"
    failures: list[str] = []
    checker.check_static(lock, dockerfile, failures)
    assert any("below the declared floor" in f for f in failures)


def test_in_repo_component_reconciles_against_its_manifest(lock: dict, dockerfile: str) -> None:
    """homeiq's version is not a build ARG; it must track its own manifest.json."""
    homeiq = next(c for c in lock["custom_components"] if c["source"].startswith("in-repo:"))
    homeiq["version"] = "99.99.99"
    failures: list[str] = []
    checker.check_static(lock, dockerfile, failures)
    assert any("manifest.json says" in f for f in failures)


def test_missing_quirk_source_is_caught(lock: dict, dockerfile: str) -> None:
    lock["zha_quirks"][0]["source"] = "in-repo:libs/does/not/exist.py"
    failures: list[str] = []
    checker.check_static(lock, dockerfile, failures)
    assert any("does not exist" in f for f in failures)


def test_dockerfile_without_a_pin_is_caught(lock: dict) -> None:
    failures: list[str] = []
    checker.check_static(lock, "FROM scratch\n", failures)
    assert any("no `FROM ghcr.io/home-assistant" in f for f in failures)


@pytest.mark.parametrize(
    ("version", "expected"),
    [("2026.8.3", (2026, 8, 3)), ("2026.8.0", (2026, 8, 0)), ("1.25.1", (1, 25, 1))],
)
def test_version_key_orders_numerically(version: str, expected: tuple[int, ...]) -> None:
    assert checker._version_key(version) == expected


def test_version_key_compares_across_minor_versions() -> None:
    """String compare would call 2026.10.0 < 2026.8.0; the numeric key must not."""
    assert checker._version_key("2026.10.0") > checker._version_key("2026.8.0")


def test_lock_file_shape_is_what_the_checker_expects(lock: dict) -> None:
    """Guards the lock file itself, which nothing else validates."""
    assert lock["home_assistant"]["version"] not in checker.MOVING_TAGS
    assert lock["custom_components"], "at least one component must be locked"
    for component in lock["custom_components"]:
        assert component["name"] and component["version"]
        assert component["source"].startswith(("github:", "in-repo:"))
    for quirk in lock.get("zha_quirks", []):
        assert quirk["installed_to"].startswith("/config/")

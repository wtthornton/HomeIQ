"""
Tests for LinterClient

Epic 67, Story 67.1: Automation Linter Client
"""

import pytest

from src.clients.linter_client import LinterClient, LintResult


def test_lint_result_dataclass():
    """LintResult correctly reports pass/fail."""
    result = LintResult(passed=True, error_count=0, warning_count=2, info_count=1)
    assert result.passed is True
    assert result.error_count == 0
    assert result.warning_count == 2

    result2 = LintResult(passed=False, error_count=1)
    assert result2.passed is False


def test_lint_result_defaults():
    """LintResult has sensible defaults."""
    result = LintResult(passed=True)
    assert result.findings == []
    assert result.error_count == 0
    assert result.warning_count == 0
    assert result.info_count == 0
    assert result.raw_response is None


def test_linter_client_init():
    """LinterClient initializes with correct defaults."""
    client = LinterClient()
    assert client.base_url == "http://automation-linter:8020"
    assert client._timeout == 2.0

    client2 = LinterClient(base_url="http://localhost:8020", timeout=5.0)
    assert client2.base_url == "http://localhost:8020"
    assert client2._timeout == 5.0


def test_linter_client_strips_trailing_slash():
    """LinterClient strips trailing slash from base_url."""
    client = LinterClient(base_url="http://localhost:8020/")
    assert client.base_url == "http://localhost:8020"

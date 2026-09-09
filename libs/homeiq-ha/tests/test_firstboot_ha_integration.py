"""Integration test: first-boot onboarding against a REAL, fresh HA container.

Every other test in this package mocks the network edges; this module is the
one place the real `homeiq/home-assistant:2026.8.3` image is driven end to
end (TAP-6570). It is deliberately excluded from the default collection
(`-m integration` selects it) so the fast unit suite never needs a container.

The target comes ONLY from $HIQ_B1_HA_BASE_URL. There is no fallback to
$HOME_ASSISTANT_TOKEN, $HA_TOKEN, or any other host env var, and no fallback
to a default host — an unset target FAILS this module's own precondition
test rather than silently skipping, so a misconfigured run cannot report
"nothing to see here" by accident. It also refuses to target the live
production HA box (192.168.1.80) even if that value ever ends up in the env.
"""

from __future__ import annotations

import asyncio
import os
from urllib.parse import urlparse

import pytest
from homeiq_ha.agent.onboarding import OnboardingState, run_first_boot

pytestmark = pytest.mark.integration

_BASE_URL_ENV = "HIQ_B1_HA_BASE_URL"
_LIVE_HA_HOST = "192.168.1.80"


def _read_base_url() -> str:
    return os.environ.get(_BASE_URL_ENV, "")


def test_precondition_base_url_env_is_set_and_not_the_live_ha() -> None:
    """FAILS (never skips) when the target precondition does not hold.

    An unset $HIQ_B1_HA_BASE_URL, or one pointed at the live production HA
    box, is a broken test run, not an absent one.
    """
    base_url = _read_base_url()
    assert base_url, f"{_BASE_URL_ENV} must be set to the throwaway HA base URL"
    host = urlparse(base_url).hostname
    assert host != _LIVE_HA_HOST, "refusing to target the live production HA box"
    assert host == "127.0.0.1", f"expected the throwaway HA on 127.0.0.1, got {host!r}"


def test_first_boot_mints_a_real_token_against_a_fresh_ha() -> None:
    base_url = _read_base_url()
    assert base_url, f"{_BASE_URL_ENV} must be set"
    host = urlparse(base_url).hostname
    assert host == "127.0.0.1", f"expected 127.0.0.1, got {host!r}"
    assert host != _LIVE_HA_HOST

    result = asyncio.run(run_first_boot(base_url))

    assert result.state is OnboardingState.COMPLETED, result.detail
    assert result.credential is not None
    assert len(result.credential.token) > 20

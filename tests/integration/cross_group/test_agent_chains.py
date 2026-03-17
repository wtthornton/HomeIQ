"""Agent Chain Integration Tests (Story 78.3).

Verifies the proactive-agent -> ha-ai-agent -> ha-device-control chain:
CrossGroupClient retry and circuit breaker behavior, confidence scoring
contract, auth token propagation, and safety guardrails.

Tests the REAL client/library code paths with mocked HTTP transports.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from homeiq_resilience import CircuitBreaker, CircuitOpenError, CrossGroupClient
from homeiq_resilience.circuit_breaker import CircuitState


@pytest.mark.integration
class TestAgentChains:
    """Verify cross-group agent chain: retry, circuit breaker, auth, safety."""

    @pytest.mark.asyncio
    async def test_cross_group_client_retry_on_connection_error(self):
        """CrossGroupClient should retry on transient connection errors.

        Validates the exponential backoff retry loop: first two calls fail
        with ConnectError, third succeeds.
        """
        cb = CircuitBreaker(name="test-retry", failure_threshold=10)

        client = CrossGroupClient(
            base_url="http://ha-ai-agent:8030",
            group_name="automation-core",
            timeout=5.0,
            max_retries=3,
            circuit_breaker=cb,
        )

        call_count = 0
        mock_response = httpx.Response(
            status_code=200,
            json={"status": "ok"},
            request=httpx.Request("GET", "http://ha-ai-agent:8030/health"),
        )

        async def mock_do_request(method, path, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("connection refused")
            return mock_response

        with patch.object(client, "_do_request", side_effect=mock_do_request):
            with patch("homeiq_resilience.cross_group_client.asyncio.sleep", new_callable=AsyncMock):
                response = await client.call("GET", "/health")

        assert response.status_code == 200
        assert call_count == 3, "Should have retried twice before succeeding"

    @pytest.mark.asyncio
    async def test_cross_group_client_circuit_breaker_opens_on_failures(self):
        """CircuitBreaker should open after reaching failure threshold.

        Validates the three-state machine: CLOSED -> OPEN after consecutive
        failures, then requests are blocked with CircuitOpenError.
        """
        cb = CircuitBreaker(
            name="test-cb-open",
            failure_threshold=3,
            recovery_timeout=60.0,
        )

        assert cb.state == CircuitState.CLOSED

        # Record enough failures to open the circuit
        for _ in range(3):
            await cb.record_failure()

        assert cb.state == CircuitState.OPEN

        # Requests should now be blocked
        allowed = await cb.allow_request()
        assert allowed is False, "Circuit is OPEN, requests should be blocked"

        # Reset for cleanup
        await cb.reset()
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_proactive_agent_confidence_scoring_contract(self):
        """ConfidenceScorer.score_action should return ActionScore with correct schema.

        Validates the confidence/risk scoring model contract used by
        proactive-agent-service for action decisions.
        """
        from services.confidence_scorer import (
            ActionScore,
            ConfidenceScorer,
            SAFETY_BLOCKED_DOMAINS,
        )

        scorer = ConfidenceScorer()

        # Score a safe light action
        score = scorer.score_action(
            action_type="turn_off",
            entity_domain="light",
            context_type="historical_pattern",
            llm_confidence=0.9,
            acceptance_rate=0.85,
            context_match_strength=0.8,
            preference_alignment=0.7,
        )

        assert isinstance(score, ActionScore)
        assert isinstance(score.confidence, int)
        assert 0 <= score.confidence <= 100
        assert score.risk_level in ("low", "medium", "high", "critical")
        assert isinstance(score.reversibility, float)
        assert score.reasoning != ""
        assert isinstance(score.factors, dict)

        # Properties should be consistent
        assert isinstance(score.should_auto_execute, bool)
        assert isinstance(score.should_suggest, bool)
        assert isinstance(score.should_suppress, bool)
        assert isinstance(score.is_safety_blocked, bool)

    @pytest.mark.asyncio
    async def test_agent_chain_auth_token_propagation(self):
        """Bearer tokens should propagate across CrossGroupClient calls.

        Validates that when auth_token is set on CrossGroupClient, the
        Authorization header is correctly injected into outgoing requests.
        """
        client = CrossGroupClient(
            base_url="http://data-api:8006",
            group_name="core-platform",
            auth_token="secret-bearer-token",
        )

        # Verify the auth token is stored
        assert client._auth_token == "secret-bearer-token"

        # Mock the HTTP layer to capture headers
        captured_headers = {}

        async def mock_request(method, path, headers=None, **kwargs):
            nonlocal captured_headers
            captured_headers = dict(headers or {})
            return httpx.Response(
                status_code=200,
                json={"ok": True},
                request=httpx.Request(method, f"http://data-api:8006{path}"),
            )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_ctx = AsyncMock()
            mock_ctx.request = mock_request
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            cb = CircuitBreaker(name="test-auth", failure_threshold=10)
            client._breaker = cb

            await client.call("GET", "/api/v1/entities")

        assert "Authorization" in captured_headers
        assert captured_headers["Authorization"] == "Bearer secret-bearer-token"

    def test_safety_guardrails_block_restricted_domains(self):
        """Safety guardrails must always block lock, alarm, and camera domains.

        Validates that SAFETY_BLOCKED_DOMAINS is a hardcoded frozen set
        containing the three restricted domains, and that scoring them
        returns confidence=0 and risk_level=critical.
        """
        from services.confidence_scorer import (
            ConfidenceScorer,
            SAFETY_BLOCKED_DOMAINS,
        )

        # Verify the blocked domains set
        assert "lock" in SAFETY_BLOCKED_DOMAINS
        assert "alarm_control_panel" in SAFETY_BLOCKED_DOMAINS
        assert "camera" in SAFETY_BLOCKED_DOMAINS
        assert isinstance(SAFETY_BLOCKED_DOMAINS, frozenset)

        scorer = ConfidenceScorer()

        for domain in SAFETY_BLOCKED_DOMAINS:
            score = scorer.score_action(
                action_type="turn_on",
                entity_domain=domain,
                context_type="test",
                llm_confidence=1.0,
                acceptance_rate=1.0,
                context_match_strength=1.0,
                preference_alignment=1.0,
            )

            assert score.confidence == 0, (
                f"{domain} domain should always have confidence=0"
            )
            assert score.risk_level == "critical", (
                f"{domain} domain should always be critical risk"
            )
            assert score.is_safety_blocked is True, (
                f"{domain} domain should be safety-blocked"
            )

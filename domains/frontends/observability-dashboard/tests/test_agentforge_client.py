"""Tests for AgentForge client."""

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx
from services.agentforge_client import (
    AgentForgeClient,
    AgentStats,
    GateDecision,
    Invocation,
    ProjectSpend,
    SpendBySource,
)


def _invocation(agent, cost, *, is_error=False, inv_id="inv-1", result_excerpt=""):
    """An Invocation varying only the fields these tests assert on; the rest is fixed noise."""
    return Invocation(
        invocation_id=inv_id,
        agent_used=agent,
        status="error" if is_error else "success",
        is_error=is_error,
        cost_usd=cost,
        duration_ms=100.0,
        timestamp="2026-08-17T00:00:00Z",
        result_excerpt=result_excerpt,
    )


def _payload(inv_id, agent, **overrides):
    """One `/invocations` wire record, with only the fields a test asserts on spelled out."""
    return {
        "invocation_id": inv_id,
        "agent_used": agent,
        "status": "success",
        "is_error": False,
        "cost_usd": 1.0,
        "duration_ms": 500.0,
        "timestamp": "2026-08-17T00:00:00Z",
        "mcp_call_count": 0,
        "mcp_hosts": [],
        "result_excerpt": "",
    } | overrides


def _mock_invocations(payload):
    """Point the invocations endpoint at `payload`."""
    respx.get("http://localhost:8010/projects/homeiq/invocations").mock(
        return_value=httpx.Response(200, json=payload)
    )


class TestAgentForgeClient:
    """Test suite for AgentForgeClient."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return AgentForgeClient(
            base_url="http://localhost:8010",
            api_key="test-key",
            timeout=30.0,
        )

    def test_init(self, client):
        """Test client initialization."""
        assert client.base_url == "http://localhost:8010"
        assert client.api_key == "test-key"
        assert client.timeout == 30.0
        assert client.project == "homeiq"

    def test_init_strips_trailing_slash(self):
        """Test that base_url trailing slash is stripped."""
        client = AgentForgeClient(
            base_url="http://localhost:8010/",
            api_key="key",
        )
        assert client.base_url == "http://localhost:8010"

    def test_auth_headers_with_key(self, client):
        """Test auth headers include bearer token."""
        headers = client._auth_headers()
        assert headers["Authorization"] == "Bearer test-key"

    def test_auth_headers_without_key(self):
        """Test auth headers when no key provided."""
        client = AgentForgeClient(
            base_url="http://localhost:8010",
            api_key="",
        )
        headers = client._auth_headers()
        assert "Authorization" not in headers

    @pytest.mark.asyncio
    async def test_get_spend_success(self, client):
        """Test successful spend data fetch."""
        spend_data = {
            "slug": "homeiq",
            "entry_count": 100,
            "by_source": {
                "llm_cost_usd": 50.0,
                "provider_cost_usd": 10.0,
                "total_cost_usd": 60.0,
            },
            "by_activity": {},
        }

        with respx.mock:
            respx.get("http://localhost:8010/projects/homeiq/spend").mock(
                return_value=httpx.Response(200, json=spend_data)
            )

            spend = await client.get_spend()

            assert spend is not None
            assert spend.slug == "homeiq"
            assert spend.by_source.total_cost_usd == 60.0

    @pytest.mark.asyncio
    async def test_get_spend_failure(self, client):
        """Test spend endpoint failure returns None."""
        with respx.mock:
            respx.get("http://localhost:8010/projects/homeiq/spend").mock(
                return_value=httpx.Response(500)
            )

            spend = await client.get_spend()

            assert spend is None

    @pytest.mark.asyncio
    async def test_get_spend_network_error(self, client):
        """Test network error in spend fetch."""
        with respx.mock:
            respx.get("http://localhost:8010/projects/homeiq/spend").mock(
                side_effect=httpx.RequestError("Connection refused")
            )

            spend = await client.get_spend()

            assert spend is None

    @pytest.mark.asyncio
    async def test_get_invocations_success(self, client):
        """Test successful invocations list fetch."""
        inv_data = [
            _payload("inv-123", "hiq-extract", cost_usd=1.5, mcp_call_count=2, mcp_hosts=["mcp1"]),
            _payload("inv-124", "hiq-classify", cost_usd=2.0, mcp_call_count=1),
        ]

        with respx.mock:
            _mock_invocations(inv_data)

            invocations = await client.get_invocations(limit=100)

            assert len(invocations) == 2
            assert invocations[0].invocation_id == "inv-123"
            assert invocations[1].agent_used == "hiq-classify"

    @pytest.mark.asyncio
    async def test_get_invocations_wrapped_response(self, client):
        """Test invocations response wrapped in {items: [...]}."""
        inv_data = {"items": [_payload("inv-125", "hiq-extract")]}

        with respx.mock:
            _mock_invocations(inv_data)

            invocations = await client.get_invocations(limit=10)

            assert len(invocations) == 1
            assert invocations[0].invocation_id == "inv-125"

    @pytest.mark.asyncio
    async def test_get_invocations_empty(self, client):
        """Test empty invocations list."""
        with respx.mock:
            _mock_invocations([])

            invocations = await client.get_invocations()

            assert len(invocations) == 0

    @pytest.mark.asyncio
    async def test_get_invocations_accepts_fractional_duration(self, client):
        """AF serializes duration_ms as a float; an int-typed model rejects the live payload."""
        inv_data = {
            "items": [
                _payload(
                    "inv-frac",
                    "homeiq-hiq-notify",
                    status="error",
                    is_error=True,
                    cost_usd=0.0,
                    duration_ms=2.6579119730740786,
                )
            ]
        }

        with respx.mock:
            _mock_invocations(inv_data)

            (invocation,) = await client.get_invocations()

            assert invocation.duration_ms == pytest.approx(2.6579119730740786)

    @pytest.mark.asyncio
    async def test_get_gate_decisions_approved(self, client):
        """Test gate decision extraction for approved cases."""
        invocations = [
            _invocation(
                "hiq-judge",
                1.0,
                result_excerpt=json.dumps({"pass": True, "rule_id": "allow.basic"}),
            )
        ]

        with patch.object(client, "get_invocations", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = invocations

            decisions = await client.get_gate_decisions()

            assert len(decisions) == 1
            assert decisions[0].decision == "approved"
            assert decisions[0].rule_id == "allow.basic"

    @pytest.mark.asyncio
    async def test_get_gate_decisions_blocked(self, client):
        """Test gate decision extraction for blocked cases."""
        invocations = [
            _invocation(
                "hiq-judge",
                0.5,
                is_error=True,
                result_excerpt=json.dumps({"pass": False, "rule_id": "deny.unlock_lock"}),
            )
        ]

        with patch.object(client, "get_invocations", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = invocations

            decisions = await client.get_gate_decisions()

            assert len(decisions) == 1
            assert decisions[0].decision == "blocked"
            assert decisions[0].rule_id == "deny.unlock_lock"

    @pytest.mark.asyncio
    async def test_get_gate_decisions_non_gate_result(self, client):
        """Test that non-gate results are skipped."""
        invocations = [_invocation("hiq-extract", 1.0, result_excerpt="No gate decision here")]

        with patch.object(client, "get_invocations", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = invocations

            decisions = await client.get_gate_decisions()

            assert len(decisions) == 0

    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test health check returns True on 200."""
        with respx.mock:
            respx.get("http://localhost:8010/health").mock(return_value=httpx.Response(200))

            is_healthy = await client.health_check()

            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """Test health check returns False on non-2xx."""
        with respx.mock:
            respx.get("http://localhost:8010/health").mock(return_value=httpx.Response(503))

            is_healthy = await client.health_check()

            assert is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_network_error(self, client):
        """Test health check returns False on network error."""
        with respx.mock:
            respx.get("http://localhost:8010/health").mock(
                side_effect=httpx.RequestError("Connection refused")
            )

            is_healthy = await client.health_check()

            assert is_healthy is False


class TestPydanticModels:
    """Test Pydantic models for correctness."""

    def test_spend_by_source(self):
        """Test SpendBySource model."""
        spend = SpendBySource(
            llm_cost_usd=50.0,
            provider_cost_usd=10.0,
            total_cost_usd=60.0,
        )
        assert spend.total_cost_usd == 60.0

    def test_project_spend(self):
        """Test ProjectSpend model."""
        spend = ProjectSpend(
            slug="homeiq",
            entry_count=100,
            by_source=SpendBySource(
                llm_cost_usd=50.0,
                provider_cost_usd=10.0,
                total_cost_usd=60.0,
            ),
        )
        assert spend.entry_count == 100

    def test_invocation(self):
        """Test Invocation model."""
        inv = Invocation(
            invocation_id="inv-123",
            agent_used="hiq-extract",
            status="success",
            is_error=False,
            cost_usd=1.5,
            duration_ms=1000,
            timestamp="2026-08-17T00:00:00Z",
        )
        assert inv.agent_used == "hiq-extract"

    def test_agent_stats(self):
        """Test AgentStats model."""
        stats = AgentStats(
            agent="hiq-extract",
            invocation_count=10,
            error_count=1,
            total_cost_usd=15.0,
            avg_cost_usd=1.5,
            max_budget_usd=20.0,
        )
        assert stats.agent == "hiq-extract"
        assert stats.avg_cost_usd == 1.5

    def test_gate_decision(self):
        """Test GateDecision model."""
        decision = GateDecision(
            invocation_id="inv-1",
            agent="hiq-judge",
            decision="approved",
            rule_id="allow.basic",
            cost_usd=1.0,
            timestamp="2026-08-17T00:00:00Z",
        )
        assert decision.decision == "approved"

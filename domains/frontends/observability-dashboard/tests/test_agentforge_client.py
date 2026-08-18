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
            {
                "invocation_id": "inv-123",
                "agent_used": "hiq-extract",
                "status": "success",
                "is_error": False,
                "cost_usd": 1.5,
                "duration_ms": 1000,
                "timestamp": "2026-08-17T00:00:00Z",
                "mcp_call_count": 2,
                "mcp_hosts": ["mcp1"],
                "result_excerpt": "",
            },
            {
                "invocation_id": "inv-124",
                "agent_used": "hiq-classify",
                "status": "success",
                "is_error": False,
                "cost_usd": 2.0,
                "duration_ms": 500,
                "timestamp": "2026-08-17T00:01:00Z",
                "mcp_call_count": 1,
                "mcp_hosts": [],
                "result_excerpt": "",
            },
        ]

        with respx.mock:
            respx.get("http://localhost:8010/projects/homeiq/invocations").mock(
                return_value=httpx.Response(200, json=inv_data)
            )

            invocations = await client.get_invocations(limit=100)

            assert len(invocations) == 2
            assert invocations[0].invocation_id == "inv-123"
            assert invocations[1].agent_used == "hiq-classify"

    @pytest.mark.asyncio
    async def test_get_invocations_wrapped_response(self, client):
        """Test invocations response wrapped in {items: [...]}."""
        inv_data = {
            "items": [
                {
                    "invocation_id": "inv-125",
                    "agent_used": "hiq-extract",
                    "status": "success",
                    "is_error": False,
                    "cost_usd": 1.0,
                    "duration_ms": 500,
                    "timestamp": "2026-08-17T00:00:00Z",
                    "mcp_call_count": 0,
                    "mcp_hosts": [],
                    "result_excerpt": "",
                }
            ]
        }

        with respx.mock:
            respx.get("http://localhost:8010/projects/homeiq/invocations").mock(
                return_value=httpx.Response(200, json=inv_data)
            )

            invocations = await client.get_invocations(limit=10)

            assert len(invocations) == 1
            assert invocations[0].invocation_id == "inv-125"

    @pytest.mark.asyncio
    async def test_get_invocations_empty(self, client):
        """Test empty invocations list."""
        with respx.mock:
            respx.get("http://localhost:8010/projects/homeiq/invocations").mock(
                return_value=httpx.Response(200, json=[])
            )

            invocations = await client.get_invocations()

            assert len(invocations) == 0

    @pytest.mark.asyncio
    async def test_get_per_agent_stats(self, client):
        """Test per-agent stats aggregation."""
        invocations = [
            Invocation(
                invocation_id="inv-1",
                agent_used="hiq-extract",
                status="success",
                is_error=False,
                cost_usd=1.0,
                duration_ms=100,
                timestamp="2026-08-17T00:00:00Z",
            ),
            Invocation(
                invocation_id="inv-2",
                agent_used="hiq-extract",
                status="success",
                is_error=False,
                cost_usd=2.0,
                duration_ms=200,
                timestamp="2026-08-17T00:01:00Z",
            ),
            Invocation(
                invocation_id="inv-3",
                agent_used="hiq-classify",
                status="error",
                is_error=True,
                cost_usd=0.5,
                duration_ms=50,
                timestamp="2026-08-17T00:02:00Z",
            ),
        ]

        with patch.object(client, "get_invocations", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = invocations

            budgets = {
                "hiq-extract": 10.0,
                "hiq-classify": 5.0,
            }

            stats = await client.get_per_agent_stats(budgets)

            assert len(stats) == 2

            # Extract should be first (higher cost)
            assert stats[0].agent == "hiq-extract"
            assert stats[0].invocation_count == 2
            assert stats[0].error_count == 0
            assert stats[0].total_cost_usd == 3.0
            assert stats[0].avg_cost_usd == 1.5

            # Classify should be second
            assert stats[1].agent == "hiq-classify"
            assert stats[1].invocation_count == 1
            assert stats[1].error_count == 1
            assert stats[1].total_cost_usd == 0.5

    @pytest.mark.asyncio
    async def test_get_per_agent_stats_with_budget_alert(self, client):
        """Test budget alert for agents over cap."""
        invocations = [
            Invocation(
                invocation_id="inv-1",
                agent_used="hiq-extract",
                status="success",
                is_error=False,
                cost_usd=8.0,
                duration_ms=100,
                timestamp="2026-08-17T00:00:00Z",
            ),
            Invocation(
                invocation_id="inv-2",
                agent_used="hiq-extract",
                status="error",
                is_error=True,
                cost_usd=2.5,
                duration_ms=50,
                timestamp="2026-08-17T00:01:00Z",
            ),
        ]

        with patch.object(client, "get_invocations", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = invocations

            budgets = {"hiq-extract": 10.0}

            stats = await client.get_per_agent_stats(budgets)

            # At 95% of budget when error occurs, should count as budget kill
            assert stats[0].over_budget_kills == 1

    @pytest.mark.asyncio
    async def test_get_gate_decisions_approved(self, client):
        """Test gate decision extraction for approved cases."""
        invocations = [
            Invocation(
                invocation_id="inv-1",
                agent_used="hiq-judge",
                status="success",
                is_error=False,
                cost_usd=1.0,
                duration_ms=100,
                timestamp="2026-08-17T00:00:00Z",
                result_excerpt=json.dumps({"pass": True, "rule_id": "allow.basic"}),
            ),
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
            Invocation(
                invocation_id="inv-1",
                agent_used="hiq-judge",
                status="error",
                is_error=True,
                cost_usd=0.5,
                duration_ms=50,
                timestamp="2026-08-17T00:00:00Z",
                result_excerpt=json.dumps({"pass": False, "rule_id": "deny.unlock_lock"}),
            ),
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
        invocations = [
            Invocation(
                invocation_id="inv-1",
                agent_used="hiq-extract",
                status="success",
                is_error=False,
                cost_usd=1.0,
                duration_ms=100,
                timestamp="2026-08-17T00:00:00Z",
                result_excerpt="No gate decision here",
            ),
        ]

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

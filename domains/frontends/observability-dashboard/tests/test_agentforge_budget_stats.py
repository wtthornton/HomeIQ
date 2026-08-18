"""Budget and per-agent spend aggregation in the AgentForge client.

Split from `test_agentforge_client.py` so the cap semantics — a per-invocation
ceiling, never a lifetime allowance — read as one coherent suite.
"""

from unittest.mock import AsyncMock, patch

import pytest
from services.agent_budget_loader import UnreadableCap
from services.agentforge_client import AgentForgeClient, Invocation, resolve_budget_key


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


class TestPerAgentBudgets:
    """Spend aggregation, cap matching, and budget-kill detection."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return AgentForgeClient(base_url="http://localhost:8010", api_key="afp_test_key")

    @pytest.mark.asyncio
    async def test_get_per_agent_stats(self, client):
        """Test per-agent stats aggregation."""
        invocations = [
            _invocation("hiq-extract", 1.0, inv_id="inv-1"),
            _invocation("hiq-extract", 2.0, inv_id="inv-2"),
            _invocation("hiq-classify", 0.5, is_error=True, inv_id="inv-3"),
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
    async def test_get_per_agent_stats_matches_namespaced_agent_names(self, client):
        """Published genes report as `<slug>-<gene>`; the cap is still keyed on the filename."""
        invocations = [
            _invocation("homeiq-hiq-summarize", 0.05, inv_id="inv-1"),
            _invocation("homeiq-homeiq-service-auditor", 0.64, inv_id="inv-2"),
        ]

        with patch.object(client, "get_invocations", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = invocations
            budgets = {"hiq-summarize": 0.25, "homeiq-service-auditor": 2.0}

            stats = await client.get_per_agent_stats(budgets)

        by_agent = {s.agent: s for s in stats}
        assert by_agent["homeiq-hiq-summarize"].budget_key == "hiq-summarize"
        assert by_agent["homeiq-hiq-summarize"].max_budget_usd == 0.25
        assert by_agent["homeiq-homeiq-service-auditor"].budget_key == "homeiq-service-auditor"
        assert by_agent["homeiq-homeiq-service-auditor"].max_budget_usd == 2.0

    def test_resolve_budget_key_prefers_the_bare_name(self):
        """A gene literally named `homeiq-…` must not be stripped to `…`."""
        budgets = {"homeiq-service-auditor": 2.0, "service-auditor": 9.9}

        assert resolve_budget_key("homeiq-service-auditor", budgets, "homeiq") == (
            "homeiq-service-auditor"
        )

    def test_resolve_budget_key_falls_back_to_the_wire_name(self):
        """Platform agents (expert-*, _system-*) declare no cap and keep their own key."""
        assert resolve_budget_key("expert-security", {"hiq-rank": 0.25}, "homeiq") == (
            "expert-security"
        )

    @pytest.mark.asyncio
    async def test_budget_kill_counts_an_invocation_that_reached_its_own_cap(self, client):
        """The cap bounds one run, so only that run's own cost can have tripped it."""
        invocations = [
            _invocation("hiq-extract", 8.0, inv_id="inv-1"),
            _invocation("hiq-extract", 9.6, is_error=True, inv_id="inv-2"),
        ]

        with patch.object(client, "get_invocations", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = invocations

            stats = await client.get_per_agent_stats({"hiq-extract": 10.0})

            assert stats[0].over_budget_kills == 1
            assert stats[0].max_invocation_cost_usd == 9.6

    @pytest.mark.asyncio
    async def test_cumulative_spend_past_the_cap_is_not_a_budget_kill(self, client):
        """Cheap runs summing past a per-invocation cap refuse nothing — AF killed none."""
        invocations = [
            _invocation("hiq-extract", 6.0, is_error=i == 2, inv_id=f"inv-{i}") for i in range(3)
        ]

        with patch.object(client, "get_invocations", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = invocations

            stats = await client.get_per_agent_stats({"hiq-extract": 10.0})

            assert stats[0].total_cost_usd == 18.0
            assert stats[0].max_invocation_cost_usd == 6.0
            assert stats[0].over_budget_kills == 0

    @pytest.mark.asyncio
    async def test_unreadable_cap_is_flagged_rather_than_read_as_uncapped(self, client):
        """An UnreadableCap must not land on the page as "no cap declared"."""
        invocations = [_invocation("hiq-extract", 1.0)]

        with patch.object(client, "get_invocations", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = invocations

            budgets = {"hiq-extract": UnreadableCap(reason="PermissionError: denied")}
            stats = await client.get_per_agent_stats(budgets)

            assert stats[0].budget_cap_unreadable is True
            assert stats[0].max_budget_usd is None

"""AgentForge API client for operations dashboard.

Fetches spend data, invocations, gate decisions, and agent budget caps
from AgentForge HTTP API.
"""

import json
import logging
from typing import Any

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SpendBySource(BaseModel):
    """Spend breakdown by source."""

    llm_cost_usd: float = 0.0
    provider_cost_usd: float = 0.0
    total_cost_usd: float = 0.0


class ProjectSpend(BaseModel):
    """Project-level spend data."""

    slug: str
    entry_count: int
    by_source: SpendBySource
    by_activity: dict[str, Any] = Field(default_factory=dict)


class Invocation(BaseModel):
    """Single invocation record."""

    invocation_id: str
    agent_used: str
    status: str  # "success", "error", etc.
    is_error: bool
    cost_usd: float
    duration_ms: int
    timestamp: str  # ISO 8601
    mcp_call_count: int = 0
    mcp_hosts: list[str] = Field(default_factory=list)
    result_excerpt: str = ""


class AgentStats(BaseModel):
    """Aggregated stats for one agent."""

    agent: str
    invocation_count: int = 0
    error_count: int = 0
    total_cost_usd: float = 0.0
    avg_cost_usd: float = 0.0
    max_budget_usd: float | None = None
    over_budget_kills: int = 0  # Count of budget-limited kills


class GateDecision(BaseModel):
    """Gate decision extracted from invocation result."""

    invocation_id: str
    agent: str
    decision: str  # "approved", "blocked", "error"
    rule_id: str | None = None
    cost_usd: float
    timestamp: str


class AgentForgeClient:
    """HTTP client for AgentForge ops data."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0):
        """Initialize client.

        Args:
            base_url: Base URL for AgentForge API (e.g. http://localhost:8010)
            api_key: Bearer token for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.project = "homeiq"

    async def get_spend(self) -> ProjectSpend | None:
        """Fetch project spend data.

        Returns:
            ProjectSpend or None if request fails.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/projects/{self.project}/spend",
                    headers=self._auth_headers(),
                    timeout=self.timeout,
                )
                if response.status_code == 200:
                    data = response.json()
                    return ProjectSpend(**data)
                logger.warning(f"AF spend endpoint returned {response.status_code}")
                return None
        except httpx.RequestError as e:
            logger.error(f"AF spend request failed: {e}")
            return None

    async def get_invocations(self, limit: int = 100) -> list[Invocation]:
        """Fetch recent invocations.

        Args:
            limit: Max number of invocations to return

        Returns:
            List of invocations, empty if request fails.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/projects/{self.project}/invocations",
                    params={"limit": limit},
                    headers=self._auth_headers(),
                    timeout=self.timeout,
                )
                if response.status_code == 200:
                    data = response.json()
                    # data is either a list or {items: []}
                    invocations = data if isinstance(data, list) else data.get("items", [])
                    return [Invocation(**item) for item in invocations]
                logger.warning(f"AF invocations endpoint returned {response.status_code}")
                return []
        except httpx.RequestError as e:
            logger.error(f"AF invocations request failed: {e}")
            return []

    async def get_agent(self, _agent_name: str) -> dict[str, Any] | None:
        """Fetch agent definition to extract max_budget_usd.

        Reads from project agentforge/projects/homeiq/agents/{name}.md
        frontmatter (local repo) or falls back to AF API if needed.

        Args:
            agent_name: Name of agent (e.g. "hiq-extract")

        Returns:
            Agent dict with metadata, or None if not found.
        """
        # For now, just return empty dict; budget will be read from local repo
        return {}

    async def get_per_agent_stats(self, agent_budgets: dict[str, float | None]) -> list[AgentStats]:
        """Aggregate spend and invocation stats per agent.

        Args:
            agent_budgets: Mapping of agent name -> max_budget_usd

        Returns:
            List of per-agent stats, sorted by cost descending.
        """
        invocations = await self.get_invocations(limit=500)

        # Aggregate by agent
        stats_map: dict[str, AgentStats] = {}
        for inv in invocations:
            agent = inv.agent_used or "unknown"
            if agent not in stats_map:
                stats_map[agent] = AgentStats(
                    agent=agent,
                    max_budget_usd=agent_budgets.get(agent),
                )

            s = stats_map[agent]
            s.invocation_count += 1
            s.total_cost_usd += inv.cost_usd
            if inv.is_error:
                s.error_count += 1
                # Check if budget-killed by looking at cost near budget cap
                if s.max_budget_usd and s.total_cost_usd >= s.max_budget_usd * 0.95:
                    s.over_budget_kills += 1

        # Compute averages
        for s in stats_map.values():
            if s.invocation_count > 0:
                s.avg_cost_usd = s.total_cost_usd / s.invocation_count

        # Return sorted by cost descending
        return sorted(stats_map.values(), key=lambda x: x.total_cost_usd, reverse=True)

    async def get_gate_decisions(
        self,
    ) -> list[GateDecision]:
        """Extract gate decisions from recent invocations.

        Looks for result_excerpt containing gate verdicts (pass: true/false).

        Returns:
            List of gate decisions, most recent first.
        """
        invocations = await self.get_invocations(limit=200)
        decisions: list[GateDecision] = []

        for inv in invocations:
            # Try to parse result_excerpt as JSON
            if not inv.result_excerpt:
                continue

            try:
                # result_excerpt might be JSON or plain text
                result = json.loads(inv.result_excerpt)
                if isinstance(result, dict) and "pass" in result:
                    decision = "approved" if result.get("pass") else "blocked"
                    rule_id = result.get("rule_id")
                    decisions.append(
                        GateDecision(
                            invocation_id=inv.invocation_id,
                            agent=inv.agent_used,
                            decision=decision,
                            rule_id=rule_id,
                            cost_usd=inv.cost_usd,
                            timestamp=inv.timestamp,
                        )
                    )
            except (json.JSONDecodeError, KeyError, TypeError):
                # Not a gate decision result; skip
                pass

        return decisions

    def _auth_headers(self) -> dict[str, str]:
        """Return auth headers for AF API."""
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {}

    async def health_check(self) -> bool:
        """Check if AF API is reachable.

        Returns:
            True if GET / returns 2xx, False otherwise.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    headers=self._auth_headers(),
                    timeout=5.0,
                )
                return 200 <= response.status_code < 300
        except httpx.RequestError:
            return False

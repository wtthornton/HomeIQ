"""AgentForge API client for operations dashboard.

Fetches spend data, invocations, gate decisions, and agent budget caps
from AgentForge HTTP API.
"""

import json
import logging
from typing import Any

import httpx
from pydantic import BaseModel, Field
from services.agent_budget_loader import BudgetCap, UnreadableCap

logger = logging.getLogger(__name__)

BUDGET_KILL_FRACTION = 0.95
"""How close one invocation's cost must come to its cap to read as a budget-limited kill."""


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
    duration_ms: float  # AF serializes a fractional millisecond duration
    timestamp: str  # ISO 8601
    mcp_call_count: int = 0
    mcp_hosts: list[str] = Field(default_factory=list)
    result_excerpt: str = ""


class AgentStats(BaseModel):
    """Aggregated stats for one agent.

    `max_budget_usd` is AgentForge's **per-invocation** ceiling, so the figure it
    governs is `max_invocation_cost_usd` — the costliest single run — not the
    cumulative `total_cost_usd`, which no cap in this project bounds.
    """

    agent: str
    budget_key: str = ""  # Gene filename the cap was matched on (see resolve_budget_key)
    invocation_count: int = 0
    error_count: int = 0
    total_cost_usd: float = 0.0
    avg_cost_usd: float = 0.0
    max_invocation_cost_usd: float = 0.0  # Costliest single run — what the cap governs
    max_budget_usd: float | None = None  # Per-invocation cap; None when none is declared
    budget_cap_unreadable: bool = False  # Cap could not be read, so it is unknown, not absent
    over_budget_kills: int = 0  # Count of budget-limited kills


class GateDecision(BaseModel):
    """Gate decision extracted from invocation result."""

    invocation_id: str
    agent: str
    decision: str  # "approved", "blocked", "error"
    rule_id: str | None = None
    cost_usd: float
    timestamp: str


def resolve_budget_key(agent_used: str, agent_budgets: dict[str, BudgetCap], project: str) -> str:
    """Map an invocation's `agent_used` onto the gene filename that declares its cap.

    `load_agent_budgets` keys on the gene filename (`hiq-summarize`), while AF stamps
    published genes with the project namespace (`homeiq-hiq-summarize`). Try the bare
    name first so a gene genuinely named `homeiq-service-auditor` is not mis-stripped
    down to `service-auditor`. Returns `agent_used` unchanged when nothing matches, so
    the caller still gets a stable grouping key for an undeclared agent.
    """
    if agent_used in agent_budgets:
        return agent_used
    stripped = agent_used.removeprefix(f"{project}-")
    return stripped if stripped in agent_budgets else agent_used


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

    async def get_per_agent_stats(self, agent_budgets: dict[str, BudgetCap]) -> list[AgentStats]:
        """Aggregate spend and invocation stats per agent.

        Args:
            agent_budgets: Mapping of agent name -> per-invocation cap (see
                `agent_budget_loader.load_agent_budgets`)

        Returns:
            List of per-agent stats, sorted by cost descending.
        """
        invocations = await self.get_invocations(limit=500)

        # Aggregate by agent
        stats_map: dict[str, AgentStats] = {}
        for inv in invocations:
            agent = inv.agent_used or "unknown"
            if agent not in stats_map:
                budget_key = resolve_budget_key(agent, agent_budgets, self.project)
                cap = agent_budgets.get(budget_key)
                stats_map[agent] = AgentStats(
                    agent=agent,
                    budget_key=budget_key,
                    max_budget_usd=None if isinstance(cap, UnreadableCap) else cap,
                    budget_cap_unreadable=isinstance(cap, UnreadableCap),
                )

            s = stats_map[agent]
            s.invocation_count += 1
            s.total_cost_usd += inv.cost_usd
            s.max_invocation_cost_usd = max(s.max_invocation_cost_usd, inv.cost_usd)
            if inv.is_error:
                s.error_count += 1
                # A budget kill is one invocation whose own cost reached its own cap —
                # cumulative spend crossing a per-invocation cap kills nothing.
                if s.max_budget_usd and inv.cost_usd >= s.max_budget_usd * BUDGET_KILL_FRACTION:
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

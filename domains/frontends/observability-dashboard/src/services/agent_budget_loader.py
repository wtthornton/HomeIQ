"""Load agent budget caps from repo agentforge definitions.

Parses YAML frontmatter of agent markdown files to extract `max_budget_usd` — the
**per-invocation** ceiling AgentForge enforces on each run of a gene.

AgentForge treats an absent or non-positive cap as *unlimited*, so "no cap declared"
and "we could not read the file" must never collapse into the same value: the first is
a deliberate choice, the second is a spend-safety hole wearing its costume. A file that
cannot be read yields `UnreadableCap` and is reported as such.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UnreadableCap:
    """The gene file could not be read, so whether it declares a cap is unknown."""

    reason: str


BudgetCap = float | None | UnreadableCap
"""A declared per-invocation cap, `None` when the gene declares none, or `UnreadableCap`."""


def load_agent_budgets(
    project_root: Path | None = None,
) -> dict[str, BudgetCap]:
    """Load max_budget_usd from agent definitions.

    Scans agentforge/projects/homeiq/agents/*.md files and parses YAML
    frontmatter to extract max_budget_usd per agent.

    Args:
        project_root: Project root directory (auto-detected if None)

    Returns:
        Mapping of agent name -> per-invocation cap, `None` when none is declared, or
        `UnreadableCap` when the definition could not be read.
    """
    if project_root is None:
        # Try to find project root from this file's location
        current = Path(__file__).resolve()
        for parent in current.parents:
            if (parent / ".git").exists():
                project_root = parent
                break
        if project_root is None:
            logger.warning("Could not auto-detect project root; returning empty budgets")
            return {}

    agents_dir = project_root / "agentforge" / "projects" / "homeiq" / "agents"
    if not agents_dir.exists():
        logger.warning(f"Agents directory not found: {agents_dir}; returning empty budgets")
        return {}

    budgets: dict[str, BudgetCap] = {}

    for agent_file in agents_dir.glob("*.md"):
        agent_name = agent_file.stem
        budget = _extract_budget_from_frontmatter(agent_file)
        budgets[agent_name] = budget
        if isinstance(budget, float):
            logger.debug(f"Loaded agent budget: {agent_name} = ${budget} USD per invocation")

    unreadable = [name for name, cap in budgets.items() if isinstance(cap, UnreadableCap)]
    if unreadable:
        logger.error(
            f"Could not read the declared cap for {len(unreadable)} agent(s): "
            f"{', '.join(sorted(unreadable))} — their spend is ungoverned by this surface"
        )
    logger.info(f"Loaded budgets for {len(budgets)} agents")
    return budgets


def _extract_budget_from_frontmatter(
    agent_file: Path,
) -> BudgetCap:
    """Extract max_budget_usd from agent markdown frontmatter.

    Expects format:
        ---
        max_budget_usd: 10.0
        ...
        ---

    Args:
        agent_file: Path to agent .md file

    Returns:
        The declared per-invocation cap, `None` when the file declares no usable cap
        (no frontmatter, no field, or a non-numeric value), or `UnreadableCap` when the
        file itself could not be read or decoded.
    """
    try:
        content = agent_file.read_text()
    except (OSError, UnicodeDecodeError) as e:
        logger.error(f"Cannot read agent definition {agent_file}: {e}")
        return UnreadableCap(reason=f"{type(e).__name__}: {e}")

    # Extract YAML frontmatter (between --- delimiters)
    if not content.startswith("---"):
        return None

    end_of_frontmatter = content.find("---", 3)
    if end_of_frontmatter == -1:
        return None

    frontmatter_str = content[3:end_of_frontmatter].strip()
    try:
        frontmatter = yaml.safe_load(frontmatter_str)
    except yaml.YAMLError as e:
        logger.warning(f"Malformed frontmatter in {agent_file.name}; no cap declared: {e}")
        return None

    if not isinstance(frontmatter, dict):
        logger.warning(f"Frontmatter in {agent_file.name} is not a mapping; no cap declared")
        return None

    budget = frontmatter.get("max_budget_usd")
    if budget is None:
        return None

    try:
        return float(budget)
    except (TypeError, ValueError):
        logger.warning(
            f"max_budget_usd in {agent_file.name} is not a number ({budget!r}); no cap declared"
        )
        return None

"""Load agent budget caps from repo agentforge definitions.

Parses YAML frontmatter of agent markdown files to extract max_budget_usd.
"""

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def load_agent_budgets(
    project_root: Path | None = None,
) -> dict[str, float | None]:
    """Load max_budget_usd from agent definitions.

    Scans agentforge/projects/homeiq/agents/*.md files and parses YAML
    frontmatter to extract max_budget_usd per agent.

    Args:
        project_root: Project root directory (auto-detected if None)

    Returns:
        Mapping of agent name -> max_budget_usd (or None if not set).
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

    budgets: dict[str, float | None] = {}

    for agent_file in agents_dir.glob("*.md"):
        agent_name = agent_file.stem
        budget = _extract_budget_from_frontmatter(agent_file)
        budgets[agent_name] = budget
        if budget is not None:
            logger.debug(f"Loaded agent budget: {agent_name} = ${budget} USD")

    logger.info(f"Loaded budgets for {len(budgets)} agents")
    return budgets


def _extract_budget_from_frontmatter(
    agent_file: Path,
) -> float | None:
    """Extract max_budget_usd from agent markdown frontmatter.

    Expects format:
        ---
        max_budget_usd: 10.0
        ...
        ---

    Args:
        agent_file: Path to agent .md file

    Returns:
        Budget value or None if not found/not a number.
    """
    try:
        with agent_file.open() as f:
            content = f.read()

        # Extract YAML frontmatter (between --- delimiters)
        if not content.startswith("---"):
            return None

        end_of_frontmatter = content.find("---", 3)
        if end_of_frontmatter == -1:
            return None

        frontmatter_str = content[3:end_of_frontmatter].strip()
        frontmatter = yaml.safe_load(frontmatter_str) or {}

        budget = frontmatter.get("max_budget_usd")
        if budget is not None:
            return float(budget)
        return None

    except Exception as e:
        logger.debug(f"Error parsing {agent_file.name}: {e}")
        return None

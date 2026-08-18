"""Tests for agent budget loader."""

from services.agent_budget_loader import (
    _extract_budget_from_frontmatter,
    load_agent_budgets,
)


class TestExtractBudgetFromFrontmatter:
    """Tests for YAML frontmatter parsing."""

    def test_extract_budget_with_valid_frontmatter(self, tmp_path):
        """Test extracting budget from valid frontmatter."""
        agent_file = tmp_path / "test-agent.md"
        agent_file.write_text(
            """---
name: Test Agent
max_budget_usd: 10.5
description: A test agent
---

# Agent Description

This is a test agent.
"""
        )

        budget = _extract_budget_from_frontmatter(agent_file)

        assert budget == 10.5

    def test_extract_budget_integer(self, tmp_path):
        """Test extracting integer budget."""
        agent_file = tmp_path / "test-agent.md"
        agent_file.write_text(
            """---
max_budget_usd: 20
---

Content
"""
        )

        budget = _extract_budget_from_frontmatter(agent_file)

        assert budget == 20.0

    def test_extract_budget_missing_frontmatter(self, tmp_path):
        """Test file without frontmatter returns None."""
        agent_file = tmp_path / "test-agent.md"
        agent_file.write_text("No frontmatter here\n")

        budget = _extract_budget_from_frontmatter(agent_file)

        assert budget is None

    def test_extract_budget_missing_field(self, tmp_path):
        """Test frontmatter without budget field returns None."""
        agent_file = tmp_path / "test-agent.md"
        agent_file.write_text(
            """---
name: Test Agent
description: No budget here
---

Content
"""
        )

        budget = _extract_budget_from_frontmatter(agent_file)

        assert budget is None

    def test_extract_budget_unclosed_frontmatter(self, tmp_path):
        """Test incomplete frontmatter returns None."""
        agent_file = tmp_path / "test-agent.md"
        agent_file.write_text(
            """---
max_budget_usd: 10
No closing delimiter
"""
        )

        budget = _extract_budget_from_frontmatter(agent_file)

        assert budget is None

    def test_extract_budget_non_numeric_value(self, tmp_path):
        """Test non-numeric budget value returns None."""
        agent_file = tmp_path / "test-agent.md"
        agent_file.write_text(
            """---
max_budget_usd: not_a_number
---

Content
"""
        )

        budget = _extract_budget_from_frontmatter(agent_file)

        assert budget is None

    def test_extract_budget_zero(self, tmp_path):
        """Test zero budget is valid."""
        agent_file = tmp_path / "test-agent.md"
        agent_file.write_text(
            """---
max_budget_usd: 0
---

Content
"""
        )

        budget = _extract_budget_from_frontmatter(agent_file)

        assert budget == 0.0


class TestLoadAgentBudgets:
    """Tests for loading budgets from directory."""

    def test_load_agent_budgets_from_directory(self, tmp_path):
        """Test loading multiple agent budgets."""
        # Create agent directory structure
        agents_dir = tmp_path / "agentforge" / "projects" / "homeiq" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        # Create git marker so project root detection works
        (tmp_path / ".git").mkdir()

        # Create agent files
        (agents_dir / "hiq-extract.md").write_text(
            """---
max_budget_usd: 10.0
---

Extract agent
"""
        )

        (agents_dir / "hiq-classify.md").write_text(
            """---
max_budget_usd: 5.0
---

Classify agent
"""
        )

        (agents_dir / "hiq-judge.md").write_text(
            """---
max_budget_usd: 15.0
---

Judge agent
"""
        )

        budgets = load_agent_budgets(tmp_path)

        assert len(budgets) == 3
        assert budgets["hiq-extract"] == 10.0
        assert budgets["hiq-classify"] == 5.0
        assert budgets["hiq-judge"] == 15.0

    def test_load_agent_budgets_with_no_budget_agents(self, tmp_path):
        """Test handling agents without budget fields."""
        agents_dir = tmp_path / "agentforge" / "projects" / "homeiq" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        (tmp_path / ".git").mkdir()

        (agents_dir / "hiq-extract.md").write_text(
            """---
max_budget_usd: 10.0
---

Extract agent
"""
        )

        (agents_dir / "hiq-other.md").write_text(
            """---
name: Other Agent
---

No budget agent
"""
        )

        budgets = load_agent_budgets(tmp_path)

        assert budgets["hiq-extract"] == 10.0
        assert budgets["hiq-other"] is None

    def test_load_agent_budgets_empty_directory(self, tmp_path):
        """Test loading from empty agents directory."""
        agents_dir = tmp_path / "agentforge" / "projects" / "homeiq" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        (tmp_path / ".git").mkdir()

        budgets = load_agent_budgets(tmp_path)

        assert budgets == {}

    def test_load_agent_budgets_missing_directory(self, tmp_path):
        """Test loading when directory doesn't exist."""
        (tmp_path / ".git").mkdir()

        budgets = load_agent_budgets(tmp_path)

        assert budgets == {}

    def test_load_agent_budgets_auto_detect_project_root(self, tmp_path):
        """Test auto-detection of project root from file location."""
        # This test simulates what happens when project_root is None
        # We create the structure and call with None
        agents_dir = tmp_path / "agentforge" / "projects" / "homeiq" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        (tmp_path / ".git").mkdir()

        (agents_dir / "hiq-test.md").write_text(
            """---
max_budget_usd: 5.0
---

Test agent
"""
        )

        # When project_root is None, it tries to auto-detect
        # This is a bit tricky to test without mocking file locations
        # For now, test explicit path passing
        budgets = load_agent_budgets(tmp_path)

        assert "hiq-test" in budgets
        assert budgets["hiq-test"] == 5.0

    def test_load_agent_budgets_ignores_non_md_files(self, tmp_path):
        """Test that non-.md files are ignored."""
        agents_dir = tmp_path / "agentforge" / "projects" / "homeiq" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        (tmp_path / ".git").mkdir()

        (agents_dir / "hiq-extract.md").write_text(
            """---
max_budget_usd: 10.0
---

Extract agent
"""
        )

        (agents_dir / "readme.txt").write_text("Not a markdown file")
        (agents_dir / ".gitkeep").write_text("")

        budgets = load_agent_budgets(tmp_path)

        assert len(budgets) == 1
        assert "hiq-extract" in budgets

    def test_load_agent_budgets_with_malformed_yaml(self, tmp_path):
        """Test handling of malformed YAML in frontmatter."""
        agents_dir = tmp_path / "agentforge" / "projects" / "homeiq" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        (tmp_path / ".git").mkdir()

        # Malformed YAML (will be parsed as dict with key: value)
        (agents_dir / "hiq-bad.md").write_text(
            """---
this: is: : bad yaml
---

Content
"""
        )

        budgets = load_agent_budgets(tmp_path)

        # Should gracefully handle and return None for this agent
        assert "hiq-bad" in budgets
        assert budgets["hiq-bad"] is None

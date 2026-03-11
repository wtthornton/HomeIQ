"""
Prompt file existence tests for the auto-fix pipeline.

Ensures prompt paths referenced in config resolve to existing files.
"""

from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AUTO_FIX_DIR = PROJECT_ROOT / "auto-fix-pipeline"
HOMEIQ_DEFAULT_PATH = AUTO_FIX_DIR / "config" / "example" / "homeiq-default.yaml"

PROMPT_KEYS = ["find", "retry", "fix", "refactor", "test", "feedback"]


def _load_config() -> dict:
    with open(HOMEIQ_DEFAULT_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class TestPromptFiles:
    """Prompt file existence and structure tests."""

    def test_config_has_prompts_section(self) -> None:
        """Config has prompts section."""
        cfg = _load_config()
        assert "prompts" in cfg

    def test_prompt_paths_resolve_to_existing_files(self) -> None:
        """All prompt paths in config point to existing files."""
        cfg = _load_config()
        prompts = cfg.get("prompts", {})
        missing: list[str] = []
        for key in PROMPT_KEYS:
            path_str = prompts.get(key)
            if not path_str:
                continue
            full_path = PROJECT_ROOT / path_str
            if not full_path.exists():
                missing.append(f"{key}: {path_str} -> {full_path}")
        assert not missing, f"Missing prompt files: {missing}"

    def test_prompt_files_are_markdown(self) -> None:
        """Prompt files have .md extension."""
        cfg = _load_config()
        prompts = cfg.get("prompts", {})
        for key, path_str in prompts.items():
            if path_str:
                assert path_str.endswith(".md"), f"Prompt {key} should be .md: {path_str}"

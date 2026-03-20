"""Tests for PromptLoader — Epic 94: Prompt Sections to Config Files.

Story 94.5: Validation & Regression Tests
"""

from __future__ import annotations

import os
import shutil
import textwrap
from pathlib import Path

import pytest
import yaml

# ── Path setup ──────────────────────────────────────────────────────
SRC_DIR = Path(__file__).parent.parent / "src"
import sys

sys.path.insert(0, str(SRC_DIR))

from prompts.prompt_loader import PromptLoader
from prompts.system_prompt import SYSTEM_PROMPT


# ═══════════════════════════════════════════════════════════════════
# 94.5.1  Byte-identical regression test
# ═══════════════════════════════════════════════════════════════════

class TestRegressionByteIdentical:
    """Assembled prompt from PromptLoader must equal SYSTEM_PROMPT constant."""

    def test_assembled_equals_system_prompt(self):
        """Core regression: load() output == SYSTEM_PROMPT byte-for-byte."""
        loader = PromptLoader()
        assembled = loader.load()
        assert assembled == SYSTEM_PROMPT, (
            f"Assembled prompt differs from SYSTEM_PROMPT. "
            f"Lengths: assembled={len(assembled)} vs constant={len(SYSTEM_PROMPT)}"
        )

    def test_assembled_length(self):
        loader = PromptLoader()
        assembled = loader.load()
        assert len(assembled) == len(SYSTEM_PROMPT)

    def test_version(self):
        loader = PromptLoader()
        assert loader.version == "2.1.0"

    def test_section_count(self):
        loader = PromptLoader()
        loader.load()
        assert loader.section_count == 13


# ═══════════════════════════════════════════════════════════════════
# 94.5.3  Config validation tests
# ═══════════════════════════════════════════════════════════════════

class TestConfigValidation:

    def test_missing_config_falls_back(self, tmp_path):
        """Missing config file → fallback to SYSTEM_PROMPT constant."""
        loader = PromptLoader(config_path=str(tmp_path / "nonexistent.yaml"))
        result = loader.load()
        assert result == SYSTEM_PROMPT

    def test_invalid_yaml_falls_back(self, tmp_path):
        """Malformed YAML config → fallback to constant."""
        bad_config = tmp_path / "bad.yaml"
        bad_config.write_text("{{{{not valid yaml", encoding="utf-8")
        loader = PromptLoader(config_path=str(bad_config))
        result = loader.load()
        assert result == SYSTEM_PROMPT


# ═══════════════════════════════════════════════════════════════════
# 94.5.4  Missing section file fallback
# ═══════════════════════════════════════════════════════════════════

class TestMissingSectionFallback:

    def test_missing_section_file_falls_back(self, tmp_path):
        """If a section file is absent, loader falls back to constant."""
        # Create minimal config pointing to nonexistent section file
        config = {
            "version": "test",
            "preamble_file": "preamble.txt",
            "sections": [
                {
                    "name": "test",
                    "file": "missing.txt",
                    "index": "0",
                    "title": "TEST",
                    "enabled": True,
                }
            ],
            "header_template": "# SECTION {index}: {title}",
            "section_separator": "\n\n",
        }
        config_path = tmp_path / "prompt_config.yaml"
        config_path.write_text(yaml.dump(config), encoding="utf-8")
        (tmp_path / "sections").mkdir()

        loader = PromptLoader(config_path=str(config_path))
        result = loader.load()
        assert result == SYSTEM_PROMPT  # fell back


# ═══════════════════════════════════════════════════════════════════
# 94.5.5  Section ordering test
# ═══════════════════════════════════════════════════════════════════

class TestSectionOrdering:

    def _make_config(self, tmp_path, sections_order):
        """Helper to build a minimal config in tmp_path."""
        sections_dir = tmp_path / "sections"
        sections_dir.mkdir(exist_ok=True)

        # Preamble
        (sections_dir / "preamble.txt").write_text("PREAMBLE", encoding="utf-8")

        section_defs = []
        for i, name in enumerate(sections_order):
            fname = f"{name}.txt"
            (sections_dir / fname).write_text(f"Content of {name}", encoding="utf-8")
            section_defs.append(
                {
                    "name": name,
                    "file": fname,
                    "index": str(i),
                    "title": name.upper(),
                    "enabled": True,
                }
            )

        config = {
            "version": "test",
            "preamble_file": "preamble.txt",
            "sections": section_defs,
            "header_template": "## {index}: {title}",
            "section_separator": "\n\n",
            "variables": {},
        }
        config_path = tmp_path / "prompt_config.yaml"
        config_path.write_text(yaml.dump(config), encoding="utf-8")
        return str(config_path)

    def test_order_abc(self, tmp_path):
        config = self._make_config(tmp_path, ["alpha", "bravo", "charlie"])
        loader = PromptLoader(config_path=config)
        result = loader.load()
        a_pos = result.index("Content of alpha")
        b_pos = result.index("Content of bravo")
        c_pos = result.index("Content of charlie")
        assert a_pos < b_pos < c_pos

    def test_order_reversed(self, tmp_path):
        config = self._make_config(tmp_path, ["charlie", "bravo", "alpha"])
        loader = PromptLoader(config_path=config)
        result = loader.load()
        c_pos = result.index("Content of charlie")
        b_pos = result.index("Content of bravo")
        a_pos = result.index("Content of alpha")
        assert c_pos < b_pos < a_pos


# ═══════════════════════════════════════════════════════════════════
# 94.5.6  Disabled section test
# ═══════════════════════════════════════════════════════════════════

class TestDisabledSections:

    def test_disabled_section_excluded(self, tmp_path):
        sections_dir = tmp_path / "sections"
        sections_dir.mkdir()
        (sections_dir / "preamble.txt").write_text("PRE", encoding="utf-8")
        (sections_dir / "a.txt").write_text("AAA", encoding="utf-8")
        (sections_dir / "b.txt").write_text("BBB", encoding="utf-8")

        config = {
            "version": "test",
            "preamble_file": "preamble.txt",
            "sections": [
                {"name": "a", "file": "a.txt", "index": "0", "title": "A", "enabled": True},
                {"name": "b", "file": "b.txt", "index": "1", "title": "B", "enabled": False},
            ],
            "header_template": "## {index}: {title}",
            "section_separator": "\n\n",
            "variables": {},
        }
        config_path = tmp_path / "prompt_config.yaml"
        config_path.write_text(yaml.dump(config), encoding="utf-8")

        loader = PromptLoader(config_path=str(config_path))
        result = loader.load()
        assert "AAA" in result
        assert "BBB" not in result
        assert loader.section_count == 1


# ═══════════════════════════════════════════════════════════════════
# 94.5.7  Token budget test
# ═══════════════════════════════════════════════════════════════════

class TestTokenBudget:

    def test_fits_within_32k_tokens(self):
        """Assembled prompt should fit within MAX_INPUT_TOKENS (32K)."""
        loader = PromptLoader()
        prompt = loader.load()
        # Rough estimate: 4 chars ≈ 1 token
        approx_tokens = len(prompt) // 4
        assert approx_tokens < 32_000, (
            f"Prompt is ~{approx_tokens} tokens, exceeds 32K budget"
        )


# ═══════════════════════════════════════════════════════════════════
# 94.4.5  Variable substitution tests
# ═══════════════════════════════════════════════════════════════════

class TestVariableSubstitution:

    def test_default_variables_produce_identical_output(self):
        """Default config variables → byte-identical to SYSTEM_PROMPT."""
        loader = PromptLoader()
        result = loader.load()
        assert result == SYSTEM_PROMPT

    def test_env_var_override(self, monkeypatch):
        """PROMPT_VAR_HA_VERSION overrides config default."""
        monkeypatch.setenv("PROMPT_VAR_HA_VERSION", "2026.4")
        loader = PromptLoader()
        result = loader.load()
        assert "2026.4" in result
        assert "2025.10+/2026.x" not in result

    def test_extra_vars(self):
        """Extra vars passed to load() are substituted."""
        loader = PromptLoader()
        result = loader.load(extra_vars={"ha_version": "3000.1"})
        assert "3000.1" in result

    def test_unknown_placeholders_left_as_is(self, tmp_path):
        """Unresolved placeholders are kept verbatim (no crash)."""
        sections_dir = tmp_path / "sections"
        sections_dir.mkdir()
        (sections_dir / "preamble.txt").write_text("Hello", encoding="utf-8")
        (sections_dir / "a.txt").write_text(
            "Use {unknown_var} here", encoding="utf-8"
        )

        config = {
            "version": "test",
            "preamble_file": "preamble.txt",
            "sections": [
                {"name": "a", "file": "a.txt", "index": "0", "title": "A", "enabled": True},
            ],
            "header_template": "## {index}: {title}",
            "section_separator": "\n\n",
            "variables": {"known": "value"},
        }
        config_path = tmp_path / "prompt_config.yaml"
        config_path.write_text(yaml.dump(config), encoding="utf-8")

        loader = PromptLoader(config_path=str(config_path))
        result = loader.load()
        assert "{unknown_var}" in result  # left as-is


# ═══════════════════════════════════════════════════════════════════
# 94.3.5  PromptLoader unit tests
# ═══════════════════════════════════════════════════════════════════

class TestPromptLoaderUnit:

    def test_get_section(self):
        loader = PromptLoader()
        loader.load()
        section = loader.get_section("core_identity")
        assert section is not None
        assert "Your Role" in section

    def test_get_section_not_found(self):
        loader = PromptLoader()
        loader.load()
        assert loader.get_section("nonexistent") is None

    def test_reload(self):
        loader = PromptLoader()
        first = loader.load()
        second = loader.reload()
        assert first == second

    def test_load_raw_has_placeholders(self):
        loader = PromptLoader()
        raw = loader.load_raw()
        assert "{ha_version}" in raw

    def test_load_resolves_placeholders(self):
        loader = PromptLoader()
        result = loader.load()
        assert "{ha_version}" not in result
        assert "2025.10+/2026.x" in result

    def test_prompt_config_env_var(self, monkeypatch, tmp_path):
        """PROMPT_CONFIG_PATH env var overrides default config location."""
        # Point to a nonexistent path → fallback
        monkeypatch.setenv("PROMPT_CONFIG_PATH", str(tmp_path / "custom.yaml"))
        loader = PromptLoader()
        result = loader.load()
        assert result == SYSTEM_PROMPT  # fell back

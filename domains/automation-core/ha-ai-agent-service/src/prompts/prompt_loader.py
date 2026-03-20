"""Prompt Loader — assembles system prompt from config + section files.

Epic 94: Prompt Sections to Config Files
Story 94.3: PromptLoader service

Loads prompt_config.yaml, reads section .txt files, and assembles
the complete system prompt. Falls back to the SYSTEM_PROMPT constant
if section files are unavailable.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# Default paths (relative to this file)
_PROMPTS_DIR = Path(__file__).parent
_DEFAULT_CONFIG = _PROMPTS_DIR / "prompt_config.yaml"


class PromptLoader:
    """Loads and assembles system prompt from section files."""

    def __init__(self, config_path: str | None = None) -> None:
        self._config_path = Path(
            config_path
            or os.environ.get("PROMPT_CONFIG_PATH", "")
            or str(_DEFAULT_CONFIG)
        )
        self._config: dict | None = None
        self._sections: dict[str, str] = {}
        self._assembled_raw: str | None = None
        self._assembled: str | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, extra_vars: dict[str, str] | None = None) -> str:
        """Load config, read section files, assemble prompt with variable substitution.

        Variable resolution order (highest priority first):
        1. ``PROMPT_VAR_<NAME>`` environment variables
        2. *extra_vars* argument
        3. ``variables`` section in prompt_config.yaml

        Unrecognised ``{placeholders}`` (e.g. error-template examples in the
        prompt) are left untouched — only configured variable names are
        substituted.

        Args:
            extra_vars: Optional additional variables to merge in.

        Returns:
            The fully assembled and variable-substituted system prompt.
        """
        if self._assembled is not None and extra_vars is None:
            return self._assembled

        try:
            raw = self._load_raw()
            result = self._apply_variables(raw, extra_vars)
            if extra_vars is None:
                self._assembled = result
            self._log_summary(result)
            return result
        except Exception:
            logger.warning(
                "⚠️ Failed to load prompt from config — falling back to SYSTEM_PROMPT constant"
            )
            from .system_prompt import SYSTEM_PROMPT

            self._assembled = SYSTEM_PROMPT
            return self._assembled

    def load_raw(self) -> str:
        """Load and assemble WITHOUT variable substitution.

        Useful for regression tests comparing against the raw section files.
        """
        return self._load_raw()

    def get_section(self, name: str) -> str | None:
        """Get a specific section's raw text by name."""
        if not self._sections:
            self._load_raw()
        return self._sections.get(name)

    @property
    def version(self) -> str:
        """Prompt version from config."""
        if not self._config:
            self._load_config()
        return self._config.get("version", "unknown") if self._config else "unknown"

    @property
    def section_count(self) -> int:
        """Number of enabled sections."""
        if not self._config:
            return 0
        return sum(
            1
            for s in self._config.get("sections", [])
            if s.get("enabled", True)
        )

    def reload(self) -> str:
        """Force reload from disk."""
        self._config = None
        self._sections.clear()
        self._assembled_raw = None
        self._assembled = None
        return self.load()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_raw(self) -> str:
        """Load config + sections and assemble without variable substitution."""
        if self._assembled_raw is not None:
            return self._assembled_raw
        self._load_config()
        self._read_sections()
        self._assembled_raw = self._assemble()
        return self._assembled_raw

    def _apply_variables(
        self, text: str, extra_vars: dict[str, str] | None = None
    ) -> str:
        """Substitute only known config/env variables in *text*."""
        variables: dict[str, str] = {}
        if self._config:
            variables.update(self._config.get("variables", {}))
        if extra_vars:
            variables.update(extra_vars)

        # Env var overrides: PROMPT_VAR_HA_VERSION → ha_version
        for key, val in os.environ.items():
            if key.startswith("PROMPT_VAR_"):
                var_name = key[len("PROMPT_VAR_"):].lower()
                variables[var_name] = val

        if not variables:
            return text

        result = text
        for name, value in variables.items():
            placeholder = "{" + name + "}"
            result = result.replace(placeholder, str(value))

        return result

    def _load_config(self) -> None:
        if self._config is not None:
            return
        if not self._config_path.exists():
            raise FileNotFoundError(
                f"Prompt config not found: {self._config_path}"
            )
        with open(self._config_path, encoding="utf-8") as f:
            self._config = yaml.safe_load(f)
        logger.debug("Loaded prompt config from %s", self._config_path)

    def _read_sections(self) -> None:
        if not self._config:
            return
        sections_dir = self._config_path.parent / "sections"

        # Read preamble
        preamble_file = self._config.get("preamble_file")
        if preamble_file:
            preamble_path = sections_dir / preamble_file
            if preamble_path.exists():
                self._sections["__preamble__"] = preamble_path.read_text(
                    encoding="utf-8"
                )

        # Read each enabled section
        for section in self._config.get("sections", []):
            if not section.get("enabled", True):
                continue
            name = section["name"]
            filepath = sections_dir / section["file"]
            if not filepath.exists():
                raise FileNotFoundError(
                    f"Section file missing: {filepath} (section '{name}')"
                )
            self._sections[name] = filepath.read_text(encoding="utf-8")

    def _assemble(self) -> str:
        if not self._config:
            raise RuntimeError("Config not loaded")

        separator = self._config.get("section_separator", "\n\n")
        header_tpl = self._config.get(
            "header_template",
            "# ═══════════════════════════════════════════════════════════════════════════════\n"
            "# SECTION {index}: {title}\n"
            "# ═══════════════════════════════════════════════════════════════════════════════",
        )

        parts: list[str] = []

        # Preamble
        preamble = self._sections.get("__preamble__", "")
        if preamble:
            parts.append(preamble)

        # Sections
        for section in self._config.get("sections", []):
            if not section.get("enabled", True):
                continue
            name = section["name"]
            content = self._sections.get(name, "")
            header = header_tpl.replace("{index}", section["index"]).replace(
                "{title}", section["title"]
            )
            parts.append(header)
            parts.append(content)

        return separator.join(parts)

    def _log_summary(self, prompt: str) -> None:
        approx_tokens = len(prompt) // 4
        logger.info(
            "✅ System prompt loaded from config (v%s, %d sections, ~%d tokens, %d chars)",
            self.version,
            self.section_count,
            approx_tokens,
            len(prompt),
        )

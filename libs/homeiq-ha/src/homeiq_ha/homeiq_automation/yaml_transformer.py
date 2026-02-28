"""
YAML Transformation Rules Engine

Applies strict rules, blueprints, examples, and LLM for YAML transformation.
Strategy:
1. Strict Rules First: Apply deterministic rules based on HA version
2. Blueprint Matching: Match to Home Assistant blueprints when applicable
3. Example-Based: Use example YAML from community automations
4. LLM Fallback: Use LLM for complex transformations not covered by rules
"""

import logging

from homeiq_ha.yaml_validation_service.version_aware_renderer import VersionAwareRenderer

from .blueprints import BlueprintPatternLibrary
from .converter import HomeIQToAutomationSpecConverter
from .schema import HomeIQAutomation

logger = logging.getLogger(__name__)

# LLM prompt template — version and JSON placeholders filled at runtime.
_LLM_PROMPT = (
    "Convert this HomeIQ JSON Automation to Home Assistant YAML format.\n\n"
    "Target HA Version: {version}\n\nHomeIQ JSON:\n{json}\n\n"
    "Requirements:\n"
    "- Valid HA automation YAML following {version} format\n"
    "- All triggers, conditions, and actions included\n"
    "- Proper field names (trigger:/action: for 2025.10+)\n"
    "- initial_state: true for 2025.10+\n"
    "- Return ONLY the YAML, no explanations\n"
)


class YAMLTransformer:
    """
    Transforms HomeIQ JSON to YAML using multiple strategies.

    Strategy order:
    1. Strict rules (deterministic, version-based)
    2. Blueprint matching (reusable patterns)
    3. Example-based (community automations)
    4. LLM fallback (complex cases)
    """

    def __init__(
        self,
        ha_version: str | None = None,
        openai_client=None,
        use_llm_fallback: bool = True,
    ):
        """
        Initialize YAML transformer.

        Args:
            ha_version: Target Home Assistant version
            openai_client: Optional OpenAI client for LLM fallback
            use_llm_fallback: Whether to use LLM for complex transformations
        """
        self.ha_version = ha_version
        self.openai_client = openai_client
        self.use_llm_fallback = use_llm_fallback
        # Renderer handles HA version-specific YAML field names and structure
        self.version_renderer = VersionAwareRenderer(ha_version=ha_version)
        # Blueprint library provides reusable automation templates
        self.blueprint_library = BlueprintPatternLibrary()
        # Extensible pattern store for community-contributed examples
        self.example_patterns: dict[str, str] = {}

    async def transform_to_yaml(
        self,
        automation: HomeIQAutomation,
        strategy: str = "auto"
    ) -> str:
        """
        Transform HomeIQ JSON Automation to YAML.

        Args:
            automation: HomeIQ JSON Automation
            strategy: Transformation strategy ("strict", "blueprint", "example", "llm", "auto")

        Returns:
            YAML string
        """
        # Strategy dispatch: maps strategy name to async handler method
        dispatch = {
            "strict": self._transform_with_strict_rules,
            "blueprint": self._transform_with_blueprint,
            "example": self._transform_with_examples,
            "llm": self._transform_with_llm,
        }
        # "auto" tries all strategies in priority order; named strategy tries only one
        strategies = list(dispatch) if strategy == "auto" else [strategy]

        for strat in strategies:
            handler = dispatch.get(strat)
            if not handler:
                continue
            try:
                yaml_content = await handler(automation)
                if yaml_content:
                    logger.info("Successfully transformed using %s strategy", strat)
                    return yaml_content
            except Exception as e:
                logger.warning("Strategy %s failed: %s", strat, e)
                continue

        # All strategies exhausted — use direct converter as last resort
        return self._fallback_render(automation)

    def _fallback_render(self, automation: HomeIQAutomation) -> str:
        """Fallback: convert via AutomationSpec and render directly."""
        logger.warning("All strategies failed, using direct renderer")
        # Direct path: HomeIQ JSON → AutomationSpec → version-aware YAML
        spec = HomeIQToAutomationSpecConverter().convert(automation)
        return self.version_renderer.render(spec)

    async def _transform_with_strict_rules(self, automation: HomeIQAutomation) -> str:
        """Transform using strict deterministic rules (version-specific)."""
        # Primary strategy: deterministic conversion without LLM or pattern matching
        spec = HomeIQToAutomationSpecConverter().convert(automation)
        return self.version_renderer.render(spec)

    async def _transform_with_blueprint(self, automation: HomeIQAutomation) -> str:
        """Transform by matching automation to Home Assistant blueprint patterns."""
        # Match automation triggers/actions to a known blueprint template
        blueprint = self.blueprint_library.find_matching_blueprint(automation)
        if not blueprint:
            raise ValueError("No matching blueprint found")
        # Generate YAML using the matched blueprint's template and input values
        return self.blueprint_library.generate_blueprint_yaml(automation, blueprint)

    async def _transform_with_examples(self, automation: HomeIQAutomation) -> str:
        """Transform using example YAML from community automations."""
        # Delegates to strict rules until community example matching is implemented
        return await self._transform_with_strict_rules(automation)

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        """Strip markdown code fences (``` blocks) from LLM-generated YAML."""
        # Early return when no fences are present
        if not text.startswith("```"):
            return text
        lines = text.split("\n")
        # Skip opening fence (e.g. ```yaml) and optional closing fence
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines)

    def _build_llm_prompt(self, automation: HomeIQAutomation) -> str:
        """Build the LLM prompt for YAML generation."""
        # Fill module-level template with HA version and serialized automation JSON
        return _LLM_PROMPT.format(
            version=self.ha_version or "latest",
            json=automation.model_dump_json(indent=2),
        )

    async def _transform_with_llm(self, automation: HomeIQAutomation) -> str:
        """Transform using LLM for complex cases not covered by other strategies."""
        # Requires both an OpenAI client and LLM fallback to be enabled
        if not self.openai_client or not self.use_llm_fallback:
            raise ValueError("LLM fallback not available")

        try:
            # Low temperature for deterministic YAML output
            yaml_content = await self.openai_client.generate_yaml(
                prompt=self._build_llm_prompt(automation),
                temperature=0.1,
                max_tokens=3000,
            )
            # LLM may wrap YAML in markdown fences — strip them
            return self._strip_markdown_fences(yaml_content).strip()
        except Exception as e:
            logger.error("LLM transformation failed: %s", e)
            raise


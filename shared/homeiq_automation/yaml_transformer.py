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
from typing import Any

from shared.yaml_validation_service.schema import AutomationSpec
from shared.yaml_validation_service.version_aware_renderer import VersionAwareRenderer

from .blueprints import BlueprintPatternLibrary
from .schema import HomeIQAutomation

logger = logging.getLogger(__name__)


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
        use_llm_fallback: bool = True
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
        self.version_renderer = VersionAwareRenderer(ha_version=ha_version)
        self.blueprint_library = BlueprintPatternLibrary()
        
        # Example YAML patterns (could be loaded from community automations)
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
        if strategy == "auto":
            # Try strategies in order until one succeeds
            strategies = ["strict", "blueprint", "example", "llm"]
        else:
            strategies = [strategy]
        
        for strat in strategies:
            try:
                if strat == "strict":
                    yaml_content = await self._transform_with_strict_rules(automation)
                elif strat == "blueprint":
                    yaml_content = await self._transform_with_blueprint(automation)
                elif strat == "example":
                    yaml_content = await self._transform_with_examples(automation)
                elif strat == "llm":
                    yaml_content = await self._transform_with_llm(automation)
                else:
                    continue
                
                if yaml_content:
                    logger.info(f"Successfully transformed using {strat} strategy")
                    return yaml_content
            except Exception as e:
                logger.warning(f"Strategy {strat} failed: {e}")
                continue
        
        # Fallback: use version-aware renderer directly
        logger.warning("All transformation strategies failed, using direct renderer")
        from shared.homeiq_automation.converter import HomeIQToAutomationSpecConverter
        converter = HomeIQToAutomationSpecConverter()
        spec = converter.convert(automation)
        return self.version_renderer.render(spec)
    
    async def _transform_with_strict_rules(self, automation: HomeIQAutomation) -> str:
        """
        Transform using strict deterministic rules.
        
        This is the primary method - applies version-specific rules.
        """
        # Convert to AutomationSpec
        from shared.homeiq_automation.converter import HomeIQToAutomationSpecConverter
        converter = HomeIQToAutomationSpecConverter()
        spec = converter.convert(automation)
        
        # Render with version awareness
        yaml_content = self.version_renderer.render(spec)
        
        return yaml_content
    
    async def _transform_with_blueprint(self, automation: HomeIQAutomation) -> str:
        """
        Transform using Home Assistant blueprint patterns.
        
        Matches automation to blueprint and generates blueprint YAML.
        """
        # Find matching blueprint
        blueprint = self.blueprint_library.find_matching_blueprint(automation)
        if not blueprint:
            raise ValueError("No matching blueprint found")
        
        # Generate blueprint YAML
        blueprint_yaml = self.blueprint_library.generate_blueprint_yaml(
            automation, blueprint
        )
        
        return blueprint_yaml
    
    async def _transform_with_examples(self, automation: HomeIQAutomation) -> str:
        """
        Transform using example YAML from community automations.
        
        Matches automation structure to known examples and adapts them.
        """
        # For now, fall back to strict rules
        # In full implementation, would match to example patterns
        return await self._transform_with_strict_rules(automation)
    
    async def _transform_with_llm(self, automation: HomeIQAutomation) -> str:
        """
        Transform using LLM for complex cases.
        
        Uses LLM to generate YAML from HomeIQ JSON when other methods fail.
        """
        if not self.openai_client or not self.use_llm_fallback:
            raise ValueError("LLM fallback not available")
        
        # Build prompt with HomeIQ JSON and version requirements
        prompt = f"""Convert this HomeIQ JSON Automation to Home Assistant YAML format.

Target Home Assistant Version: {self.ha_version or 'latest'}

HomeIQ JSON:
{automation.model_dump_json(indent=2)}

Requirements:
- Generate valid Home Assistant automation YAML
- Follow {self.ha_version or 'latest'} format requirements
- Include all triggers, conditions, and actions
- Use proper field names (trigger: not triggers:, action: not actions: for 2025.10+)
- Include initial_state: true for 2025.10+
- Return ONLY the YAML, no explanations or markdown code blocks
"""
        
        try:
            yaml_content = await self.openai_client.generate_yaml(
                prompt=prompt,
                temperature=0.1,
                max_tokens=3000
            )
            
            # Clean YAML
            if yaml_content.startswith("```"):
                lines = yaml_content.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                yaml_content = "\n".join(lines)
            
            return yaml_content.strip()
        
        except Exception as e:
            logger.error(f"LLM transformation failed: {e}")
            raise


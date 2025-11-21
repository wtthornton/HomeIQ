"""
Enhanced Automation Generator

Intelligent automation generation using pattern matching + LLM fallback.

Flow:
1. Try pattern matching first (fast, free, high quality)
2. If no pattern match, use LLM generation (existing flow)
3. Support hybrid mode: pattern + LLM enhancement for customizations
"""

import logging
from dataclasses import dataclass
from typing import Any

from .nl_automation_generator import NLAutomationGenerator, NLAutomationRequest
from .patterns import (
    PatternComposer,
    PatternMatcher,
    get_pattern_composer,
    get_pattern_matcher,
)

logger = logging.getLogger(__name__)


@dataclass
class EnhancedGenerationResult:
    """Result from enhanced automation generation"""
    automations: list[dict[str, Any]]  # List of generated automations
    method: str  # 'pattern', 'llm', 'hybrid'
    patterns_used: list[str] | None = None
    confidence: float = 0.0
    generation_time_ms: int = 0


class EnhancedAutomationGenerator:
    """
    Enhanced automation generator with pattern matching + LLM fallback.

    Strategies:
    1. Pure pattern - Pattern match with high confidence (> 0.7)
    2. Hybrid - Pattern match with customizations needed
    3. Pure LLM - No pattern match, use existing NL generator
    """

    def __init__(
        self,
        nl_generator: NLAutomationGenerator,
        pattern_matcher: PatternMatcher | None = None,
        pattern_composer: PatternComposer | None = None,
        pattern_threshold: float = 0.5,  # Minimum confidence for pattern use
    ):
        """
        Initialize enhanced generator.

        Args:
            nl_generator: Existing NL automation generator (LLM-based)
            pattern_matcher: Pattern matcher (default: create new)
            pattern_composer: Pattern composer (default: create new)
            pattern_threshold: Minimum confidence to use pattern (0.0-1.0)
        """
        self.nl_generator = nl_generator
        self.pattern_matcher = pattern_matcher or get_pattern_matcher()
        self.pattern_composer = pattern_composer or get_pattern_composer()
        self.pattern_threshold = pattern_threshold

    async def generate(
        self,
        request: NLAutomationRequest,
        available_entities: list[dict[str, Any]],
    ) -> EnhancedGenerationResult:
        """
        Generate automation using best available method.

        Args:
            request: Natural language automation request
            available_entities: List of available HA entities

        Returns:
            EnhancedGenerationResult with automation(s) and metadata
        """
        import time
        start_time = time.time()

        logger.info(f"Enhanced generation for: '{request.request_text[:100]}'")

        # Step 1: Try pattern matching
        pattern_matches = await self.pattern_matcher.match_patterns(
            request.request_text,
            available_entities,
        )

        if pattern_matches and pattern_matches[0].confidence >= self.pattern_threshold:
            # Found pattern match(es) with sufficient confidence
            logger.info(
                f"Using pattern-based generation "
                f"({len(pattern_matches)} match(es), "
                f"best confidence: {pattern_matches[0].confidence:.2f})",
            )

            # Compose patterns into automation(s)
            composed = await self.pattern_composer.compose(
                pattern_matches,
                request.request_text,
            )

            generation_time_ms = int((time.time() - start_time) * 1000)

            return EnhancedGenerationResult(
                automations=composed.automations,
                method=composed.strategy,
                patterns_used=composed.patterns_used,
                confidence=composed.confidence,
                generation_time_ms=generation_time_ms,
            )

        # Step 2: No pattern match or low confidence → use LLM
        logger.info(
            f"No pattern match (threshold: {self.pattern_threshold}), "
            f"using LLM generation",
        )

        llm_result = await self.nl_generator.generate(request)

        generation_time_ms = int((time.time() - start_time) * 1000)

        return EnhancedGenerationResult(
            automations=[{
                "yaml": llm_result.automation_yaml,
                "title": llm_result.title,
                "description": llm_result.description,
                "explanation": llm_result.explanation,
                "safety_result": llm_result.safety_result,
                "warnings": llm_result.warnings,
            }],
            method="llm",
            confidence=llm_result.confidence,
            generation_time_ms=generation_time_ms,
        )

    async def get_pattern_suggestions(
        self,
        request: str,
        available_entities: list[dict[str, Any]],
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Get suggested patterns for a request without generating YAML.

        Useful for showing users what patterns could be used.

        Args:
            request: Natural language request
            available_entities: Available HA entities
            limit: Maximum number of suggestions

        Returns:
            List of pattern suggestions with confidence scores
        """
        matches = await self.pattern_matcher.match_patterns(
            request,
            available_entities,
        )

        suggestions = []
        for match in matches[:limit]:
            suggestions.append({
                "pattern_id": match.pattern_id,
                "name": match.pattern.name,
                "description": match.pattern.description,
                "confidence": match.confidence,
                "category": match.pattern.category,
                "variables": match.variables,
                "missing_variables": match.missing_variables,
            })

        return suggestions


def get_enhanced_generator(
    nl_generator: NLAutomationGenerator,
    pattern_threshold: float = 0.5,
) -> EnhancedAutomationGenerator:
    """
    Factory function to create enhanced automation generator.

    Args:
        nl_generator: Existing NL automation generator
        pattern_threshold: Minimum confidence for pattern use

    Returns:
        Configured EnhancedAutomationGenerator
    """
    return EnhancedAutomationGenerator(
        nl_generator=nl_generator,
        pattern_threshold=pattern_threshold,
    )

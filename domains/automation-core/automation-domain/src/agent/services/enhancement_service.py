"""
Automation Enhancement Service

Generates automation enhancements using:
- LLM for small/medium/large enhancements
- Patterns API for advanced enhancements
- Synergies API for fun/crazy enhancements
- LRU caching for repeated prompts (cost optimization)
"""

import asyncio
import hashlib
import logging
import re
import time
from typing import Any

from ..clients.patterns_client import PatternsClient
from ..clients.synergies_client import SynergiesClient
from ..config import Settings

logger = logging.getLogger(__name__)


# Cache for enhancement results (prompt hash -> (timestamp, result))
# TTL: 30 minutes for prompt enhancements (prompts don't change often)
_enhancement_cache: dict[str, tuple[float, list[Any]]] = {}
_CACHE_TTL_SECONDS = 1800  # 30 minutes
_MAX_CACHE_SIZE = 100  # Maximum cached entries


def _get_prompt_hash(prompt: str, mode: str = "default") -> str:
    """Generate a cache key from prompt and mode."""
    content = f"{mode}:{prompt.strip().lower()}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _get_cached_enhancement(cache_key: str) -> list[Any] | None:
    """Get cached enhancement if still valid."""
    if cache_key in _enhancement_cache:
        timestamp, result = _enhancement_cache[cache_key]
        if time.time() - timestamp < _CACHE_TTL_SECONDS:
            logger.debug(f"[Cache] HIT for enhancement key {cache_key[:8]}...")
            return result
        # Expired, remove it
        del _enhancement_cache[cache_key]
        logger.debug(f"[Cache] EXPIRED for enhancement key {cache_key[:8]}...")
    return None


def _set_cached_enhancement(cache_key: str, result: list[Any]) -> None:
    """Cache an enhancement result."""
    # Evict oldest entries if cache is full
    if len(_enhancement_cache) >= _MAX_CACHE_SIZE:
        oldest_key = min(_enhancement_cache.keys(), key=lambda k: _enhancement_cache[k][0])
        del _enhancement_cache[oldest_key]
        logger.debug("[Cache] EVICTED oldest entry to make room")

    _enhancement_cache[cache_key] = (time.time(), result)
    logger.debug(
        f"[Cache] STORED enhancement key {cache_key[:8]}... (cache size: {len(_enhancement_cache)})"
    )


class Enhancement:
    """Represents a single automation enhancement"""

    def __init__(
        self,
        level: str,
        title: str,
        description: str,
        enhanced_yaml: str,
        changes: list[str],
        source: str = "llm",
        pattern_id: int | None = None,
        synergy_id: str | None = None,
    ):
        self.level = level
        self.title = title
        self.description = description
        self.enhanced_yaml = enhanced_yaml
        self.changes = changes
        self.source = source
        self.pattern_id = pattern_id
        self.synergy_id = synergy_id

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "level": self.level,
            "title": self.title,
            "description": self.description,
            "enhanced_yaml": self.enhanced_yaml,
            "changes": self.changes,
            "source": self.source,
            "pattern_id": self.pattern_id,
            "synergy_id": self.synergy_id,
        }


class AutomationEnhancementService:
    """
    Generates automation enhancements using patterns and synergies.
    """

    def __init__(
        self,
        chat_client: Any,
        patterns_client: PatternsClient | None = None,
        synergies_client: SynergiesClient | None = None,
        settings: Settings | None = None,
    ):
        """
        Initialize enhancement service.

        Args:
            chat_client: AgentForge-backed chat client (AgentChatClient)
            patterns_client: Patterns API client (optional)
            synergies_client: Synergies API client (optional)
            settings: Settings instance (optional)
        """
        if settings is None:
            settings = Settings()
        self.chat_client = chat_client
        self.settings = settings
        self.patterns_client = patterns_client or PatternsClient(settings=settings)
        self.synergies_client = synergies_client or SynergiesClient(settings=settings)

    async def _enhance(
        self,
        *,
        original_prompt: str,
        automation_yaml: str = "",
        entities: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Run the ``automation-enhance`` workflow once and return its variants.

        TAP-7275: this one call replaces nine separate provider calls this
        service used to make -- three graded YAML variants, three graded prompt
        variants, and one each for the pattern, synergy and fallback paths. Each
        of those built its own prompt and asked for its own JSON shape; the
        workflow answers every graded variant in one run, so the shapes below
        are derived from one answer rather than from nine.

        Returns the raw enhancement dicts as the workflow declares them:
        ``{level, title, description, enhanced_prompt, automation_yaml,
        entities_referenced}``.
        """
        inventory = ""
        if entities:
            inventory = "ENTITIES: " + ", ".join(entities)
        answer = await self.chat_client.run_enhance(
            original_prompt=original_prompt,
            automation_yaml=automation_yaml,
            entity_inventory=inventory,
            context=context or {},
        )
        raw = answer.get("enhancements")
        return raw if isinstance(raw, list) else []

    @staticmethod
    def _to_enhancement(item: dict[str, Any], fallback_yaml: str, use_prompt: bool) -> Enhancement:
        """Map one workflow enhancement onto this service's Enhancement.

        ``use_prompt`` picks which half of the variant the caller wants: the
        prompt-enhancement paths store the enriched *request* in
        ``enhanced_yaml``, which is what they did before this change too (the
        field has carried a prompt on those paths since the method was written).
        """
        text = item.get("enhanced_prompt") if use_prompt else item.get("automation_yaml")
        return Enhancement(
            level=item.get("level", "small"),
            title=item.get("title", "Enhancement"),
            description=item.get("description", ""),
            enhanced_yaml=text or fallback_yaml,
            changes=[item.get("description", "")] if item.get("description") else [],
            source="agentforge",
        )

    async def generate_enhancements(
        self, automation_yaml: str, original_prompt: str, entities: list[str], areas: list[str]
    ) -> list[Enhancement]:
        """
        Generate 5 enhancements:
        1-3: LLM-based (small, medium, large)
        4: Pattern-driven (advanced)
        5: Synergy-driven (fun/crazy)

        Uses caching for identical prompt+YAML combinations.

        Args:
            automation_yaml: Original automation YAML
            original_prompt: User's original request
            entities: List of entity IDs in the automation
            areas: List of area IDs in the automation

        Returns:
            List of 5 Enhancement objects (may be fewer if some fail)
        """
        # Check cache first (key based on prompt and YAML)
        cache_key = _get_prompt_hash(
            f"{original_prompt}:{automation_yaml[:200]}", "yaml_enhancement"
        )
        cached_result = _get_cached_enhancement(cache_key)
        if cached_result:
            logger.info(
                f"[Enhancement] Using cached YAML enhancements for: {original_prompt[:50]}..."
            )
            return cached_result

        enhancements = []

        # 1-3: LLM-based enhancements (with timeout)
        logger.info("Generating LLM-based enhancements (small, medium, large)")
        try:
            llm_enhancements = await asyncio.wait_for(
                self._generate_llm_enhancements(automation_yaml, original_prompt, entities),
                timeout=45.0,  # 45 second timeout for 3 enhancements (LLM can be slow)
            )
            enhancements.extend(llm_enhancements)
        except TimeoutError as e:
            logger.warning(f"LLM enhancements timed out: {e}. Using fallbacks.")
            enhancements.extend(
                [
                    self._create_fallback_enhancement(automation_yaml, 1),
                    self._create_fallback_enhancement(automation_yaml, 2),
                    self._create_fallback_enhancement(automation_yaml, 3),
                ]
            )
        except Exception as e:
            logger.error(f"Error generating LLM enhancements: {e}", exc_info=True)
            enhancements.extend(
                [
                    self._create_fallback_enhancement(automation_yaml, 1),
                    self._create_fallback_enhancement(automation_yaml, 2),
                    self._create_fallback_enhancement(automation_yaml, 3),
                ]
            )

        # 4: Pattern-driven (Advanced) - with timeout
        logger.info("Generating pattern-driven enhancement (advanced)")
        try:
            pattern_enhancement = await asyncio.wait_for(
                self._generate_pattern_enhancement(automation_yaml, entities, areas),
                timeout=30.0,  # Increased timeout for pattern + LLM enhancement
            )
            enhancements.append(pattern_enhancement)
        except TimeoutError as e:
            logger.warning(f"Pattern enhancement timed out: {e}. Using fallback.")
            enhancements.append(await self._generate_fallback_advanced(automation_yaml))
        except Exception as e:
            logger.error(f"Error generating pattern enhancement: {e}", exc_info=True)
            enhancements.append(await self._generate_fallback_advanced(automation_yaml))

        # 5: Synergy-driven (Fun/Crazy) - with timeout
        logger.info("Generating synergy-driven enhancement (fun/crazy)")
        try:
            synergy_enhancement = await asyncio.wait_for(
                self._generate_synergy_enhancement(automation_yaml, entities, areas),
                timeout=30.0,  # Increased timeout for synergy + LLM enhancement
            )
            enhancements.append(synergy_enhancement)
        except TimeoutError as e:
            logger.warning(f"Synergy enhancement timed out: {e}. Using fallback.")
            enhancements.append(self._create_fallback_enhancement(automation_yaml, 5))
        except Exception as e:
            logger.error(f"Error generating synergy enhancement: {e}", exc_info=True)
            enhancements.append(self._create_fallback_enhancement(automation_yaml, 5))

        # Ensure we have at least 3 enhancements
        while len(enhancements) < 3:
            enhancements.append(
                self._create_fallback_enhancement(automation_yaml, len(enhancements) + 1)
            )

        result = enhancements[:5]  # Return up to 5

        # Cache the result
        _set_cached_enhancement(cache_key, result)
        logger.info(f"[Enhancement] Generated and cached {len(result)} YAML enhancements")

        return result

    async def generate_prompt_enhancements(
        self,
        original_prompt: str,
        creativity_level: str = "balanced",
        entities: list[str] | None = None,
        areas: list[str] | None = None,
    ) -> list[Enhancement]:
        """
        Generate prompt enhancement suggestions (no YAML required).

        Enhances the user's prompt to make it more comprehensive, specific, and
        context-aware. Returns enhanced prompt suggestions that can be used to
        generate better automations.

        Uses LRU caching to avoid regenerating identical prompt enhancements.

        Args:
            original_prompt: User's original request
            creativity_level: Creativity level ("conservative", "balanced", "creative")
            entities: Optional list of entity IDs for pattern/synergy lookup
            areas: Optional list of area IDs for pattern/synergy lookup

        Returns:
            List of 5 Enhancement objects with enhanced prompts (stored in enhanced_yaml field)
        """
        # Check cache first (key based on prompt and creativity level)
        cache_key = _get_prompt_hash(original_prompt, f"prompt_{creativity_level}")
        cached_result = _get_cached_enhancement(cache_key)
        if cached_result:
            logger.info(
                f"[Enhancement] Using cached prompt enhancements for: {original_prompt[:50]}..."
            )
            return cached_result

        try:
            # For creative/balanced levels, try to use patterns and synergies
            use_patterns_synergies = creativity_level in ("balanced", "creative")
            pattern_enhancement = None
            synergy_enhancement = None

            if use_patterns_synergies and entities and areas:
                try:
                    # Try to get pattern-based enhancement for advanced level
                    if entities:
                        patterns = await self.patterns_client.get_patterns(
                            device_ids=entities,
                            min_confidence=0.6 if creativity_level == "creative" else 0.7,
                            limit=5,
                        )
                        if patterns:
                            relevant_pattern = self._find_best_pattern(patterns, "")
                            if relevant_pattern:
                                pattern_enhancement = (
                                    await self._generate_pattern_prompt_enhancement(
                                        original_prompt, relevant_pattern
                                    )
                                )
                except Exception as e:
                    logger.warning(f"Failed to generate pattern enhancement for prompt: {e}")

                try:
                    # Try to get synergy-based enhancement for fun/creative level
                    if areas and entities:
                        area = areas[0] if areas else None
                        synergies = await self.synergies_client.get_synergies(
                            area=area,
                            device_ids=entities,
                            min_confidence=0.5 if creativity_level == "creative" else 0.6,
                            limit=5,
                        )
                        if synergies:
                            relevant_synergy = self._find_best_synergy(synergies, entities, areas)
                            if relevant_synergy:
                                synergy_enhancement = (
                                    await self._generate_synergy_prompt_enhancement(
                                        original_prompt, relevant_synergy
                                    )
                                )
                except Exception as e:
                    logger.warning(f"Failed to generate synergy enhancement for prompt: {e}")

            # The graded levels used to be three hard-coded preset lists that only
            # ever fed a prompt string. The gene owns the grading now, so
            # creativity_level is passed through as context rather than silently
            # dropped -- it still selects how adventurous the variants are, and it
            # still selects the pattern/synergy confidence floors above.
            variants = await self._enhance(
                original_prompt=original_prompt,
                context={"creativity_level": creativity_level},
            )

            data = {"enhancements": variants}

            enhancements = []
            for enh_data in data.get("enhancements", []):
                enhancements.append(
                    Enhancement(
                        level=enh_data.get("level", "small"),
                        title=enh_data.get("title", "Enhancement"),
                        description=enh_data.get("description", ""),
                        enhanced_yaml=enh_data.get(
                            "enhanced_prompt", original_prompt
                        ),  # Store enhanced prompt in yaml field for compatibility
                        changes=enh_data.get("changes", []),
                        source="llm",
                    )
                )

            # Replace advanced enhancement with pattern-based if available
            if pattern_enhancement:
                # Find and replace the advanced enhancement (usually index 3)
                if len(enhancements) > 3:
                    enhancements[3] = pattern_enhancement
                else:
                    enhancements.append(pattern_enhancement)

            # Replace creative/fun enhancement with synergy-based if available
            if synergy_enhancement:
                # Find and replace the last enhancement (creative/fun, usually index 4)
                if len(enhancements) > 4:
                    enhancements[4] = synergy_enhancement
                else:
                    enhancements.append(synergy_enhancement)

            # Ensure we have at least 3 enhancements
            while len(enhancements) < 3:
                enhancements.append(
                    self._create_fallback_prompt_enhancement(original_prompt, len(enhancements) + 1)
                )

            result = enhancements[:5]

            # Cache the result for future requests
            _set_cached_enhancement(cache_key, result)
            logger.info(f"[Enhancement] Generated and cached {len(result)} prompt enhancements")

            return result

        except Exception as e:
            logger.error(f"Error generating prompt enhancements: {e}", exc_info=True)
            # Return fallback enhancements (don't cache fallbacks)
            return [
                self._create_fallback_prompt_enhancement(original_prompt, 1),
                self._create_fallback_prompt_enhancement(original_prompt, 2),
                self._create_fallback_prompt_enhancement(original_prompt, 3),
                self._create_fallback_prompt_enhancement(original_prompt, 4),
                self._create_fallback_prompt_enhancement(original_prompt, 5),
            ]

    def _create_fallback_prompt_enhancement(
        self, original_prompt: str, level_num: int
    ) -> Enhancement:
        """Create a simple fallback prompt enhancement"""
        level_map = {
            1: ("small", "Small Enhancement", "Add minor details"),
            2: ("medium", "Medium Enhancement", "Add functional details"),
            3: ("large", "Large Enhancement", "Add feature details"),
            4: ("advanced", "Advanced Enhancement", "Add smart features"),
            5: ("fun", "Creative Enhancement", "Add creative elements"),
        }

        level, title, description = level_map.get(
            level_num, ("small", "Enhancement", "Prompt enhancement")
        )

        return Enhancement(
            level=level,
            title=title,
            description=description,
            enhanced_yaml=original_prompt,  # Store prompt in yaml field for compatibility
            changes=["Enhancement applied"],
            source="fallback",
        )

    async def _generate_llm_enhancements(
        self, automation_yaml: str, original_prompt: str, entities: list[str]
    ) -> list[Enhancement]:
        """Generate 3 LLM-based enhancements (small, medium, large)"""
        try:
            variants = await self._enhance(
                original_prompt=original_prompt,
                automation_yaml=automation_yaml,
                entities=entities,
            )

            data = {"enhancements": variants}

            enhancements = []
            for enh_data in data.get("enhancements", []):
                enhancements.append(
                    Enhancement(
                        level=enh_data.get("level", "small"),
                        title=enh_data.get("title", "Enhancement"),
                        description=enh_data.get("description", ""),
                        enhanced_yaml=enh_data.get("enhanced_yaml", automation_yaml),
                        changes=enh_data.get("changes", []),
                        source="llm",
                    )
                )

            # Ensure we have exactly 3 enhancements
            while len(enhancements) < 3:
                enhancements.append(
                    self._create_fallback_enhancement(automation_yaml, len(enhancements) + 1)
                )

            return enhancements[:3]

        except Exception as e:
            logger.error(f"Error generating LLM enhancements: {e}", exc_info=True)
            # Return fallback enhancements
            return [
                self._create_fallback_enhancement(automation_yaml, 1),
                self._create_fallback_enhancement(automation_yaml, 2),
                self._create_fallback_enhancement(automation_yaml, 3),
            ]

    async def _generate_pattern_enhancement(
        self, automation_yaml: str, entities: list[str], _areas: list[str]
    ) -> Enhancement:
        """Generate pattern-driven enhancement (advanced)"""
        try:
            # Query patterns for relevant devices/entities
            patterns = await self.patterns_client.get_patterns(
                device_ids=entities, min_confidence=0.7, limit=10
            )

            if not patterns:
                logger.info("No patterns found, generating fallback advanced enhancement")
                return await self._generate_fallback_advanced(automation_yaml)

            # Find most relevant pattern
            relevant_pattern = self._find_best_pattern(patterns, automation_yaml)

            if relevant_pattern:
                # Generate enhancement YAML using pattern
                enhanced_yaml = await self._apply_pattern_to_automation(
                    automation_yaml, relevant_pattern
                )

                pattern_type = relevant_pattern.get("pattern_type", "pattern")
                confidence = relevant_pattern.get("confidence", 0.0)
                occurrences = relevant_pattern.get("occurrences", 0)

                return Enhancement(
                    level="advanced",
                    title=f"Optimize with {pattern_type.replace('_', ' ').title()} Pattern",
                    description=f"Based on detected pattern: {relevant_pattern.get('pattern_metadata', {}).get('description', 'Pattern-based optimization')}",
                    enhanced_yaml=enhanced_yaml,
                    changes=[
                        f"Applied {pattern_type.replace('_', ' ')} pattern",
                        f"Confidence: {confidence:.0%}",
                        f"Occurrences: {occurrences} times",
                    ],
                    source="pattern",
                    pattern_id=relevant_pattern.get("id"),
                )
            return await self._generate_fallback_advanced(automation_yaml)

        except Exception as e:
            logger.error(f"Error generating pattern enhancement: {e}", exc_info=True)
            return await self._generate_fallback_advanced(automation_yaml)

    async def _generate_synergy_enhancement(
        self, automation_yaml: str, entities: list[str], areas: list[str]
    ) -> Enhancement:
        """Generate synergy-driven enhancement (fun/crazy)"""
        try:
            # Query synergies for relevant areas/devices
            area = areas[0] if areas else None
            synergies = await self.synergies_client.get_synergies(
                area=area, device_ids=entities, min_confidence=0.6, limit=10
            )

            if not synergies:
                logger.info("No synergies found, generating fallback fun enhancement")
                return await self._generate_fallback_fun(automation_yaml)

            # Find most relevant synergy
            relevant_synergy = self._find_best_synergy(synergies, entities, areas)

            if relevant_synergy:
                # Generate enhancement YAML using synergy
                enhanced_yaml = await self._apply_synergy_to_automation(
                    automation_yaml, relevant_synergy
                )

                synergy_type = relevant_synergy.get("synergy_type", "device_pair")
                impact_score = relevant_synergy.get("impact_score", 0.0)
                device_ids = relevant_synergy.get("device_ids", [])
                explanation = relevant_synergy.get("explanation", {})
                description = (
                    explanation.get("summary", "")
                    if isinstance(explanation, dict)
                    else str(explanation)
                )

                return Enhancement(
                    level="fun",
                    title=f"Combine with {synergy_type.replace('_', ' ').title()}",
                    description=description
                    or f"Creative multi-device coordination using {synergy_type}",
                    enhanced_yaml=enhanced_yaml,
                    changes=[
                        f"Added {synergy_type.replace('_', ' ')} coordination",
                        f"Impact score: {impact_score:.1f}",
                        f"Devices: {', '.join(device_ids[:3])}",
                    ],
                    source="synergy",
                    synergy_id=relevant_synergy.get("synergy_id"),
                )
            return await self._generate_fallback_fun(automation_yaml)

        except Exception as e:
            logger.error(f"Error generating synergy enhancement: {e}", exc_info=True)
            return await self._generate_fallback_fun(automation_yaml)

    def _find_best_pattern(
        self, patterns: list[dict[str, Any]], _automation_yaml: str
    ) -> dict[str, Any] | None:
        """Find the most relevant pattern for the automation"""
        if not patterns:
            return None

        # Simple scoring: prefer higher confidence and more occurrences
        scored_patterns = [
            (p, p.get("confidence", 0.0) * p.get("occurrences", 0)) for p in patterns
        ]
        scored_patterns.sort(key=lambda x: x[1], reverse=True)

        return scored_patterns[0][0] if scored_patterns else None

    def _find_best_synergy(
        self, synergies: list[dict[str, Any]], entities: list[str], _areas: list[str]
    ) -> dict[str, Any] | None:
        """Find the most relevant synergy for the automation"""
        if not synergies:
            return None

        # Score synergies by impact and relevance
        scored_synergies = []
        for synergy in synergies:
            synergy_device_ids = synergy.get("device_ids", [])
            # Check overlap with automation entities
            overlap = len(set(entities) & set(synergy_device_ids))
            impact_score = synergy.get("impact_score", 0.0)
            confidence = synergy.get("confidence", 0.0)

            # Score: impact * confidence * (1 + overlap bonus)
            score = impact_score * confidence * (1 + overlap * 0.2)
            scored_synergies.append((synergy, score))

        scored_synergies.sort(key=lambda x: x[1], reverse=True)
        return scored_synergies[0][0] if scored_synergies else None

    async def _apply_pattern_to_automation(
        self, automation_yaml: str, pattern: dict[str, Any]
    ) -> str:
        """Apply pattern to automation YAML using LLM"""
        try:
            variants = await self._enhance(
                original_prompt="Apply this detected pattern to the automation.",
                automation_yaml=automation_yaml,
                context={"pattern": pattern},
            )

            enhanced_yaml = (
                variants[0].get("automation_yaml") if variants else None
            ) or automation_yaml
            # Clean up markdown code blocks if present
            enhanced_yaml = re.sub(r"```yaml\n?", "", enhanced_yaml)
            return re.sub(r"```\n?", "", enhanced_yaml).strip()

        except Exception as e:
            logger.error(f"Error applying pattern: {e}", exc_info=True)
            return automation_yaml

    async def _apply_synergy_to_automation(
        self, automation_yaml: str, synergy: dict[str, Any]
    ) -> str:
        """Apply synergy to automation YAML using LLM"""
        try:
            variants = await self._enhance(
                original_prompt="Apply this detected synergy to the automation.",
                automation_yaml=automation_yaml,
                context={"synergy": synergy},
            )

            enhanced_yaml = (
                variants[0].get("automation_yaml") if variants else None
            ) or automation_yaml
            # Clean up markdown code blocks if present
            enhanced_yaml = re.sub(r"```yaml\n?", "", enhanced_yaml)
            return re.sub(r"```\n?", "", enhanced_yaml).strip()

        except Exception as e:
            logger.error(f"Error applying synergy: {e}", exc_info=True)
            return automation_yaml

    async def _generate_fallback_advanced(self, automation_yaml: str) -> Enhancement:
        """Generate fallback advanced enhancement using LLM"""
        try:
            variants = await self._enhance(
                original_prompt="Add advanced behaviour to this automation: time-based conditions, multi-device coordination, energy optimisation, adaptive behaviour.",
                automation_yaml=automation_yaml,
            )

            data = variants[0] if variants else {}

            return Enhancement(
                level="advanced",
                title=data.get("title", "Advanced Enhancement"),
                description=data.get("description", "Smart automation features"),
                enhanced_yaml=data.get("enhanced_yaml", automation_yaml),
                changes=data.get("changes", ["Advanced features added"]),
                source="llm",
            )
        except Exception as e:
            logger.error(f"Error generating fallback advanced: {e}", exc_info=True)
            return self._create_fallback_enhancement(automation_yaml, 4)

    async def _generate_fallback_fun(self, automation_yaml: str) -> Enhancement:
        """Generate fallback fun enhancement using LLM"""
        try:
            variants = await self._enhance(
                original_prompt="Add a fun, creative twist to this automation.",
                automation_yaml=automation_yaml,
            )

            data = variants[0] if variants else {}

            return Enhancement(
                level="fun",
                title=data.get("title", "Fun Enhancement"),
                description=data.get("description", "Creative automation features"),
                enhanced_yaml=data.get("enhanced_yaml", automation_yaml),
                changes=data.get("changes", ["Fun features added"]),
                source="llm",
            )
        except Exception as e:
            logger.error(f"Error generating fallback fun: {e}", exc_info=True)
            return self._create_fallback_enhancement(automation_yaml, 5)

    def _create_fallback_enhancement(self, automation_yaml: str, level_num: int) -> Enhancement:
        """Create a simple fallback enhancement"""
        level_map = {
            1: ("small", "Small Enhancement", "Minor tweaks and improvements"),
            2: ("medium", "Medium Enhancement", "Functional improvements"),
            3: ("large", "Large Enhancement", "Feature additions"),
            4: ("advanced", "Advanced Enhancement", "Smart pattern-based features"),
            5: ("fun", "Fun Enhancement", "Creative and interactive features"),
        }

        level, title, description = level_map.get(
            level_num, ("small", "Enhancement", "Automation enhancement")
        )

        return Enhancement(
            level=level,
            title=title,
            description=description,
            enhanced_yaml=automation_yaml,
            changes=["Enhancement applied"],
            source="fallback",
        )

    async def _generate_pattern_prompt_enhancement(
        self, original_prompt: str, pattern: dict[str, Any]
    ) -> Enhancement:
        """Generate pattern-based prompt enhancement"""
        try:
            pattern_type = pattern.get("pattern_type", "")
            variants = await self._enhance(
                original_prompt=original_prompt,
                context={"pattern": pattern},
            )

            data = variants[0] if variants else {}

            return Enhancement(
                level=data.get("level", "advanced"),
                title=data.get("title", f"Pattern-Based: {pattern_type.replace('_', ' ').title()}"),
                description=data.get("description", f"Leverages {pattern_type} pattern"),
                enhanced_yaml=data.get("enhanced_prompt", original_prompt),
                changes=data.get("changes", ["Pattern-based optimization"]),
                source="pattern",
                pattern_id=pattern.get("id"),
            )
        except Exception as e:
            logger.error(f"Error generating pattern prompt enhancement: {e}", exc_info=True)
            return self._create_fallback_prompt_enhancement(original_prompt, 4)

    async def _generate_synergy_prompt_enhancement(
        self, original_prompt: str, synergy: dict[str, Any]
    ) -> Enhancement:
        """Generate synergy-based prompt enhancement"""
        try:
            synergy_type = synergy.get("synergy_type", "")

            variants = await self._enhance(
                original_prompt=original_prompt,
                context={"synergy": synergy},
            )

            data = variants[0] if variants else {}

            return Enhancement(
                level=data.get("level", "fun"),
                title=data.get("title", f"Synergy-Based: {synergy_type.replace('_', ' ').title()}"),
                description=data.get("description", "Creative multi-device coordination"),
                enhanced_yaml=data.get("enhanced_prompt", original_prompt),
                changes=data.get("changes", ["Synergy-based coordination"]),
                source="synergy",
                synergy_id=synergy.get("synergy_id"),
            )
        except Exception as e:
            logger.error(f"Error generating synergy prompt enhancement: {e}", exc_info=True)
            return self._create_fallback_prompt_enhancement(original_prompt, 5)

    @staticmethod
    def extract_entities_from_yaml(yaml_str: str) -> list[str]:
        """Extract entity IDs from YAML string"""
        entities = []
        # Match entity_id patterns
        entity_pattern = r'entity_id:\s*["\']?([^"\'\n]+)["\']?'
        matches = re.findall(entity_pattern, yaml_str, re.IGNORECASE)
        entities.extend(matches)

        # Match target.entity_id patterns
        target_pattern = r'target:\s*\n\s*entity_id:\s*["\']?([^"\'\n]+)["\']?'
        matches = re.findall(target_pattern, yaml_str, re.IGNORECASE | re.MULTILINE)
        entities.extend(matches)

        return list(set(entities))  # Remove duplicates

    @staticmethod
    def extract_areas_from_yaml(yaml_str: str) -> list[str]:
        """Extract area IDs from YAML string"""
        areas = []
        # Match area_id patterns
        area_pattern = r'area_id:\s*["\']?([^"\'\n]+)["\']?'
        matches = re.findall(area_pattern, yaml_str, re.IGNORECASE)
        areas.extend(matches)

        # Match target.area_id patterns
        target_pattern = r'target:\s*\n\s*area_id:\s*["\']?([^"\'\n]+)["\']?'
        matches = re.findall(target_pattern, yaml_str, re.IGNORECASE | re.MULTILINE)
        areas.extend(matches)

        return list(set(areas))  # Remove duplicates

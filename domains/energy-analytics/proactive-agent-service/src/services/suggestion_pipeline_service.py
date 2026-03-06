"""
Suggestion Generation Pipeline Service for Proactive Agent Service

Orchestrates the full flow: Context Analysis → AI Prompt Generation → Agent Communication → Storage

Updated to use AI-powered prompt generation instead of hardcoded templates.

Story 33.4: Memory-aware proactive suggestions - uses behavioral, routine, and boundary
memories to improve suggestion timing and relevance.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any

try:
    from homeiq_patterns import RAGContextRegistry

    _RAG_AVAILABLE = True
except ImportError:
    _RAG_AVAILABLE = False

try:
    from homeiq_memory import MemorySearch, MemorySearchResult, MemoryType

    _MEMORY_AVAILABLE = True
except ImportError:
    MemorySearch = None  # type: ignore[assignment,misc]
    MemorySearchResult = None  # type: ignore[assignment,misc]
    MemoryType = None  # type: ignore[assignment,misc]
    _MEMORY_AVAILABLE = False

from ..clients.ha_agent_client import HAAgentClient
from ..services.ai_prompt_generation_service import AIPromptGenerationService
from ..services.context_analysis_service import ContextAnalysisService
from ..services.prompt_generation_service import PromptGenerationService
from ..services.suggestion_storage_service import SuggestionStorageService

if _RAG_AVAILABLE:
    from ..services.rag_services import (
        ComfortOptimizationRAGService,
        EnergySavingsRAGService,
        SecurityBestPracticesRAGService,
    )

logger = logging.getLogger(__name__)


class PipelineInitializationError(Exception):
    """Raised when pipeline services fail to initialize"""
    pass


class SuggestionPipelineService:
    """Service for orchestrating suggestion generation pipeline"""

    def __init__(
        self,
        context_service: ContextAnalysisService | None = None,
        prompt_service: PromptGenerationService | None = None,
        ai_prompt_service: AIPromptGenerationService | None = None,
        agent_client: HAAgentClient | None = None,
        storage_service: SuggestionStorageService | None = None,
        memory_search: MemorySearch | None = None,
        quality_threshold: float = 0.6,
        max_suggestions_per_batch: int = 10,
        use_ai_generation: bool = True,
    ):
        """
        Initialize Suggestion Pipeline Service.

        Args:
            context_service: Context Analysis Service (creates default if None)
            prompt_service: Basic Prompt Generation Service (fallback)
            ai_prompt_service: AI-Powered Prompt Generation Service (primary)
            agent_client: HA Agent Client (creates default if None)
            storage_service: Suggestion Storage Service (creates default if None)
            memory_search: Memory Search for memory-aware suggestions (Story 33.4)
            quality_threshold: Minimum quality score for suggestions (default: 0.6)
            max_suggestions_per_batch: Maximum suggestions per batch (default: 10)
            use_ai_generation: Use AI-powered generation (default: True)

        Raises:
            PipelineInitializationError: If any required service fails to initialize
        """
        self.use_ai_generation = use_ai_generation and os.getenv("OPENAI_API_KEY")
        self.memory_search = memory_search

        try:
            self.context_service = context_service or ContextAnalysisService()
        except Exception as e:
            logger.error(f"Failed to initialize ContextAnalysisService: {e}", exc_info=True)
            raise PipelineInitializationError(f"ContextAnalysisService initialization failed: {e}") from e

        # Initialize RAG Context Registry for domain-specific context
        rag_registry = None
        if _RAG_AVAILABLE:
            try:
                rag_registry = RAGContextRegistry()
                rag_registry.register(EnergySavingsRAGService())
                rag_registry.register(SecurityBestPracticesRAGService())
                rag_registry.register(ComfortOptimizationRAGService())
                logger.info(f"RAG registry initialized with {len(rag_registry.services)} services")
            except Exception as e:
                logger.warning(f"Failed to initialize RAG registry: {e}")
                rag_registry = None
        else:
            logger.info("homeiq-patterns not available - RAG context disabled")

        # Initialize AI-powered prompt service (primary)
        if self.use_ai_generation:
            try:
                self.ai_prompt_service = ai_prompt_service or AIPromptGenerationService(
                    rag_registry=rag_registry,
                )
                logger.info("✅ AI-powered prompt generation ENABLED")
            except Exception as e:
                logger.warning(f"Failed to initialize AIPromptGenerationService: {e}. Falling back to templates.")
                self.ai_prompt_service = None
                self.use_ai_generation = False
        else:
            self.ai_prompt_service = None
            logger.info("⚠️ AI prompt generation DISABLED (no OPENAI_API_KEY)")

        # Initialize basic prompt service (fallback)
        try:
            self.prompt_service = prompt_service or PromptGenerationService()
        except Exception as e:
            logger.error(f"Failed to initialize PromptGenerationService: {e}", exc_info=True)
            raise PipelineInitializationError(f"PromptGenerationService initialization failed: {e}") from e

        try:
            self.agent_client = agent_client or HAAgentClient()
        except Exception as e:
            logger.error(f"Failed to initialize HAAgentClient: {e}", exc_info=True)
            raise PipelineInitializationError(f"HAAgentClient initialization failed: {e}") from e

        try:
            self.storage_service = storage_service or SuggestionStorageService()
        except Exception as e:
            logger.error(f"Failed to initialize SuggestionStorageService: {e}", exc_info=True)
            raise PipelineInitializationError(f"SuggestionStorageService initialization failed: {e}") from e

        # Validate all services are properly initialized (not None)
        if self.context_service is None:
            raise PipelineInitializationError("ContextAnalysisService is None after initialization")
        if self.prompt_service is None:
            raise PipelineInitializationError("PromptGenerationService is None after initialization")
        if self.agent_client is None:
            raise PipelineInitializationError("HAAgentClient is None after initialization")
        if self.storage_service is None:
            raise PipelineInitializationError("SuggestionStorageService is None after initialization")

        self.quality_threshold = quality_threshold
        self.max_suggestions_per_batch = max_suggestions_per_batch

        mode = "AI-powered" if self.use_ai_generation else "template-based"
        memory_status = "enabled" if self.memory_search else "disabled"
        logger.info(
            f"Suggestion Pipeline Service initialized ({mode} generation, "
            f"memory={memory_status}, quality_threshold={quality_threshold}, "
            f"max_batch={max_suggestions_per_batch})"
        )

    async def _query_memory_context(self) -> dict[str, Any]:
        """
        Query Memory Brain for behavioral, routine, and boundary memories.

        Story 33.4: Uses memories to improve proactive suggestion timing and relevance.

        Returns:
            Dictionary containing memory context:
            {
                "engagement_context": {...},  # From behavioral memories
                "timing_context": {...},      # From routine memories
                "blocked_domains": [...],     # From boundary memories
                "memory_available": bool,
            }
        """
        if not self.memory_search or not _MEMORY_AVAILABLE:
            return {
                "memory_available": False,
                "engagement_context": None,
                "timing_context": None,
                "blocked_domains": [],
            }

        try:
            # Query behavioral memories for engagement patterns
            behavioral_results = await self.memory_search.search(
                query="user engages suggestions",
                memory_types=[MemoryType.BEHAVIORAL],
                limit=10,
            )

            # Query routine memories for optimal timing
            routine_results = await self.memory_search.search(
                query="daily routine",
                memory_types=[MemoryType.ROUTINE],
                limit=5,
            )

            # Query boundary memories to filter domains
            boundary_results = await self.memory_search.search(
                query="",
                memory_types=[MemoryType.BOUNDARY],
                limit=20,
                min_confidence=0.5,  # Higher threshold for boundaries
            )

            # Build context from memories
            engagement_context = self._build_engagement_context(behavioral_results)
            timing_context = self._build_timing_context(routine_results)
            blocked_domains = self._extract_blocked_domains(boundary_results)

            logger.info(
                f"Memory context loaded: {len(behavioral_results)} behavioral, "
                f"{len(routine_results)} routine, {len(blocked_domains)} blocked domains"
            )

            return {
                "memory_available": True,
                "engagement_context": engagement_context,
                "timing_context": timing_context,
                "blocked_domains": blocked_domains,
            }

        except Exception as e:
            logger.warning(f"Failed to query memory context: {e}")
            return {
                "memory_available": False,
                "engagement_context": None,
                "timing_context": None,
                "blocked_domains": [],
                "error": str(e),
            }

    def _build_engagement_context(
        self, behavioral_results: list
    ) -> dict[str, Any] | None:
        """
        Build engagement context from behavioral memories.

        Extracts patterns about when and how users engage with suggestions.
        """
        if not behavioral_results:
            return None

        context = {
            "preferred_suggestion_types": [],
            "engagement_times": [],
            "dismissed_patterns": [],
            "interaction_style": None,
        }

        for result in behavioral_results:
            memory = result.memory
            content = memory.content.lower()

            # Extract preferred suggestion types
            if "likes" in content or "engages" in content or "accepts" in content:
                if "energy" in content:
                    context["preferred_suggestion_types"].append("energy")
                if "comfort" in content:
                    context["preferred_suggestion_types"].append("comfort")
                if "security" in content:
                    context["preferred_suggestion_types"].append("security")
                if "weather" in content:
                    context["preferred_suggestion_types"].append("weather")

            # Extract dismissed patterns
            if "dismisses" in content or "ignores" in content or "rejects" in content:
                context["dismissed_patterns"].append(memory.content)

            # Extract timing preferences
            if memory.metadata_:
                time_pref = memory.metadata_.get("preferred_time")
                if time_pref:
                    context["engagement_times"].append(time_pref)

        # Deduplicate
        context["preferred_suggestion_types"] = list(
            set(context["preferred_suggestion_types"])
        )

        return context if any(context.values()) else None

    def _build_timing_context(self, routine_results: list) -> dict[str, Any] | None:
        """
        Build timing context from routine memories.

        Extracts patterns about daily routines to suggest at optimal times.
        """
        if not routine_results:
            return None

        context = {
            "morning_routine_start": None,
            "evening_routine_start": None,
            "away_periods": [],
            "active_periods": [],
            "quiet_hours": [],
        }

        for result in routine_results:
            memory = result.memory
            content = memory.content.lower()
            has_start_time = memory.metadata_ and "start_time" in memory.metadata_

            # Extract routine timing
            if "morning" in content and has_start_time:
                context["morning_routine_start"] = memory.metadata_["start_time"]
            elif ("evening" in content or "night" in content) and has_start_time:
                context["evening_routine_start"] = memory.metadata_["start_time"]

            # Extract away periods
            is_away_content = "away" in content or "leave" in content or "work" in content
            if is_away_content and memory.metadata_:
                away_info = {
                    "start": memory.metadata_.get("start_time"),
                    "end": memory.metadata_.get("end_time"),
                    "days": memory.metadata_.get("days", []),
                }
                if away_info["start"]:
                    context["away_periods"].append(away_info)

            # Extract quiet hours
            is_quiet_content = "quiet" in content or "sleep" in content or "do not disturb" in content
            if is_quiet_content and memory.metadata_:
                quiet_info = {
                    "start": memory.metadata_.get("start_time"),
                    "end": memory.metadata_.get("end_time"),
                }
                if quiet_info["start"]:
                    context["quiet_hours"].append(quiet_info)

        return context if any(context.values()) else None

    def _extract_blocked_domains(self, boundary_results: list) -> list[str]:
        """
        Extract blocked domains from boundary memories.

        Identifies domains/topics the user has indicated they don't want suggestions about.
        """
        blocked = set()

        for result in boundary_results:
            memory = result.memory
            content = memory.content.lower()

            # Common boundary patterns
            if "don't suggest" in content or "no suggestions about" in content:
                # Extract the domain from the content
                if "energy" in content:
                    blocked.add("energy")
                if "sports" in content:
                    blocked.add("sports")
                if "weather" in content:
                    blocked.add("weather")
                if "security" in content:
                    blocked.add("security")
                if "temperature" in content or "thermostat" in content:
                    blocked.add("temperature")
                if "lighting" in content or "lights" in content:
                    blocked.add("lighting")

            # Check metadata for explicit blocks
            if memory.metadata_:
                if memory.metadata_.get("blocked_domain"):
                    blocked.add(memory.metadata_["blocked_domain"])
                if memory.metadata_.get("blocked_entity_types"):
                    blocked.update(memory.metadata_["blocked_entity_types"])

        return list(blocked)

    def _filter_by_timing(
        self, candidates: list[dict[str, Any]], timing_context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Filter suggestion candidates based on timing context.

        Removes suggestions that would be delivered at inappropriate times.
        """
        if not timing_context:
            return candidates

        current_hour = datetime.now(UTC).hour
        filtered = []

        for candidate in candidates:
            # Check quiet hours
            quiet_hours = timing_context.get("quiet_hours", [])
            in_quiet_period = False
            for quiet in quiet_hours:
                start = quiet.get("start")
                end = quiet.get("end")
                if start and end:
                    try:
                        start_hour = int(start.split(":")[0])
                        end_hour = int(end.split(":")[0])
                        # Handle overnight quiet hours (e.g., 22:00 - 07:00)
                        if start_hour > end_hour:
                            in_quiet_period = current_hour >= start_hour or current_hour < end_hour
                        else:
                            in_quiet_period = start_hour <= current_hour < end_hour
                    except (ValueError, IndexError):
                        pass

            if in_quiet_period:
                logger.debug(
                    f"Filtering suggestion during quiet hours: {candidate.get('prompt', '')[:50]}..."
                )
                continue

            filtered.append(candidate)

        return filtered

    def _filter_by_blocked_domains(
        self, candidates: list[dict[str, Any]], blocked_domains: list[str]
    ) -> list[dict[str, Any]]:
        """
        Filter suggestion candidates that match blocked domains.
        """
        if not blocked_domains:
            return candidates

        filtered = []
        blocked_set = {d.lower() for d in blocked_domains}

        for candidate in candidates:
            context_type = candidate.get("context_type", "").lower()
            prompt_text = candidate.get("prompt", "").lower()

            # Check if the context type or prompt content matches blocked domains
            is_blocked = False
            for blocked in blocked_set:
                if blocked in context_type or blocked in prompt_text:
                    is_blocked = True
                    logger.debug(
                        f"Filtering blocked domain '{blocked}': {candidate.get('prompt', '')[:50]}..."
                    )
                    break

            if not is_blocked:
                filtered.append(candidate)

        return filtered

    def _boost_preferred_suggestions(
        self,
        candidates: list[dict[str, Any]],
        engagement_context: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """
        Boost quality scores for suggestions matching user preferences.
        """
        if not engagement_context:
            return candidates

        preferred_types = engagement_context.get("preferred_suggestion_types", [])
        if not preferred_types:
            return candidates

        boosted = []
        for candidate in candidates:
            context_type = candidate.get("context_type", "").lower()
            quality_score = candidate.get("quality_score", 0.5)

            # Boost score if matches preferred type
            for pref in preferred_types:
                if pref.lower() in context_type:
                    quality_score = min(1.0, quality_score + 0.1)
                    candidate["quality_score"] = quality_score
                    candidate["boosted_by_preference"] = True
                    break

            boosted.append(candidate)

        # Re-sort by quality score
        boosted.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
        return boosted

    async def generate_suggestions(self) -> dict[str, Any]:
        """
        Generate proactive automation suggestions.

        Full pipeline:
        1. Query memory context (behavioral, routine, boundary)
        2. Analyze context (weather, sports, energy, patterns)
        3. Generate context-aware prompts
        4. Filter by memory context (blocked domains, timing)
        5. Store suggestions in database (status: pending)

        Suggestions are stored with status "pending" and can be manually sent to
        the HA AI Agent Service via the API endpoint POST /api/v1/suggestions/{id}/send.

        Returns:
            Dictionary with pipeline results:
            {
                "success": bool,
                "suggestions_created": int,
                "suggestions_failed": int,
                "memory_context_used": bool,
                "details": [...]
            }
        """
        logger.info("Starting suggestion generation pipeline")

        results = {
            "success": True,
            "suggestions_created": 0,
            "suggestions_failed": 0,
            "memory_context_used": False,
            "details": [],
        }

        try:
            # Step 0: Query memory context (Story 33.4)
            logger.debug("Step 0: Querying memory context")
            memory_context = await self._query_memory_context()
            results["memory_context_used"] = memory_context.get("memory_available", False)

            # Step 1: Analyze context
            logger.debug("Step 1: Analyzing context")
            context_analysis = await self.context_service.analyze_all_context()

            if not context_analysis:
                logger.warning("No context available for suggestion generation")
                results["success"] = False
                results["details"].append({"step": "context_analysis", "error": "No context available"})
                return results

            # Step 2: Generate prompts (AI-powered or fallback)
            logger.debug(f"Step 2: Generating prompts (AI={self.use_ai_generation})")
            generation_mode = "unknown"
            try:
                if self.use_ai_generation and self.ai_prompt_service:
                    # Use AI-powered generation
                    logger.info("🤖 Using AI-powered prompt generation")
                    prompts = await self.ai_prompt_service.generate_prompts(
                        context_analysis, max_prompts=self.max_suggestions_per_batch
                    )
                    generation_mode = "ai"
                else:
                    # Fallback to template-based generation
                    logger.info("📝 Using template-based prompt generation")
                    if not callable(getattr(self.prompt_service, 'generate_prompts', None)):
                        raise TypeError(
                            f"prompt_service.generate_prompts is not callable: "
                            f"type={type(self.prompt_service)}"
                        )
                    prompts = self.prompt_service.generate_prompts(
                        context_analysis, max_prompts=self.max_suggestions_per_batch
                    )
                    generation_mode = "template"

                results["generation_mode"] = generation_mode

            except TypeError as e:
                logger.error(f"TypeError in prompt generation: {e}", exc_info=True)
                results["success"] = False
                results["details"].append({
                    "step": "prompt_generation",
                    "error": f"TypeError: {str(e)}",
                    "prompt_service_type": str(type(self.prompt_service)),
                })
                return results
            except Exception as e:
                logger.error(f"Error generating prompts: {e}", exc_info=True)
                results["success"] = False
                results["details"].append({
                    "step": "prompt_generation",
                    "error": str(e),
                })
                return results

            if not prompts:
                logger.warning("No prompts generated from context analysis")
                results["success"] = False
                results["details"].append({"step": "prompt_generation", "error": "No prompts generated"})
                return results

            logger.info(f"Generated {len(prompts)} prompts")

            # Step 2.5: Apply memory-aware filtering (Story 33.4)
            if memory_context.get("memory_available"):
                original_count = len(prompts)

                # Filter by blocked domains
                blocked_domains = memory_context.get("blocked_domains", [])
                if blocked_domains:
                    prompts = self._filter_by_blocked_domains(prompts, blocked_domains)
                    logger.debug(
                        f"Filtered {original_count - len(prompts)} prompts by blocked domains"
                    )

                # Filter by timing context
                timing_context = memory_context.get("timing_context")
                if timing_context:
                    pre_timing_count = len(prompts)
                    prompts = self._filter_by_timing(prompts, timing_context)
                    logger.debug(
                        f"Filtered {pre_timing_count - len(prompts)} prompts by timing"
                    )

                # Boost preferred suggestions
                engagement_context = memory_context.get("engagement_context")
                if engagement_context:
                    prompts = self._boost_preferred_suggestions(prompts, engagement_context)

                results["details"].append({
                    "step": "memory_filtering",
                    "original_count": original_count,
                    "filtered_count": len(prompts),
                    "blocked_domains": blocked_domains,
                    "has_timing_context": timing_context is not None,
                    "has_engagement_context": engagement_context is not None,
                })

            # Step 3: Process each prompt (send to agent and store)
            for prompt_data in prompts:
                try:
                    # Filter by quality threshold
                    if prompt_data.get("quality_score", 0.0) < self.quality_threshold:
                        logger.debug(
                            f"Skipping prompt with quality score {prompt_data.get('quality_score')} "
                            f"(threshold: {self.quality_threshold})"
                        )
                        results["suggestions_failed"] += 1
                        results["details"].append(
                            {
                                "step": "quality_filter",
                                "prompt": prompt_data.get("prompt", "")[:50],
                                "quality_score": prompt_data.get("quality_score"),
                                "reason": "Below quality threshold",
                            }
                        )
                        continue

                    # Store suggestion (pending status) - duplicate check enabled by default
                    suggestion = await self.storage_service.create_suggestion(
                        prompt=prompt_data["prompt"],
                        context_type=prompt_data["context_type"],
                        quality_score=prompt_data.get("quality_score", 0.0),
                        context_metadata=context_analysis,
                        prompt_metadata=prompt_data.get("metadata", {}),
                        check_duplicates=True,  # Prevent duplicate suggestions
                        duplicate_window_hours=24,  # Check last 24 hours
                    )

                    # Skip if duplicate (None returned)
                    if not suggestion:
                        logger.debug(f"Skipping duplicate prompt: {prompt_data.get('prompt', '')[:50]}...")
                        results["suggestions_failed"] += 1
                        results["details"].append(
                            {
                                "step": "duplicate_check",
                                "prompt": prompt_data.get("prompt", "")[:50],
                                "reason": "Duplicate suggestion found within time window",
                            }
                        )
                        continue

                    results["suggestions_created"] += 1
                    logger.debug(f"Created suggestion {suggestion.id} (status: pending - ready for user to send)")

                except Exception as prompt_error:
                    # Error processing individual prompt - continue with next
                    logger.error(f"Error processing prompt: {prompt_error}", exc_info=True)
                    results["suggestions_failed"] += 1
                    results["details"].append(
                        {
                            "step": "prompt_processing",
                            "prompt": prompt_data.get("prompt", "")[:50],
                            "error": str(prompt_error),
                        }
                    )
                    continue

            logger.info(
                f"Pipeline complete: {results['suggestions_created']} created, "
                f"{results['suggestions_failed']} failed"
            )

            return results

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            results["success"] = False
            results["details"].append({"step": "pipeline", "error": str(e)})
            return results

    async def close(self):
        """Close all client connections"""
        try:
            if hasattr(self.agent_client, "close"):
                await self.agent_client.close()
            if hasattr(self.context_service, "close"):
                await self.context_service.close()
            if self.ai_prompt_service and hasattr(self.ai_prompt_service, "close"):
                await self.ai_prompt_service.close()
            logger.info("Pipeline service closed")
        except Exception as e:
            logger.error(f"Error closing pipeline service: {e}", exc_info=True)


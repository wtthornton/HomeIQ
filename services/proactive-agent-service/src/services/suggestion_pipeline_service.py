"""
Suggestion Generation Pipeline Service for Proactive Agent Service

Orchestrates the full flow: Context Analysis → AI Prompt Generation → Agent Communication → Storage

Updated to use AI-powered prompt generation instead of hardcoded templates.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from ..clients.ha_agent_client import HAAgentClient
from ..services.context_analysis_service import ContextAnalysisService
from ..services.ai_prompt_generation_service import AIPromptGenerationService
from ..services.prompt_generation_service import PromptGenerationService
from ..services.suggestion_storage_service import SuggestionStorageService

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
            quality_threshold: Minimum quality score for suggestions (default: 0.6)
            max_suggestions_per_batch: Maximum suggestions per batch (default: 10)
            use_ai_generation: Use AI-powered generation (default: True)
            
        Raises:
            PipelineInitializationError: If any required service fails to initialize
        """
        self.use_ai_generation = use_ai_generation and os.getenv("OPENAI_API_KEY")
        
        try:
            self.context_service = context_service or ContextAnalysisService()
        except Exception as e:
            logger.error(f"Failed to initialize ContextAnalysisService: {e}", exc_info=True)
            raise PipelineInitializationError(f"ContextAnalysisService initialization failed: {e}") from e
        
        # Initialize AI-powered prompt service (primary)
        if self.use_ai_generation:
            try:
                self.ai_prompt_service = ai_prompt_service or AIPromptGenerationService()
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
        logger.info(
            f"Suggestion Pipeline Service initialized ({mode} generation, "
            f"quality_threshold={quality_threshold}, max_batch={max_suggestions_per_batch})"
        )

    async def generate_suggestions(self) -> dict[str, Any]:
        """
        Generate proactive automation suggestions.

        Full pipeline:
        1. Analyze context (weather, sports, energy, patterns)
        2. Generate context-aware prompts
        3. Store suggestions in database (status: pending)

        Suggestions are stored with status "pending" and can be manually sent to
        the HA AI Agent Service via the API endpoint POST /api/v1/suggestions/{id}/send.

        Returns:
            Dictionary with pipeline results:
            {
                "success": bool,
                "suggestions_created": int,
                "suggestions_failed": int,
                "details": [...]
            }
        """
        logger.info("Starting suggestion generation pipeline")

        results = {
            "success": True,
            "suggestions_created": 0,
            "suggestions_failed": 0,
            "details": [],
        }

        try:
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


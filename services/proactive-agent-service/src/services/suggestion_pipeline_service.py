"""
Suggestion Generation Pipeline Service for Proactive Agent Service

Orchestrates the full flow: Context Analysis → Prompt Generation → Agent Communication → Storage
"""

from __future__ import annotations

import logging
from typing import Any

from ..clients.ha_agent_client import HAAgentClient
from ..services.context_analysis_service import ContextAnalysisService
from ..services.prompt_generation_service import PromptGenerationService
from ..services.suggestion_storage_service import SuggestionStorageService

logger = logging.getLogger(__name__)


class SuggestionPipelineService:
    """Service for orchestrating suggestion generation pipeline"""

    def __init__(
        self,
        context_service: ContextAnalysisService | None = None,
        prompt_service: PromptGenerationService | None = None,
        agent_client: HAAgentClient | None = None,
        storage_service: SuggestionStorageService | None = None,
        quality_threshold: float = 0.6,
        max_suggestions_per_batch: int = 10,
    ):
        """
        Initialize Suggestion Pipeline Service.

        Args:
            context_service: Context Analysis Service (creates default if None)
            prompt_service: Prompt Generation Service (creates default if None)
            agent_client: HA Agent Client (creates default if None)
            storage_service: Suggestion Storage Service (creates default if None)
            quality_threshold: Minimum quality score for suggestions (default: 0.6)
            max_suggestions_per_batch: Maximum suggestions per batch (default: 10)
        """
        self.context_service = context_service or ContextAnalysisService()
        self.prompt_service = prompt_service or PromptGenerationService()
        self.agent_client = agent_client or HAAgentClient()
        self.storage_service = storage_service or SuggestionStorageService()
        self.quality_threshold = quality_threshold
        self.max_suggestions_per_batch = max_suggestions_per_batch

        logger.info(
            f"Suggestion Pipeline Service initialized "
            f"(quality_threshold={quality_threshold}, max_batch={max_suggestions_per_batch})"
        )

    async def generate_suggestions(self) -> dict[str, Any]:
        """
        Generate proactive automation suggestions.

        Full pipeline:
        1. Analyze context (weather, sports, energy, patterns)
        2. Generate context-aware prompts
        3. Send prompts to HA AI Agent Service
        4. Store suggestions in database

        Returns:
            Dictionary with pipeline results:
            {
                "success": bool,
                "suggestions_created": int,
                "suggestions_sent": int,
                "suggestions_failed": int,
                "details": [...]
            }
        """
        logger.info("Starting suggestion generation pipeline")

        results = {
            "success": True,
            "suggestions_created": 0,
            "suggestions_sent": 0,
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

            # Step 2: Generate prompts
            logger.debug("Step 2: Generating prompts")
            prompts = self.prompt_service.generate_prompts(
                context_analysis, max_prompts=self.max_suggestions_per_batch
            )

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

                    # Store suggestion (pending status)
                    suggestion = await self.storage_service.create_suggestion(
                        prompt=prompt_data["prompt"],
                        context_type=prompt_data["context_type"],
                        quality_score=prompt_data.get("quality_score", 0.0),
                        context_metadata=context_analysis,
                        prompt_metadata=prompt_data.get("metadata", {}),
                    )

                    results["suggestions_created"] += 1
                    logger.debug(f"Created suggestion {suggestion.id}")

                    # Send to HA AI Agent Service
                    try:
                        agent_response = await self.agent_client.send_message(prompt_data["prompt"])

                        if agent_response:
                            # Update suggestion with agent response and mark as sent
                            await self.storage_service.update_suggestion_status(
                                suggestion.id,
                                status="sent",
                                agent_response={
                                    "message": agent_response.get("message", ""),
                                    "conversation_id": agent_response.get("conversation_id"),
                                    "tool_calls": agent_response.get("tool_calls", []),
                                    "metadata": agent_response.get("metadata", {}),
                                },
                            )

                            results["suggestions_sent"] += 1
                            results["details"].append(
                                {
                                    "step": "agent_communication",
                                    "suggestion_id": suggestion.id,
                                    "status": "sent",
                                    "conversation_id": agent_response.get("conversation_id"),
                                }
                            )
                            logger.info(f"Successfully sent suggestion {suggestion.id} to HA AI Agent")
                        else:
                            # Agent communication failed, but suggestion is stored
                            logger.warning(f"Agent communication failed for suggestion {suggestion.id}")
                            results["suggestions_failed"] += 1
                            results["details"].append(
                                {
                                    "step": "agent_communication",
                                    "suggestion_id": suggestion.id,
                                    "status": "pending",
                                    "error": "Agent communication failed",
                                }
                            )

                    except Exception as agent_error:
                        # Agent error - suggestion stored but not sent
                        logger.error(
                            f"Error sending suggestion {suggestion.id} to agent: {agent_error}",
                            exc_info=True,
                        )
                        results["suggestions_failed"] += 1
                        results["details"].append(
                            {
                                "step": "agent_communication",
                                "suggestion_id": suggestion.id,
                                "status": "pending",
                                "error": str(agent_error),
                            }
                        )

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
                f"{results['suggestions_sent']} sent, {results['suggestions_failed']} failed"
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
            logger.info("Pipeline service closed")
        except Exception as e:
            logger.error(f"Error closing pipeline service: {e}", exc_info=True)


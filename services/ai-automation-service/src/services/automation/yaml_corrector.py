"""
Automation YAML Corrector

Self-correction service for YAML errors.
Wraps existing YAMLSelfCorrectionService.

Created: Phase 2 - Core Service Refactoring
"""

import logging
from typing import Dict, Optional, Any
from openai import AsyncOpenAI
from ...services.yaml_self_correction import YAMLSelfCorrectionService, SelfCorrectionResponse
from ...clients.ha_client import HomeAssistantClient

logger = logging.getLogger(__name__)


class AutomationYAMLCorrector:
    """
    Unified YAML corrector for fixing automation YAML errors.
    
    Uses reverse engineering and similarity comparison to iteratively
    improve YAML until it matches the intended prompt.
    """
    
    def __init__(
        self,
        openai_client: AsyncOpenAI,
        ha_client: Optional[HomeAssistantClient] = None,
        device_intelligence_client: Optional[Any] = None
    ):
        """
        Initialize YAML corrector.
        
        Args:
            openai_client: OpenAI client for correction
            ha_client: Optional Home Assistant client
            device_intelligence_client: Optional device intelligence client
        """
        self.correction_service = YAMLSelfCorrectionService(
            openai_client=openai_client,
            ha_client=ha_client,
            device_intelligence_client=device_intelligence_client
        )
        
        logger.info("AutomationYAMLCorrector initialized")
    
    async def correct(
        self,
        user_prompt: str,
        generated_yaml: str,
        context: Optional[Dict] = None,
        comprehensive_enriched_data: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> SelfCorrectionResponse:
        """
        Correct YAML using self-correction service.
        
        Args:
            user_prompt: Original user prompt
            generated_yaml: Generated YAML to correct
            context: Optional context
            comprehensive_enriched_data: Optional enriched entity data
        
        Returns:
            SelfCorrectionResponse with corrected YAML
        """
        try:
            result = await self.correction_service.correct_yaml(
                user_prompt=user_prompt,
                generated_yaml=generated_yaml,
                context=context,
                comprehensive_enriched_data=comprehensive_enriched_data
            )
            
            logger.info(f"✅ YAML correction completed: {result.iterations_completed} iterations, similarity: {result.final_similarity:.2%}")
            return result
            
        except Exception as e:
            logger.error(f"❌ YAML correction failed: {e}", exc_info=True)
            raise


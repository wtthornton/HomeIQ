"""
Unified Pipeline Orchestrator (2025)

Orchestrates the execution of the extraction pipeline components.
"""

import logging
from typing import Any
from .models import AutomationContext
from .extractors.spatial import SpatialExtractor
from .extractors.device import DeviceExtractor
from .extractors.intent import IntentExtractor

logger = logging.getLogger(__name__)

class UnifiedExtractionPipeline:
    """
    Main entry point for the unified extraction process.
    Runs extractors in sequence (or parallel where possible) to build the AutomationContext.
    """
    
    def __init__(self, ha_client: Any, openai_client: Any, device_client: Any = None):
        self.spatial = SpatialExtractor(ha_client)
        self.device = DeviceExtractor(ha_client, device_client)
        self.intent = IntentExtractor(openai_client)
        
    async def process(self, query: str) -> AutomationContext:
        """
        Run the full extraction pipeline on a query.
        
        Flow:
        1. Init Context
        2. Spatial Extraction (Where?)
        3. Device Extraction (What? - scoped by Where)
        4. Intent Extraction (How/When? - grounded by What/Where)
        """
        logger.info(f"Starting unified extraction for: '{query}'")
        
        # 1. Initialize Context
        context = AutomationContext(raw_query=query)
        
        try:
            # 2. Spatial Extraction
            # Identifies areas to filter the device search
            context = await self.spatial.extract(query, context)
            
            # 3. Device Extraction
            # Identifies candidate entities, prioritized by spatial context
            context = await self.device.extract(query, context)
            
            # 4. Intent Extraction
            # Uses LLM to parse logic, grounded by the candidates found above
            context = await self.intent.extract(query, context)
            
            logger.info("Pipeline completed successfully.")
            return context
            
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}", exc_info=True)
            # Return whatever partial context we have
            return context


"""
Ask AI Flow Simulator

Complete Ask AI conversational flow simulation with mocked services.
Integrates with production Ask AI flow but uses mocked dependencies.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class AskAISimulator:
    """
    Simulator for Ask AI conversational flow.
    
    Executes complete Ask AI flow with mocked services.
    All phases execute with real logic but mocked data/services.
    """

    def __init__(
        self,
        container: Any,  # DependencyContainer
        synthetic_data: dict[str, Any] | None = None
    ):
        """
        Initialize Ask AI flow simulator.
        
        Args:
            container: Dependency injection container with mock services
            synthetic_data: Synthetic home data for simulation
        """
        self.container = container
        self.synthetic_data = synthetic_data or {}
        self.results: dict[str, Any] = {}
        
        logger.info("AskAISimulator initialized")

    async def simulate_query(
        self,
        home_id: str,
        query: str,
        config: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Simulate complete Ask AI query flow for a home.
        
        Args:
            home_id: Home identifier
            query: User query
            config: Optional configuration overrides
            
        Returns:
            Simulation results dictionary
        """
        logger.info(f"Starting Ask AI query simulation for home {home_id}: {query[:50]}...")
        start_time = datetime.now(timezone.utc)
        
        try:
            # Step 1: Entity Extraction (mocked HA Conversation API)
            step1_result = await self._simulate_entity_extraction(home_id, query)
            
            # Step 2: Entity Resolution (mocked HA Client)
            step2_result = await self._simulate_entity_resolution(home_id, step1_result)
            
            # Step 3: Suggestion Generation (mocked OpenAI)
            step3_result = await self._simulate_suggestion_generation(home_id, query, step2_result)
            
            # Step 4: YAML Generation (real logic, mocked services)
            step4_result = await self._simulate_yaml_generation(home_id, step3_result)
            
            # Step 5: YAML Validation (real logic)
            step5_result = await self._simulate_yaml_validation(home_id, step4_result)
            
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            result = {
                "status": "success",
                "home_id": home_id,
                "query": query,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "steps": {
                    "step1_entity_extraction": step1_result,
                    "step2_entity_resolution": step2_result,
                    "step3_suggestion_generation": step3_result,
                    "step4_yaml_generation": step4_result,
                    "step5_yaml_validation": step5_result
                }
            }
            
            self.results[f"{home_id}_{query}"] = result
            
            logger.info(f"Ask AI query simulation completed for home {home_id} in {duration:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Ask AI query simulation failed for home {home_id}: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "home_id": home_id,
                "query": query
            }

    async def _simulate_entity_extraction(
        self,
        home_id: str,
        query: str
    ) -> dict[str, Any]:
        """Simulate Step 1: Entity Extraction."""
        logger.debug(f"Step 1: Entity Extraction for {home_id}")
        
        # Get mock HA Conversation API
        ha_conversation = self.container.get("ha_conversation_api")
        
        # Extract entities
        entities = await ha_conversation.extract_entities(query)
        
        return {
            "entities_count": len(entities),
            "entities": entities,
            "status": "completed"
        }

    async def _simulate_entity_resolution(
        self,
        home_id: str,
        step1_result: dict[str, Any]
    ) -> dict[str, Any]:
        """Simulate Step 2: Entity Resolution."""
        logger.debug(f"Step 2: Entity Resolution for {home_id}")
        
        # Get mock HA Client
        ha_client = self.container.get("ha_client")
        
        # Resolve entities
        entities = step1_result.get("entities", [])
        resolved_entities = []
        
        for entity in entities:
            entity_id = entity.get("entity_id", "")
            if entity_id:
                is_valid = await ha_client.validate_entity(entity_id)
                if is_valid:
                    resolved_entities.append(entity)
        
        return {
            "resolved_entities_count": len(resolved_entities),
            "resolved_entities": resolved_entities,
            "status": "completed"
        }

    async def _simulate_suggestion_generation(
        self,
        home_id: str,
        query: str,
        step2_result: dict[str, Any]
    ) -> dict[str, Any]:
        """Simulate Step 3: Suggestion Generation."""
        logger.debug(f"Step 3: Suggestion Generation for {home_id}")
        
        # Get mock OpenAI client
        openai_client = self.container.get("openai_client")
        
        # Generate suggestions
        entities = step2_result.get("resolved_entities", [])
        
        prompt_dict = {
            "system_prompt": "You are an automation expert",
            "user_prompt": f"Query: {query}\nEntities: {entities}"
        }
        
        suggestion = await openai_client.generate_with_unified_prompt(
            prompt_dict,
            output_format="description"
        )
        
        return {
            "suggestions_count": 1,
            "suggestions": [suggestion],
            "status": "completed"
        }

    async def _simulate_yaml_generation(
        self,
        home_id: str,
        step3_result: dict[str, Any]
    ) -> dict[str, Any]:
        """Simulate Step 4: YAML Generation (real logic, mocked services)."""
        logger.debug(f"Step 4: YAML Generation for {home_id}")
        
        # In real implementation, would use production YAML generator
        # For now, return mock YAML
        suggestions = step3_result.get("suggestions", [])
        
        yaml_content = ""
        if suggestions:
            # Mock YAML generation
            yaml_content = """
automation:
  - alias: "Mock Automation"
    trigger:
      - platform: state
        entity_id: light.office
    action:
      - service: light.turn_on
        entity_id: light.office
"""
        
        return {
            "yaml_generated": bool(yaml_content),
            "yaml_content": yaml_content,
            "status": "completed"
        }

    async def _simulate_yaml_validation(
        self,
        home_id: str,
        step4_result: dict[str, Any]
    ) -> dict[str, Any]:
        """Simulate Step 5: YAML Validation (real logic)."""
        logger.debug(f"Step 5: YAML Validation for {home_id}")
        
        # Get mock safety validator
        safety_validator = self.container.get("safety_validator")
        
        yaml_content = step4_result.get("yaml_content", "")
        
        validation_result = await safety_validator.validate(
            yaml_content,
            existing_automations=[]
        )
        
        return {
            "yaml_valid": validation_result.get("is_valid", False),
            "validation_errors": validation_result.get("errors", []),
            "status": "completed"
        }


"""
Device Suggestion Service
Phase 2: Device-Based Automation Suggestions Feature

Generates automation suggestions for devices by aggregating data from multiple sources.
"""

import logging
import uuid
from typing import Any

import httpx

from ..api.device_suggestions_models import (
    DeviceContext,
    DeviceSuggestion,
    DeviceSuggestionContext,
    DeviceSuggestionsResponse,
    AutomationPreview,
    DataSources,
    HomeAssistantEntities,
    HomeAssistantServices,
)
from ..clients.data_api_client import DataAPIClient
from ..config import Settings

logger = logging.getLogger(__name__)


class DeviceSuggestionService:
    """Service for generating device-based automation suggestions"""
    
    def __init__(self, settings: Settings):
        """
        Initialize device suggestion service.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.data_api_client = DataAPIClient(
            base_url=settings.data_api_url or "http://data-api:8006"
        )
        # HTTP client for other services
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
    
    async def generate_suggestions(
        self,
        device_id: str,
        conversation_id: str | None = None,
        context: DeviceSuggestionContext | None = None,
    ) -> DeviceSuggestionsResponse:
        """
        Generate automation suggestions for a device.
        
        Args:
            device_id: Device ID to generate suggestions for
            conversation_id: Optional conversation ID for context
            context: Context configuration for data aggregation
            
        Returns:
            DeviceSuggestionsResponse with suggestions and device context
        """
        if context is None:
            context = DeviceSuggestionContext()
        
        logger.info(f"Generating suggestions for device: {device_id}")
        
        # Aggregate data from multiple sources
        device_context = await self._aggregate_device_data(
            device_id=device_id,
            context=context,
        )
        
        # Generate suggestions from aggregated data
        suggestions = await self._generate_suggestions_from_data(
            device_id=device_id,
            device_context=device_context,
            context=context,
        )
        
        # Rank and filter suggestions (limit to 3-5)
        ranked_suggestions = self._rank_suggestions(suggestions)
        
        return DeviceSuggestionsResponse(
            suggestions=ranked_suggestions[:5],  # Limit to top 5
            device_context=device_context,
        )
    
    async def _aggregate_device_data(
        self,
        device_id: str,
        context: DeviceSuggestionContext,
    ) -> DeviceContext:
        """
        Aggregate device data from multiple sources.
        
        Args:
            device_id: Device ID
            context: Context configuration
            
        Returns:
            DeviceContext with aggregated data
        """
        # Fetch device data from data-api
        device_data = await self._fetch_device_data(device_id)
        capabilities = await self._fetch_device_capabilities(device_id)
        entities = await self._fetch_device_entities(device_id)
        
        # Initialize context
        device_context = DeviceContext(
            device_id=device_id,
            capabilities=capabilities,
            related_synergies=[],
            compatible_blueprints=[],
            home_assistant_entities=entities,
            home_assistant_services=[],
        )
        
        # Aggregate synergies if requested
        if context.include_synergies:
            try:
                synergies = await self._fetch_synergies(device_id)
                device_context.related_synergies = synergies
            except Exception as e:
                logger.warning(f"Failed to fetch synergies: {e}")
        
        # Aggregate blueprints if requested
        if context.include_blueprints:
            try:
                blueprints = await self._fetch_blueprints(device_id)
                device_context.compatible_blueprints = blueprints
            except Exception as e:
                logger.warning(f"Failed to fetch blueprints: {e}")
        
        # Aggregate sports data if requested
        if context.include_sports:
            try:
                sports_data = await self._fetch_sports_data(device_id)
                # Add sports data to context if needed
            except Exception as e:
                logger.warning(f"Failed to fetch sports data: {e}")
        
        # Aggregate weather data if requested
        if context.include_weather:
            try:
                weather_data = await self._fetch_weather_data(device_id)
                # Add weather data to context if needed
            except Exception as e:
                logger.warning(f"Failed to fetch weather data: {e}")
        
        return device_context
    
    async def _fetch_device_data(self, device_id: str) -> dict[str, Any]:
        """Fetch device data from data-api"""
        try:
            device = await self.data_api_client.fetch_device(device_id)
            return device
        except Exception as e:
            logger.error(f"Failed to fetch device data: {e}")
            return {}
    
    async def _fetch_device_capabilities(self, device_id: str) -> list[dict[str, Any]]:
        """Fetch device capabilities from data-api"""
        try:
            # TODO: Implement device capabilities endpoint call
            # For now, return empty list
            return []
        except Exception as e:
            logger.error(f"Failed to fetch device capabilities: {e}")
            return []
    
    async def _fetch_device_entities(self, device_id: str) -> list[dict[str, Any]]:
        """Fetch device entities from data-api"""
        try:
            entities = await self.data_api_client.fetch_entities(device_id=device_id)
            return entities
        except Exception as e:
            logger.error(f"Failed to fetch device entities: {e}")
            return []
    
    async def _fetch_synergies(self, device_id: str) -> list[dict[str, Any]]:
        """Fetch synergies from ai-pattern-service"""
        try:
            # TODO: Implement synergies API call
            # For now, return empty list
            return []
        except Exception as e:
            logger.error(f"Failed to fetch synergies: {e}")
            return []
    
    async def _fetch_blueprints(self, device_id: str) -> list[dict[str, Any]]:
        """Fetch compatible blueprints from blueprint-suggestion-service"""
        try:
            # TODO: Implement blueprint API call
            # For now, return empty list
            return []
        except Exception as e:
            logger.error(f"Failed to fetch blueprints: {e}")
            return []
    
    async def _fetch_sports_data(self, device_id: str) -> dict[str, Any] | None:
        """Fetch sports data from sports-api"""
        try:
            # TODO: Implement sports API call
            # For now, return None
            return None
        except Exception as e:
            logger.error(f"Failed to fetch sports data: {e}")
            return None
    
    async def _fetch_weather_data(self, device_id: str) -> dict[str, Any] | None:
        """Fetch weather data from weather-api"""
        try:
            # TODO: Implement weather API call
            # For now, return None
            return None
        except Exception as e:
            logger.error(f"Failed to fetch weather data: {e}")
            return None
    
    async def _generate_suggestions_from_data(
        self,
        device_id: str,
        device_context: DeviceContext,
        context: DeviceSuggestionContext,
    ) -> list[DeviceSuggestion]:
        """
        Generate suggestions from aggregated device data.
        
        This is a placeholder implementation that generates basic suggestions.
        In production, this would use LLM or rule-based generation.
        """
        suggestions: list[DeviceSuggestion] = []
        
        # Generate suggestion from device capabilities
        if device_context.capabilities:
            suggestion = DeviceSuggestion(
                suggestion_id=str(uuid.uuid4()),
                title="Device Capability Automation",
                description=f"Automation based on device capabilities for {device_id}",
                automation_preview=AutomationPreview(
                    trigger="Device state change",
                    action=f"Control {device_id}",
                ),
                data_sources=DataSources(
                    device_capabilities=True,
                ),
                home_assistant_entities=HomeAssistantEntities(
                    action_entities=[entity.get("entity_id") for entity in device_context.home_assistant_entities if entity.get("entity_id")],
                ),
                home_assistant_services=HomeAssistantServices(
                    actions=["switch.turn_on"],
                    validated=False,
                ),
                confidence_score=0.7,
                quality_score=0.65,
                enhanceable=True,
                home_assistant_compatible=True,
            )
            suggestions.append(suggestion)
        
        # Generate suggestion from synergies
        if device_context.related_synergies:
            suggestion = DeviceSuggestion(
                suggestion_id=str(uuid.uuid4()),
                title="Synergy-Based Automation",
                description=f"Automation based on device interaction patterns",
                automation_preview=AutomationPreview(
                    trigger="Related device state change",
                    action=f"Control {device_id}",
                ),
                data_sources=DataSources(
                    synergies=[s.get("id", "") for s in device_context.related_synergies if s.get("id")],
                    device_capabilities=True,
                ),
                confidence_score=0.8,
                quality_score=0.75,
                enhanceable=True,
                home_assistant_compatible=True,
            )
            suggestions.append(suggestion)
        
        # Generate suggestion from blueprints
        if device_context.compatible_blueprints:
            suggestion = DeviceSuggestion(
                suggestion_id=str(uuid.uuid4()),
                title="Blueprint-Based Automation",
                description=f"Automation based on Home Assistant blueprint",
                automation_preview=AutomationPreview(
                    trigger="Blueprint trigger",
                    action=f"Blueprint action for {device_id}",
                ),
                data_sources=DataSources(
                    blueprints=[b.get("id", "") for b in device_context.compatible_blueprints if b.get("id")],
                ),
                confidence_score=0.85,
                quality_score=0.8,
                enhanceable=True,
                home_assistant_compatible=True,
            )
            suggestions.append(suggestion)
        
        # If no suggestions generated, create a basic one
        if not suggestions:
            suggestion = DeviceSuggestion(
                suggestion_id=str(uuid.uuid4()),
                title="Basic Device Automation",
                description=f"Basic automation for {device_id}",
                automation_preview=AutomationPreview(
                    trigger="Time-based trigger",
                    action=f"Control {device_id}",
                ),
                data_sources=DataSources(
                    device_capabilities=True,
                ),
                confidence_score=0.6,
                quality_score=0.6,
                enhanceable=True,
                home_assistant_compatible=True,
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def _rank_suggestions(
        self,
        suggestions: list[DeviceSuggestion],
    ) -> list[DeviceSuggestion]:
        """
        Rank suggestions by confidence, quality, and diversity.
        
        Prioritizes:
        - High confidence scores (≥0.7)
        - High quality scores (≥0.7)
        - Suggestions with blueprint matches
        - Suggestions with synergy support
        - Diversity (different trigger types)
        """
        # Sort by combined score (confidence + quality)
        ranked = sorted(
            suggestions,
            key=lambda s: (
                s.confidence_score + s.quality_score,  # Combined score
                s.confidence_score,  # Then by confidence
                s.quality_score,  # Then by quality
            ),
            reverse=True,
        )
        
        # Filter by minimum thresholds
        filtered = [
            s for s in ranked
            if s.confidence_score >= 0.6 and s.quality_score >= 0.6
        ]
        
        return filtered
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()

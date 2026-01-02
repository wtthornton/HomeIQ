"""
Context Prioritization Service

Phase 3.1: Semantic Context Prioritization (Score: 60)

Scores entities, services, and devices by relevance to user prompt,
then sorts and filters context to include only top N most relevant items.
This reduces token usage while improving accuracy.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class ContextPrioritizationService:
    """
    Service for prioritizing context by semantic relevance to user prompt.
    
    Scores entities, services, devices, and areas by how relevant they are
    to the user's intent, then filters to top N most relevant items.
    """

    def __init__(self):
        """Initialize context prioritization service."""
        self.logger = logger

    def score_entity_relevance(
        self,
        entity: dict[str, Any],
        user_prompt: str
    ) -> float:
        """
        Score entity relevance to user prompt.
        
        Args:
            entity: Entity dictionary with entity_id, friendly_name, domain, etc.
            user_prompt: User's natural language prompt
            
        Returns:
            Relevance score (0.0 to 1.0, higher = more relevant)
        """
        prompt_lower = user_prompt.lower()
        score = 0.0
        
        # Extract entity information
        entity_id = (entity.get("entity_id") or "").lower()
        friendly_name = (entity.get("friendly_name") or entity.get("name") or "").lower()
        domain = (entity.get("domain") or "").lower()
        area_id = (entity.get("area_id") or "").lower()
        
        # Score by exact entity_id match (highest priority)
        if entity_id and entity_id in prompt_lower:
            score += 0.5
        
        # Score by friendly name match
        if friendly_name:
            # Exact match
            if friendly_name in prompt_lower:
                score += 0.4
            # Partial word matches
            friendly_words = friendly_name.split()
            prompt_words = set(prompt_lower.split())
            matches = sum(1 for word in friendly_words if word in prompt_words and len(word) > 3)
            if matches > 0:
                score += 0.2 * (matches / max(len(friendly_words), 1))
        
        # Score by domain match (light, sensor, switch, etc.)
        domain_keywords = {
            "light": ["light", "lamp", "bulb", "brightness", "illuminate"],
            "sensor": ["sensor", "detect", "motion", "temperature", "humidity"],
            "switch": ["switch", "turn on", "turn off", "toggle"],
            "climate": ["climate", "temperature", "heat", "cool", "hvac", "thermostat"],
            "cover": ["cover", "blind", "shade", "curtain", "garage"],
            "fan": ["fan", "ventilate", "air"],
            "lock": ["lock", "unlock", "door"],
            "media_player": ["media", "music", "speaker", "play", "volume"],
        }
        
        if domain in domain_keywords:
            keywords = domain_keywords[domain]
            if any(keyword in prompt_lower for keyword in keywords):
                score += 0.3
        
        # Score by area match
        if area_id:
            area_name = area_id.replace("_", " ").lower()
            if area_name in prompt_lower:
                score += 0.3
        
        # Normalize score to 0.0-1.0
        return min(1.0, score)

    def score_service_relevance(
        self,
        service: str,
        user_prompt: str
    ) -> float:
        """
        Score service relevance to user prompt.
        
        Args:
            service: Service name (e.g., "light.turn_on")
            user_prompt: User's natural language prompt
            
        Returns:
            Relevance score (0.0 to 1.0, higher = more relevant)
        """
        prompt_lower = user_prompt.lower()
        score = 0.0
        
        service_lower = service.lower()
        
        # Extract domain and action
        if "." in service:
            domain, action = service.split(".", 1)
        else:
            domain = service
            action = ""
        
        # Score by exact service match
        if service_lower in prompt_lower:
            score += 0.5
        
        # Score by domain match
        domain_keywords = {
            "light": ["light", "lamp", "bulb", "brightness"],
            "switch": ["switch", "turn on", "turn off"],
            "climate": ["climate", "temperature", "heat", "cool"],
            "cover": ["cover", "blind", "shade"],
            "fan": ["fan", "ventilate"],
        }
        
        if domain in domain_keywords:
            if any(keyword in prompt_lower for keyword in domain_keywords[domain]):
                score += 0.3
        
        # Score by action match
        action_keywords = {
            "turn_on": ["turn on", "enable", "activate", "start"],
            "turn_off": ["turn off", "disable", "deactivate", "stop"],
            "toggle": ["toggle", "switch"],
            "set": ["set", "change", "adjust"],
        }
        
        if action in action_keywords:
            if any(keyword in prompt_lower for keyword in action_keywords[action]):
                score += 0.2
        
        return min(1.0, score)

    def score_device_relevance(
        self,
        device: dict[str, Any],
        user_prompt: str
    ) -> float:
        """
        Score device relevance to user prompt.
        
        Args:
            device: Device dictionary with device_id, name, manufacturer, model, etc.
            user_prompt: User's natural language prompt
            
        Returns:
            Relevance score (0.0 to 1.0, higher = more relevant)
        """
        prompt_lower = user_prompt.lower()
        score = 0.0
        
        device_name = (device.get("name") or device.get("device_id") or "").lower()
        manufacturer = (device.get("manufacturer") or "").lower()
        model = (device.get("model") or "").lower()
        area_id = (device.get("area_id") or "").lower()
        
        # Score by device name match
        if device_name and device_name in prompt_lower:
            score += 0.4
        
        # Score by manufacturer/model match
        if manufacturer and manufacturer in prompt_lower:
            score += 0.2
        if model and model in prompt_lower:
            score += 0.2
        
        # Score by area match
        if area_id:
            area_name = area_id.replace("_", " ").lower()
            if area_name in prompt_lower:
                score += 0.3
        
        return min(1.0, score)

    def prioritize_entities(
        self,
        entities: list[dict[str, Any]],
        user_prompt: str,
        top_n: int = 20
    ) -> list[dict[str, Any]]:
        """
        Prioritize entities by relevance to user prompt.
        
        Args:
            entities: List of entity dictionaries
            user_prompt: User's natural language prompt
            top_n: Maximum number of entities to return
            
        Returns:
            List of top N most relevant entities, sorted by relevance score
        """
        if not entities or not user_prompt:
            return entities[:top_n] if entities else []
        
        # Score all entities
        scored_entities = []
        for entity in entities:
            score = self.score_entity_relevance(entity, user_prompt)
            scored_entities.append((score, entity))
        
        # Sort by score (descending)
        scored_entities.sort(key=lambda x: x[0], reverse=True)
        
        # Return top N
        return [entity for score, entity in scored_entities[:top_n]]

    def prioritize_services(
        self,
        services: list[str],
        user_prompt: str,
        top_n: int = 15
    ) -> list[str]:
        """
        Prioritize services by relevance to user prompt.
        
        Args:
            services: List of service names
            user_prompt: User's natural language prompt
            top_n: Maximum number of services to return
            
        Returns:
            List of top N most relevant services, sorted by relevance score
        """
        if not services or not user_prompt:
            return services[:top_n] if services else []
        
        # Score all services
        scored_services = []
        for service in services:
            score = self.score_service_relevance(service, user_prompt)
            scored_services.append((score, service))
        
        # Sort by score (descending)
        scored_services.sort(key=lambda x: x[0], reverse=True)
        
        # Return top N
        return [service for score, service in scored_services[:top_n]]

    def prioritize_devices(
        self,
        devices: list[dict[str, Any]],
        user_prompt: str,
        top_n: int = 15
    ) -> list[dict[str, Any]]:
        """
        Prioritize devices by relevance to user prompt.
        
        Args:
            devices: List of device dictionaries
            user_prompt: User's natural language prompt
            top_n: Maximum number of devices to return
            
        Returns:
            List of top N most relevant devices, sorted by relevance score
        """
        if not devices or not user_prompt:
            return devices[:top_n] if devices else []
        
        # Score all devices
        scored_devices = []
        for device in devices:
            score = self.score_device_relevance(device, user_prompt)
            scored_devices.append((score, device))
        
        # Sort by score (descending)
        scored_devices.sort(key=lambda x: x[0], reverse=True)
        
        # Return top N
        return [device for score, device in scored_devices[:top_n]]

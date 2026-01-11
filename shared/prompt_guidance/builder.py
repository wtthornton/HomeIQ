"""
Prompt builder utility for constructing consistent prompts.

Provides utilities for building prompts with shared principles and templates.
"""

from typing import Any

from .core_principles import AUTOMATION_FORMAT_STANDARD, CORE_IDENTITY
from .homeiq_json_schema import HOMEIQ_JSON_SCHEMA_DOC
from .templates.automation_generation import AUTOMATION_GENERATION_SYSTEM_PROMPT
from .templates.suggestion_generation import SUGGESTION_GENERATION_SYSTEM_PROMPT
from .templates.yaml_generation import YAML_GENERATION_SYSTEM_PROMPT


class PromptBuilder:
    """
    Builder for constructing consistent prompts with shared principles.
    """
    
    @staticmethod
    def build_automation_generation_prompt(
        additional_context: str = "",
        entity_context: dict[str, Any] | None = None
    ) -> str:
        """
        Build system prompt for automation generation.
        
        Args:
            additional_context: Additional context to include
            entity_context: Entity context (entities by domain)
        
        Returns:
            Complete system prompt for automation generation
        """
        prompt = AUTOMATION_GENERATION_SYSTEM_PROMPT.format(
            CORE_IDENTITY=CORE_IDENTITY,
            AUTOMATION_FORMAT_STANDARD=AUTOMATION_FORMAT_STANDARD,
            HOMEIQ_JSON_SCHEMA_DOC=HOMEIQ_JSON_SCHEMA_DOC
        )
        
        if additional_context:
            prompt += f"\n\n## Additional Context\n\n{additional_context}"
        
        if entity_context:
            entity_section = "\n\n## Available Entities\n\n"
            entity_section += "You MUST use ONLY the entity IDs listed below:\n\n"
            for domain, entities in entity_context.items():
                if entities:
                    entity_ids = [e.get("entity_id", "") for e in entities[:30] if e.get("entity_id")]
                    if entity_ids:
                        entity_section += f"{domain.upper()}: {', '.join(entity_ids)}\n"
            prompt += entity_section
        
        return prompt
    
    @staticmethod
    def build_suggestion_generation_prompt(
        device_inventory: dict[str, Any] | None = None,
        home_context: str = ""
    ) -> str:
        """
        Build system prompt for suggestion generation.
        
        Args:
            device_inventory: Device inventory for validation
            home_context: Home context information
        
        Returns:
            Complete system prompt for suggestion generation
        """
        prompt = SUGGESTION_GENERATION_SYSTEM_PROMPT.format(
            CORE_IDENTITY=CORE_IDENTITY
        )
        
        if device_inventory:
            device_section = "\n\n## Available Devices\n\n"
            device_section += "You may ONLY suggest automations for devices that exist in this list:\n\n"
            # Format device list from inventory
            if "devices" in device_inventory:
                for device in device_inventory["devices"][:50]:  # Limit to 50 devices
                    device_name = device.get("name", device.get("friendly_name", ""))
                    device_type = device.get("device_type", "")
                    if device_name:
                        device_section += f"- {device_name} ({device_type})\n"
            prompt += device_section
        
        if home_context:
            prompt += f"\n\n## Home Context\n\n{home_context}"
        
        return prompt
    
    @staticmethod
    def build_yaml_generation_prompt(
        ha_version: str = "2025.10",
        additional_instructions: str = ""
    ) -> str:
        """
        Build system prompt for YAML generation (deployment-only).
        
        Args:
            ha_version: Home Assistant version
            additional_instructions: Additional YAML generation instructions
        
        Returns:
            Complete system prompt for YAML generation
        """
        prompt = YAML_GENERATION_SYSTEM_PROMPT.format(
            AUTOMATION_FORMAT_STANDARD=AUTOMATION_FORMAT_STANDARD
        )
        
        prompt += f"\n\n## Home Assistant Version\n\nTarget version: {ha_version}\n"
        
        if additional_instructions:
            prompt += f"\n\n## Additional Instructions\n\n{additional_instructions}"
        
        return prompt

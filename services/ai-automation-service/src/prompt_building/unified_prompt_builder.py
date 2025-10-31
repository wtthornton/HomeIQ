"""
Unified Prompt Builder for AI Automation Service

This module provides a centralized prompt building system that unifies:
- Pattern-based prompts (3AM batch process)
- Query-based prompts (Ask AI interface)
- Description-only prompts (conversational flow)

All prompts leverage device intelligence when available for enhanced context.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..utils.capability_utils import normalize_capability, format_capability_for_display

logger = logging.getLogger(__name__)


class UnifiedPromptBuilder:
    """
    Unified prompt builder that consolidates all AI prompt generation
    with device intelligence integration.
    """
    
    # Unified system prompt for all AI interactions
    UNIFIED_SYSTEM_PROMPT = """You are a HIGHLY CREATIVE and experienced Home Assistant automation expert with deep knowledge of device capabilities and smart home best practices.

Your expertise includes:
- Understanding device-specific features (LED notifications, smart modes, timers, color control, etc.)
- Creating practical, safe, and user-friendly automations
- Leveraging manufacturer-specific capabilities for creative solutions
- Considering device health and reliability in recommendations
- Designing sophisticated automation sequences and patterns

ADVANCED CAPABILITY EXAMPLES:

Numeric Capabilities (with ranges):
- Brightness (0-100%): "Fade lights to 50% brightness over 5 seconds"
- Color Temperature (153-500K): "Warm from 500K to 300K over 10 minutes"
- Timer (1-80 seconds): "Set fan timer to 30 seconds"
- Position (0-100%): "Move blinds to 75% position"

Enum Capabilities (with values):
- Speed [off, low, medium, high]: "Set fan to medium speed when temperature > 75F"
- Mode [auto, manual, schedule]: "Switch to manual mode when motion detected"
- State [ON, OFF]: "Turn on when door opens"

Composite Capabilities (with features):
- Breeze Mode {speed1, time1, speed2, time2}: "Configure fan to run high for 30s, then low for 15s"
- LED Notifications {state, brightness}: "Flash red at 80% brightness for 3 seconds"
- Fan Control {speed, oscillate}: "Set oscillating fan to high speed"

Binary Capabilities:
- LED Notifications (ON/OFF): "Flash LED when door opens"
- Power State (ON/OFF): "Toggle device when condition met"

Guidelines:
- Use device friendly names, not entity IDs in descriptions
- Leverage ACTUAL capability types, ranges, and values from device intelligence
- Use capability properties (min/max, enum values) for precise automations
- Consider device health scores (prioritize devices with health_score > 70, avoid devices with health_score < 50)
- Keep automations simple, practical, and easy to understand
- Always include proper service calls and valid Home Assistant syntax
- Be creative and think beyond basic on/off patterns
- Create sophisticated sequences using composite capabilities
- Use numeric ranges for smooth transitions and graduated effects
- Leverage enum values for state-specific automations"""

    def __init__(self, device_intelligence_client=None):
        """
        Initialize the unified prompt builder.
        
        Args:
            device_intelligence_client: Optional client for device intelligence service
        """
        self.device_intel_client = device_intelligence_client
        
    async def build_pattern_prompt(
        self, 
        pattern: Dict, 
        device_context: Optional[Dict] = None,
        output_mode: str = "yaml"  # "yaml" | "description"
    ) -> Dict[str, str]:
        """
        Build prompt for pattern-based suggestion generation (3AM batch process).
        
        Args:
            pattern: Pattern dictionary with pattern data
            device_context: Enhanced device context with capabilities
            output_mode: "yaml" for full automation, "description" for description-only
            
        Returns:
            Dictionary with "system_prompt" and "user_prompt" keys
        """
        pattern_type = pattern.get('type', 'unknown')
        device_id = pattern.get('device_id')
        
        # Build device context section
        device_section = await self._build_device_context_section(device_context)
        
        # Pattern-specific user prompt
        if pattern_type == 'time_of_day':
            user_prompt = self._build_time_of_day_prompt(pattern, device_section, output_mode)
        elif pattern_type == 'co_occurrence':
            user_prompt = self._build_co_occurrence_prompt(pattern, device_section, output_mode)
        elif pattern_type == 'synergy':
            user_prompt = self._build_synergy_prompt(pattern, device_section, output_mode)
        else:
            user_prompt = self._build_generic_pattern_prompt(pattern, device_section, output_mode)
            
        return {
            "system_prompt": self.UNIFIED_SYSTEM_PROMPT,
            "user_prompt": user_prompt
        }
    
    async def build_query_prompt(
        self,
        query: str,
        entities: List[Dict],
        output_mode: str = "suggestions",  # "suggestions" | "yaml"
        entity_context_json: Optional[str] = None  # Enriched entity context JSON
    ) -> Dict[str, str]:
        """
        Build prompt for Ask AI query-based suggestion generation.
        
        Args:
            query: User's natural language query
            entities: List of detected entities with capabilities
            output_mode: "suggestions" for creative ideas, "yaml" for full automation
            entity_context_json: Optional enriched entity context JSON from EntityContextBuilder
            
        Returns:
            Dictionary with "system_prompt" and "user_prompt" keys
        """
        # Build entity context section
        try:
            entity_section = await self._build_entity_context_section(entities)
        except Exception as e:
            logger.warning(f"Failed to build entity context section: {e}")
            entity_section = "No device information available."
        
        # Add enriched entity context JSON if available
        enriched_context_section = ""
        if entity_context_json:
            enriched_context_section = f"""

ENRICHED ENTITY CONTEXT (Complete Entity Information):
{entity_context_json}

Use this enriched context to:
- Distinguish between group entities and individual entities
- Understand device capabilities and limitations
- Generate automations that respect device types (e.g., don't control individual Hue lights when room group is available)
- Create appropriate service calls based on entity attributes
"""
        
        # Generate capability-specific examples
        capability_examples = self._generate_capability_examples(entities)
        
        # Build creative query prompt with enhanced examples
        user_prompt = f"""Based on this query: "{query}"

Available devices and capabilities:
{entity_section}

{enriched_context_section}

CAPABILITY-SPECIFIC AUTOMATION IDEAS:
{capability_examples}

CRITICAL: DEVICE NAMING REQUIREMENTS:
- ONLY use devices that are listed in the "Available devices and capabilities" section OR the "ENRICHED ENTITY CONTEXT" section above
- Count how many devices are actually available - DO NOT assume a specific number
- Use ACTUAL device friendly names from the enriched entity context JSON - DO NOT make up generic names like "Device 1" or "office lights"
- Reference devices by their EXACT friendly_name from the entities list
- If the enriched context shows 6 individual lights, list all 6 with their actual names
- DO NOT use group entity names unless the enriched context shows it's a group entity
- Example: If enriched context shows ["Office light 1", "Office light 2", "Office light 3"], use those exact names

Generate 3-5 {output_mode} that PROGRESS from CLOSE to your request → to CRAZY CREATIVE ideas:

PROGRESSION STRATEGY:
1. FIRST suggestion(s): Direct, straightforward automation closely matching the request
   - Simple implementation
   - Exactly what was asked for
   - High confidence (0.9+)
   
2. MIDDLE suggestion(s): Enhanced variations building on the request
   - Practical improvements
   - Leverage device capabilities
   - Moderate-high confidence (0.8-0.9)
   
3. LAST suggestion(s): Creative, "outside the box" ideas pushing boundaries
   - Advanced features
   - Unique combinations
   - Innovative approaches
   - Moderate confidence (0.7-0.8)

All suggestions should:
- Be practical and achievable
- Leverage the specific capabilities of available devices
- Be safe and user-friendly
- Consider device health scores (avoid devices with health_score < 50)

The progression should show INCREASING CREATIVITY from first to last.

IMPORTANT: Return your response as a JSON array of suggestion objects, each with these fields:
- description: A detailed description of the automation
- trigger_summary: What triggers the automation
- action_summary: What actions will be performed
- devices_involved: Array of device names - MUST use EXACT friendly_name values from the enriched entity context JSON above
- capabilities_used: Array of device capabilities being used
- confidence: A confidence score between 0 and 1 (higher for conservative, lower for creative)

CRITICAL: For devices_involved, extract the exact "friendly_name" values from the enriched entity context JSON. Do NOT invent generic names like "Device 1" or "office lights". Use the actual device names from the entities array in the enriched context."""

        return {
            "system_prompt": self.UNIFIED_SYSTEM_PROMPT,
            "user_prompt": user_prompt
        }
    
    async def build_yaml_generation_prompt(
        self,
        suggestion: Dict[str, Any],
        entities: List[Dict[str, Any]],
        device_context: Optional[Dict] = None
    ) -> Dict[str, str]:
        """
        Build prompt for YAML generation with device validation.
        
        Args:
            suggestion: Suggestion dictionary with description, trigger, action
            entities: List of entities for validation
            device_context: Optional enhanced device context
            
        Returns:
            Dictionary with "system_prompt" and "user_prompt" keys
        """
        # Build entity validation context
        entity_context = await self._build_entity_validation_context(entities)
        
        # Build device context section
        device_section = await self._build_device_context_section(device_context)
        
        user_prompt = f"""Generate a sophisticated Home Assistant automation YAML configuration that brings this creative suggestion to life.

Suggestion: "{suggestion.get('description', '')}"

Trigger: {suggestion.get('trigger_summary', '')}
Action: {suggestion.get('action_summary', '')}
Devices: {suggestion.get('devices_involved', [])}
Capabilities Used: {suggestion.get('capabilities_used', [])}

Validated Entity IDs (USE ONLY THESE):
{entity_context}

Device Context:
{device_section}

Requirements:
1. Use YAML format (not JSON)
2. Include: id, alias, trigger, action
3. CRITICAL: Use ONLY the validated entity IDs provided above - do NOT create new entity IDs
4. Add appropriate conditions if needed
5. Include mode: single or restart
6. Add description field
7. Use advanced HA features for creative implementations:
   - `sequence` for multi-step actions
   - `choose` for conditional logic
   - `repeat` for repeated actions
   - `delay` for timing control
   - `condition` for complex conditions
8. Leverage device capabilities when available (LED notifications, smart modes, etc.)
9. Consider device health scores (avoid unreliable devices)
10. Make the automation robust and user-friendly

Generate a complete, valid Home Assistant automation YAML."""

        return {
            "system_prompt": self.UNIFIED_SYSTEM_PROMPT,
            "user_prompt": user_prompt
        }
    
    async def _build_entity_validation_context(self, entities: List[Dict[str, Any]]) -> str:
        """Build entity validation context for YAML generation."""
        if not entities:
            return "No entities available for validation."
        
        sections = []
        for entity in entities:
            entity_id = entity.get('entity_id', 'unknown')
            friendly_name = entity.get('friendly_name', entity_id)
            domain = entity.get('domain', entity_id.split('.')[0] if '.' in entity_id else 'unknown')
            
            entity_info = f"- {friendly_name}: {entity_id} (domain: {domain})"
            
            # Add capabilities if available
            capabilities = entity.get('capabilities', [])
            if capabilities:
                supported_caps = [cap.get('feature', cap) for cap in capabilities if isinstance(cap, dict) and cap.get('supported', False)]
                if supported_caps:
                    entity_info += f" [Supported: {', '.join(supported_caps)}]"
            
            sections.append(entity_info)
        
        return "\n".join(sections)
    
    async def build_feature_prompt(
        self,
        opportunity: Dict,
        device_context: Dict,
        output_mode: str = "description"
    ) -> Dict[str, str]:
        """
        Build prompt for device feature-based suggestion generation.
        
        Args:
            opportunity: Feature opportunity dictionary
            device_context: Device context with capabilities
            output_mode: Output format preference
            
        Returns:
            Dictionary with "system_prompt" and "user_prompt" keys
        """
        device_section = await self._build_device_context_section(device_context)
        
        user_prompt = f"""Device Feature Opportunity:
{opportunity.get('description', 'Unknown feature')}

Device Context:
{device_section}

Generate automation suggestions that leverage this specific device feature.
Focus on practical applications that enhance the user experience."""

        return {
            "system_prompt": self.UNIFIED_SYSTEM_PROMPT,
            "user_prompt": user_prompt
        }
    
    async def get_enhanced_device_context(self, pattern: Dict) -> Dict:
        """
        Get enhanced device context with intelligence data.
        
        Args:
            pattern: Pattern dictionary with device_id
            
        Returns:
            Enhanced device context with capabilities, health, manufacturer
        """
        device_id = pattern.get('device_id')
        if not device_id or not self.device_intel_client:
            return {}
            
        try:
            device_details = await self.device_intel_client.get_device_details(device_id)
            return {
                'device_id': device_id,
                'capabilities': device_details.get('capabilities', []),
                'health_score': device_details.get('health_score'),
                'manufacturer': device_details.get('manufacturer'),
                'model': device_details.get('model'),
                'integration': device_details.get('integration'),
                'friendly_name': device_details.get('friendly_name', device_id)
            }
        except Exception as e:
            logger.warning(f"Device intelligence unavailable for {device_id}: {e}")
            return {'device_id': device_id}
    
    async def _build_device_context_section(self, device_context: Optional[Dict]) -> str:
        """Build device context section for prompts."""
        if not device_context:
            return "No specific device context available."
            
        sections = []
        
        # Basic device info
        if device_context.get('friendly_name'):
            sections.append(f"Device: {device_context['friendly_name']}")
        
        if device_context.get('manufacturer'):
            sections.append(f"Manufacturer: {device_context['manufacturer']}")
            
        if device_context.get('model'):
            sections.append(f"Model: {device_context['model']}")
            
        # Health score
        health_score = device_context.get('health_score')
        if health_score is not None:
            health_status = "Excellent" if health_score > 80 else "Good" if health_score > 60 else "Fair"
            sections.append(f"Health Score: {health_score} ({health_status})")
            
        # Capabilities with detailed descriptions
        capabilities = device_context.get('capabilities', [])
        if capabilities:
            capability_descriptions = []
            for cap in capabilities:
                if isinstance(cap, dict):
                    feature = cap.get('feature', 'unknown')
                    supported = cap.get('supported', False)
                    status = "✓" if supported else "✗"
                    capability_descriptions.append(f"{status} {feature}")
                else:
                    capability_descriptions.append(str(cap))
            sections.append(f"Capabilities: {', '.join(capability_descriptions)}")
            
        return "\n".join(sections) if sections else "No device context available."
    
    async def _build_entity_context_section(self, entities: List[Dict]) -> str:
        """Build entity context section for Ask AI prompts with enhanced capability details."""
        if not entities:
            return "No devices detected in query."
            
        sections = []
        for entity in entities:
            # Try 'name' first (from device intelligence), then fall back to friendly_name, entity_id
            entity_name = entity.get('name', entity.get('friendly_name', entity.get('entity_id', 'Unknown')))
            entity_info = f"- {entity_name}"
            
            # Add manufacturer and model if available
            if entity.get('manufacturer'):
                entity_info += f" ({entity['manufacturer']}"
                if entity.get('model'):
                    entity_info += f" {entity['model']}"
                entity_info += ")"
            
            # Add capabilities with DETAILED information using normalization
            capabilities = entity.get('capabilities', [])
            if capabilities:
                capability_descriptions = []
                for cap in capabilities:
                    if isinstance(cap, dict):
                        # Use normalized capability and format for display
                        normalized = normalize_capability(cap)
                        formatted = format_capability_for_display(normalized)
                        capability_descriptions.append(formatted)
                    else:
                        capability_descriptions.append(str(cap))
                entity_info += f" [Capabilities: {', '.join(capability_descriptions)}]"
                
            # Add health score with status
            health_score = entity.get('health_score')
            if health_score is not None:
                health_status = "Excellent" if health_score > 80 else "Good" if health_score > 60 else "Fair"
                entity_info += f" [Health: {health_score} ({health_status})]"
            
            # Add area if available
            if entity.get('area'):
                entity_info += f" [Area: {entity['area']}]"
                
            sections.append(entity_info)
            
        return "\n".join(sections)
    
    def _generate_capability_examples(self, entities: List[Dict]) -> str:
        """Generate capability-specific examples based on detected devices."""
        examples = []
        
        # Collect unique capability types across all entities
        capability_types_found = {}
        
        for entity in entities:
            capabilities = entity.get('capabilities', [])
            for cap in capabilities:
                if isinstance(cap, dict):
                    normalized = normalize_capability(cap)
                    cap_type = normalized.get('type', 'unknown')
                    props = normalized.get('properties', {})
                    
                    if cap_type not in capability_types_found:
                        capability_types_found[cap_type] = []
                    capability_types_found[cap_type].append((normalized.get('name', 'unknown'), props))
        
        # Generate examples based on capabilities found
        for cap_type, caps in capability_types_found.items():
            if cap_type == 'numeric':
                examples.append("- For numeric capabilities (brightness, color_temp, timer): Use ranges for smooth transitions - 'Fade to 50% over 5 seconds', 'Warm from 500K to 300K over 10 minutes'")
            
            elif cap_type == 'enum':
                examples.append("- For enum capabilities (speed, mode, state): Use specific values - 'Set fan to medium speed when temperature > 75F'")
            
            elif cap_type == 'composite':
                examples.append("- For composite capabilities (breeze_mode, LED_notifications): Configure multiple features - 'Set fan to high for 30s, then low for 15s'")
            
            elif cap_type == 'binary':
                examples.append("- For binary capabilities (state, toggle): Use state changes - 'Toggle device when door opens'")
        
        return '\n'.join(examples) if examples else "- Use available device capabilities creatively"
    
    def _filter_suggestions_by_capabilities(self, suggestions: List[Dict], entities: List[Dict]) -> List[Dict]:
        """
        Filter suggestions to only include those using available capabilities.
        
        This prevents AI from suggesting features that devices don't have.
        
        Args:
            suggestions: List of suggestion dictionaries
            entities: List of entity dictionaries with capabilities
            
        Returns:
            Filtered list of suggestions
        """
        if not entities or not suggestions:
            return suggestions
        
        # Collect all available capabilities from entities
        entity_capabilities = set()
        for entity in entities:
            capabilities = entity.get('capabilities', [])
            for cap in capabilities:
                if isinstance(cap, dict):
                    normalized = normalize_capability(cap)
                    if normalized.get('supported'):
                        entity_capabilities.add(normalized.get('name', '').lower())
        
        # Filter suggestions based on capabilities used
        filtered = []
        for suggestion in suggestions:
            capabilities_used = suggestion.get('capabilities_used', [])
            
            # Check if any capability is mentioned
            if not capabilities_used:
                filtered.append(suggestion)  # Generic suggestion, keep it
                continue
            
            # Check if capabilities exist in available entities
            caps_mentioned = [c.lower() for c in capabilities_used]
            
            # Allow if at least one capability matches (fuzzy match)
            matches = [cap for cap in caps_mentioned if cap in entity_capabilities]
            
            if matches:
                filtered.append(suggestion)
                logger.debug(f"Kept suggestion: {suggestion.get('description', '')} - using capabilities: {matches}")
            else:
                logger.debug(f"Filtered suggestion: {suggestion.get('description', '')} - capabilities not available")
        
        # If all suggestions filtered out, return original (better than nothing)
        return filtered if filtered else suggestions
    
    def _build_time_of_day_prompt(self, pattern: Dict, device_section: str, output_mode: str) -> str:
        """Build time-of-day pattern prompt."""
        time_range = pattern.get('time_range', 'unknown time')
        frequency = pattern.get('frequency', 'unknown')
        confidence = pattern.get('confidence', 0.0)
        
        prompt = f"""Time-based Pattern Detected:
- Time Range: {time_range}
- Frequency: {frequency}
- Confidence: {confidence:.1%}
- Device Context: {device_section}

CREATIVE TIME-BASED AUTOMATION IDEAS:
- Instead of simple on/off, consider: "Gradually increase brightness over 5 minutes for a gentle wake-up"
- Use device capabilities: "Leverage smart bulb color temperature changes to simulate natural daylight"
- Add conditions: "Only activate during weekdays" or "Skip if already on"
- Create sequences: "Turn on lights → adjust temperature → play morning news"
- Health-aware: "Use most reliable devices for critical time-based automations"

Generate automation suggestions for this time-based pattern that leverage device capabilities."""

        if output_mode == "yaml":
            prompt += "\n\nProvide a complete Home Assistant YAML automation with proper triggers, conditions, and actions."
        else:
            prompt += "\n\nProvide a clear, descriptive automation idea without YAML that explains what it does and why it's helpful."

        return prompt
    
    def _build_co_occurrence_prompt(self, pattern: Dict, device_section: str, output_mode: str) -> str:
        """Build co-occurrence pattern prompt."""
        entities = pattern.get('entities', [])
        confidence = pattern.get('confidence', 0)
        time_delta = pattern.get('time_delta', 0)
        
        prompt = f"""Co-occurrence Pattern Detected:
- Entities: {', '.join(entities)}
- Confidence: {confidence:.1%}
- Time Delta: {time_delta} seconds
- Device Context: {device_section}

CREATIVE CO-OCCURRENCE AUTOMATION IDEAS:
- Instead of simple triggers, consider: "Create a choreographed sequence when first device activates"
- Use timing: "Add a {time_delta}s delay to create a natural flow between devices"
- Add conditions: "Only trigger if both devices are in specific states"
- Create cascading effects: "First device → wait → second device → wait → third device"
- Health-aware: "Use device health scores to determine which device should be the primary trigger"
- Smart combinations: "Combine device capabilities for enhanced user experience"

Generate automation suggestions for this co-occurrence pattern that create smooth, intelligent device interactions."""

        if output_mode == "yaml":
            prompt += "\n\nProvide a complete Home Assistant YAML automation with proper triggers, delays, and actions."
        else:
            prompt += "\n\nProvide a clear, descriptive automation idea without YAML that explains the device interaction and its benefits."

        return prompt
    
    def _build_synergy_prompt(self, pattern: Dict, device_section: str, output_mode: str) -> str:
        """Build synergy pattern prompt."""
        synergy_type = pattern.get('synergy_type', 'unknown')
        devices = pattern.get('devices', [])
        
        prompt = f"""Synergy Pattern Detected:
- Type: {synergy_type}
- Devices: {', '.join(devices)}
- Device Context: {device_section}

Generate automation suggestions that leverage the synergy between these devices."""

        if output_mode == "yaml":
            prompt += "\n\nProvide a complete Home Assistant YAML automation."
        else:
            prompt += "\n\nProvide a clear, descriptive automation idea without YAML."

        return prompt
    
    def _build_generic_pattern_prompt(self, pattern: Dict, device_section: str, output_mode: str) -> str:
        """Build generic pattern prompt."""
        pattern_data = pattern.get('data', {})
        
        prompt = f"""Pattern Detected:
- Pattern Data: {pattern_data}
- Device Context: {device_section}

Generate automation suggestions for this pattern."""

        if output_mode == "yaml":
            prompt += "\n\nProvide a complete Home Assistant YAML automation."
        else:
            prompt += "\n\nProvide a clear, descriptive automation idea without YAML."

        return prompt

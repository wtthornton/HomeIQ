"""
Enhanced Prompt Builder with Device Intelligence Context

Builds rich AI prompts using device capabilities and health data.
"""

import logging
from typing import List, Dict, Any, Set

logger = logging.getLogger(__name__)

class EnhancedPromptBuilder:
    """Builds enhanced AI prompts with device intelligence context"""
    
    def build_suggestion_prompt(self, query: str, entities: List[Dict[str, Any]]) -> str:
        """Build enhanced prompt for suggestion generation"""
        
        # Build rich device context
        device_context = self._build_device_context(entities)
        
        # Extract capabilities for examples
        capabilities_available = self._extract_capabilities(entities)
        
        prompt = f"""
You are a HIGHLY CREATIVE and experienced Home Assistant automation expert with access to detailed device capabilities and health data. Your goal is to generate 3-4 DISTINCT, DIVERSE, and IMAGINATIVE automation suggestions that leverage the SPECIFIC capabilities of the available devices.

Query: "{query}"

Available Devices with FULL Capabilities:
{device_context}

CREATIVE EXAMPLES USING DEVICE CAPABILITIES:
- Instead of basic "flash lights", consider: "Use LED notifications to flash red-blue pattern when door opens"
- Instead of simple on/off, think: "Use smart bulb mode to create sunrise effect over 30 seconds"
- Instead of basic control, consider: "Use auto-off timer to turn lights off after 10 minutes"
- Combine capabilities: "Use LED notifications + smart bulb mode for color-coded door alerts"
- Health-aware: "Prioritize devices with health_score > 80 for reliable automations"

CREATIVE EXAMPLES TO INSPIRE YOU:
- Instead of just "flash lights when door opens", consider: "Flash all four office lights in sequence (left, right, back, front) when front door opens"
- Instead of simple on/off, think: "Flash red for front door opening and blue for back door opening"
- Combine multiple triggers: "Flash lights when BOTH front and garage doors open"
- Add conditions: "Flash lights when door opens, but only after sunset"
- Use different patterns: "Strobe lights rapidly for 3 seconds, then steady blue for 10 seconds"
- Consider device combinations: "Flash lights AND play door chime when front door opens"

Generate 3-4 CREATIVE and DISTINCT automation suggestions. Each suggestion must be UNIQUE and offer a different perspective. Be imaginative and think of creative ways to use the available devices and their capabilities.

Each suggestion should:
1. Use actual device capabilities when available (LED notifications, smart bulb mode, auto-timers, etc.)
2. Have a creative, detailed description with specific details about patterns, colors, sequences
3. Specify the trigger (when it happens) - be specific about conditions
4. Specify the action (what it does) - include patterns, colors, timing details
5. List the devices involved - think of creative combinations
6. Consider device health scores (avoid devices with health_score < 50)
7. Have a confidence score (0.0-1.0) based on available capabilities

Return as JSON array with this structure:
[
  {{
    "description": "Creative, detailed description using specific device capabilities",
    "trigger_summary": "Specific trigger conditions",
    "action_summary": "Detailed action using device capabilities (LED patterns, smart modes, etc.)",
    "devices_involved": ["Device1", "Device2", "Device3"],
    "capabilities_used": ["led_notifications", "smart_bulb_mode", "auto_off_timer"],
    "confidence": 0.85
  }}
]
"""
        return prompt
    
    def build_yaml_generation_prompt(self, suggestion: Dict[str, Any], entities: List[Dict[str, Any]]) -> str:
        """Build prompt for YAML generation with device validation"""
        
        # Build entity validation context
        entity_context = self._build_entity_validation_context(entities)
        
        prompt = f"""
Generate a sophisticated Home Assistant automation YAML configuration that brings this creative suggestion to life.

Suggestion: "{suggestion.get('description', '')}"

Trigger: {suggestion.get('trigger_summary', '')}
Action: {suggestion.get('action_summary', '')}
Devices: {suggestion.get('devices_involved', [])}
Capabilities Used: {suggestion.get('capabilities_used', [])}

Validated Entity IDs (USE ONLY THESE):
{entity_context}

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
   - `template` for dynamic values
   - `condition` for complex triggers
   - `delay` for timing
   - `repeat` for patterns
   - `parallel` for simultaneous actions

Safety Guidelines:
- NEVER disable security systems, alarms, or locks
- Avoid extreme climate changes (keep 60-80°F range)
- Add time or condition constraints for destructive actions (turn_off, close, lock)
- Use reasonable defaults (brightness: 50%, temperature: 70°F)
- Avoid "turn off all" unless explicitly requested
- Add debounce ('for' duration) for frequently-changing sensors

Generate the automation now (respond ONLY with YAML, no other text):"""
        
        return prompt
    
    def _build_device_context(self, entities: List[Dict[str, Any]]) -> str:
        """Build rich device context for AI prompt"""
        
        device_context = ""
        
        for entity in entities:
            if entity.get('extraction_method') == 'device_intelligence':
                # Rich device with capabilities
                capabilities = entity.get('capabilities', [])
                capability_list = [cap['feature'] for cap in capabilities if cap.get('supported')]
                
                device_context += f"""
- {entity['name']} ({entity.get('manufacturer', 'Unknown')} {entity.get('model', 'Unknown')})
  Entity ID: {entity.get('entity_id', 'N/A')}
  Area: {entity.get('area', 'N/A')}
  Current State: {entity.get('state', 'unknown')}
  Health Score: {entity.get('health_score', 'N/A')}
  Integration: {entity.get('integration', 'N/A')}
  Available Capabilities: {', '.join(capability_list) if capability_list else 'Basic on/off'}
  Attributes: {entity.get('attributes', {})}
"""
            else:
                # Basic entity (fallback)
                device_context += f"""
- {entity['name']} ({entity.get('domain', 'unknown')})
  State: {entity.get('state', 'unknown')}
  Note: Basic entity (limited capability data)
"""
        
        return device_context
    
    def _extract_capabilities(self, entities: List[Dict[str, Any]]) -> Set[str]:
        """Extract all available capabilities from entities"""
        
        capabilities = set()
        
        for entity in entities:
            if entity.get('extraction_method') == 'device_intelligence':
                entity_capabilities = entity.get('capabilities', [])
                for cap in entity_capabilities:
                    if cap.get('supported'):
                        capabilities.add(cap['feature'])
        
        return capabilities
    
    def _build_entity_validation_context(self, entities: List[Dict[str, Any]]) -> str:
        """Build context for entity validation in YAML generation"""
        
        entity_context = ""
        
        for entity in entities:
            if entity.get('extraction_method') == 'device_intelligence' and entity.get('entity_id'):
                entity_context += f"- {entity['entity_id']} ({entity['name']})\n"
            elif entity.get('name'):
                entity_context += f"- {entity['name']} (basic entity)\n"
        
        return entity_context
    
    def build_capability_examples(self, capabilities: Set[str]) -> str:
        """Build capability-specific examples"""
        
        if not capabilities:
            return ""
        
        examples = []
        
        if 'led_notifications' in capabilities:
            examples.append("- Use LED notifications to flash red-blue pattern when door opens")
        
        if 'smart_bulb_mode' in capabilities:
            examples.append("- Use smart bulb mode to create sunrise effect over 30 seconds")
        
        if 'auto_off_timer' in capabilities:
            examples.append("- Use auto-off timer to turn lights off after 10 minutes")
        
        if 'power_monitoring' in capabilities:
            examples.append("- Use power monitoring to track energy usage")
        
        if 'scene_control' in capabilities:
            examples.append("- Use scene control for complex lighting sequences")
        
        if examples:
            return f"""
CREATIVE EXAMPLES USING AVAILABLE CAPABILITIES:
{chr(10).join(examples)}
- Combine capabilities: "Use LED notifications + smart bulb mode for color-coded door alerts"
- Health-aware: "Prioritize devices with health_score > 80 for reliable automations"

Available Capabilities: {', '.join(sorted(capabilities))}
"""
        
        return ""

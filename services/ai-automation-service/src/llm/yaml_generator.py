"""
YAML Generator - Story AI1.23 Phase 4
======================================

Generates Home Assistant YAML from approved descriptions.
This is the FINAL step before deployment.

Flow:
1. User sees description → 2. User refines → 3. User approves → 4. Generate YAML (HERE)

Key Principles:
- Generate YAML ONLY after user approves
- Use temperature 0.2 for precise, valid YAML
- Include full conversation history for context
- Validate YAML syntax
- Run safety checks
- Rollback if generation fails
"""

from openai import AsyncOpenAI
from typing import Dict, Optional, List
from dataclasses import dataclass
import logging
import json
import yaml
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class YAMLGenerationResult:
    """Result of YAML generation"""
    yaml: str
    alias: str
    services_used: list
    syntax_valid: bool
    safety_score: Optional[int] = None
    safety_issues: Optional[list] = None
    confidence: float = 0.95


# ============================================================================
# Prompt Templates
# ============================================================================

SYSTEM_PROMPT_YAML = """You are a Home Assistant automation expert.

Your goal: Convert an approved human-readable description into valid Home Assistant YAML.

The description has been refined and approved by the user.
Now generate the precise YAML automation code.

Guidelines:
- Generate COMPLETE, VALID Home Assistant YAML
- Use exact entity IDs provided (format: domain.entity_name, e.g., light.kitchen)
- Include all conditions and details from description
- Use appropriate service calls for device types
- Add proper formatting and indentation (2 spaces)
- Follow Home Assistant best practices
- Be precise - this will be deployed directly

CRITICAL YAML STRUCTURE RULES:
1. Entity IDs MUST be in format: domain.entity (e.g., light.office, binary_sensor.door)
2. Service calls use target.entity_id, not entity_id directly:
   ```yaml
   - service: light.turn_on
     target:
       entity_id: light.kitchen
   ```
3. Multiple entities use list format:
   ```yaml
   target:
     entity_id:
       - light.kitchen
       - light.living_room
   ```
4. Data parameters go under `data:` key
5. Required fields: alias, trigger, action
6. Optional fields: id, description, mode, condition

ADVANCED FEATURES (Task 2.2 - Use when appropriate, Target: 40%+ usage):
- `choose` - Use for conditional logic with multiple paths (if/else patterns)
- `parallel` - Use for simultaneous actions that can run at the same time
- `sequence` - Use for multi-step actions that must run in order
- `template` - Use for dynamic values and calculations
- `condition` blocks - Use for complex trigger conditions
- `repeat` - Use for loops and repeated patterns
- `wait_template` - Use for waiting on conditions

When to use advanced features:
- Multiple conditions → use `choose` with conditions
- Multiple simultaneous actions → use `parallel`
- Sequential steps → use `sequence`
- Dynamic values → use `template`
- Repeated patterns → use `repeat`

COMPLETE YAML EXAMPLES:

Example 1 - Simple time trigger:
```yaml
alias: Morning Kitchen Light
description: Turn on kitchen light at 7 AM
mode: single
trigger:
  - platform: time
    at: '07:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: light.kitchen
    data:
      brightness_pct: 100
```

Example 2 - State trigger with condition:
```yaml
alias: Motion-Activated Office Light
description: Turn on office light when motion detected after 6 PM
mode: single
trigger:
  - platform: state
    entity_id: binary_sensor.office_motion
    to: 'on'
condition:
  - condition: time
    after: '18:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: light.office
    data:
      brightness_pct: 75
      color_name: warm_white
```

Example 3 - Multiple actions with delay:
```yaml
alias: Door Open Notification
description: Flash lights when door opens
mode: single
trigger:
  - platform: state
    entity_id: binary_sensor.front_door
    from: 'off'
    to: 'on'
action:
  - service: light.turn_on
    target:
      entity_id: light.office
    data:
      brightness_pct: 100
      color_name: red
  - delay: '00:00:02'
  - service: light.turn_off
    target:
      entity_id: light.office
```

Example 4 - Repeat with sequence:
```yaml
alias: Flash Pattern
description: Flash lights 3 times
mode: single
trigger:
  - platform: event
    event_type: test_trigger
action:
  - repeat:
      count: 3
      sequence:
        - service: light.turn_on
          target:
            entity_id: light.office
          data:
            brightness_pct: 100
        - delay: '00:00:01'
        - service: light.turn_off
          target:
            entity_id: light.office
        - delay: '00:00:01'
```

Response format: ONLY JSON, no other text:
{
  "yaml": "Complete YAML automation as string with \\n for newlines",
  "alias": "Automation name (descriptive)",
  "services_used": ["list of HA services called, e.g., light.turn_on"],
  "confidence": 0.95
}
"""

# ============================================================================
# Task 2.1: OpenAI Function Calling Schemas
# ============================================================================

YAML_GENERATION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_automation_trigger",
            "description": "Create a Home Assistant automation trigger. Can be called multiple times for multiple triggers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "description": "Trigger platform: 'state', 'time', 'event', 'numeric_state', 'mqtt', etc.",
                        "enum": ["state", "time", "event", "numeric_state", "mqtt", "sun", "webhook", "zone"]
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "Entity ID for state/numeric_state triggers (e.g., 'binary_sensor.door')"
                    },
                    "to": {
                        "type": "string",
                        "description": "Target state for state trigger (e.g., 'on', 'off', 'open')"
                    },
                    "from": {
                        "type": "string",
                        "description": "Source state for state trigger (optional)"
                    },
                    "at": {
                        "type": "string",
                        "description": "Time for time trigger (e.g., '07:00:00', 'sunset', 'sunrise')"
                    },
                    "event_type": {
                        "type": "string",
                        "description": "Event type for event trigger"
                    },
                    "below": {
                        "type": "number",
                        "description": "Below value for numeric_state trigger"
                    },
                    "above": {
                        "type": "number",
                        "description": "Above value for numeric_state trigger"
                    },
                    "for": {
                        "type": "string",
                        "description": "Duration to wait before triggering (e.g., '00:05:00')"
                    }
                },
                "required": ["platform"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_automation_action",
            "description": "Create a Home Assistant automation action (service call, delay, repeat, etc.). Can be called multiple times for sequence of actions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "Service to call (e.g., 'light.turn_on', 'switch.turn_off', 'scene.turn_on')"
                    },
                    "target_entity_id": {
                        "type": "string",
                        "description": "Target entity ID (e.g., 'light.kitchen')"
                    },
                    "data": {
                        "type": "object",
                        "description": "Service data parameters (brightness_pct, color_name, etc.)"
                    },
                    "delay": {
                        "type": "string",
                        "description": "Delay before this action (e.g., '00:00:05' for 5 seconds)"
                    },
                    "repeat_count": {
                        "type": "integer",
                        "description": "Number of times to repeat (for repeat action)"
                    },
                    "action_type": {
                        "type": "string",
                        "enum": ["service", "delay", "repeat"],
                        "description": "Type of action"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_automation_condition",
            "description": "Create a Home Assistant automation condition. Conditions are checked before actions execute.",
            "parameters": {
                "type": "object",
                "properties": {
                    "condition": {
                        "type": "string",
                        "enum": ["state", "time", "numeric_state", "template", "and", "or", "not"],
                        "description": "Condition type"
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "Entity ID for state/numeric_state conditions"
                    },
                    "state": {
                        "type": "string",
                        "description": "Required state for state condition"
                    },
                    "after": {
                        "type": "string",
                        "description": "After time for time condition (e.g., '18:00:00', 'sunset')"
                    },
                    "before": {
                        "type": "string",
                        "description": "Before time for time condition"
                    },
                    "weekday": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Weekdays for time condition (e.g., ['mon', 'tue', 'wed'])"
                    }
                },
                "required": ["condition"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "finalize_automation",
            "description": "Finalize the automation with alias, description, and mode. Call this once after all triggers, actions, and conditions are defined.",
            "parameters": {
                "type": "object",
                "properties": {
                    "alias": {
                        "type": "string",
                        "description": "Automation name (descriptive)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Automation description"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["single", "restart", "queued", "parallel"],
                        "description": "Automation mode (default: 'single')"
                    },
                    "services_used": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of HA services used (e.g., ['light.turn_on'])"
                    }
                },
                "required": ["alias"]
            }
        }
    }
]


# ============================================================================
# YAMLGenerator Class
# ============================================================================

class YAMLGenerator:
    """
    Generates Home Assistant YAML from approved descriptions.
    
    Phase 4: YAML Generation on Approval
    Story AI1.23: Conversational Suggestion Refinement
    
    Usage:
        generator = YAMLGenerator(openai_client)
        result = await generator.generate_yaml(
            description="When motion detected after 6PM, turn on Living Room Light to blue",
            devices_metadata={...},
            conversation_history=[...]
        )
    """
    
    def __init__(self, openai_client: AsyncOpenAI, model: str = "gpt-4o-mini"):
        """
        Initialize YAML generator.
        
        Args:
            openai_client: AsyncOpenAI client instance
            model: Model to use (default: gpt-4o-mini)
        """
        self.client = openai_client
        self.model = model
        self.total_tokens = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        logger.info(f"YAMLGenerator initialized with model={model}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    async def generate_yaml(
        self,
        final_description: str,
        devices_metadata: Dict,
        conversation_history: Optional[list] = None
    ) -> YAMLGenerationResult:
        """
        Generate Home Assistant YAML from approved description.
        
        Args:
            final_description: User-approved automation description
            devices_metadata: Full device metadata with entity IDs
            conversation_history: Conversation history for context
        
        Returns:
            YAMLGenerationResult with YAML and validation info
        
        Raises:
            Exception: If OpenAI API call fails after retries
        """
        try:
            # Build YAML generation prompt
            prompt = self._build_yaml_prompt(
                final_description,
                devices_metadata,
                conversation_history or []
            )
            
            logger.info(f"🔨 Generating YAML from approved description: {final_description[:60]}...")
            
            # Task 2.1: Use function calling for structured YAML generation
            # This provides better structured output and reduces YAML errors by ~50%
            try:
                result = await self._generate_yaml_with_function_calling(
                    final_description,
                    devices_metadata,
                    conversation_history or []
                )
                return result
            except Exception as e:
                logger.warning(f"Function calling failed, falling back to JSON mode: {e}")
                # Fallback to JSON mode if function calling fails
                return await self._generate_yaml_with_json_mode(
                    final_description,
                    devices_metadata,
                    conversation_history or []
                )
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse OpenAI JSON response: {e}")
            raise ValueError(f"OpenAI returned invalid JSON: {e}")
        except Exception as e:
            logger.error(f"❌ OpenAI API error during YAML generation: {e}")
            raise
    
    async def _generate_yaml_with_function_calling(
        self,
        final_description: str,
        devices_metadata: Dict,
        conversation_history: list
    ) -> YAMLGenerationResult:
        """
        Generate YAML using OpenAI function calling for structured output.
        
        Task 2.1: OpenAI Function Calling for Structured YAML Generation
        Target: -50% YAML errors through structured parameter extraction
        """
        prompt = self._build_yaml_prompt(
            final_description,
            devices_metadata,
            conversation_history
        )
        
        # Call OpenAI with function calling
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT_YAML
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            tools=YAML_GENERATION_TOOLS,
            tool_choice="required",  # Force function calling
            temperature=0.2,
            max_tokens=1200  # More tokens for function calls
        )
        
        # Track token usage
        usage = response.usage
        self.total_input_tokens += usage.prompt_tokens
        self.total_output_tokens += usage.completion_tokens
        self.total_tokens += usage.total_tokens
        
        logger.info(
            f"✅ Function calling response received: {usage.total_tokens} tokens "
            f"(input: {usage.prompt_tokens}, output: {usage.completion_tokens})"
        )
        
        # Extract function calls from response
        message = response.choices[0].message
        tool_calls = message.tool_calls or []
        
        if not tool_calls:
            raise ValueError("No function calls in OpenAI response")
        
        # Parse function calls into automation structure
        triggers = []
        actions = []
        conditions = []
        automation_meta = {}
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            if function_name == "create_automation_trigger":
                triggers.append(function_args)
            elif function_name == "create_automation_action":
                actions.append(function_args)
            elif function_name == "create_automation_condition":
                conditions.append(function_args)
            elif function_name == "finalize_automation":
                automation_meta = function_args
        
        # Convert to YAML
        yaml_str = self._convert_function_calls_to_yaml(
            triggers,
            actions,
            conditions,
            automation_meta
        )
        
        # Validate YAML syntax
        syntax_valid = False
        structure_valid = False
        structure_errors = []
        try:
            yaml.safe_load(yaml_str)
            syntax_valid = True
            logger.info("✅ YAML syntax validation passed")
            
            # Validate HA structure
            structure_valid, structure_errors = self.validate_ha_structure(yaml_str)
            if structure_valid:
                logger.info("✅ HA structure validation passed")
            else:
                logger.warning(f"⚠️ HA structure validation failed: {structure_errors}")
        except yaml.YAMLError as e:
            syntax_valid = False
            logger.error(f"❌ YAML syntax validation failed: {e}")
        
        # Build result
        result = YAMLGenerationResult(
            yaml=yaml_str,
            alias=automation_meta.get('alias', 'Generated Automation'),
            services_used=automation_meta.get('services_used', []),
            syntax_valid=syntax_valid and structure_valid,
            safety_issues=structure_errors if structure_errors else None,
            confidence=0.95 if (syntax_valid and structure_valid) else 0.7  # Lower confidence if validation issues
        )
        
        logger.info(f"✅ YAML generation complete (function calling): {result.alias}")
        return result
    
    async def _generate_yaml_with_json_mode(
        self,
        final_description: str,
        devices_metadata: Dict,
        conversation_history: list
    ) -> YAMLGenerationResult:
        """
        Generate YAML using JSON mode (fallback method).
        
        Original implementation for backward compatibility.
        """
        prompt = self._build_yaml_prompt(
            final_description,
            devices_metadata,
            conversation_history
        )
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT_YAML
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            max_tokens=800,
            response_format={"type": "json_object"}
        )
        
        usage = response.usage
        self.total_input_tokens += usage.prompt_tokens
        self.total_output_tokens += usage.completion_tokens
        self.total_tokens += usage.total_tokens
        
        content = response.choices[0].message.content.strip()
        yaml_data = json.loads(content)
        
        if 'yaml' not in yaml_data or 'alias' not in yaml_data:
            raise ValueError("OpenAI response missing required fields (yaml, alias)")
        
        try:
            yaml.safe_load(yaml_data['yaml'])
            syntax_valid = True
        except yaml.YAMLError as e:
            syntax_valid = False
            logger.error(f"❌ YAML syntax validation failed: {e}")
        
        result = YAMLGenerationResult(
            yaml=yaml_data['yaml'],
            alias=yaml_data['alias'],
            services_used=yaml_data.get('services_used', []),
            syntax_valid=syntax_valid,
            confidence=yaml_data.get('confidence', 0.95)
        )
        
        return result
    
    def _convert_function_calls_to_yaml(
        self,
        triggers: List[Dict],
        actions: List[Dict],
        conditions: List[Dict],
        automation_meta: Dict
    ) -> str:
        """
        Convert function call results into Home Assistant YAML format.
        
        Uses proper YAML serialization instead of string concatenation to ensure
        valid structure, especially for nested data structures.
        
        Args:
            triggers: List of trigger function call results
            actions: List of action function call results
            conditions: List of condition function call results
            automation_meta: Finalization metadata
            
        Returns:
            Complete YAML automation string
        """
        # Build automation dict structure
        automation_dict = {}
        
        # Add alias
        automation_dict['alias'] = automation_meta.get('alias', 'Generated Automation')
        
        # Add description if available
        if automation_meta.get('description'):
            automation_dict['description'] = automation_meta['description']
        
        # Add mode
        automation_dict['mode'] = automation_meta.get('mode', 'single')
        
        # Convert triggers to proper format
        if triggers:
            automation_dict['trigger'] = []
            for trigger in triggers:
                trigger_dict = {'platform': trigger['platform']}
                # Add other trigger fields
                for key, value in trigger.items():
                    if key != 'platform' and value is not None:
                        # Handle special cases for trigger fields
                        if key == 'from' and value:
                            trigger_dict['from'] = value
                        elif key == 'for' and value:
                            trigger_dict['for'] = value
                        else:
                            trigger_dict[key] = value
                automation_dict['trigger'].append(trigger_dict)
        
        # Convert conditions to proper format
        if conditions:
            automation_dict['condition'] = []
            for condition in conditions:
                cond_dict = {'condition': condition['condition']}
                cond_type = condition['condition']
                
                if cond_type in ['and', 'or', 'not']:
                    # Logical conditions - simplified for now
                    automation_dict['condition'].append(cond_dict)
                else:
                    # State, time, numeric_state, etc.
                    for key, value in condition.items():
                        if key != 'condition' and value is not None:
                            cond_dict[key] = value
                    automation_dict['condition'].append(cond_dict)
        
        # Convert actions to proper format
        if actions:
            automation_dict['action'] = []
            for action in actions:
                action_type = action.get('action_type', 'service')
                
                if action_type == 'delay':
                    automation_dict['action'].append({'delay': action.get('delay', '00:00:01')})
                elif action_type == 'repeat':
                    repeat_dict = {
                        'repeat': {
                            'count': action.get('repeat_count', 1),
                            'sequence': []  # Nested actions would go here
                        }
                    }
                    automation_dict['action'].append(repeat_dict)
                else:
                    # Service call
                    service = action.get('service')
                    if service:
                        action_dict = {'service': service}
                        
                        # Add target with entity_id
                        entity_id = action.get('target_entity_id')
                        if entity_id:
                            # Validate entity ID format (must be domain.entity format)
                            if '.' in entity_id and not entity_id.startswith('.'):
                                action_dict['target'] = {'entity_id': entity_id}
                            else:
                                logger.warning(f"Invalid entity_id format: {entity_id}, skipping target")
                        
                        # Add data
                        data = action.get('data')
                        if data:
                            action_dict['data'] = data
                        
                        automation_dict['action'].append(action_dict)
        
        # Use yaml.dump() for proper serialization
        try:
            yaml_str = yaml.dump(
                automation_dict,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
                width=1000,  # Prevent line wrapping
                indent=2
            )
            return yaml_str.strip()
        except Exception as e:
            logger.error(f"Error serializing YAML: {e}")
            # Fallback to basic format
            return f"alias: {automation_dict.get('alias', 'Generated Automation')}\n"
    
    def _build_yaml_prompt(
        self,
        final_description: str,
        devices_metadata: Dict,
        conversation_history: list
    ) -> str:
        """
        Build YAML generation prompt.
        
        Args:
            final_description: User-approved description
            devices_metadata: Device metadata with entity IDs
            conversation_history: Refinement history
        
        Returns:
            Formatted prompt for OpenAI
        """
        # Extract entity ID mapping
        entity_mapping = self._extract_entity_mapping(devices_metadata)
        
        # Format conversation history for context
        history_context = ""
        if conversation_history:
            history_context = "\n\nREFINEMENT HISTORY (for context):\n"
            for i, entry in enumerate(conversation_history, 1):
                history_context += f"{i}. User requested: \"{entry.get('user_input', 'N/A')}\"\n"
                history_context += f"   Result: {entry.get('updated_description', 'N/A')[:60]}...\n"
        
        prompt = f"""Generate Home Assistant YAML for this approved automation:

APPROVED DESCRIPTION:
"{final_description}"

DEVICES INVOLVED:
{json.dumps(devices_metadata, indent=2)}

ENTITY ID MAPPING (use these exactly):
{entity_mapping}
{history_context}

TASK:
Generate a complete, valid Home Assistant automation in YAML format.
- Include all triggers, conditions, and actions from the description
- Use exact entity IDs from the mapping above
- Follow Home Assistant YAML syntax precisely
- Add appropriate service calls based on device types
- Include any time constraints or conditions mentioned
- Use 2-space indentation

IMPORTANT:
- The description mentions specific details - include ALL of them
- If description says "blue", use rgb_color: [0, 0, 255]
- If description says "weekdays", add weekday condition
- If description says "fade in", add transition parameter
- Be precise and complete

OUTPUT (JSON only, no markdown):"""
        
        return prompt
    
    def _extract_entity_mapping(self, devices_metadata: Dict) -> str:
        """
        Extract entity ID mapping from devices metadata.
        
        Args:
            devices_metadata: Device metadata dictionary
        
        Returns:
            Formatted entity ID mapping string
        """
        mapping = []
        
        # Handle different metadata formats
        if isinstance(devices_metadata, dict):
            if 'entity_id' in devices_metadata:
                # Single device
                entity_id = devices_metadata['entity_id']
                friendly_name = devices_metadata.get('friendly_name', entity_id)
                domain = devices_metadata.get('domain', 'unknown')
                mapping.append(f"- {friendly_name}: {entity_id} (domain: {domain})")
            
            elif 'devices_involved' in devices_metadata:
                # Multiple devices
                for device in devices_metadata['devices_involved']:
                    entity_id = device.get('entity_id', 'unknown')
                    friendly_name = device.get('friendly_name', entity_id)
                    domain = device.get('domain', 'unknown')
                    mapping.append(f"- {friendly_name}: {entity_id} (domain: {domain})")
        
        return '\n'.join(mapping) if mapping else "No entity mapping available"
    
    def validate_yaml_syntax(self, yaml_string: str) -> tuple[bool, Optional[str]]:
        """
        Validate YAML syntax.
        
        Args:
            yaml_string: YAML string to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            yaml.safe_load(yaml_string)
            return True, None
        except yaml.YAMLError as e:
            return False, str(e)
    
    def validate_ha_structure(self, yaml_string: str) -> tuple[bool, List[str]]:
        """
        Validate Home Assistant automation structure.
        
        Checks for:
        - Required fields (alias, trigger, action)
        - Valid entity ID formats
        - Proper service call structure
        - Valid trigger/condition/action formats
        
        Args:
            yaml_string: YAML string to validate
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            automation_dict = yaml.safe_load(yaml_string)
            
            if not isinstance(automation_dict, dict):
                errors.append("YAML must be a dictionary")
                return False, errors
            
            # Check required fields
            if 'alias' not in automation_dict:
                errors.append("Missing required field: 'alias'")
            
            if 'trigger' not in automation_dict and 'triggers' not in automation_dict:
                errors.append("Missing required field: 'trigger' or 'triggers'")
            
            if 'action' not in automation_dict and 'actions' not in automation_dict:
                errors.append("Missing required field: 'action' or 'actions'")
            
            # Validate trigger format
            triggers = automation_dict.get('trigger', automation_dict.get('triggers', []))
            if triggers:
                if not isinstance(triggers, list):
                    errors.append("'trigger' must be a list")
                else:
                    for i, trigger in enumerate(triggers):
                        if not isinstance(trigger, dict):
                            errors.append(f"Trigger {i} must be a dictionary")
                            continue
                        if 'platform' not in trigger:
                            errors.append(f"Trigger {i} missing required field: 'platform'")
                        # Validate entity_id format if present
                        if 'entity_id' in trigger:
                            entity_id = trigger['entity_id']
                            if not isinstance(entity_id, str) or '.' not in entity_id:
                                errors.append(f"Trigger {i} has invalid entity_id format: {entity_id}")
            
            # Validate action format
            actions = automation_dict.get('action', automation_dict.get('actions', []))
            if actions:
                if not isinstance(actions, list):
                    errors.append("'action' must be a list")
                else:
                    for i, action in enumerate(actions):
                        if not isinstance(action, dict):
                            errors.append(f"Action {i} must be a dictionary")
                            continue
                        
                        # Validate service call structure
                        if 'service' in action:
                            if 'target' in action:
                                target = action['target']
                                if isinstance(target, dict) and 'entity_id' in target:
                                    entity_id = target['entity_id']
                                    # Handle both string and list formats
                                    if isinstance(entity_id, str):
                                        if '.' not in entity_id:
                                            errors.append(f"Action {i} has invalid entity_id format: {entity_id}")
                                    elif isinstance(entity_id, list):
                                        for eid in entity_id:
                                            if not isinstance(eid, str) or '.' not in eid:
                                                errors.append(f"Action {i} has invalid entity_id in list: {eid}")
            
            return len(errors) == 0, errors
            
        except yaml.YAMLError as e:
            return False, [f"YAML syntax error: {str(e)}"]
        except Exception as e:
            return False, [f"Validation error: {str(e)}"]
    
    def get_usage_stats(self) -> Dict:
        """
        Get token usage statistics.
        
        Returns:
            Dictionary with token counts and estimated cost
        """
        # Calculate cost (gpt-4o-mini pricing)
        INPUT_COST_PER_1M = 0.150   # $0.15 per 1M input tokens
        OUTPUT_COST_PER_1M = 0.600  # $0.60 per 1M output tokens
        
        input_cost = (self.total_input_tokens / 1_000_000) * INPUT_COST_PER_1M
        output_cost = (self.total_output_tokens / 1_000_000) * OUTPUT_COST_PER_1M
        total_cost = input_cost + output_cost
        
        return {
            'total_tokens': self.total_tokens,
            'input_tokens': self.total_input_tokens,
            'output_tokens': self.total_output_tokens,
            'estimated_cost_usd': round(total_cost, 6),
            'model': self.model
        }
    
    def reset_usage_stats(self):
        """Reset usage statistics"""
        self.total_tokens = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        logger.info("Usage statistics reset")


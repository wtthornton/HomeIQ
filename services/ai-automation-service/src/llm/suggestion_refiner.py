"""
Suggestion Refiner - Story AI1.23 Phase 3
==========================================

Refines automation descriptions based on user's natural language edits.
This is the conversational editing step.

Flow:
1. User sees description → 2. User edits ("Make it blue") → 3. Refine (HERE) → 4. Show updated description

Key Principles:
- Update descriptions with user's natural language input
- Validate against device capabilities
- Track conversation history
- Return JSON with validation results
- Temperature 0.5 for balanced consistency
"""

from openai import AsyncOpenAI
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging
import json
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ValidationResult:
    """Result of feasibility validation"""
    ok: bool
    messages: List[str]
    warnings: List[str]
    alternatives: List[str]


@dataclass
class RefinementResult:
    """Result of description refinement"""
    updated_description: str
    changes_made: List[str]
    validation: ValidationResult
    clarification_needed: Optional[str] = None
    history_entry: Optional[Dict] = None


# ============================================================================
# Prompt Templates
# ============================================================================

SYSTEM_PROMPT_REFINE = """You are a home automation expert helping users refine automation descriptions.

Your goal: Update the automation description based on the user's natural language edits.
DO NOT generate YAML yet. Only update the description.

Rules:
1. Preserve existing details unless user changes them
2. Add new requirements naturally into the description
3. Use device friendly names, not entity IDs
4. Check if requested changes are possible given device capabilities
5. If something can't be done, explain why and suggest alternatives
6. Keep descriptions to 1-2 sentences

Response format: ONLY JSON, no other text:
{
  "updated_description": "New description with user's changes",
  "changes_made": ["List of what changed"],
  "validation": {
    "ok": true/false,
    "messages": ["Validation messages"],
    "warnings": ["Any issues with the request"],
    "alternatives": ["Suggestions if request isn't possible"]
  },
  "clarification_needed": null or "Question if request is ambiguous"
}

Examples:
User says: "Make it blue"
Response: {
  "updated_description": "...turn on the Kitchen Light to blue",
  "changes_made": ["Added color: blue (RGB supported ✓)"],
  "validation": {"ok": true, "messages": ["✓ Device supports RGB color"]},
  "clarification_needed": null
}

User says: "Make it blue" (but device doesn't support RGB)
Response: {
  "updated_description": "...turn on the Kitchen Light to 50% brightness",
  "changes_made": [],
  "validation": {
    "ok": false,
    "warnings": ["⚠️ Device does not support RGB color (brightness only)"],
    "alternatives": ["Try: 'Set to warm white' or 'Adjust brightness to 75%'"]
  },
  "clarification_needed": "This light doesn't support colors. Would you like to adjust brightness or color temperature instead?"
}
"""


# ============================================================================
# SuggestionRefiner Class
# ============================================================================

class SuggestionRefiner:
    """
    Refines automation descriptions based on user's natural language input.
    
    Phase 3: Conversational Refinement
    Story AI1.23: Conversational Suggestion Refinement
    
    Usage:
        refiner = SuggestionRefiner(openai_client, data_api_client)
        result = await refiner.refine_description(
            current_description="When motion detected, turn on light",
            user_input="Make it blue and only on weekdays",
            device_capabilities={...}
        )
    """
    
    def __init__(self, openai_client: AsyncOpenAI, model: str = "gpt-4o-mini"):
        """
        Initialize suggestion refiner.
        
        Args:
            openai_client: AsyncOpenAI client instance
            model: Model to use (default: gpt-4o-mini)
        """
        self.client = openai_client
        self.model = model
        self.total_tokens = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        logger.info(f"SuggestionRefiner initialized with model={model}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    async def refine_description(
        self,
        current_description: str,
        user_input: str,
        device_capabilities: Dict,
        conversation_history: Optional[List[Dict]] = None
    ) -> RefinementResult:
        """
        Refine automation description with user's natural language input.
        
        Args:
            current_description: Current automation description
            user_input: User's requested changes (e.g., "Make it blue and only on weekdays")
            device_capabilities: Capabilities of devices involved
            conversation_history: Previous edits (for context)
        
        Returns:
            RefinementResult with updated description and validation
        
        Raises:
            Exception: If OpenAI API call fails after retries
        """
        try:
            # Build refinement prompt
            prompt = self._build_refinement_prompt(
                current_description,
                user_input,
                device_capabilities,
                conversation_history or []
            )
            
            logger.info(f"✏️  Refining description: '{user_input}'")
            
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT_REFINE
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.5,  # More consistent for refinement
                max_completion_tokens=400,   # Longer for validation messages (use max_completion_tokens for newer models)
                response_format={"type": "json_object"}  # Force JSON
            )
            
            # Track token usage
            usage = response.usage
            self.total_input_tokens += usage.prompt_tokens
            self.total_output_tokens += usage.completion_tokens
            self.total_tokens += usage.total_tokens
            
            logger.info(
                f"✅ Refinement processed: {usage.total_tokens} tokens "
                f"(input: {usage.prompt_tokens}, output: {usage.completion_tokens})"
            )
            
            # Parse JSON response
            content = response.choices[0].message.content.strip()
            result_data = json.loads(content)
            
            # Build validation result
            validation = ValidationResult(
                ok=result_data['validation']['ok'],
                messages=result_data['validation'].get('messages', []),
                warnings=result_data['validation'].get('warnings', []),
                alternatives=result_data['validation'].get('alternatives', [])
            )
            
            # Build history entry for this refinement
            history_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "user_input": user_input,
                "updated_description": result_data['updated_description'],
                "validation_result": {
                    "ok": validation.ok,
                    "messages": validation.messages,
                    "warnings": validation.warnings
                },
                "changes_made": result_data['changes_made']
            }
            
            result = RefinementResult(
                updated_description=result_data['updated_description'],
                changes_made=result_data['changes_made'],
                validation=validation,
                clarification_needed=result_data.get('clarification_needed'),
                history_entry=history_entry
            )
            
            logger.info(f"✅ Refinement complete: {len(result.changes_made)} changes")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse OpenAI JSON response: {e}")
            raise ValueError(f"OpenAI returned invalid JSON: {e}")
        except Exception as e:
            logger.error(f"❌ OpenAI API error during refinement: {e}")
            raise
    
    def _build_refinement_prompt(
        self,
        current_description: str,
        user_input: str,
        device_capabilities: Dict,
        conversation_history: List[Dict]
    ) -> str:
        """
        Build refinement prompt with full context.
        
        Args:
            current_description: Current automation description
            user_input: User's requested changes
            device_capabilities: Device capability information
            conversation_history: Previous edits
        
        Returns:
            Formatted prompt for OpenAI
        """
        # Format device capabilities for prompt
        capabilities_summary = self._format_capabilities_for_prompt(device_capabilities)
        
        # Format conversation history if exists
        history_summary = ""
        if conversation_history:
            history_summary = "\n\nPREVIOUS EDITS:\n"
            for i, entry in enumerate(conversation_history[-3:], 1):  # Last 3 edits
                history_summary += f"{i}. User said: \"{entry['user_input']}\"\n"
                history_summary += f"   Result: {entry['updated_description'][:60]}...\n"
        
        prompt = f"""The user wants to modify this automation:

CURRENT DESCRIPTION:
"{current_description}"

USER'S REQUESTED CHANGES:
"{user_input}"

DEVICE CAPABILITIES:
{capabilities_summary}
{history_summary}

TASK:
1. Check if the user's request is possible given device capabilities
2. If possible: Update the description to incorporate their changes naturally
3. If not possible: Explain why and suggest alternatives
4. If ambiguous: Ask for clarification
5. Keep the description to 1-2 sentences

IMPORTANT:
- Preserve details the user didn't mention changing
- Use device friendly names, not entity IDs
- Be specific about what changed
- Check capabilities carefully before adding features

OUTPUT (JSON only, no markdown):"""
        
        return prompt
    
    def _format_capabilities_for_prompt(self, device_capabilities: Dict) -> str:
        """
        Format device capabilities for the prompt.
        
        Args:
            device_capabilities: Capability dictionary from data-api
        
        Returns:
            Formatted string for prompt
        """
        if not device_capabilities:
            return "No capability information available"
        
        # Extract key info
        entity_id = device_capabilities.get('entity_id', 'unknown')
        friendly_name = device_capabilities.get('friendly_name', entity_id)
        domain = device_capabilities.get('domain', 'unknown')
        features = device_capabilities.get('supported_features', {})
        friendly_caps = device_capabilities.get('friendly_capabilities', [])
        
        # Build summary
        summary = f"Device: {friendly_name} ({entity_id})\n"
        summary += f"Type: {domain}\n"
        summary += f"Supported Features:\n"
        
        if friendly_caps:
            for cap in friendly_caps:
                summary += f"  ✓ {cap}\n"
        else:
            summary += "  • Basic on/off control\n"
        
        # Add specific capabilities  
        if features:
            summary += f"\nAvailable capabilities:\n"
            for feature, is_available in features.items():
                if is_available:
                    summary += f"  ✓ {feature}\n"
        
        return summary
    
    async def validate_feasibility(
        self,
        requested_change: str,
        device_capabilities: Dict
    ) -> ValidationResult:
        """
        Validate if requested change is feasible given device capabilities.
        
        This is a fast pre-check before calling OpenAI.
        Helps reduce unnecessary API calls.
        
        Args:
            requested_change: User's requested change (e.g., "Make it blue")
            device_capabilities: Device capability information
        
        Returns:
            ValidationResult indicating if change is feasible
        """
        # Extract supported features
        features = device_capabilities.get('supported_features', {})
        domain = device_capabilities.get('domain', 'unknown')
        device_name = device_capabilities.get('friendly_name', 'device')
        
        messages = []
        warnings = []
        alternatives = []
        ok = True
        
        # Check for common requests
        request_lower = requested_change.lower()
        
        # Color-related requests
        if any(color in request_lower for color in ['blue', 'red', 'green', 'purple', 'color', 'rgb']):
            if not features.get('rgb_color'):
                ok = False
                warnings.append(f"⚠️ {device_name} does not support RGB color changes")
                if features.get('color_temp'):
                    alternatives.append("Try: 'Set to warm white' or 'Set to cool white'")
                else:
                    alternatives.append("Try: 'Set brightness to 75%' or 'Turn on brighter'")
            else:
                messages.append(f"✓ {device_name} supports RGB color")
        
        # Brightness requests
        if any(word in request_lower for word in ['bright', 'dim', 'brightness', '%', 'percent']):
            if not features.get('brightness'):
                ok = False
                warnings.append(f"⚠️ {device_name} does not support brightness control (on/off only)")
                alternatives.append("Try: 'Turn on earlier' or 'Add a delay'")
            else:
                messages.append(f"✓ {device_name} supports brightness control")
        
        # Temperature requests (climate devices)
        if domain == 'climate':
            if any(word in request_lower for word in ['temperature', 'degrees', '°', 'warmer', 'cooler']):
                if features.get('temperature'):
                    messages.append(f"✓ {device_name} supports temperature control")
                else:
                    ok = False
                    warnings.append(f"⚠️ {device_name} does not support temperature control")
        
        # Time/schedule requests (always feasible)
        if any(word in request_lower for word in ['weekday', 'weekend', 'monday', 'only on', 'except', 'between']):
            messages.append("✓ Time/schedule conditions can be added")
        
        # Transition/fade requests
        if any(word in request_lower for word in ['fade', 'transition', 'slowly', 'gradually']):
            if not features.get('transition'):
                warnings.append(f"⚠️ {device_name} may not support smooth transitions")
                alternatives.append("Note: Transition may appear instant on some devices")
            else:
                messages.append(f"✓ {device_name} supports smooth transitions")
        
        return ValidationResult(
            ok=ok,
            messages=messages,
            warnings=warnings,
            alternatives=alternatives
        )
    
    def _build_refinement_prompt(
        self,
        current_description: str,
        user_input: str,
        device_capabilities: Dict,
        conversation_history: List[Dict]
    ) -> str:
        """
        Build refinement prompt with full context.
        
        Args:
            current_description: Current automation description
            user_input: User's requested changes
            device_capabilities: Device capability information
            conversation_history: Previous edits
        
        Returns:
            Formatted prompt for OpenAI
        """
        # Format device capabilities for prompt
        capabilities_summary = self._format_capabilities_for_prompt(device_capabilities)
        
        # Format conversation history if exists
        history_summary = ""
        if conversation_history:
            history_summary = "\n\nPREVIOUS EDITS:\n"
            for i, entry in enumerate(conversation_history[-3:], 1):  # Last 3 edits
                history_summary += f"{i}. User said: \"{entry['user_input']}\"\n"
                history_summary += f"   Result: {entry['updated_description'][:60]}...\n"
        
        prompt = f"""The user wants to modify this automation:

CURRENT DESCRIPTION:
"{current_description}"

USER'S REQUESTED CHANGES:
"{user_input}"

DEVICE CAPABILITIES:
{capabilities_summary}
{history_summary}

TASK:
1. Check if the user's request is possible given device capabilities
2. If possible: Update the description to incorporate their changes naturally
3. If not possible: Explain why and suggest alternatives
4. If ambiguous: Ask for clarification
5. Keep the description to 1-2 sentences

IMPORTANT:
- Preserve details the user didn't mention changing
- Use device friendly names, not entity IDs
- Be specific about what changed
- Check capabilities carefully before adding features

OUTPUT (JSON only, no markdown):"""
        
        return prompt
    
    def _format_capabilities_for_prompt(self, device_capabilities: Dict) -> str:
        """
        Format device capabilities for the prompt.
        
        Args:
            device_capabilities: Capability dictionary from data-api
        
        Returns:
            Formatted string for prompt
        """
        if not device_capabilities:
            return "No capability information available"
        
        # Extract key info
        entity_id = device_capabilities.get('entity_id', 'unknown')
        friendly_name = device_capabilities.get('friendly_name', entity_id)
        domain = device_capabilities.get('domain', 'unknown')
        features = device_capabilities.get('supported_features', {})
        friendly_caps = device_capabilities.get('friendly_capabilities', [])
        
        # Build summary
        summary = f"Device: {friendly_name} ({entity_id})\n"
        summary += f"Type: {domain}\n"
        summary += f"Supported Features:\n"
        
        if friendly_caps:
            for cap in friendly_caps:
                summary += f"  ✓ {cap}\n"
        else:
            summary += "  • Basic on/off control\n"
        
        # Add specific capabilities
        if features:
            summary += f"\nAvailable capabilities:\n"
            for feature, is_available in features.items():
                if is_available:
                    summary += f"  ✓ {feature}\n"
        
        return summary
    
    def get_usage_stats(self) -> Dict:
        """
        Get token usage statistics.
        
        Returns:
            Dictionary with token counts and estimated cost
        """
        # Use CostTracker for consistent cost calculation
        from .cost_tracker import CostTracker
        
        total_cost = CostTracker.calculate_cost(
            self.total_input_tokens,
            self.total_output_tokens,
            model=self.model
        )
        
        return {
            'total_tokens': self.total_tokens,
            'input_tokens': self.total_input_tokens,
            'output_tokens': self.total_output_tokens,
            'estimated_cost_usd': round(total_cost, 6),
            'total_cost_usd': round(total_cost, 6),
            'model': self.model
        }
    
    def reset_usage_stats(self):
        """Reset usage statistics"""
        self.total_tokens = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        logger.info("Usage statistics reset")


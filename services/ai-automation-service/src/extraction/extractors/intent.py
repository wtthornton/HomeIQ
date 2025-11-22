"""
Intent Extractor (2025)

The "Brain" of the pipeline. Uses an LLM (OpenAI/Local) to parse natural language
into structured intent, utilizing the context gathered by previous extractors.
"""

import logging
import json
from typing import Any
from ..models import AutomationContext, TriggerContext, ActionContext, TemporalContext
from .base_extractor import BaseExtractor

logger = logging.getLogger(__name__)

class IntentExtractor(BaseExtractor):
    """
    Uses an LLM to extract:
    - Triggers (Events)
    - Actions (Commands)
    - Temporal Constraints (Time)
    - Behavioral Mode
    
    It receives the filtered list of candidate devices/areas from previous steps
    to help ground its predictions (RAG-lite).
    """

    def __init__(self, openai_client: Any):
        super().__init__()
        self.openai_client = openai_client
        self.model_name = "gpt-4o-mini" # or config

    def _build_system_prompt(self, context: AutomationContext) -> str:
        """Construct the prompt with context-aware grounding."""
        
        # Grounding Data
        available_areas = ", ".join(context.spatial.areas) if context.spatial.areas else "None detected"
        candidate_devices = ", ".join(context.devices.action_device_names) if context.devices.action_device_names else "None detected"
        
        prompt = f"""You are an expert Home Assistant Automation Architect.
Your goal is to extract structured automation intent from a user query.

CONTEXT:
- Identified Areas: {available_areas}
- Candidate Devices: {candidate_devices}

INSTRUCTIONS:
1. Analyze the User Query.
2. Extract Triggers (what starts it), Actions (what happens), and Time constraints.
3. Map fuzzy concepts to standard Home Assistant types (e.g. "motion" -> trigger_type="state", device_class="motion").
4. Return STRICT JSON matching the schema below.

OUTPUT SCHEMA:
{{
  "triggers": [
    {{ "trigger_type": "state|time|zone|event", "raw_condition": "text", "platform": "state", "to_state": "on|off|home", "attribute": "optional" }}
  ],
  "actions": [
    {{ "intent_type": "turn_on|turn_off|toggle", "service": "domain.service", "parameters": {{ "key": "value" }} }}
  ],
  "temporal": {{
    "time_references": ["7 AM"],
    "schedules": [],
    "durations": [],
    "delays": []
  }},
  "behavioral": {{
    "mode": "single",
    "confidence": 0.9,
    "rationale": "Reasoning..."
  }}
}}
"""
        return prompt

    async def extract(self, query: str, context: AutomationContext) -> AutomationContext:
        """
        Call LLM to structure the intent.
        """
        if not self.openai_client:
            logger.warning("OpenAI client missing for IntentExtractor")
            return context

        system_prompt = self._build_system_prompt(context)
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                response_format={"type": "json_object"},
                temperature=0.1 # Deterministic
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            # Map JSON back to Pydantic Models
            # Triggers
            for t in data.get("triggers", []):
                context.triggers.append(TriggerContext(**t))
                
            # Actions
            for a in data.get("actions", []):
                context.actions.append(ActionContext(**a))
                
            # Temporal
            temp = data.get("temporal", {})
            context.temporal.time_references = temp.get("time_references", [])
            context.temporal.schedules = temp.get("schedules", [])
            context.temporal.durations = temp.get("durations", [])
            context.temporal.delays = temp.get("delays", [])
            
            # Behavioral
            beh = data.get("behavioral", {})
            context.behavioral.mode = beh.get("mode", "single")
            context.behavioral.confidence = beh.get("confidence", 0.0)
            context.behavioral.rationale = beh.get("rationale", "")
            
            logger.info(f"Intent extraction successful. Rationale: {context.behavioral.rationale}")
            
        except Exception as e:
            logger.error(f"Intent extraction failed: {e}")
            
        return context

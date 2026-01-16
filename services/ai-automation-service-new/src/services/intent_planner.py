"""
Intent Planner Service

Hybrid Flow Implementation: Converts user intent to structured plan (template_id + parameters)
LLM outputs structured plan, NEVER YAML directly.
"""

import json
import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.data_api_client import DataAPIClient
from ..clients.openai_client import OpenAIClient
from ..database.models import Plan
from ..templates.template_library import TemplateLibrary

logger = logging.getLogger(__name__)


class IntentPlanner:
    """
    Service for planning automations from user intent.
    
    Converts natural language requests into structured plans (template_id + parameters).
    LLM selects appropriate template and fills in parameters.
    """
    
    def __init__(
        self,
        openai_client: OpenAIClient,
        template_library: TemplateLibrary,
        data_api_client: DataAPIClient | None = None
    ):
        """
        Initialize intent planner.
        
        Args:
            openai_client: OpenAI client for LLM calls
            template_library: Template library for template selection
            data_api_client: Optional Data API client for context
        """
        self.openai_client = openai_client
        self.template_library = template_library
        self.data_api_client = data_api_client
    
    async def create_plan(
        self,
        user_text: str,
        conversation_id: str | None = None,
        context: dict[str, Any] | None = None,
        db: AsyncSession | None = None
    ) -> dict[str, Any]:
        """
        Create automation plan from user intent.
        
        Args:
            user_text: User's natural language request
            conversation_id: Optional conversation ID for tracking
            context: Optional context (selected devices, room, timezone, etc.)
            db: Optional database session for storing plan
        
        Returns:
            Plan dictionary with plan_id, template_id, parameters, confidence, etc.
        """
        # Get available templates for LLM selection
        available_templates = self.template_library.list_templates()
        
        # Build prompt for template selection
        template_descriptions = []
        for template_info in available_templates:
            template = self.template_library.get_template(
                template_info["template_id"],
                template_info["version"]
            )
            if template:
                template_descriptions.append({
                    "template_id": template.template_id,
                    "version": template.version,
                    "description": template.description,
                    "required_capabilities": template.required_capabilities.model_dump(),
                    "parameter_schema": {
                        param_name: {
                            "type": param.type.value,
                            "required": param.required,
                            "description": param.description,
                            "enum": param.enum,
                            "default": param.default
                        }
                        for param_name, param in template.parameter_schema.items()
                    }
                })
        
        # Build system prompt for template selection
        system_prompt = f"""You are an automation planning assistant. Your job is to select the best template and fill in parameters based on user requests.

Available Templates:
{json.dumps(template_descriptions, indent=2)}

Rules:
1. Select the template_id that best matches the user's intent
2. Fill in parameters based on user text and context
3. Set confidence score (0.0-1.0) based on how well the template matches
4. If clarification is needed, add questions to clarifications_needed array
5. NEVER output YAML - only structured plan with template_id and parameters
6. Set safety_class based on devices involved (low/medium/high/critical)

Output Format (JSON):
{{
  "template_id": "room_entry_light_on",
  "template_version": 1,
  "parameters": {{
    "room_type": "office",
    "brightness_pct": 100,
    "time_window": {{"after": "08:00", "before": "18:00"}}
  }},
  "confidence": 0.92,
  "clarifications_needed": [],
  "safety_class": "low",
  "explanation": "Office entry detected via presence; user wants lights on during work hours."
}}"""
        
        # Build user prompt with context
        user_prompt = f"User request: {user_text}"
        if context:
            user_prompt += f"\n\nContext: {json.dumps(context, indent=2)}"
        
        # Call LLM with structured output
        try:
            if not self.openai_client.client:
                raise ValueError("OpenAI client not initialized")
            
            response = await self.openai_client.client.chat.completions.create(
                model=self.openai_client.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},  # Force JSON output
                temperature=0.3  # Lower temperature for more consistent template selection
            )
            
            plan_data = json.loads(response.choices[0].message.content)
            
            # Validate template exists
            template = self.template_library.get_template(
                plan_data["template_id"],
                plan_data.get("template_version")
            )
            if not template:
                raise ValueError(f"Template {plan_data['template_id']} not found")
            
            # Generate plan_id
            plan_id = f"p_{uuid.uuid4().hex[:8]}"
            
            # Create plan object
            plan = Plan(
                plan_id=plan_id,
                conversation_id=conversation_id,
                template_id=plan_data["template_id"],
                template_version=plan_data.get("template_version", 1),
                parameters=plan_data["parameters"],
                confidence=plan_data.get("confidence", 0.5),
                clarifications_needed=plan_data.get("clarifications_needed", []),
                safety_class=plan_data.get("safety_class", "low"),
                explanation=plan_data.get("explanation")
            )
            
            # Store in database if session provided
            if db:
                db.add(plan)
                await db.commit()
                await db.refresh(plan)
            
            logger.info(
                f"Created plan {plan_id}: template={plan_data['template_id']}, "
                f"confidence={plan_data.get('confidence', 0.0):.2f}"
            )
            
            return {
                "plan_id": plan_id,
                "intent_type": "automation_request",
                "template_id": plan_data["template_id"],
                "template_version": plan_data.get("template_version", 1),
                "parameters": plan_data["parameters"],
                "confidence": plan_data.get("confidence", 0.5),
                "clarifications_needed": plan_data.get("clarifications_needed", []),
                "safety_class": plan_data.get("safety_class", "low"),
                "promotion_recommended": plan_data.get("confidence", 0.5) >= 0.8,
                "explanation": plan_data.get("explanation", "")
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise ValueError(f"LLM returned invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Failed to create plan: {e}", exc_info=True)
            raise

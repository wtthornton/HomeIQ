"""
Hybrid Flow Client

Client for calling Hybrid Flow endpoints in ai-automation-service-new.
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class HybridFlowClient:
    """
    Client for Hybrid Flow API endpoints.
    
    Handles:
    - POST /automation/plan - Create plan from user intent
    - POST /automation/validate - Validate plan
    - POST /automation/compile - Compile plan to YAML
    - POST /automation/deploy - Deploy compiled artifact
    """
    
    def __init__(self, base_url: str, api_key: str | None = None):
        """
        Initialize hybrid flow client.
        
        Args:
            base_url: Base URL for ai-automation-service-new
            api_key: Optional API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"X-HomeIQ-API-Key": api_key} if api_key else {}
        )
    
    async def create_plan(
        self,
        user_text: str,
        conversation_id: str | None = None,
        context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Create automation plan from user intent.
        
        Args:
            user_text: User's natural language request
            conversation_id: Optional conversation ID
            context: Optional context (devices, room, etc.)
        
        Returns:
            Plan dictionary with plan_id, template_id, parameters, etc.
        """
        url = f"{self.base_url}/automation/plan"
        
        response = await self.client.post(
            url,
            json={
                "conversation_id": conversation_id,
                "user_text": user_text,
                "context": context or {}
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def validate_plan(
        self,
        plan_id: str,
        template_id: str,
        template_version: int,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Validate automation plan.
        
        Args:
            plan_id: Plan identifier
            template_id: Template identifier
            template_version: Template version
            parameters: Template parameters
        
        Returns:
            Validation result
        """
        url = f"{self.base_url}/automation/validate"
        
        response = await self.client.post(
            url,
            json={
                "plan_id": plan_id,
                "template_id": template_id,
                "template_version": template_version,
                "parameters": parameters
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def compile_plan(
        self,
        plan_id: str,
        template_id: str,
        template_version: int,
        parameters: dict[str, Any],
        resolved_context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Compile plan to YAML.
        
        Args:
            plan_id: Plan identifier
            template_id: Template identifier
            template_version: Template version
            parameters: Template parameters
            resolved_context: Resolved context from validator
        
        Returns:
            Compiled artifact with yaml, human_summary, etc.
        """
        url = f"{self.base_url}/automation/compile"
        
        response = await self.client.post(
            url,
            json={
                "plan_id": plan_id,
                "template_id": template_id,
                "template_version": template_version,
                "parameters": parameters,
                "resolved_context": resolved_context
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def deploy_compiled(
        self,
        compiled_id: str,
        approved_by: str | None = None,
        ui_source: str = "ha-ai-agent"
    ) -> dict[str, Any]:
        """
        Deploy compiled automation to Home Assistant.
        
        Args:
            compiled_id: Compiled artifact identifier
            approved_by: User/API key who approved
            ui_source: UI source identifier
        
        Returns:
            Deployment result
        """
        url = f"{self.base_url}/api/deploy/automation/deploy"
        
        response = await self.client.post(
            url,
            json={
                "compiled_id": compiled_id,
                "approved_by": approved_by,
                "ui_source": ui_source,
                "audit_data": {
                    "source": "ha-ai-agent-service",
                    "ui_source": ui_source
                }
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

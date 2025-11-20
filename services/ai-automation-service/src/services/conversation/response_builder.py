"""
Response Builder

Builds structured responses with response_type.
Consolidates response formatting logic.

Created: Phase 2 - Core Service Refactoring
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ResponseType(str, Enum):
    """Types of conversation responses"""
    AUTOMATION_GENERATED = "automation_generated"
    CLARIFICATION_NEEDED = "clarification_needed"
    ACTION_DONE = "action_done"
    INFORMATION_PROVIDED = "information_provided"
    ERROR = "error"
    NO_INTENT_MATCH = "no_intent_match"


class ResponseBuilder:
    """
    Builds structured responses for conversation turns.
    
    Creates responses with:
    - Response type
    - Content
    - Suggestions (if applicable)
    - Clarification questions (if applicable)
    - Confidence scores
    - Next actions
    """

    def __init__(self):
        """Initialize response builder"""
        logger.info("ResponseBuilder initialized")

    def build_response(
        self,
        response_type: ResponseType,
        content: str,
        conversation_id: str,
        turn_number: int,
        suggestions: list[dict[str, Any]] | None = None,
        clarification_questions: list[dict[str, Any]] | None = None,
        confidence: float | None = None,
        processing_time_ms: int = 0,
        next_actions: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Build structured response.
        
        Args:
            response_type: Type of response
            content: Response content text
            conversation_id: Conversation ID
            turn_number: Turn number
            suggestions: Optional automation suggestions
            clarification_questions: Optional clarification questions
            confidence: Optional confidence score
            processing_time_ms: Processing time in milliseconds
            next_actions: Optional suggested next actions
        
        Returns:
            Structured response dictionary
        """
        response = {
            "conversation_id": conversation_id,
            "turn_number": turn_number,
            "response_type": response_type.value,
            "content": content,
            "processing_time_ms": processing_time_ms,
            "created_at": datetime.utcnow().isoformat()
        }

        if suggestions:
            response["suggestions"] = suggestions

        if clarification_questions:
            response["clarification_questions"] = clarification_questions

        if confidence is not None:
            response["confidence"] = confidence

        if next_actions:
            response["next_actions"] = next_actions
        else:
            # Generate default next actions based on response type
            response["next_actions"] = self._generate_default_next_actions(response_type)

        return response

    def _generate_default_next_actions(self, response_type: ResponseType) -> list[str]:
        """Generate default next actions based on response type"""
        if response_type == ResponseType.AUTOMATION_GENERATED:
            return [
                "Review the automation suggestions",
                "Test an automation before deploying",
                "Refine the automation if needed"
            ]
        elif response_type == ResponseType.CLARIFICATION_NEEDED:
            return [
                "Answer the clarification questions",
                "Provide more details about your request"
            ]
        elif response_type == ResponseType.ACTION_DONE:
            return [
                "Check if the action was successful",
                "Create an automation for this action"
            ]
        elif response_type == ResponseType.INFORMATION_PROVIDED:
            return [
                "Ask follow-up questions",
                "Create an automation based on this information"
            ]
        elif response_type == ResponseType.ERROR:
            return [
                "Try rephrasing your request",
                "Check device names and try again"
            ]
        else:
            return [
                "Try rephrasing your request",
                "Provide more details"
            ]


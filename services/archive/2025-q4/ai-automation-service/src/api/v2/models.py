"""
API v2 Request/Response Models

Defines all request and response models for v2 API endpoints.

Created: Phase 3 - New API Routers
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ResponseType(str, Enum):
    """Types of conversation responses"""
    AUTOMATION_GENERATED = "automation_generated"
    CLARIFICATION_NEEDED = "clarification_needed"
    ACTION_DONE = "action_done"
    INFORMATION_PROVIDED = "information_provided"
    ERROR = "error"
    NO_INTENT_MATCH = "no_intent_match"


class ConversationType(str, Enum):
    """Types of conversations"""
    AUTOMATION = "automation"
    CLARIFICATION = "clarification"
    ACTION = "action"
    INFORMATION = "information"


class ConversationStartRequest(BaseModel):
    """Request to start a new conversation"""
    query: str = Field(..., description="Initial query to start conversation")
    user_id: str = Field(default="anonymous", description="User identifier")
    conversation_type: ConversationType | None = Field(default=None, description="Optional conversation type hint")
    context: dict[str, Any] | None = Field(default=None, description="Additional context")


class MessageRequest(BaseModel):
    """Request to send a message in existing conversation"""
    message: str = Field(..., description="Message content")
    context: dict[str, Any] | None = Field(default=None, description="Additional context")


class ConversationResponse(BaseModel):
    """Response from starting a conversation"""
    conversation_id: str
    user_id: str
    conversation_type: ConversationType
    status: str
    initial_query: str
    created_at: str


class ConfidenceScore(BaseModel):
    """Confidence score with breakdown"""
    overall: float
    factors: dict[str, float]
    explanation: str
    breakdown: dict[str, Any] | None = None


class AutomationSuggestion(BaseModel):
    """Automation suggestion"""
    suggestion_id: str
    title: str
    description: str
    automation_yaml: str | None = None
    confidence: float
    validated_entities: dict[str, str]
    status: str = "draft"


class ClarificationQuestion(BaseModel):
    """Clarification question"""
    id: str
    category: str
    question_text: str
    question_type: str
    options: list[str] | None = None
    priority: int = 0
    related_entities: list[str] | None = None


class ConversationTurnResponse(BaseModel):
    """Response from a conversation turn"""
    conversation_id: str
    turn_number: int
    response_type: ResponseType
    content: str
    suggestions: list[AutomationSuggestion] | None = None
    clarification_questions: list[ClarificationQuestion] | None = None
    confidence: ConfidenceScore | None = None
    processing_time_ms: int
    next_actions: list[str]
    created_at: str


class ConversationDetail(BaseModel):
    """Full conversation details with history"""
    conversation_id: str
    user_id: str
    conversation_type: ConversationType
    status: str
    initial_query: str
    turns: list[ConversationTurnResponse]
    created_at: str
    updated_at: str
    completed_at: str | None = None


class ActionRequest(BaseModel):
    """Request to execute immediate action"""
    query: str = Field(..., description="Action query (e.g., 'turn on office lights')")
    user_id: str = Field(default="anonymous", description="User identifier")


class ActionResult(BaseModel):
    """Result of immediate action execution"""
    success: bool
    action_type: str
    entity_id: str | None = None
    result: dict[str, Any]
    message: str
    execution_time_ms: int


class AutomationGenerationRequest(BaseModel):
    """Request to generate automation"""
    suggestion_id: str
    conversation_id: str
    turn_id: int


class AutomationGenerationResponse(BaseModel):
    """Response from automation generation"""
    suggestion_id: str
    automation_yaml: str
    validation_result: dict[str, Any]
    confidence: float


class TestRequest(BaseModel):
    """Request to test automation"""
    suggestion_id: str
    automation_yaml: str


class TestResult(BaseModel):
    """Result of automation test"""
    success: bool
    state_changes: dict[str, Any]
    errors: list[str]
    warnings: list[str]
    execution_time_ms: int


class DeploymentRequest(BaseModel):
    """Request to deploy automation"""
    suggestion_id: str
    automation_yaml: str
    automation_id: str | None = None


class DeploymentResult(BaseModel):
    """Result of automation deployment"""
    success: bool
    automation_id: str
    message: str
    deployed_at: str


class AutomationSummary(BaseModel):
    """Summary of automation"""
    suggestion_id: str
    conversation_id: str
    title: str
    description: str
    status: str
    confidence: float
    created_at: str
    updated_at: str


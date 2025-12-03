"""
Conversation Management API Models
Epic AI-20 Story AI20.5: Conversation Management API

Pydantic 2.9+ models for conversation management endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..services.conversation_service import ConversationState


class MessageResponse(BaseModel):
    """Message response model"""

    message_id: str = Field(..., description="Message ID")
    role: str = Field(..., description="Message role (user, assistant)")
    content: str = Field(..., description="Message content")
    created_at: datetime = Field(..., description="Message creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    """Conversation response model"""

    conversation_id: str = Field(..., description="Conversation ID")
    state: str = Field(..., description="Conversation state (active, archived)")
    message_count: int = Field(..., description="Number of messages in conversation")
    created_at: datetime = Field(..., description="Conversation creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    messages: list[MessageResponse] | None = Field(
        None, description="Message history (included in detail view)"
    )

    model_config = ConfigDict(from_attributes=True)


class ConversationListResponse(BaseModel):
    """Paginated conversation list response"""

    conversations: list[ConversationResponse] = Field(
        ..., description="List of conversations"
    )
    total: int = Field(..., description="Total number of conversations")
    limit: int = Field(..., description="Page size limit")
    offset: int = Field(..., description="Offset for pagination")
    has_more: bool = Field(..., description="Whether there are more conversations")

    model_config = ConfigDict(from_attributes=True)


class CreateConversationRequest(BaseModel):
    """Request model for creating a new conversation"""

    initial_message: str | None = Field(
        None, description="Optional initial message to start the conversation"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "initial_message": "Hello, I need help with my home automation",
            }
        }
    )


class ConversationListQueryParams(BaseModel):
    """Query parameters for listing conversations"""

    limit: int = Field(default=20, ge=1, le=100, description="Page size (1-100)")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")
    state: ConversationState | None = Field(
        None, description="Filter by conversation state"
    )
    start_date: datetime | None = Field(
        None, description="Filter conversations created after this date"
    )
    end_date: datetime | None = Field(
        None, description="Filter conversations created before this date"
    )

    model_config = ConfigDict(from_attributes=True)


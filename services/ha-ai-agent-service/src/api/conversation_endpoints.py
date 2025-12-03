"""
Conversation Management API Endpoints
Epic AI-20 Story AI20.5: Conversation Management API

Endpoints for managing conversations:
- GET /api/v1/conversations - List conversations (paginated)
- GET /api/v1/conversations/{id} - Get conversation with full history
- POST /api/v1/conversations - Create new conversation
- DELETE /api/v1/conversations/{id} - Delete conversation
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..services.conversation_service import ConversationService, ConversationState
from .conversation_models import (
    ConversationListResponse,
    ConversationResponse,
    CreateConversationRequest,
    MessageResponse,
)
from .dependencies import get_conversation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = Query(default=20, ge=1, le=100, description="Page size (1-100)"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    state: str | None = Query(
        None, description="Filter by conversation state (active, archived)"
    ),
    start_date: str | None = Query(
        None, description="Filter conversations created after this date (ISO format)"
    ),
    end_date: str | None = Query(
        None, description="Filter conversations created before this date (ISO format)"
    ),
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    """
    List conversations with pagination and filtering.

    **Query Parameters:**
    - `limit`: Page size (1-100, default: 20)
    - `offset`: Offset for pagination (default: 0)
    - `state`: Filter by state (active, archived)
    - `start_date`: Filter conversations created after this date (ISO format)
    - `end_date`: Filter conversations created before this date (ISO format)
    """
    try:
        # Parse state filter
        state_filter = None
        if state:
            try:
                state_filter = ConversationState(state.lower())
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid state: {state}. Must be 'active' or 'archived'",
                ) from e

        # Parse date filters
        from datetime import datetime

        start_date_parsed = None
        end_date_parsed = None
        if start_date:
            try:
                start_date_parsed = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid start_date format: {start_date}. Use ISO format.",
                ) from e
        if end_date:
            try:
                end_date_parsed = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid end_date format: {end_date}. Use ISO format.",
                ) from e

        # Get conversations
        conversations = await conversation_service.list_conversations(
            limit=limit,
            offset=offset,
            state=state_filter,
            start_date=start_date_parsed,
            end_date=end_date_parsed,
        )

        # Get total count
        total = await conversation_service.count_conversations(
            state=state_filter, start_date=start_date_parsed, end_date=end_date_parsed
        )

        # Convert to response models
        conversation_responses = [
            ConversationResponse(
                conversation_id=conv.conversation_id,
                state=conv.state.value,
                message_count=conv.message_count,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                messages=None,  # Don't include messages in list view
            )
            for conv in conversations
        ]

        return ConversationListResponse(
            conversations=conversation_responses,
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error listing conversations")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        ) from e


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    """
    Get a conversation with full message history.

    **Path Parameters:**
    - `conversation_id`: Conversation ID
    """
    try:
        conversation = await conversation_service.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found",
            )

        # Get messages
        messages = conversation.messages

        # Convert to response model
        message_responses = [
            MessageResponse(
                message_id=msg.message_id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
            )
            for msg in messages
        ]

        return ConversationResponse(
            conversation_id=conversation.conversation_id,
            state=conversation.state.value,
            message_count=conversation.message_count,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=message_responses,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting conversation {conversation_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        ) from e


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: CreateConversationRequest,
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    """
    Create a new conversation.

    **Request Body:**
    - `initial_message` (optional): Initial message to start the conversation
    """
    try:
        # Create conversation
        conversation = await conversation_service.create_conversation()

        # Add initial message if provided
        if request.initial_message:
            await conversation_service.add_message(
                conversation.conversation_id, "user", request.initial_message
            )
            # Refresh conversation to get updated message count
            conversation = await conversation_service.get_conversation(
                conversation.conversation_id
            )

        # Get messages
        messages = conversation.messages if conversation else []

        # Convert to response model
        message_responses = [
            MessageResponse(
                message_id=msg.message_id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
            )
            for msg in messages
        ]

        return ConversationResponse(
            conversation_id=conversation.conversation_id,
            state=conversation.state.value,
            message_count=conversation.message_count,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=message_responses,
        )

    except Exception as e:
        logger.exception("Error creating conversation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        ) from e


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    """
    Delete a conversation.

    **Path Parameters:**
    - `conversation_id`: Conversation ID to delete
    """
    try:
        # Check if conversation exists
        conversation = await conversation_service.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found",
            )

        # Delete conversation
        await conversation_service.delete_conversation(conversation_id)

        return None  # 204 No Content

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting conversation {conversation_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        ) from e


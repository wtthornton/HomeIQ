"""
Conversation Router v2

Main conversation API endpoints.
Replaces: POST /api/v1/ask-ai/query

Created: Phase 3 - New API Routers
"""

import logging
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ...database import get_db
from ...services.service_container import get_service_container, ServiceContainer
from .models import (
    ConversationStartRequest,
    ConversationResponse,
    MessageRequest,
    ConversationTurnResponse,
    ConversationDetail,
    ResponseType,
    ConversationType,
    AutomationSuggestion,
    ClarificationQuestion
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/conversations", tags=["Conversations v2"])


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def start_conversation(
    request: ConversationStartRequest,
    container: ServiceContainer = Depends(get_service_container),
    db: AsyncSession = Depends(get_db)
) -> ConversationResponse:
    """
    Start a new conversation.
    
    Replaces: POST /api/v1/ask-ai/query
    
    Creates a new conversation and processes the initial query.
    """
    conversation_id = f"conv-{uuid.uuid4().hex[:12]}"
    
    # Determine conversation type
    intent_matcher = container.intent_matcher
    intent = intent_matcher.match_intent(request.query)
    
    conversation_type = ConversationType.AUTOMATION
    if intent.value == "action":
        conversation_type = ConversationType.ACTION
    elif intent.value == "information":
        conversation_type = ConversationType.INFORMATION
    
    # Override with explicit type if provided
    if request.conversation_type:
        conversation_type = request.conversation_type
    
    try:
        # Create conversation in database
        await db.execute(text("""
            INSERT INTO conversations (
                conversation_id, user_id, conversation_type, status,
                initial_query, context, created_at
            ) VALUES (
                :conversation_id, :user_id, :conversation_type, 'active',
                :initial_query, :context, :created_at
            )
        """), {
            "conversation_id": conversation_id,
            "user_id": request.user_id,
            "conversation_type": conversation_type.value,
            "initial_query": request.query,
            "context": str(request.context) if request.context else None,
            "created_at": datetime.utcnow().isoformat()
        })
        
        # Create context
        context_manager = container.context_manager
        context_manager.create_context(
            conversation_id=conversation_id,
            user_id=request.user_id,
            initial_query=request.query
        )
        
        # Process initial query (create first turn)
        turn_response = await _process_message(
            conversation_id=conversation_id,
            message=request.query,
            turn_number=1,
            container=container,
            db=db
        )
        
        await db.commit()
        
        return ConversationResponse(
            conversation_id=conversation_id,
            user_id=request.user_id,
            conversation_type=conversation_type,
            status="active",
            initial_query=request.query,
            created_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to start conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start conversation: {str(e)}"
        )


@router.post("/{conversation_id}/message", response_model=ConversationTurnResponse)
async def send_message(
    conversation_id: str,
    request: MessageRequest,
    container: ServiceContainer = Depends(get_service_container),
    db: AsyncSession = Depends(get_db)
) -> ConversationTurnResponse:
    """
    Send message in existing conversation.
    
    Handles: clarification answers, refinements, follow-ups
    """
    # Get conversation (verify it exists)
    result = await db.execute(text("""
        SELECT conversation_id FROM conversations WHERE conversation_id = :conversation_id
    """), {"conversation_id": conversation_id})
    
    conversation = result.fetchone()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )
    
    # Get current turn number
    turn_result = await db.execute(text("""
        SELECT MAX(turn_number) as max_turn FROM conversation_turns
        WHERE conversation_id = :conversation_id
    """), {"conversation_id": conversation_id})
    
    max_turn_row = turn_result.fetchone()
    turn_number = (max_turn_row[0] or 0) + 1 if max_turn_row else 1
    
    # Process message
    turn_response = await _process_message(
        conversation_id=conversation_id,
        message=request.message,
        turn_number=turn_number,
        container=container,
        db=db
    )
    
    await db.commit()
    
    return turn_response


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
) -> ConversationDetail:
    """Get full conversation history with all turns"""
    # Get conversation
    result = await db.execute(text("""
        SELECT * FROM conversations WHERE conversation_id = :conversation_id
    """), {"conversation_id": conversation_id})
    
    conversation = result.fetchone()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )
    
    # Get turns
    history_manager = get_service_container().history_manager
    turns_data = await history_manager.get_conversation_history(conversation_id, db)
    
    # Convert to response models
    turns = []
    for turn_data in turns_data:
        # Handle both dict and row tuple formats
        if isinstance(turn_data, dict):
            turn_number = turn_data.get("turn_number", 0)
            content = turn_data.get("content", "")
            response_type_str = turn_data.get("response_type", "information_provided")
            processing_time = turn_data.get("processing_time_ms", 0)
            created_at_str = turn_data.get("created_at", datetime.utcnow().isoformat())
        else:
            # Row tuple format
            turn_number = turn_data[3] if len(turn_data) > 3 else 0  # turn_number
            content = turn_data[4] if len(turn_data) > 4 else ""  # content
            response_type_str = turn_data[5] if len(turn_data) > 5 else "information_provided"  # response_type
            processing_time = turn_data[9] if len(turn_data) > 9 else 0  # processing_time_ms
            created_at_str = turn_data[10].isoformat() if len(turn_data) > 10 and turn_data[10] else datetime.utcnow().isoformat()  # created_at
        
        turns.append(ConversationTurnResponse(
            conversation_id=conversation_id,
            turn_number=turn_number,
            response_type=ResponseType(response_type_str),
            content=content,
            suggestions=None,  # Will be loaded separately if needed
            clarification_questions=None,
            confidence=None,
            processing_time_ms=processing_time,
            next_actions=[],
            created_at=created_at_str
        ))
    
    return ConversationDetail(
        conversation_id=conversation_id,
        user_id=conversation_row[1],  # user_id
        conversation_type=ConversationType(conversation_row[2]),  # conversation_type
        status=conversation_row[3],  # status
        initial_query=conversation_row[4],  # initial_query
        turns=turns,
        created_at=conversation_row[7].isoformat() if conversation_row[7] else datetime.utcnow().isoformat(),  # created_at
        updated_at=conversation_row[8].isoformat() if conversation_row[8] else datetime.utcnow().isoformat(),  # updated_at
        completed_at=conversation_row[9].isoformat() if conversation_row[9] else None  # completed_at
    )


@router.get("/{conversation_id}/suggestions", response_model=List[AutomationSuggestion])
async def get_suggestions(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
) -> List[AutomationSuggestion]:
    """Get all automation suggestions from conversation"""
    result = await db.execute(text("""
        SELECT * FROM automation_suggestions
        WHERE conversation_id = :conversation_id
        ORDER BY created_at DESC
    """), {"conversation_id": conversation_id})
    
    import json
    suggestions = []
    for row in result:
        # Parse validated_entities JSON
        validated_entities = {}
        if len(row) > 9 and row[9]:  # validated_entities column
            if isinstance(row[9], str):
                validated_entities = json.loads(row[9])
            elif isinstance(row[9], dict):
                validated_entities = row[9]
        
        suggestions.append(AutomationSuggestion(
            suggestion_id=row[1] if len(row) > 1 else "",  # suggestion_id
            title=row[4] if len(row) > 4 else "",  # title
            description=row[5] if len(row) > 5 else "",  # description
            automation_yaml=row[6] if len(row) > 6 else None,  # automation_yaml
            confidence=row[8] if len(row) > 8 else 0.5,  # confidence
            validated_entities=validated_entities,
            status=row[10] if len(row) > 10 else "draft"  # status
        ))
    
    return suggestions


async def _process_message(
    conversation_id: str,
    message: str,
    turn_number: int,
    container: ServiceContainer,
    db: AsyncSession
) -> ConversationTurnResponse:
    """
    Process a message in a conversation.
    
    This is the core message processing logic that will be enhanced
    in later phases with full entity extraction, suggestion generation, etc.
    """
    start_time = datetime.utcnow()
    
    # Extract entities
    entity_extractor = container.entity_extractor
    entities = await entity_extractor.extract(message)
    
    # Match intent
    intent_matcher = container.intent_matcher
    intent = intent_matcher.match_intent(message)
    
    # Build response (placeholder - will be enhanced)
    response_builder = container.response_builder
    
    # For now, return a simple response
    # Full implementation will generate suggestions, handle clarification, etc.
    response = response_builder.build_response(
        response_type=ResponseType.INFORMATION_PROVIDED,
        content=f"Processing your request: {message}",
        conversation_id=conversation_id,
        turn_number=turn_number,
        processing_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
    )
    
    # Save turn to database
    await db.execute(text("""
        INSERT INTO conversation_turns (
            conversation_id, turn_number, role, content,
            response_type, intent, extracted_entities,
            processing_time_ms, created_at
        ) VALUES (
            :conversation_id, :turn_number, 'user', :content,
            :response_type, :intent, :extracted_entities,
            :processing_time_ms, :created_at
        )
    """), {
        "conversation_id": conversation_id,
        "turn_number": turn_number,
        "content": message,
        "response_type": response["response_type"],
        "intent": intent.value,
        "extracted_entities": str(entities) if entities else None,
        "processing_time_ms": response["processing_time_ms"],
        "created_at": datetime.utcnow().isoformat()
    })
    
    return ConversationTurnResponse(**response)


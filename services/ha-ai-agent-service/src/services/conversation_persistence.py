"""
Conversation Persistence Layer
Epic AI-20 Story AI20.6: Conversation Persistence

Database operations for conversations and messages.
"""

import logging
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import ConversationModel, MessageModel
from .conversation_models import Conversation, ConversationState, Message

logger = logging.getLogger(__name__)


def _conversation_model_to_domain(model: ConversationModel) -> Conversation:
    """Convert ConversationModel to domain Conversation"""
    # Get debug_id from model (generate if missing as fallback)
    debug_id = getattr(model, 'debug_id', None)
    if not debug_id:
        debug_id = str(uuid4())  # Generate as fallback if missing
    
    conversation = Conversation(
        conversation_id=model.conversation_id,
        created_at=model.created_at,
        state=ConversationState(model.state),
        debug_id=debug_id,
    )
    conversation.updated_at = model.updated_at

    # Convert messages (only if loaded - use getattr to avoid lazy loading)
    # Messages are eagerly loaded via selectinload in queries
    messages = getattr(model, '_messages_loaded', None)
    if messages is None:
        # Try to access messages (may trigger lazy load if not already loaded)
        try:
            messages = list(model.messages) if hasattr(model, 'messages') else []
        except Exception:
            # If lazy loading fails (session closed), use empty list
            messages = []

    for msg_model in messages:
        message = Message(
            role=msg_model.role,
            content=msg_model.content,
            message_id=msg_model.message_id,
            created_at=msg_model.created_at,
        )
        conversation.messages.append(message)

    # Load pending preview (2025 Preview-and-Approval Workflow)
    if model.pending_preview:
        conversation.set_pending_preview(model.pending_preview)

    return conversation


def _message_model_to_domain(model: MessageModel) -> Message:
    """Convert MessageModel to domain Message"""
    return Message(
        role=model.role,
        content=model.content,
        message_id=model.message_id,
        created_at=model.created_at,
    )


async def create_conversation(
    session: AsyncSession, conversation_id: str | None = None
) -> Conversation:
    """Create a new conversation in the database"""
    conv_id = conversation_id or str(uuid4())
    debug_id = str(uuid4())  # Generate unique troubleshooting ID
    now = datetime.now()

    conversation_model = ConversationModel(
        conversation_id=conv_id,
        debug_id=debug_id,
        state=ConversationState.ACTIVE.value,
        created_at=now,
        updated_at=now,
    )

    session.add(conversation_model)
    await session.commit()
    await session.refresh(conversation_model)

    # Mark messages as loaded (empty list for new conversation)
    conversation_model._messages_loaded = []

    logger.info(f"Created conversation {conv_id} in database with debug_id {debug_id}")
    return _conversation_model_to_domain(conversation_model)


async def get_conversation(
    session: AsyncSession, conversation_id: str
) -> Conversation | None:
    """Get a conversation by ID from the database"""
    from sqlalchemy.orm import selectinload

    stmt = (
        select(ConversationModel)
        .where(ConversationModel.conversation_id == conversation_id)
        .options(selectinload(ConversationModel.messages))
    )

    result = await session.execute(stmt)
    conversation_model = result.scalar_one_or_none()

    if not conversation_model:
        return None

    # Ensure debug_id exists (generate if missing - handles edge cases)
    if not conversation_model.debug_id:
        conversation_model.debug_id = str(uuid4())
        await session.commit()
        await session.refresh(conversation_model)
        logger.info(f"Generated missing debug_id for conversation {conversation_id}")

    # Messages are already loaded via selectinload
    conversation_model._messages_loaded = list(conversation_model.messages)
    return _conversation_model_to_domain(conversation_model)


async def list_conversations(
    session: AsyncSession,
    state: ConversationState | None = None,
    limit: int | None = None,
    offset: int = 0,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[Conversation]:
    """List conversations with filtering and pagination"""
    from sqlalchemy.orm import selectinload

    stmt = select(ConversationModel).options(selectinload(ConversationModel.messages))

    # Apply filters
    conditions = []
    if state:
        conditions.append(ConversationModel.state == state.value)
    if start_date:
        conditions.append(ConversationModel.created_at >= start_date)
    if end_date:
        conditions.append(ConversationModel.created_at <= end_date)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    # Order by updated_at descending (most recent first)
    stmt = stmt.order_by(ConversationModel.updated_at.desc())

    # Apply pagination
    if offset:
        stmt = stmt.offset(offset)
    if limit:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    conversation_models = result.scalars().all()

    # Convert to domain models (messages already loaded via selectinload)
    conversations = []
    for model in conversation_models:
        model._messages_loaded = list(model.messages)
        conversations.append(_conversation_model_to_domain(model))

    return conversations


async def count_conversations(
    session: AsyncSession,
    state: ConversationState | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> int:
    """Count conversations with optional filtering"""
    stmt = select(func.count(ConversationModel.conversation_id))

    # Apply filters
    conditions = []
    if state:
        conditions.append(ConversationModel.state == state.value)
    if start_date:
        conditions.append(ConversationModel.created_at >= start_date)
    if end_date:
        conditions.append(ConversationModel.created_at <= end_date)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    result = await session.execute(stmt)
    return result.scalar_one()


async def delete_conversation(session: AsyncSession, conversation_id: str) -> bool:
    """Delete a conversation (cascade deletes messages)"""
    stmt = delete(ConversationModel).where(
        ConversationModel.conversation_id == conversation_id
    )

    result = await session.execute(stmt)
    await session.commit()

    deleted = result.rowcount > 0
    if deleted:
        logger.info(f"Deleted conversation {conversation_id} from database")
    return deleted


async def add_message(
    session: AsyncSession, conversation_id: str, role: str, content: str
) -> Message | None:
    """Add a message to a conversation"""
    # Verify conversation exists
    conversation_model = await session.get(ConversationModel, conversation_id)
    if not conversation_model:
        logger.warning(f"Conversation {conversation_id} not found")
        return None

    # Create message
    message_model = MessageModel(
        message_id=str(uuid4()),
        conversation_id=conversation_id,
        role=role,
        content=content,
        created_at=datetime.now(),
    )

    session.add(message_model)

    # Update conversation's updated_at
    conversation_model.updated_at = datetime.now()

    await session.commit()
    await session.refresh(message_model)

    logger.debug(
        f"Added {role} message to conversation {conversation_id} in database"
    )

    return _message_model_to_domain(message_model)


async def update_conversation_state(
    session: AsyncSession, conversation_id: str, state: ConversationState
) -> bool:
    """Update conversation state"""
    conversation_model = await session.get(ConversationModel, conversation_id)
    if not conversation_model:
        return False

    conversation_model.state = state.value
    conversation_model.updated_at = datetime.now()
    await session.commit()
    return True


async def cleanup_old_conversations(
    session: AsyncSession, ttl_days: int = 30
) -> int:
    """
    Clean up conversations older than TTL days.

    Args:
        session: Database session
        ttl_days: Time-to-live in days (default: 30)

    Returns:
        Number of conversations deleted
    """
    cutoff_date = datetime.now() - timedelta(days=ttl_days)

    stmt = delete(ConversationModel).where(
        ConversationModel.created_at < cutoff_date
    )

    result = await session.execute(stmt)
    await session.commit()

    deleted_count = result.rowcount
    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} conversations older than {ttl_days} days")

    return deleted_count


async def set_pending_preview(
    session: AsyncSession, conversation_id: str, preview: dict
) -> bool:
    """
    Store pending automation preview for a conversation.

    Args:
        session: Database session
        conversation_id: Conversation ID
        preview: Preview dictionary from preview_automation_from_prompt tool

    Returns:
        True if updated, False if conversation not found
    """
    conversation_model = await session.get(ConversationModel, conversation_id)
    if not conversation_model:
        return False

    conversation_model.pending_preview = preview
    conversation_model.updated_at = datetime.now()
    await session.commit()

    logger.debug(f"Stored pending preview for conversation {conversation_id}")
    return True


async def clear_pending_preview(
    session: AsyncSession, conversation_id: str
) -> bool:
    """
    Clear pending automation preview for a conversation.

    Args:
        session: Database session
        conversation_id: Conversation ID

    Returns:
        True if cleared, False if conversation not found
    """
    conversation_model = await session.get(ConversationModel, conversation_id)
    if not conversation_model:
        return False

    conversation_model.pending_preview = None
    conversation_model.updated_at = datetime.now()
    await session.commit()

    logger.debug(f"Cleared pending preview for conversation {conversation_id}")
    return True


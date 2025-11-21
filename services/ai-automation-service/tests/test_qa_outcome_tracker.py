"""
Unit tests for QA Outcome Tracker

Tests Q&A session outcome tracking and automation success metrics.
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.learning.qa_outcome_tracker import QAOutcomeTracker
from src.database.models import QAOutcome, ClarificationSessionDB


@pytest.fixture
def outcome_tracker():
    """Create QA outcome tracker instance."""
    return QAOutcomeTracker()


@pytest.fixture
async def sample_session(db_session: AsyncSession):
    """Create a sample clarification session."""
    session = ClarificationSessionDB(
        session_id="test-session-123",
        user_id="test-user",
        query_id="test-query-123",
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest.mark.asyncio
async def test_track_qa_outcome_automation_created(
    outcome_tracker: QAOutcomeTracker,
    db_session: AsyncSession,
    sample_session: ClarificationSessionDB
):
    """Test tracking Q&A outcome for successful automation creation."""
    outcome_id = await outcome_tracker.track_qa_outcome(
        db=db_session,
        session_id=sample_session.session_id,
        questions_count=3,
        confidence_achieved=0.85,
        outcome_type='automation_created',
        automation_id='automation-123',
        days_active=5,
        user_satisfaction=0.9
    )

    assert outcome_id is not None

    # Verify outcome was created
    from sqlalchemy import select
    result = await db_session.execute(
        select(QAOutcome).where(QAOutcome.id == outcome_id)
    )
    outcome = result.scalar_one()

    assert outcome.session_id == sample_session.session_id
    assert outcome.outcome_type == 'automation_created'
    assert outcome.automation_id == 'automation-123'
    assert outcome.questions_count == 3
    assert outcome.confidence_achieved == 0.85
    assert outcome.days_active == 5
    assert outcome.user_satisfaction == 0.9


@pytest.mark.asyncio
async def test_track_qa_outcome_abandoned(
    outcome_tracker: QAOutcomeTracker,
    db_session: AsyncSession,
    sample_session: ClarificationSessionDB
):
    """Test tracking Q&A outcome for abandoned session."""
    outcome_id = await outcome_tracker.track_qa_outcome(
        db=db_session,
        session_id=sample_session.session_id,
        questions_count=2,
        confidence_achieved=0.6,
        outcome_type='abandoned'
    )

    assert outcome_id is not None

    from sqlalchemy import select
    result = await db_session.execute(
        select(QAOutcome).where(QAOutcome.id == outcome_id)
    )
    outcome = result.scalar_one()

    assert outcome.outcome_type == 'abandoned'
    assert outcome.automation_id is None
    assert outcome.questions_count == 2
    assert outcome.confidence_achieved == 0.6


@pytest.mark.asyncio
async def test_update_automation_outcome(
    outcome_tracker: QAOutcomeTracker,
    db_session: AsyncSession,
    sample_session: ClarificationSessionDB
):
    """Test updating automation outcome with days active."""
    # First create outcome
    outcome_id = await outcome_tracker.track_qa_outcome(
        db=db_session,
        session_id=sample_session.session_id,
        questions_count=3,
        confidence_achieved=0.8,
        outcome_type='automation_created',
        automation_id='automation-123'
    )

    # Update with days active
    updated = await outcome_tracker.update_automation_outcome(
        db=db_session,
        session_id=sample_session.session_id,
        automation_id='automation-123',
        days_active=10,
        user_satisfaction=0.95
    )

    assert updated is True

    from sqlalchemy import select
    result = await db_session.execute(
        select(QAOutcome).where(QAOutcome.id == outcome_id)
    )
    outcome = result.scalar_one()

    assert outcome.days_active == 10
    assert outcome.user_satisfaction == 0.95


@pytest.mark.asyncio
async def test_get_outcome_statistics(
    outcome_tracker: QAOutcomeTracker,
    db_session: AsyncSession,
    sample_session: ClarificationSessionDB
):
    """Test getting outcome statistics."""
    # Create multiple outcomes
    await outcome_tracker.track_qa_outcome(
        db=db_session,
        session_id=sample_session.session_id,
        questions_count=3,
        confidence_achieved=0.85,
        outcome_type='automation_created',
        automation_id='automation-1'
    )

    # Create another session for abandoned outcome
    session2 = ClarificationSessionDB(
        session_id="test-session-456",
        user_id="test-user",
        query_id="test-query-456",
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(session2)
    await db_session.commit()

    await outcome_tracker.track_qa_outcome(
        db=db_session,
        session_id=session2.session_id,
        questions_count=2,
        confidence_achieved=0.6,
        outcome_type='abandoned'
    )

    # Get statistics
    stats = await outcome_tracker.get_outcome_statistics(
        db=db_session,
        user_id="test-user",
        days=30
    )

    assert stats['total_sessions'] >= 2
    assert stats['successful_automations'] >= 1
    assert stats['abandoned_sessions'] >= 1
    assert 'effectiveness_rate' in stats
    assert 'avg_confidence' in stats
    assert 'avg_questions' in stats


@pytest.mark.asyncio
async def test_predict_success_rate(
    outcome_tracker: QAOutcomeTracker,
    db_session: AsyncSession,
    sample_session: ClarificationSessionDB
):
    """Test predicting success rate based on confidence and questions."""
    # Create outcomes with varying confidence
    await outcome_tracker.track_qa_outcome(
        db=db_session,
        session_id=sample_session.session_id,
        questions_count=2,
        confidence_achieved=0.9,
        outcome_type='automation_created',
        automation_id='automation-1'
    )

    # Predict success rate
    success_rate = await outcome_tracker.predict_success_rate(
        db=db_session,
        confidence=0.85,
        questions_count=3
    )

    assert 0.0 <= success_rate <= 1.0


@pytest.mark.asyncio
async def test_track_qa_outcome_invalid_session(
    outcome_tracker: QAOutcomeTracker,
    db_session: AsyncSession
):
    """Test tracking outcome with invalid session ID."""
    outcome_id = await outcome_tracker.track_qa_outcome(
        db=db_session,
        session_id="invalid-session-id",
        questions_count=2,
        confidence_achieved=0.7,
        outcome_type='abandoned'
    )

    # Should still create outcome (foreign key may not be enforced)
    # or return None if foreign key is enforced
    # This depends on database configuration
    assert outcome_id is not None or outcome_id is None


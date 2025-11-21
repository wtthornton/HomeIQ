"""
Unit tests for Question Quality Tracker

Tests tracking question effectiveness and quality metrics.
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select

from src.services.learning.question_quality_tracker import QuestionQualityTracker
from src.database.models import QuestionQualityMetric, Base


@pytest_asyncio.fixture
async def db_engine():
    """Create in-memory SQLite database for testing"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Create database session for testing"""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def quality_tracker():
    """Create question quality tracker instance."""
    return QuestionQualityTracker()


@pytest.mark.asyncio
async def test_track_question_quality(
    quality_tracker: QuestionQualityTracker,
    db_session: AsyncSession
):
    """Test tracking question quality metrics."""
    question_id = await quality_tracker.track_question_quality(
        db=db_session,
        question_id="q-test-1",
        question_text="What color should the lights be?",
        question_category="visual_effects",
        outcome="success",
        confidence_impact=0.15
    )

    assert question_id is not None

    # Verify metric was created
    result = await db_session.execute(
        select(QuestionQualityMetric).where(
            QuestionQualityMetric.question_id == "q-test-1"
        )
    )
    metric = result.scalar_one()

    assert metric.question_text == "What color should the lights be?"
    assert metric.question_category == "visual_effects"
    assert metric.times_asked == 1
    assert metric.times_led_to_success == 1
    assert metric.success_rate == 1.0
    assert metric.avg_confidence_impact == 0.15


@pytest.mark.asyncio
async def test_track_question_quality_update_existing(
    quality_tracker: QuestionQualityTracker,
    db_session: AsyncSession
):
    """Test updating existing question quality metric."""
    # Create initial metric
    await quality_tracker.track_question_quality(
        db=db_session,
        question_id="q-test-2",
        question_text="What time should this run?",
        question_category="timing",
        outcome="success",
        confidence_impact=0.1
    )

    # Update with another success
    await quality_tracker.track_question_quality(
        db=db_session,
        question_id="q-test-2",
        question_text="What time should this run?",
        question_category="timing",
        outcome="success",
        confidence_impact=0.2
    )

    # Update with failure
    await quality_tracker.track_question_quality(
        db=db_session,
        question_id="q-test-2",
        question_text="What time should this run?",
        question_category="timing",
        outcome="failure",
        confidence_impact=-0.05
    )

    # Verify updated metric
    result = await db_session.execute(
        select(QuestionQualityMetric).where(
            QuestionQualityMetric.question_id == "q-test-2"
        )
    )
    metric = result.scalar_one()

    assert metric.times_asked == 3
    assert metric.times_led_to_success == 2
    assert metric.success_rate == pytest.approx(2.0 / 3.0, abs=0.01)


@pytest.mark.asyncio
async def test_track_question_confusion(
    quality_tracker: QuestionQualityTracker,
    db_session: AsyncSession
):
    """Test tracking question confusion."""
    await quality_tracker.track_question_confusion(
        db=db_session,
        question_id="q-confusing"
    )

    result = await db_session.execute(
        select(QuestionQualityMetric).where(
            QuestionQualityMetric.question_id == "q-confusing"
        )
    )
    metric = result.scalar_one()

    assert metric.confusion_count == 1


@pytest.mark.asyncio
async def test_track_question_unnecessary(
    quality_tracker: QuestionQualityTracker,
    db_session: AsyncSession
):
    """Test tracking unnecessary questions."""
    await quality_tracker.track_question_unnecessary(
        db=db_session,
        question_id="q-unnecessary"
    )

    result = await db_session.execute(
        select(QuestionQualityMetric).where(
            QuestionQualityMetric.question_id == "q-unnecessary"
        )
    )
    metric = result.scalar_one()

    assert metric.unnecessary_count == 1


@pytest.mark.asyncio
async def test_get_question_quality(
    quality_tracker: QuestionQualityTracker,
    db_session: AsyncSession
):
    """Test retrieving question quality."""
    # Create metric
    await quality_tracker.track_question_quality(
        db=db_session,
        question_id="q-get-test",
        question_text="Test question",
        question_category="test",
        outcome="success",
        confidence_impact=0.1
    )

    # Get quality
    quality = await quality_tracker.get_question_quality(
        db=db_session,
        question_id="q-get-test"
    )

    assert quality is not None
    assert quality['question_id'] == "q-get-test"
    assert quality['times_asked'] == 1
    assert quality['success_rate'] == 1.0


@pytest.mark.asyncio
async def test_get_question_quality_statistics(
    quality_tracker: QuestionQualityTracker,
    db_session: AsyncSession
):
    """Test getting overall question quality statistics."""
    # Create multiple metrics
    await quality_tracker.track_question_quality(
        db=db_session,
        question_id="q-stat-1",
        question_text="Question 1",
        question_category="test",
        outcome="success",
        confidence_impact=0.1
    )

    await quality_tracker.track_question_quality(
        db=db_session,
        question_id="q-stat-2",
        question_text="Question 2",
        question_category="test",
        outcome="failure",
        confidence_impact=-0.05
    )

    # Get statistics
    stats = await quality_tracker.get_question_quality_statistics(db=db_session)

    assert stats['total_questions'] >= 2
    assert stats['total_asked'] >= 2
    assert 'avg_success_rate' in stats
    assert 'total_successful' in stats


@pytest.mark.asyncio
async def test_get_high_quality_questions(
    quality_tracker: QuestionQualityTracker,
    db_session: AsyncSession
):
    """Test getting high-quality questions."""
    # Create high-quality question
    await quality_tracker.track_question_quality(
        db=db_session,
        question_id="q-high-quality",
        question_text="High quality question",
        question_category="test",
        outcome="success",
        confidence_impact=0.2
    )
    # Update multiple times to meet min_times_asked
    for _ in range(5):
        await quality_tracker.track_question_quality(
            db=db_session,
            question_id="q-high-quality",
            question_text="High quality question",
            question_category="test",
            outcome="success",
            confidence_impact=0.2
        )

    # Get high-quality questions
    questions = await quality_tracker.get_high_quality_questions(
        db=db_session,
        min_success_rate=0.8,
        min_times_asked=5,
        limit=10
    )

    assert len(questions) > 0
    assert any(q['question_id'] == "q-high-quality" for q in questions)


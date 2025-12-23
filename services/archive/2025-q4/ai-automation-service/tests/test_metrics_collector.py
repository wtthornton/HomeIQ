"""
Unit tests for Metrics Collector

Tests aggregation of success metrics for Q&A learning features.
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.services.learning.metrics_collector import MetricsCollector
from src.database.models import (
    QAOutcome,
    UserPreference,
    QuestionQualityMetric,
    ClarificationSessionDB,
    Base
)


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
def metrics_collector():
    """Create metrics collector instance."""
    return MetricsCollector()


@pytest.mark.asyncio
async def test_get_effectiveness_rate(
    metrics_collector: MetricsCollector,
    db_session: AsyncSession
):
    """Test calculating effectiveness rate."""
    # Create sample session
    session = ClarificationSessionDB(
        session_id="test-session-eff",
        user_id="test-user",
        query_id="test-query-eff",
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(session)
    await db_session.commit()

    # Create successful outcome
    outcome1 = QAOutcome(
        session_id=session.session_id,
        questions_count=3,
        confidence_achieved=0.85,
        outcome_type='automation_created',
        automation_id='automation-1',
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(outcome1)

    # Create abandoned outcome
    session2 = ClarificationSessionDB(
        session_id="test-session-eff-2",
        user_id="test-user",
        query_id="test-query-eff-2",
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(session2)
    await db_session.commit()

    outcome2 = QAOutcome(
        session_id=session2.session_id,
        questions_count=2,
        confidence_achieved=0.6,
        outcome_type='abandoned',
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(outcome2)
    await db_session.commit()

    # Get effectiveness rate
    effectiveness = await metrics_collector.get_effectiveness_rate(
        db=db_session,
        user_id="test-user",
        days=30
    )

    assert effectiveness['total_sessions'] >= 2
    assert effectiveness['successful_automations'] >= 1
    assert effectiveness['abandoned_sessions'] >= 1
    assert 0.0 <= effectiveness['effectiveness_rate'] <= 100.0
    assert 'avg_confidence' in effectiveness
    assert 'avg_questions' in effectiveness


@pytest.mark.asyncio
async def test_get_preference_hit_rate(
    metrics_collector: MetricsCollector,
    db_session: AsyncSession
):
    """Test calculating preference hit rate."""
    # Create preferences
    preference = UserPreference(
        user_id="test-user",
        question_category="visual_effects",
        question_pattern="color",
        answer_pattern="random",
        consistency_score=0.95,
        usage_count=10,
        last_used=datetime.now(timezone.utc)
    )
    db_session.add(preference)
    await db_session.commit()

    # Get hit rate
    hit_rate = await metrics_collector.get_preference_hit_rate(
        db=db_session,
        user_id="test-user",
        days=30
    )

    assert 'hit_rate' in hit_rate
    assert 0.0 <= hit_rate['hit_rate'] <= 100.0
    assert hit_rate['total_preferences'] >= 1
    assert 'avg_consistency' in hit_rate


@pytest.mark.asyncio
async def test_get_question_accuracy(
    metrics_collector: MetricsCollector,
    db_session: AsyncSession
):
    """Test calculating question accuracy."""
    # Create question quality metrics
    metric1 = QuestionQualityMetric(
        question_id="q-acc-1",
        question_text="Test question 1",
        question_category="test",
        times_asked=10,
        times_led_to_success=8,
        confusion_count=1,
        unnecessary_count=1,
        avg_confidence_impact=0.15,
        success_rate=0.8,
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(metric1)

    metric2 = QuestionQualityMetric(
        question_id="q-acc-2",
        question_text="Test question 2",
        question_category="test",
        times_asked=5,
        times_led_to_success=4,
        confusion_count=0,
        unnecessary_count=1,
        avg_confidence_impact=0.1,
        success_rate=0.8,
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(metric2)
    await db_session.commit()

    # Get accuracy
    accuracy = await metrics_collector.get_question_accuracy(
        db=db_session,
        days=30
    )

    assert 'accuracy' in accuracy
    assert 0.0 <= accuracy['accuracy'] <= 100.0
    assert accuracy['total_questions'] >= 2
    assert 'avg_success_rate' in accuracy
    assert 'confusion_rate' in accuracy
    assert 'unnecessary_rate' in accuracy


@pytest.mark.asyncio
async def test_get_comprehensive_metrics(
    metrics_collector: MetricsCollector,
    db_session: AsyncSession
):
    """Test getting comprehensive metrics."""
    # Create sample data
    session = ClarificationSessionDB(
        session_id="test-session-comp",
        user_id="test-user",
        query_id="test-query-comp",
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(session)
    await db_session.commit()

    outcome = QAOutcome(
        session_id=session.session_id,
        questions_count=3,
        confidence_achieved=0.85,
        outcome_type='automation_created',
        automation_id='automation-1',
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(outcome)

    preference = UserPreference(
        user_id="test-user",
        question_category="test",
        question_pattern="test",
        answer_pattern="test",
        consistency_score=0.9,
        usage_count=5,
        last_used=datetime.now(timezone.utc)
    )
    db_session.add(preference)

    metric = QuestionQualityMetric(
        question_id="q-comp",
        question_text="Test question",
        question_category="test",
        times_asked=10,
        times_led_to_success=8,
        success_rate=0.8,
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(metric)
    await db_session.commit()

    # Get comprehensive metrics
    metrics = await metrics_collector.get_comprehensive_metrics(
        db=db_session,
        user_id="test-user",
        days=30
    )

    assert 'overall_score' in metrics
    assert 0.0 <= metrics['overall_score'] <= 100.0
    assert 'effectiveness' in metrics
    assert 'hit_rate' in metrics
    assert 'accuracy' in metrics
    assert 'timestamp' in metrics


@pytest.mark.asyncio
async def test_get_trend_metrics(
    metrics_collector: MetricsCollector,
    db_session: AsyncSession
):
    """Test getting trend metrics over time."""
    # Create sample data
    session = ClarificationSessionDB(
        session_id="test-session-trend",
        user_id="test-user",
        query_id="test-query-trend",
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(session)
    await db_session.commit()

    outcome = QAOutcome(
        session_id=session.session_id,
        questions_count=3,
        confidence_achieved=0.85,
        outcome_type='automation_created',
        automation_id='automation-1',
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(outcome)
    await db_session.commit()

    # Get trend metrics
    trends = await metrics_collector.get_trend_metrics(
        db=db_session,
        user_id="test-user",
        days=30,
        interval_days=7
    )

    assert 'intervals' in trends
    assert isinstance(trends['intervals'], list)
    assert 'interval_days' in trends
    assert trends['interval_days'] == 7


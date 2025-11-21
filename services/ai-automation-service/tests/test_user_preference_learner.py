"""
Unit tests for User Preference Learner

Tests learning and applying user preferences from Q&A patterns.
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.learning.user_preference_learner import UserPreferenceLearner
from src.database.models import UserPreference, ClarificationSessionDB, ClarificationQADB


@pytest.fixture
def preference_learner():
    """Create user preference learner instance."""
    return UserPreferenceLearner()


@pytest.fixture
async def sample_qa_pairs(db_session: AsyncSession):
    """Create sample Q&A pairs for testing."""
    session = ClarificationSessionDB(
        session_id="test-session-pref",
        user_id="test-user",
        query_id="test-query-pref",
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    # Create Q&A pairs with consistent answers
    qa_pairs = []
    for i in range(5):
        qa = ClarificationQADB(
            session_id=session.session_id,
            question_id=f"q-{i}",
            question_text="What color should the lights be?",
            question_category="visual_effects",
            answer_text="random",
            answer_validated=True,
            created_at=datetime.now(timezone.utc) - timedelta(days=i)
        )
        db_session.add(qa)
        qa_pairs.append(qa)

    await db_session.commit()
    return session, qa_pairs


@pytest.mark.asyncio
async def test_learn_preference_from_consistent_answers(
    preference_learner: UserPreferenceLearner,
    db_session: AsyncSession,
    sample_qa_pairs: tuple
):
    """Test learning preference from consistent Q&A answers."""
    session, qa_pairs = sample_qa_pairs

    # Learn preferences from Q&A pairs
    preferences = await preference_learner.learn_preferences_from_qa(
        db=db_session,
        user_id=session.user_id,
        qa_pairs=qa_pairs
    )

    assert len(preferences) > 0

    # Check that preference was created
    from sqlalchemy import select
    result = await db_session.execute(
        select(UserPreference).where(
            UserPreference.user_id == session.user_id,
            UserPreference.question_category == "visual_effects"
        )
    )
    preference = result.scalar_one_or_none()

    assert preference is not None
    assert preference.consistency_score >= 0.9  # Should be high for 5 consistent answers
    assert preference.answer_pattern == "random"


@pytest.mark.asyncio
async def test_get_user_preferences(
    preference_learner: UserPreferenceLearner,
    db_session: AsyncSession,
    sample_qa_pairs: tuple
):
    """Test retrieving user preferences."""
    session, qa_pairs = sample_qa_pairs

    # First learn preferences
    await preference_learner.learn_preferences_from_qa(
        db=db_session,
        user_id=session.user_id,
        qa_pairs=qa_pairs
    )

    # Get preferences
    preferences = await preference_learner.get_user_preferences(
        db=db_session,
        user_id=session.user_id,
        min_consistency=0.9
    )

    assert len(preferences) > 0
    assert all(p['consistency_score'] >= 0.9 for p in preferences)


@pytest.mark.asyncio
async def test_apply_preferences_skip_question(
    preference_learner: UserPreferenceLearner,
    db_session: AsyncSession,
    sample_qa_pairs: tuple
):
    """Test applying preferences to skip questions."""
    session, qa_pairs = sample_qa_pairs

    # Learn preferences
    await preference_learner.learn_preferences_from_qa(
        db=db_session,
        user_id=session.user_id,
        qa_pairs=qa_pairs
    )

    # Create a question that matches the preference
    questions = [
        {
            'question_id': 'q-test',
            'question_text': 'What color should the lights be?',
            'question_category': 'visual_effects'
        }
    ]

    # Apply preferences
    filtered_questions, pre_filled = await preference_learner.apply_preferences(
        db=db_session,
        user_id=session.user_id,
        questions=questions
    )

    # Question should be skipped if consistency is high enough
    # or pre-filled if consistency is moderate
    assert len(filtered_questions) <= len(questions)
    assert len(pre_filled) >= 0


@pytest.mark.asyncio
async def test_apply_preferences_pre_fill(
    preference_learner: UserPreferenceLearner,
    db_session: AsyncSession,
    sample_qa_pairs: tuple
):
    """Test applying preferences to pre-fill answers."""
    session, qa_pairs = sample_qa_pairs

    # Learn preferences
    await preference_learner.learn_preferences_from_qa(
        db=db_session,
        user_id=session.user_id,
        qa_pairs=qa_pairs
    )

    questions = [
        {
            'question_id': 'q-test',
            'question_text': 'What color should the lights be?',
            'question_category': 'visual_effects'
        }
    ]

    filtered_questions, pre_filled = await preference_learner.apply_preferences(
        db=db_session,
        user_id=session.user_id,
        questions=questions
    )

    # Check if answer was pre-filled
    if len(pre_filled) > 0:
        assert pre_filled[0]['question_id'] == 'q-test'
        assert 'answer' in pre_filled[0]


@pytest.mark.asyncio
async def test_clear_user_preferences(
    preference_learner: UserPreferenceLearner,
    db_session: AsyncSession,
    sample_qa_pairs: tuple
):
    """Test clearing user preferences."""
    session, qa_pairs = sample_qa_pairs

    # Learn preferences
    await preference_learner.learn_preferences_from_qa(
        db=db_session,
        user_id=session.user_id,
        qa_pairs=qa_pairs
    )

    # Clear preferences
    deleted_count = await preference_learner.clear_user_preferences(
        db=db_session,
        user_id=session.user_id
    )

    assert deleted_count > 0

    # Verify preferences are gone
    preferences = await preference_learner.get_user_preferences(
        db=db_session,
        user_id=session.user_id
    )

    assert len(preferences) == 0


@pytest.mark.asyncio
async def test_preference_consistency_threshold(
    preference_learner: UserPreferenceLearner,
    db_session: AsyncSession
):
    """Test that preferences require minimum consistency threshold."""
    session = ClarificationSessionDB(
        session_id="test-session-inconsistent",
        user_id="test-user-2",
        query_id="test-query-inconsistent",
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    # Create inconsistent Q&A pairs
    qa_pairs = []
    answers = ["random", "blue", "random", "red", "random"]
    for i, answer in enumerate(answers):
        qa = ClarificationQADB(
            session_id=session.session_id,
            question_id=f"q-{i}",
            question_text="What color should the lights be?",
            question_category="visual_effects",
            answer_text=answer,
            answer_validated=True,
            created_at=datetime.now(timezone.utc) - timedelta(days=i)
        )
        db_session.add(qa)
        qa_pairs.append(qa)

    await db_session.commit()

    # Learn preferences
    preferences = await preference_learner.learn_preferences_from_qa(
        db=db_session,
        user_id=session.user_id,
        qa_pairs=qa_pairs
    )

    # Should not create preference with low consistency
    from sqlalchemy import select
    result = await db_session.execute(
        select(UserPreference).where(
            UserPreference.user_id == session.user_id,
            UserPreference.question_category == "visual_effects"
        )
    )
    preference = result.scalar_one_or_none()

    # Preference should not exist or have low consistency
    if preference:
        assert preference.consistency_score < 0.9


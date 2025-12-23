"""
User Preference Learner

Learns user preferences from Q&A patterns to enable personalization.
Tracks consistent answer patterns to skip questions or pre-fill answers.

2025 Best Practices:
- Full type hints (PEP 484/526)
- Async/await for all database operations
- SQLAlchemy 2.0+ async patterns
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class UserPreferenceLearner:
    """
    Learns user preferences from Q&A patterns.
    
    Tracks consistent answer patterns to enable:
    - Skipping questions user always answers the same way
    - Pre-filling answers based on learned preferences
    - Adapting question style to user preferences
    """

    async def learn_user_preference(
        self,
        db: AsyncSession,
        user_id: str,
        question_category: str,
        question_pattern: str,
        answer_pattern: str
    ) -> bool:
        """
        Learn user preference from Q&A pattern.
        
        Updates or creates preference based on consistency.
        
        Args:
            db: Database session
            user_id: User ID
            question_category: Category of question (e.g., 'device_selection', 'action_type')
            question_pattern: Pattern of question text (normalized)
            answer_pattern: Pattern of answer (normalized)
            
        Returns:
            True if preference was learned/updated, False otherwise
        """
        try:
            from ...database.models import UserPreference, SystemSettings

            # Check if learning is enabled
            settings_result = await db.execute(select(SystemSettings).limit(1))
            settings = settings_result.scalar_one_or_none()
            if settings and not getattr(settings, 'enable_qa_learning', True):
                logger.debug("Q&A learning disabled in settings")
                return False

            # Check for existing preference
            query = select(UserPreference).where(
                UserPreference.user_id == user_id,
                UserPreference.question_category == question_category,
                UserPreference.question_pattern == question_pattern
            )

            result = await db.execute(query)
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing preference
                existing.usage_count += 1
                existing.last_used = datetime.now(timezone.utc)
                
                # Recalculate consistency if answer matches
                if existing.answer_pattern == answer_pattern:
                    # Answer matches - increase consistency
                    total_uses = existing.usage_count
                    existing.consistency_score = min(1.0, existing.consistency_score + (1.0 / total_uses))
                else:
                    # Answer differs - decrease consistency
                    existing.answer_pattern = answer_pattern
                    existing.consistency_score = max(0.0, existing.consistency_score - (1.0 / existing.usage_count))
                
                await db.commit()
                await db.refresh(existing)
                
                logger.debug(
                    f"Updated preference: user_id={user_id}, category={question_category}, "
                    f"consistency={existing.consistency_score:.2f}"
                )
            else:
                # Create new preference
                preference = UserPreference(
                    user_id=user_id,
                    question_category=question_category,
                    question_pattern=question_pattern,
                    answer_pattern=answer_pattern,
                    consistency_score=1.0,  # Start at 100% for first occurrence
                    usage_count=1,
                    last_used=datetime.now(timezone.utc),
                    created_at=datetime.now(timezone.utc)
                )

                db.add(preference)
                await db.commit()
                await db.refresh(preference)
                
                logger.debug(
                    f"Created preference: user_id={user_id}, category={question_category}"
                )

            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to learn user preference: {e}", exc_info=True)
            return False

    async def get_user_preferences(
        self,
        db: AsyncSession,
        user_id: str,
        question_category: str | None = None,
        min_consistency: float = 0.9
    ) -> list[dict[str, Any]]:
        """
        Get user preferences matching criteria.
        
        Args:
            db: Database session
            user_id: User ID
            question_category: Optional category filter
            min_consistency: Minimum consistency score (0.0-1.0)
            
        Returns:
            List of preference dictionaries
        """
        try:
            from ...database.models import UserPreference

            query = select(UserPreference).where(
                UserPreference.user_id == user_id,
                UserPreference.consistency_score >= min_consistency
            )

            if question_category:
                query = query.where(UserPreference.question_category == question_category)

            query = query.order_by(UserPreference.consistency_score.desc())

            result = await db.execute(query)
            preferences = list(result.scalars().all())

            return [
                {
                    'id': p.id,
                    'question_category': p.question_category,
                    'question_pattern': p.question_pattern,
                    'answer_pattern': p.answer_pattern,
                    'consistency_score': p.consistency_score,
                    'usage_count': p.usage_count,
                    'last_used': p.last_used.isoformat() if p.last_used else None
                }
                for p in preferences
            ]

        except Exception as e:
            logger.error(f"Failed to get user preferences: {e}", exc_info=True)
            return []

    async def apply_user_preferences(
        self,
        db: AsyncSession,
        user_id: str,
        questions: list[Any]  # List of ClarificationQuestion objects
    ) -> tuple[list[Any], dict[str, str]]:
        """
        Apply user preferences to questions.
        
        Skips questions with >90% consistent answers and pre-fills answers.
        
        Args:
            db: Database session
            user_id: User ID
            questions: List of ClarificationQuestion objects
            
        Returns:
            Tuple of (filtered_questions, pre_filled_answers)
            - filtered_questions: Questions to ask (skipped high-consistency ones)
            - pre_filled_answers: Dict mapping question_id to pre-filled answer
        """
        try:
            from ...database.models import SystemSettings

            # Check if learning is enabled
            settings_result = await db.execute(select(SystemSettings).limit(1))
            settings = settings_result.scalar_one_or_none()
            if not settings or not getattr(settings, 'enable_qa_learning', True):
                return questions, {}

            threshold = getattr(settings, 'preference_consistency_threshold', 0.9)
            min_questions = getattr(settings, 'min_questions_for_preference', 3)

            # Get user preferences
            preferences = await self.get_user_preferences(
                db, user_id, min_consistency=threshold
            )

            # Build preference map by question pattern
            preference_map = {}
            for pref in preferences:
                if pref['usage_count'] >= min_questions:
                    preference_map[pref['question_pattern']] = pref

            filtered_questions = []
            pre_filled_answers = {}

            for question in questions:
                # Normalize question text for matching
                question_text = getattr(question, 'question_text', str(question))
                question_category = getattr(question, 'category', 'unknown')
                question_id = getattr(question, 'id', None)

                # Check if we have a preference for this question pattern
                matching_pref = None
                for pattern, pref in preference_map.items():
                    if pattern.lower() in question_text.lower() or question_text.lower() in pattern.lower():
                        if pref['question_category'] == question_category:
                            matching_pref = pref
                            break

                if matching_pref and matching_pref['consistency_score'] >= threshold:
                    # Skip question and pre-fill answer
                    if question_id:
                        pre_filled_answers[question_id] = matching_pref['answer_pattern']
                    logger.debug(
                        f"Skipping question '{question_text[:50]}...' - "
                        f"preference consistency={matching_pref['consistency_score']:.2f}"
                    )
                else:
                    # Ask question normally
                    filtered_questions.append(question)

            logger.info(
                f"Applied preferences: {len(questions)} -> {len(filtered_questions)} questions, "
                f"{len(pre_filled_answers)} pre-filled"
            )

            return filtered_questions, pre_filled_answers

        except Exception as e:
            logger.error(f"Failed to apply user preferences: {e}", exc_info=True)
            return questions, {}

    async def clear_user_preferences(
        self,
        db: AsyncSession,
        user_id: str,
        question_category: str | None = None
    ) -> int:
        """
        Clear user preferences (privacy control).
        
        Args:
            db: Database session
            user_id: User ID
            question_category: Optional category to clear (None = all)
            
        Returns:
            Number of preferences deleted
        """
        try:
            from ...database.models import UserPreference
            from sqlalchemy import delete

            query = delete(UserPreference).where(
                UserPreference.user_id == user_id
            )

            if question_category:
                query = query.where(UserPreference.question_category == question_category)

            result = await db.execute(query)
            await db.commit()

            deleted_count = result.rowcount
            logger.info(f"Cleared {deleted_count} preferences for user_id={user_id}")
            return deleted_count

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to clear user preferences: {e}", exc_info=True)
            return 0



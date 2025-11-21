"""
Ambiguity Detection Learner

Learns from false positives and false negatives in ambiguity detection
to improve detection accuracy over time.

2025 Best Practices:
- Full type hints (PEP 484/526)
- Async/await for all database operations
- SQLAlchemy 2.0+ async patterns
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AmbiguityLearner:
    """
    Learns from ambiguity detection feedback.
    
    Tracks:
    - False positives (asked clarification when not needed)
    - False negatives (should have asked but didn't)
    - Learns patterns to improve detection rules
    """

    async def track_ambiguity_feedback(
        self,
        db: AsyncSession,
        query: str,
        detected_ambiguities: list[dict[str, Any]],
        actual_ambiguities: list[dict[str, Any]] | None = None,
        false_positive: bool = False,
        false_negative: bool = False,
        user_feedback: str | None = None
    ) -> bool:
        """
        Track ambiguity detection feedback.
        
        Args:
            db: Database session
            query: Original user query
            detected_ambiguities: Ambiguities that were detected
            actual_ambiguities: Actual ambiguities (if known from user answers)
            false_positive: Whether this was a false positive (asked when not needed)
            false_negative: Whether this was a false negative (should have asked but didn't)
            user_feedback: Optional user feedback text
            
        Returns:
            True if tracked successfully, False otherwise
        """
        try:
            from ...database.models import SystemSettings, SemanticKnowledge

            # Check if learning is enabled
            settings_result = await db.execute(select(SystemSettings).limit(1))
            settings = settings_result.scalar_one_or_none()
            if settings and not getattr(settings, 'enable_qa_learning', True):
                logger.debug("Q&A learning disabled in settings")
                return False

            # Store feedback in semantic_knowledge for pattern learning
            # This enables the system to learn patterns like:
            # "office light" with single match → not ambiguous
            # "turn on lights" with multiple matches → ambiguous
            
            feedback_text = f"Query: {query}\n"
            feedback_text += f"Detected ambiguities: {len(detected_ambiguities)}\n"
            if actual_ambiguities:
                feedback_text += f"Actual ambiguities: {len(actual_ambiguities)}\n"
            if false_positive:
                feedback_text += "False positive: Asked clarification when not needed\n"
            if false_negative:
                feedback_text += "False negative: Should have asked but didn't\n"
            if user_feedback:
                feedback_text += f"User feedback: {user_feedback}\n"

            # Store in semantic_knowledge for future pattern matching
            try:
                from ...services.rag.rag_client import RAGClient
                rag_client = RAGClient(
                    openvino_service_url=None,  # Will use default
                    db_session=db
                )
                
                await rag_client.store(
                    text=query,
                    knowledge_type='ambiguity_feedback',
                    metadata={
                        'detected_count': len(detected_ambiguities),
                        'actual_count': len(actual_ambiguities) if actual_ambiguities else None,
                        'false_positive': false_positive,
                        'false_negative': false_negative,
                        'user_feedback': user_feedback,
                        'created_at': datetime.now(timezone.utc).isoformat()
                    },
                    success_score=0.5 if (false_positive or false_negative) else 1.0  # Lower score for errors
                )
                
                logger.debug(f"✅ Stored ambiguity feedback: false_positive={false_positive}, false_negative={false_negative}")
            except Exception as e:
                logger.warning(f"Failed to store ambiguity feedback in RAG: {e}")
                # Non-critical: continue

            return True

        except Exception as e:
            logger.error(f"Failed to track ambiguity feedback: {e}", exc_info=True)
            return False

    async def learn_from_outcome(
        self,
        db: AsyncSession,
        session_id: str,
        query: str,
        detected_ambiguities: list[dict[str, Any]],
        questions_asked: int,
        confidence_achieved: float,
        automation_created: bool,
        automation_successful: bool | None = None
    ) -> bool:
        """
        Learn from Q&A session outcome.
        
        Determines if ambiguity detection was correct based on:
        - Questions asked vs. confidence achieved
        - Automation success/failure
        
        Args:
            db: Database session
            session_id: Clarification session ID
            query: Original user query
            detected_ambiguities: Ambiguities that were detected
            questions_asked: Number of questions asked
            confidence_achieved: Final confidence score
            automation_created: Whether automation was created
            automation_successful: Whether automation was successful (None if unknown)
            
        Returns:
            True if learned successfully, False otherwise
        """
        try:
            # Determine if this was a false positive or false negative
            false_positive = False
            false_negative = False

            # False positive: Asked many questions but achieved high confidence quickly
            # This suggests ambiguities weren't actually ambiguous
            if questions_asked > 0 and confidence_achieved >= 0.9:
                # Check if questions were necessary
                # If we achieved high confidence with minimal questions, might be false positive
                if questions_asked <= 1 and len(detected_ambiguities) > 1:
                    false_positive = True
                    logger.debug(f"Possible false positive: {questions_asked} questions, {len(detected_ambiguities)} ambiguities detected")

            # False negative: Low confidence but no questions asked
            # This suggests we should have asked but didn't
            if questions_asked == 0 and confidence_achieved < 0.7:
                false_negative = True
                logger.debug(f"Possible false negative: {questions_asked} questions, confidence={confidence_achieved:.2f}")

            # Track feedback
            if false_positive or false_negative:
                await self.track_ambiguity_feedback(
                    db=db,
                    query=query,
                    detected_ambiguities=detected_ambiguities,
                    false_positive=false_positive,
                    false_negative=false_negative,
                    user_feedback=f"Automation created: {automation_created}, Successful: {automation_successful}"
                )

            return True

        except Exception as e:
            logger.error(f"Failed to learn from outcome: {e}", exc_info=True)
            return False



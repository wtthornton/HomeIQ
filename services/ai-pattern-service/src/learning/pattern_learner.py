"""
Q&A Pattern Learner

Epic 39, Story 39.7: Pattern Learning & RLHF Migration
Learns correlations between Q&A patterns and automation types to improve
suggestion generation and predict user intent.

Note: This module has dependencies on RAGClient which may need to be
addressed in future stories (shared service or API call).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class PatternLearner:
    """
    Learns patterns from Q&A → automation type correlations.
    
    Analyzes successful automations to learn:
    - Which Q&A patterns lead to which automation types
    - User intent prediction from Q&A history
    - Suggestion quality improvements
    
    Epic 39, Story 39.7: Extracted to pattern service.
    Note: RAGClient dependency will need to be addressed (shared service or API call).
    """

    async def learn_from_successful_automation(
        self,
        db: AsyncSession,
        session_id: str,
        qa_pairs: list[dict[str, Any]],
        automation_type: str,
        automation_category: str | None = None,
        user_satisfaction: float | None = None,
        days_active: int | None = None
    ) -> bool:
        """
        Learn from successful automation.
        
        Analyzes Q&A patterns that led to successful automations.
        
        Args:
            db: Database session
            session_id: Clarification session ID
            qa_pairs: List of Q&A pairs from the session
            automation_type: Type of automation (e.g., 'time_based', 'motion_triggered')
            automation_category: Category (e.g., 'energy', 'comfort', 'security')
            user_satisfaction: User satisfaction score (0.0-1.0)
            days_active: Days automation was active
            
        Returns:
            True if learned successfully, False otherwise
        """
        try:
            # Note: SystemSettings and SemanticKnowledge models are in shared database
            # Import path will need to be adjusted based on how models are shared
            try:
                from ...database.models import SystemSettings
            except ImportError:
                # Fallback: Use raw SQL or skip settings check
                logger.warning("SystemSettings model not available, skipping settings check")
                SystemSettings = None

            # Check if learning is enabled
            if SystemSettings:
                settings_result = await db.execute(select(SystemSettings).limit(1))
                settings = settings_result.scalar_one_or_none()
                if settings and not getattr(settings, 'enable_qa_learning', True):
                    logger.debug("Q&A learning disabled in settings")
                    return False

            # Build pattern signature from Q&A pairs
            qa_pattern = self._build_qa_pattern(qa_pairs)
            
            # Store pattern → automation type correlation
            # Note: RAGClient dependency - will need to be addressed
            # Options: 1) Shared service, 2) API call, 3) Direct database access
            try:
                # Try to import RAGClient (may not be available in pattern service)
                try:
                    from ...services.rag.rag_client import RAGClient
                    rag_client = RAGClient(
                        openvino_service_url=None,  # Will use default
                        db_session=db
                    )
                    
                    pattern_text = f"Q&A Pattern: {qa_pattern}\nAutomation Type: {automation_type}"
                    if automation_category:
                        pattern_text += f"\nCategory: {automation_category}"
                    
                    # Calculate success score based on satisfaction and days active
                    success_score = 0.5  # Default
                    if user_satisfaction is not None:
                        success_score = user_satisfaction
                    elif days_active is not None:
                        # More days active = higher success
                        success_score = min(1.0, 0.5 + (days_active / 60.0))  # 60 days = 1.0
                    
                    await rag_client.store(
                        text=pattern_text,
                        knowledge_type='qa_automation_pattern',
                        metadata={
                            'session_id': session_id,
                            'qa_pattern': qa_pattern,
                            'automation_type': automation_type,
                            'automation_category': automation_category,
                            'user_satisfaction': user_satisfaction,
                            'days_active': days_active,
                            'qa_count': len(qa_pairs),
                            'created_at': datetime.now(timezone.utc).isoformat()
                        },
                        success_score=success_score
                    )
                    
                    logger.debug(
                        f"✅ Learned pattern: {qa_pattern} → {automation_type} "
                        f"(satisfaction={user_satisfaction}, days={days_active})"
                    )
                except ImportError:
                    logger.warning("RAGClient not available in pattern service - pattern learning disabled")
                    # Non-critical: continue without RAG storage
                    return False
            except Exception as e:
                logger.warning(f"Failed to store pattern in RAG: {e}")
                # Non-critical: continue

            return True

        except Exception as e:
            logger.error(f"Failed to learn from successful automation: {e}", exc_info=True)
            return False

    def _build_qa_pattern(self, qa_pairs: list[dict[str, Any]]) -> str:
        """
        Build normalized Q&A pattern signature.
        
        Creates a pattern string that can be matched against similar Q&A sessions.
        
        Args:
            qa_pairs: List of Q&A pairs
            
        Returns:
            Normalized pattern string
        """
        if not qa_pairs:
            return "empty"
        
        # Extract question categories and answer types
        pattern_parts = []
        for qa in qa_pairs:
            question = qa.get('question', '')
            answer = qa.get('answer', '')
            category = qa.get('category', 'unknown')
            
            # Normalize: Extract key information
            # Question type (device_selection, action_type, etc.)
            if 'device' in question.lower() or 'which' in question.lower():
                pattern_parts.append(f"device_selection:{category}")
            elif 'action' in question.lower() or 'what' in question.lower():
                pattern_parts.append(f"action_type:{category}")
            elif 'when' in question.lower() or 'time' in question.lower():
                pattern_parts.append(f"timing:{category}")
            else:
                pattern_parts.append(f"other:{category}")
            
            # Answer type (entity_selected, text_answer, etc.)
            if qa.get('selected_entities'):
                pattern_parts.append(f"entities:{len(qa['selected_entities'])}")
            elif answer:
                # Simple answer type detection
                if answer.lower() in ['yes', 'no', 'true', 'false']:
                    pattern_parts.append("boolean")
                elif any(char.isdigit() for char in answer):
                    pattern_parts.append("numeric")
                else:
                    pattern_parts.append("text")
        
        return "|".join(pattern_parts)

    async def predict_automation_type(
        self,
        db: AsyncSession,
        qa_pairs: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """
        Predict automation type from Q&A pattern.
        
        Uses learned patterns to predict what type of automation the user wants.
        
        Args:
            db: Database session
            qa_pairs: Current Q&A pairs
            
        Returns:
            Predicted automation type and confidence, or None if no match
        """
        try:
            # Note: RAGClient dependency - will need to be addressed
            try:
                from ...services.rag.rag_client import RAGClient
            except ImportError:
                logger.warning("RAGClient not available - prediction disabled")
                return None

            # Build pattern from current Q&A
            current_pattern = self._build_qa_pattern(qa_pairs)
            
            # Search for similar patterns in knowledge base
            try:
                rag_client = RAGClient(
                    openvino_service_url=None,
                    db_session=db
                )
                
                # Search for similar patterns
                results = await rag_client.retrieve_hybrid(
                    query=f"Q&A Pattern: {current_pattern}",
                    knowledge_type='qa_automation_pattern',
                    top_k=5
                )
                
                if results:
                    # Find most common automation type
                    automation_types = {}
                    for result in results:
                        metadata = result.get('metadata', {})
                        automation_type = metadata.get('automation_type')
                        success_score = result.get('score', 0.5)
                        
                        if automation_type:
                            if automation_type not in automation_types:
                                automation_types[automation_type] = []
                            automation_types[automation_type].append(success_score)
                    
                    # Calculate average confidence per type
                    best_type = None
                    best_confidence = 0.0
                    
                    for automation_type, scores in automation_types.items():
                        avg_score = sum(scores) / len(scores)
                        if avg_score > best_confidence:
                            best_confidence = avg_score
                            best_type = automation_type
                    
                    if best_type:
                        return {
                            'automation_type': best_type,
                            'confidence': best_confidence,
                            'pattern_match': current_pattern
                        }
                
            except Exception as e:
                logger.warning(f"Failed to predict automation type: {e}")
                # Non-critical: return None
            
            return None

        except Exception as e:
            logger.error(f"Failed to predict automation type: {e}", exc_info=True)
            return None

    async def get_pattern_statistics(
        self,
        db: AsyncSession,
        days: int = 30
    ) -> dict[str, Any]:
        """
        Get pattern learning statistics.
        
        Args:
            db: Database session
            days: Number of days to look back
            
        Returns:
            Statistics dictionary
        """
        try:
            # Note: QAOutcome and ClarificationSessionDB models are in shared database
            try:
                from ...database.models import QAOutcome, ClarificationSessionDB
            except ImportError:
                logger.warning("QAOutcome/ClarificationSessionDB models not available")
                return {}

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Get successful automations
            query = select(QAOutcome, ClarificationSessionDB).join(
                ClarificationSessionDB,
                QAOutcome.session_id == ClarificationSessionDB.session_id
            ).where(
                QAOutcome.outcome_type == 'automation_created',
                QAOutcome.created_at >= cutoff_date,
                QAOutcome.days_active >= 30  # Only count successful (30+ days active)
            )

            result = await db.execute(query)
            rows = result.all()

            pattern_counts = {}
            for outcome, session in rows:
                # Build pattern from session Q&A
                qa_pairs = [
                    {
                        'question': q.get('question_text', ''),
                        'answer': next(
                            (a.get('answer_text', '') for a in (session.answers or []) if a.get('question_id') == q.get('id')),
                            ''
                        ),
                        'category': q.get('category', 'unknown')
                    }
                    for q in (session.questions or [])
                ]
                
                pattern = self._build_qa_pattern(qa_pairs)
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

            return {
                'total_successful': len(rows),
                'unique_patterns': len(pattern_counts),
                'top_patterns': dict(sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:10])
            }

        except Exception as e:
            logger.error(f"Failed to get pattern statistics: {e}", exc_info=True)
            return {}


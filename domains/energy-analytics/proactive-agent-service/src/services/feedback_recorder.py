"""
Feedback Loop — Outcome Recording (Epic 68, Story 68.5).

Records every suggestion/action outcome in the preference history table
and optionally in Memory Brain. Uses outcomes to update acceptance rates
per action type, time slot, and context.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select

try:
    from homeiq_memory import MemoryClient, MemoryType

    _MEMORY_AVAILABLE = True
except ImportError:
    MemoryClient = None  # type: ignore[assignment,misc]
    MemoryType = None  # type: ignore[assignment,misc]
    _MEMORY_AVAILABLE = False

from ..models.autonomous_action import ActionOutcome, ActionPreferenceHistory
from .confidence_scorer import ActionScore

logger = logging.getLogger(__name__)


class FeedbackRecorder:
    """Records action outcomes for preference learning."""

    def __init__(self, memory_client: Any = None):
        self.memory_client = memory_client

    async def record_outcome(
        self,
        action: dict[str, Any],
        outcome: ActionOutcome,
        score: ActionScore,
        time_slot: str = "afternoon",
    ) -> None:
        """Record an action outcome for preference learning.

        Updates the preference history table and optionally Memory Brain.
        """
        action_type = action.get("action_type", "unknown")
        entity_domain = action.get("entity_domain", "unknown")
        context_type = action.get("context_type", "unknown")

        # Update database preference history
        await self._update_preference_history(
            action_type=action_type,
            entity_domain=entity_domain,
            context_type=context_type,
            time_slot=time_slot,
            outcome=outcome,
        )

        # Record in Memory Brain for broader preference learning
        if self.memory_client and _MEMORY_AVAILABLE:
            await self._record_to_memory(action, outcome, score)

    async def _update_preference_history(
        self,
        action_type: str,
        entity_domain: str,
        context_type: str,
        time_slot: str,
        outcome: ActionOutcome,
    ) -> None:
        """Update or create a preference history entry."""
        from ..database import db

        try:
            async with db.get_db() as session:
                stmt = select(ActionPreferenceHistory).where(
                    ActionPreferenceHistory.action_type == action_type,
                    ActionPreferenceHistory.entity_domain == entity_domain,
                    ActionPreferenceHistory.context_type == context_type,
                    ActionPreferenceHistory.time_slot == time_slot,
                )
                result = await session.execute(stmt)
                history = result.scalar_one_or_none()

                if not history:
                    history = ActionPreferenceHistory(
                        action_type=action_type,
                        entity_domain=entity_domain,
                        context_type=context_type,
                        time_slot=time_slot,
                    )
                    session.add(history)

                # Update counts based on outcome
                if outcome == ActionOutcome.ACCEPTED:
                    history.acceptance_count += 1
                elif outcome == ActionOutcome.REJECTED:
                    history.rejection_count += 1
                elif outcome == ActionOutcome.AUTO_EXECUTED:
                    history.auto_execute_count += 1
                elif outcome == ActionOutcome.AUTO_EXECUTED_UNDONE:
                    history.undo_count += 1
                    # Undo counts against acceptance
                    history.rejection_count += 1

                # Recalculate acceptance rate
                total = history.acceptance_count + history.rejection_count + history.auto_execute_count
                if total > 0:
                    positive = history.acceptance_count + history.auto_execute_count - history.undo_count
                    history.acceptance_rate = max(0.0, min(1.0, positive / total))

                await session.commit()

        except Exception as e:
            logger.error("Failed to update preference history: %s", e)

    async def _record_to_memory(
        self,
        action: dict[str, Any],
        outcome: ActionOutcome,
        score: ActionScore,
    ) -> None:
        """Record outcome in Memory Brain for broader preference learning."""
        if not self.memory_client or not _MEMORY_AVAILABLE:
            return

        try:
            content = (
                f"User {outcome.value} proactive action: "
                f"{action.get('action_type')} on {action.get('entity_id')} "
                f"(confidence: {score.confidence}%, context: {action.get('context_type')}). "
                f"Reasoning: {action.get('reasoning', 'N/A')}"
            )

            memory_type = MemoryType.BEHAVIORAL
            await self.memory_client.save(
                content=content,
                memory_type=memory_type,
                metadata={
                    "source": "proactive_agent",
                    "action_type": action.get("action_type"),
                    "entity_domain": action.get("entity_domain"),
                    "outcome": outcome.value,
                    "confidence": score.confidence,
                },
            )
        except Exception as e:
            logger.debug("Failed to record outcome to Memory Brain: %s", e)

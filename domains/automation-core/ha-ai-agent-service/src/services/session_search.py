"""
Session Search — Cross-Conversation Recall (Epic 70, Story 70.6).

Searches past conversations via PostgreSQL full-text search.
Returns summarized relevant sessions as context for current conversation.

Adapted from Hermes session_search_tool.py.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select, text

from ..database import ConversationModel, MessageModel, db

logger = logging.getLogger(__name__)


@dataclass
class SessionSummary:
    """Summary of a past conversation session."""

    conversation_id: str
    title: str | None
    date: str
    match_count: int
    snippet: str
    summary: str | None = None


class SessionSearch:
    """Search past conversations for relevant context."""

    def __init__(self, summarize_fn: Any = None):
        """
        Args:
            summarize_fn: Async function(prompt: str) -> str for summarization.
                         Typically uses cheap model from Story 70.3.
        """
        self.summarize_fn = summarize_fn

    async def search(
        self,
        query: str,
        exclude_conversation_id: str | None = None,
        limit: int = 3,
    ) -> list[SessionSummary]:
        """Search past conversations using text matching.

        Args:
            query: Search query keywords.
            exclude_conversation_id: Current conversation ID to exclude.
            limit: Max sessions to return.

        Returns:
            List of SessionSummary with snippets and optional summaries.
        """
        try:
            async with db.get_db() as session:
                # Text search against messages content
                stmt = (
                    select(
                        MessageModel.conversation_id,
                        func.count(MessageModel.message_id).label("match_count"),
                        func.min(MessageModel.content).label("first_match"),
                    )
                    .where(MessageModel.content.ilike(f"%{query}%"))
                    .group_by(MessageModel.conversation_id)
                    .order_by(text("match_count DESC"))
                    .limit(limit * 2)  # Over-fetch for filtering
                )

                if exclude_conversation_id:
                    stmt = stmt.where(
                        MessageModel.conversation_id != exclude_conversation_id,
                    )

                result = await session.execute(stmt)
                rows = result.all()

                if not rows:
                    return []

                # Build summaries
                summaries: list[SessionSummary] = []
                for row in rows[:limit]:
                    conv_id = row.conversation_id
                    match_count = row.match_count

                    # Get conversation metadata
                    conv = await session.get(ConversationModel, conv_id)
                    title = conv.title if conv else None
                    date = conv.created_at.isoformat() if conv and conv.created_at else "unknown"

                    # Get matching message snippet
                    msg_stmt = (
                        select(MessageModel.content)
                        .where(
                            MessageModel.conversation_id == conv_id,
                            MessageModel.content.ilike(f"%{query}%"),
                        )
                        .limit(3)
                    )
                    msg_result = await session.execute(msg_stmt)
                    snippets = [r[0][:200] for r in msg_result.all()]
                    snippet = " ... ".join(snippets)

                    summary_obj = SessionSummary(
                        conversation_id=conv_id,
                        title=title,
                        date=date,
                        match_count=match_count,
                        snippet=snippet[:500],
                    )

                    # Optional summarization
                    if self.summarize_fn and snippet:
                        try:
                            prompt = (
                                f"Summarize this past conversation in 2-3 sentences. "
                                f"Focus on what was discussed and the outcome.\n\n"
                                f"Title: {title or 'Untitled'}\n"
                                f"Content: {snippet[:2000]}"
                            )
                            summary_obj.summary = await self.summarize_fn(prompt)
                        except Exception as e:
                            logger.debug("Session summarization failed: %s", e)

                    summaries.append(summary_obj)

                logger.info(
                    "Session search for '%s': found %d relevant sessions",
                    query[:50], len(summaries),
                )
                return summaries

        except Exception as e:
            logger.error("Session search failed: %s", e)
            return []

    @staticmethod
    def format_for_context(summaries: list[SessionSummary]) -> str:
        """Format session summaries for injection into conversation context."""
        if not summaries:
            return ""

        lines = ["## Related Past Conversations\n"]
        for s in summaries:
            title = s.title or "Untitled"
            text_body = s.summary or s.snippet[:200]
            lines.append(f"- **{title}** ({s.date[:10]}): {text_body}")

        return "\n".join(lines)

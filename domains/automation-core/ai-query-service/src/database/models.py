"""
Database models for AI Query Service

Epic 39, Story 39.10: Query Service Implementation
Models for storing query sessions and clarification tracking.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


def _utcnow() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(UTC)


def _new_uuid() -> str:
    """Generate a new UUID4 string for primary keys."""
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """Base class for query service database models."""


class AskAIQuery(Base):
    """Stores query sessions for the Ask AI tab.

    Each row represents a single natural-language query submitted by a user,
    together with its processing status, extracted entities, generated
    suggestions, and confidence score.
    """

    __tablename__ = "ask_ai_queries"
    __table_args__ = {"schema": "automation"}

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_uuid,
    )
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )
    entities: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    suggestions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow,
    )

    # Relationship to clarification sessions
    clarifications: Mapped[list["ClarificationSession"]] = relationship(
        back_populates="query", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AskAIQuery id={self.id} status={self.status}>"


class ClarificationSession(Base):
    """Tracks clarification questions and user responses for a query.

    When entity extraction has low confidence, the system generates
    clarification questions.  Each question/response pair is stored here,
    linked back to the originating :class:`AskAIQuery`.
    """

    __tablename__ = "clarification_sessions"
    __table_args__ = {"schema": "automation"}

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_uuid,
    )
    query_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("automation.ask_ai_queries.id"), nullable=False,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )

    # Relationship back to parent query
    query: Mapped["AskAIQuery"] = relationship(back_populates="clarifications")

    def __repr__(self) -> str:
        return f"<ClarificationSession id={self.id} resolved={self.resolved}>"

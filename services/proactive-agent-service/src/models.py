"""
Database models for Proactive Agent Service

SQLAlchemy 2.0 async models for suggestion storage.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Suggestion(Base):
    """Suggestion table for storing proactive automation suggestions"""

    __tablename__ = "suggestions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    context_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )  # pending, sent, approved, rejected
    quality_score: Mapped[float] = mapped_column(default=0.0, nullable=False)

    # Metadata (JSON)
    context_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    prompt_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    agent_response: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Suggestion(id={self.id}, status={self.status}, context_type={self.context_type})>"


# Indexes for performance
Index("idx_suggestions_status_created", Suggestion.status, Suggestion.created_at)
Index("idx_suggestions_context_type_status", Suggestion.context_type, Suggestion.status)


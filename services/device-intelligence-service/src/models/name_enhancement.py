"""
Device Name Enhancement - Database Models

SQLAlchemy models for name suggestions and preferences.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .database import Base


class NameSuggestion(Base):
    """Name suggestions for devices/entities"""
    __tablename__ = "name_suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String, ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    entity_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("device_entities.entity_id", ondelete="CASCADE"), index=True, nullable=True
    )

    # Names
    original_name: Mapped[str] = mapped_column(String, nullable=False)
    suggested_name: Mapped[str] = mapped_column(String, nullable=False)

    # Metadata
    confidence_score: Mapped[float | None] = mapped_column(Float)  # 0.0-1.0
    suggestion_source: Mapped[str] = mapped_column(String)  # "pattern", "ai", "local_llm", "preference"
    status: Mapped[str] = mapped_column(String, default="pending")  # "pending", "accepted", "rejected", "modified"
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)  # Why this name was suggested

    # Timestamps
    suggested_at: Mapped[datetime] = mapped_column(default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Learning data
    user_feedback: Mapped[str | None] = mapped_column(String, nullable=True)  # Optional user feedback

    # Relationships
    device: Mapped["Device"] = relationship("Device", backref="name_suggestions")

    # Indexes
    __table_args__ = (
        Index("idx_name_suggestions_device", "device_id"),
        Index("idx_name_suggestions_status", "status"),
        Index("idx_name_suggestions_confidence", "confidence_score"),
        Index("idx_name_suggestions_source", "suggestion_source"),
    )


class NamePreference(Base):
    """Learned user preferences (lightweight)"""
    __tablename__ = "name_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pattern_type: Mapped[str] = mapped_column(String, index=True)  # "naming_style", "modifier", "area_convention"
    pattern_data: Mapped[dict[str, Any] | None] = mapped_column(Text)  # JSON string (simple structure)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)  # 0.0-1.0
    learned_from_count: Mapped[int] = mapped_column(Integer, default=1)
    last_updated: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    # Indexes
    __table_args__ = (
        Index("idx_name_preferences_type", "pattern_type"),
    )


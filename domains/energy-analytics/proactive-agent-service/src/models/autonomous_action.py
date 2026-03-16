"""
Database models for autonomous agent actions (Epic 68).

Story 68.6: User preference configuration
Story 68.7: Audit trail with reversibility
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class RiskLevel(str, Enum):
    """Risk levels for proactive actions."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionOutcome(str, Enum):
    """Outcome types for autonomous actions and suggestions."""

    AUTO_EXECUTED = "auto_executed"
    AUTO_EXECUTED_UNDONE = "auto_executed_undone"
    SUGGESTED = "suggested"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPPRESSED = "suppressed"


class UserPreference(Base):
    """User preferences for autonomous agent behavior (Story 68.6)."""

    __tablename__ = "user_preferences"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    # Key-value preference storage
    preference_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    preference_value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<UserPreference(key={self.preference_key})>"


class AutonomousActionAudit(Base):
    """Audit trail for autonomous actions (Story 68.7).

    Every autonomous action is logged with full context for reversibility.
    """

    __tablename__ = "autonomous_action_audit"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    # Action details
    action_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
    )  # light, switch, climate, scene
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    action_description: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)

    # Scoring
    confidence_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)

    # State snapshots for rollback
    pre_action_state: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    post_action_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Outcome
    outcome: Mapped[str] = mapped_column(
        String(30), nullable=False, default=ActionOutcome.AUTO_EXECUTED.value,
    )
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Reversibility
    undone: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    undone_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    undo_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<AutonomousActionAudit(id={self.id}, "
            f"entity={self.entity_id}, outcome={self.outcome})>"
        )


# Indexes for efficient querying
Index(
    "idx_audit_executed_at",
    AutonomousActionAudit.executed_at.desc(),
)
Index(
    "idx_audit_entity_outcome",
    AutonomousActionAudit.entity_id,
    AutonomousActionAudit.outcome,
)
Index(
    "idx_audit_undone_expires",
    AutonomousActionAudit.undone,
    AutonomousActionAudit.undo_expires_at,
)


class ActionPreferenceHistory(Base):
    """Tracks acceptance/rejection history per action type for preference learning (Story 68.5).

    Aggregated scores used by the confidence scoring engine.
    """

    __tablename__ = "action_preference_history"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    # Action classification
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_domain: Mapped[str] = mapped_column(String(50), nullable=False)
    context_type: Mapped[str] = mapped_column(String(50), nullable=False)
    time_slot: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )  # morning, afternoon, evening, night

    # Preference scoring
    acceptance_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejection_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    auto_execute_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    undo_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Calculated acceptance rate (updated on each outcome)
    acceptance_rate: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)

    # Timestamps
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<ActionPreferenceHistory(action={self.action_type}, "
            f"domain={self.entity_domain}, rate={self.acceptance_rate:.2f})>"
        )


Index(
    "idx_preference_lookup",
    ActionPreferenceHistory.action_type,
    ActionPreferenceHistory.entity_domain,
    ActionPreferenceHistory.context_type,
    ActionPreferenceHistory.time_slot,
    unique=True,
)

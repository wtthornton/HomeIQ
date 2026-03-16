"""
User Profile Store (Epic 70, Story 70.7).

Stores cross-session user preference profiles that shape agent behavior.

Profile dimensions:
- confirmation_preference: always_confirm / confirm_risky / auto_approve_low_risk
- trigger_preference: motion / time_based / state_based
- naming_patterns: how user refers to rooms/devices
- risk_tolerance: conservative / moderate / aggressive
- communication_style: verbose / balanced / terse
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import DateTime, Float, Index, String, Text, func, select
from sqlalchemy.orm import Mapped, mapped_column

from ...database import Base, db

logger = logging.getLogger(__name__)

# Default TTL for user preferences (days)
DEFAULT_PROFILE_TTL_DAYS = 90


class UserProfile(Base):
    """Stores user preference dimensions with per-dimension scores."""

    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    dimension: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<UserProfile(user={self.user_id}, dim={self.dimension}, val={self.value})>"


Index(
    "idx_user_profiles_lookup",
    UserProfile.user_id,
    UserProfile.dimension,
    unique=True,
)


class ProfileStore:
    """CRUD operations for user preference profiles."""

    def __init__(self, ttl_days: int = DEFAULT_PROFILE_TTL_DAYS):
        self.ttl_days = ttl_days

    async def get_profile(self, user_id: str) -> dict[str, Any]:
        """Get all preference dimensions for a user.

        Returns dict of dimension → {value, confidence}.
        """
        async with db.get_db() as session:
            now = datetime.now(UTC)
            stmt = (
                select(UserProfile)
                .where(
                    UserProfile.user_id == user_id,
                    UserProfile.expires_at > now,
                )
            )
            result = await session.execute(stmt)
            profiles = result.scalars().all()

            return {
                p.dimension: {
                    "value": p.value,
                    "confidence": p.confidence,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                }
                for p in profiles
            }

    async def set_dimension(
        self,
        user_id: str,
        dimension: str,
        value: str,
        confidence: float = 0.5,
    ) -> None:
        """Set or update a preference dimension."""
        async with db.get_db() as session:
            stmt = select(UserProfile).where(
                UserProfile.user_id == user_id,
                UserProfile.dimension == dimension,
            )
            result = await session.execute(stmt)
            profile = result.scalar_one_or_none()

            expires = datetime.now(UTC) + timedelta(days=self.ttl_days)

            if profile:
                profile.value = value
                profile.confidence = confidence
                profile.expires_at = expires
            else:
                profile = UserProfile(
                    user_id=user_id,
                    dimension=dimension,
                    value=value,
                    confidence=confidence,
                    expires_at=expires,
                )
                session.add(profile)

            await session.commit()

    async def delete_profile(self, user_id: str) -> int:
        """Delete all preferences for a user. Returns count deleted."""
        async with db.get_db() as session:
            stmt = select(UserProfile).where(UserProfile.user_id == user_id)
            result = await session.execute(stmt)
            profiles = result.scalars().all()
            count = len(profiles)
            for p in profiles:
                await session.delete(p)
            await session.commit()
            return count

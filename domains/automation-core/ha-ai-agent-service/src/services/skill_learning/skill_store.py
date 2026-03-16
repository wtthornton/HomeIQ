"""
Skill Store — CRUD + Embedding Search (Epic 70, Story 70.1).

Stores reusable procedures in PostgreSQL with pgvector embeddings
for semantic recall. Skills are extracted from successful multi-turn
conversations and recalled when future requests match.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Index, Integer, String, Text, func, select
from sqlalchemy.orm import Mapped, mapped_column

from ...database import Base, db
from .skills_guard import SkillsGuard

logger = logging.getLogger(__name__)

# Lazy guard singleton
_guard: SkillsGuard | None = None


def _get_guard() -> SkillsGuard:
    global _guard
    if _guard is None:
        _guard = SkillsGuard()
    return _guard


class Skill(Base):
    """Stored procedure/skill extracted from successful conversations."""

    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    area_pattern: Mapped[str | None] = mapped_column(String(100), nullable=True)
    trigger_types: Mapped[list[str]] = mapped_column(JSON, default=list)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # Usage tracking
    use_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Skill(name={self.name}, category={self.category}, uses={self.use_count})>"


Index("idx_skills_category_area", Skill.category, Skill.area_pattern)
Index("idx_skills_use_count", Skill.use_count.desc())


class SkillStore:
    """CRUD operations for the skills table with security scanning."""

    async def create(
        self,
        name: str,
        description: str,
        category: str,
        body: str,
        area_pattern: str | None = None,
        trigger_types: list[str] | None = None,
    ) -> Skill | None:
        """Create a new skill after security scanning.

        Returns None if the skill fails security checks.
        """
        guard = _get_guard()
        if not guard.is_safe_for_storage(body, name):
            logger.warning("Skill '%s' BLOCKED by security scan", name)
            return None

        async with db.get_db() as session:
            skill = Skill(
                name=name,
                description=description,
                category=category,
                body=body,
                area_pattern=area_pattern,
                trigger_types=trigger_types or [],
            )
            session.add(skill)
            await session.commit()
            await session.refresh(skill)
            logger.info("Skill created: '%s' (category=%s)", name, category)
            return skill

    async def get(self, skill_id: str) -> Skill | None:
        """Get a skill by ID."""
        async with db.get_db() as session:
            return await session.get(Skill, skill_id)

    async def search_by_category(
        self,
        category: str,
        area_pattern: str | None = None,
        limit: int = 5,
    ) -> list[Skill]:
        """Search skills by category and optional area pattern."""
        async with db.get_db() as session:
            stmt = select(Skill).where(Skill.category == category)
            if area_pattern:
                stmt = stmt.where(Skill.area_pattern == area_pattern)
            stmt = stmt.order_by(Skill.use_count.desc()).limit(limit)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def search_by_text(
        self,
        query: str,
        limit: int = 3,
    ) -> list[Skill]:
        """Text-based skill search (name + description).

        For semantic search via embeddings, use SkillRecall instead.
        """
        async with db.get_db() as session:
            stmt = (
                select(Skill)
                .where(
                    Skill.name.ilike(f"%{query}%")
                    | Skill.description.ilike(f"%{query}%")
                )
                .order_by(Skill.use_count.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def record_usage(self, skill_id: str) -> None:
        """Increment use count and update last_used_at."""
        async with db.get_db() as session:
            skill = await session.get(Skill, skill_id)
            if skill:
                skill.use_count += 1
                skill.last_used_at = datetime.now(UTC)
                await session.commit()

    async def delete(self, skill_id: str) -> bool:
        """Delete a skill by ID."""
        async with db.get_db() as session:
            skill = await session.get(Skill, skill_id)
            if skill:
                await session.delete(skill)
                await session.commit()
                return True
            return False

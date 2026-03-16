"""
Skill Recall (Epic 70, Story 70.1).

Queries stored skills by text similarity, category, and area filter.
Returns formatted skills for injection into system prompt.
"""

from __future__ import annotations

import logging
from typing import Any

from .skill_store import Skill, SkillStore
from .skills_guard import SkillsGuard

logger = logging.getLogger(__name__)

# Token budget for skill injection into system prompt
SKILL_TOKEN_BUDGET = 500


class SkillRecall:
    """Recall relevant skills for context injection."""

    def __init__(
        self,
        store: SkillStore | None = None,
        guard: SkillsGuard | None = None,
    ):
        self.store = store or SkillStore()
        self.guard = guard or SkillsGuard()

    async def recall_for_message(
        self,
        user_message: str,
        category: str | None = None,
        area: str | None = None,
        limit: int = 3,
    ) -> str:
        """Recall relevant skills and format for system prompt injection.

        Args:
            user_message: The user's current message (for text search).
            category: Optional category filter.
            area: Optional area filter.
            limit: Max skills to return.

        Returns:
            Formatted string for system prompt (within SKILL_TOKEN_BUDGET).
        """
        skills: list[Skill] = []

        # Search by category if provided
        if category:
            skills = await self.store.search_by_category(
                category=category, area_pattern=area, limit=limit,
            )

        # Fallback to text search
        if not skills:
            # Extract key terms from user message
            query = " ".join(user_message.split()[:5])
            skills = await self.store.search_by_text(query=query, limit=limit)

        if not skills:
            return ""

        # Security filter — exclude flagged skills
        skill_dicts = [
            {"name": s.name, "body": s.body, "category": s.category}
            for s in skills
        ]
        safe_skills = self.guard.filter_safe_skills(skill_dicts)

        if not safe_skills:
            return ""

        # Format within token budget
        lines = ["## Relevant Procedures\n"]
        char_budget = SKILL_TOKEN_BUDGET * 4  # ~4 chars per token

        for skill_dict in safe_skills:
            entry = f"### {skill_dict['name']}\n{skill_dict['body'][:300]}\n"
            if sum(len(l) for l in lines) + len(entry) > char_budget:
                break
            lines.append(entry)

        # Record usage
        for skill in skills[:len(safe_skills)]:
            await self.store.record_usage(skill.id)

        formatted = "\n".join(lines)
        logger.info(
            "Recalled %d skills (%d chars) for injection",
            len(safe_skills), len(formatted),
        )
        return formatted

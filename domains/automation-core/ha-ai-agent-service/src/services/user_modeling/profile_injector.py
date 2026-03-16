"""
Profile Injector (Epic 70, Story 70.7).

Loads user profile and formats it for injection into the system prompt
as a "## User Preferences" section (200-token budget).
"""

from __future__ import annotations

import logging
from typing import Any

from .profile_store import ProfileStore

logger = logging.getLogger(__name__)

# Token budget for profile injection
PROFILE_TOKEN_BUDGET = 200

# Human-readable labels for dimensions
DIMENSION_LABELS = {
    "confirmation_preference": "Confirmation",
    "trigger_preference": "Preferred triggers",
    "risk_tolerance": "Risk tolerance",
    "communication_style": "Communication",
}

VALUE_DESCRIPTIONS = {
    # confirmation_preference
    "always_confirm": "always asks for confirmation",
    "confirm_risky": "only confirms risky actions",
    "auto_approve_low_risk": "trusts auto-execution for safe actions",
    # trigger_preference
    "motion": "prefers motion-based triggers",
    "time_based": "prefers time-based triggers",
    "state_based": "prefers state-based triggers",
    "mixed": "uses various trigger types",
    # risk_tolerance
    "conservative": "cautious, prefers manual approval",
    "moderate": "balanced approach to automation",
    "aggressive": "comfortable with autonomous actions",
    # communication_style
    "verbose": "prefers detailed explanations",
    "balanced": "moderate detail level",
    "terse": "prefers brief, direct responses",
}


class ProfileInjector:
    """Formats user profile for system prompt injection."""

    def __init__(self, profile_store: ProfileStore | None = None):
        self.store = profile_store or ProfileStore()

    async def get_profile_context(self, user_id: str) -> str:
        """Load and format user profile for system prompt.

        Returns:
            Formatted string within PROFILE_TOKEN_BUDGET, or empty string.
        """
        try:
            profile = await self.store.get_profile(user_id)
            if not profile:
                return ""

            lines = ["## User Preferences\n"]
            char_budget = PROFILE_TOKEN_BUDGET * 4

            for dimension, data in profile.items():
                if sum(len(l) for l in lines) > char_budget:
                    break

                label = DIMENSION_LABELS.get(dimension, dimension)
                value = data.get("value", "")
                description = VALUE_DESCRIPTIONS.get(value, value)
                confidence = data.get("confidence", 0.5)

                if confidence >= 0.6:
                    lines.append(f"- {label}: {description}")
                elif confidence >= 0.4:
                    lines.append(f"- {label}: likely {description}")

            if len(lines) <= 1:
                return ""

            result = "\n".join(lines)
            logger.debug(
                "Profile injection for user %s: %d dimensions, %d chars",
                user_id, len(lines) - 1, len(result),
            )
            return result

        except Exception as e:
            logger.debug("Profile injection failed: %s", e)
            return ""

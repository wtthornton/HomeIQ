"""
Preference Extractor (Epic 70, Story 70.7).

Background task that analyzes conversations for preference signals
and updates the user profile store.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from .profile_store import ProfileStore

logger = logging.getLogger(__name__)

# Dimensions to extract
DIMENSIONS = [
    "confirmation_preference",
    "trigger_preference",
    "risk_tolerance",
    "communication_style",
]

EXTRACTION_PROMPT = """Analyze this conversation for user preference signals.
Extract any preferences for these dimensions:

1. confirmation_preference: Does the user want to confirm every action, only risky ones, or auto-approve?
   Values: always_confirm, confirm_risky, auto_approve_low_risk
2. trigger_preference: Does the user prefer motion, time-based, or state-based automations?
   Values: motion, time_based, state_based, mixed
3. risk_tolerance: Is the user conservative, moderate, or aggressive about automation?
   Values: conservative, moderate, aggressive
4. communication_style: Does the user prefer verbose explanations or terse responses?
   Values: verbose, balanced, terse

Return a JSON object with only the dimensions you can confidently identify.
For each dimension, include "value" and "confidence" (0.0-1.0).
If no preferences are detectable, return an empty object {{}}.

Conversation:
{conversation}

Response (JSON only):"""


class PreferenceExtractor:
    """Extracts user preferences from conversation analysis."""

    def __init__(
        self,
        profile_store: ProfileStore | None = None,
        openai_client: Any = None,
    ):
        self.store = profile_store or ProfileStore()
        self.openai_client = openai_client

    async def extract_from_conversation(
        self,
        user_id: str,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Analyze a conversation and update user profile.

        Args:
            user_id: User identifier.
            messages: Conversation messages.

        Returns:
            Dict of extracted preferences.
        """
        if not self.openai_client or len(messages) < 3:
            return {}

        try:
            # Format conversation
            conv_text = "\n".join(
                f"[{m.get('role', '?')}]: {m.get('content', '')[:200]}"
                for m in messages[-20:]  # Last 20 messages
            )

            prompt = EXTRACTION_PROMPT.format(conversation=conv_text[:4000])

            response = await self.openai_client.chat_completion_simple(
                prompt=prompt,
                temperature=0.2,
                max_tokens=300,
            )

            if not response:
                return {}

            # Parse response
            preferences = json.loads(response)
            if not isinstance(preferences, dict):
                return {}

            # Update profile store
            for dimension, data in preferences.items():
                if dimension not in DIMENSIONS:
                    continue
                if not isinstance(data, dict):
                    continue
                value = data.get("value", "")
                confidence = data.get("confidence", 0.5)
                if value and confidence >= 0.4:
                    await self.store.set_dimension(
                        user_id=user_id,
                        dimension=dimension,
                        value=value,
                        confidence=confidence,
                    )

            logger.info(
                "Extracted %d preferences for user %s",
                len(preferences), user_id,
            )
            return preferences

        except (json.JSONDecodeError, Exception) as e:
            logger.debug("Preference extraction failed: %s", e)
            return {}

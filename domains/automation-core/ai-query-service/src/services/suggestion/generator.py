"""
Suggestion Generator Service

Epic 39, Story 39.10: Query Service Migration
Handles automation suggestion generation from queries.

V1 implementation with two modes:
  1. OpenAI-based generation (when an ``openai_client`` is provided).
  2. Keyword-matching fallback (works without any external service).
"""

import json
import logging
import re
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings

logger = logging.getLogger(__name__)

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def _sanitize_for_log(text: str, max_length: int = 100) -> str:
    """Strip control characters and truncate user input for safe logging."""
    return _CONTROL_CHAR_RE.sub("", text)[:max_length]


# ---------------------------------------------------------------------------
# Keyword-based template catalogue (fallback when no LLM is available)
# ---------------------------------------------------------------------------

_KEYWORD_TEMPLATES: list[dict[str, Any]] = [
    {
        "template_id": "light_on_off",
        "keywords": ["turn on", "turn off", "switch on", "switch off", "light", "lamp", "lights"],
        "description": "Turn lights on or off",
        "category": "lighting",
        "default_params": {"action": "toggle", "domain": "light"},
    },
    {
        "template_id": "scheduled_task",
        "keywords": ["schedule", "every day", "at \\d", "every morning", "every evening", "timer", "cron"],
        "description": "Run an action at a scheduled time",
        "category": "scheduling",
        "default_params": {"trigger_platform": "time"},
    },
    {
        "template_id": "presence_automation",
        "keywords": ["leave", "arrive", "home", "away", "presence", "when i get", "when i come"],
        "description": "Trigger an action based on presence detection",
        "category": "presence",
        "default_params": {"trigger_platform": "state", "domain": "person"},
    },
    {
        "template_id": "climate_control",
        "keywords": ["temperature", "thermostat", "heating", "cooling", "ac", "air conditioner", "climate", "warm", "cool"],
        "description": "Control heating, cooling, or climate settings",
        "category": "climate",
        "default_params": {"domain": "climate"},
    },
    {
        "template_id": "motion_trigger",
        "keywords": ["motion", "movement", "sensor", "detect", "someone"],
        "description": "Trigger an action when motion is detected",
        "category": "security",
        "default_params": {"trigger_platform": "state", "domain": "binary_sensor"},
    },
    {
        "template_id": "door_window_alert",
        "keywords": ["door", "window", "open", "close", "lock", "unlock"],
        "description": "Alert or act when a door/window opens or closes",
        "category": "security",
        "default_params": {"trigger_platform": "state", "domain": "binary_sensor"},
    },
]


class SuggestionGenerator:
    """
    Service for generating automation suggestions from queries.

    When an ``openai_client`` is available the generator sends a structured
    prompt to the LLM and parses the response into suggestion dicts.

    When no client is available, a lightweight keyword-matching engine maps
    the query to built-in template suggestions.
    """

    def __init__(self, openai_client=None, rag_client=None):
        self.openai_client = openai_client
        self.rag_client = rag_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate(
        self,
        query: str,
        entities: list[dict[str, Any]],
        _user_id: str | None = None,
        _clarification_context: dict[str, Any] | None = None,
        _query_id: str | None = None,
        area_filter: str | None = None,
        _db: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        """Generate automation suggestions from query and entities.

        Args:
            query: Natural language query.
            entities: Extracted entities from the entity-extraction step.
            user_id: User ID for personalisation.
            clarification_context: Clarification context (if any).
            query_id: Query ID for tracking.
            area_filter: Area filter (e.g. ``"office"`` or ``"office,kitchen"``).
            db: Database session (reserved for future persistence).

        Returns:
            List of suggestion dicts, each with at least:
            ``suggestion_id``, ``template_id``, ``description``,
            ``confidence``, ``parameters``.
        """
        logger.info(
            "[SUGGEST] Generating suggestions for query: %s...",
            _sanitize_for_log(query, 50),
        )

        if self.openai_client:
            try:
                return await self._generate_with_openai(
                    query=query,
                    entities=entities,
                    area_filter=area_filter,
                )
            except Exception:
                logger.warning(
                    "OpenAI suggestion generation failed, falling back to keyword matching",
                    exc_info=True,
                )

        # Fallback: keyword-based matching (always available)
        return self._generate_with_keywords(
            query=query,
            entities=entities,
            area_filter=area_filter,
        )

    # ------------------------------------------------------------------
    # OpenAI-based generation
    # ------------------------------------------------------------------

    async def _generate_with_openai(
        self,
        query: str,
        entities: list[dict[str, Any]],
        area_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Use the OpenAI client to produce structured suggestions."""
        entity_summary = self._build_entity_summary(entities)
        area_clause = f"\nArea filter: {area_filter}" if area_filter else ""

        system_prompt = (
            "You are a Home Assistant automation expert. Given a user query "
            "and a list of matched entities, suggest up to 3 automations.\n\n"
            "Return ONLY a JSON array where each element has:\n"
            '  - "template_id": short snake_case identifier\n'
            '  - "description": one-sentence human-readable description\n'
            '  - "confidence": float 0-1 indicating how well this matches the query\n'
            '  - "parameters": object with relevant Home Assistant parameters '
            "(trigger, action, conditions)\n\n"
            "Return ONLY the JSON array, no markdown, no explanation."
        )

        user_prompt = (
            f"Query: {query}\n"
            f"Matched entities: {entity_summary}"
            f"{area_clause}"
        )

        # Delegate to the injected client (expected to expose a responses interface)
        response = await self.openai_client.responses.create(
            model=settings.openai_model,
            instructions=system_prompt,
            input=user_prompt,
            max_output_tokens=1500,
            text={"format": {"type": "json_object"}},
            store=False,
        )

        raw_text = response.output_text or "[]"
        # Strip optional markdown fence
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            raw_text = "\n".join(lines[1:-1])

        parsed = json.loads(raw_text)

        # The LLM may return either a list or a dict with a "suggestions" key
        if isinstance(parsed, dict):
            suggestions = parsed.get("suggestions", [])
        elif isinstance(parsed, list):
            suggestions = parsed
        else:
            suggestions = []

        # Normalise and add IDs
        return [self._normalise_suggestion(s) for s in suggestions[:5]]

    # ------------------------------------------------------------------
    # Keyword-based fallback generation
    # ------------------------------------------------------------------

    def _generate_with_keywords(
        self,
        query: str,
        entities: list[dict[str, Any]],
        area_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Match query text against built-in keyword templates."""
        query_lower = query.lower()
        matches: list[dict[str, Any]] = []

        for template in _KEYWORD_TEMPLATES:
            score = self._keyword_match_score(query_lower, template["keywords"])
            if score > 0:
                params = dict(template["default_params"])
                # Enrich with entity information
                params["entities"] = [
                    e.get("entity_id", e.get("name", ""))
                    for e in entities
                    if e.get("entity_id") or e.get("name")
                ]
                if area_filter:
                    params["area"] = area_filter

                matches.append({
                    "suggestion_id": f"sug-{uuid.uuid4().hex[:8]}",
                    "template_id": template["template_id"],
                    "description": template["description"],
                    "confidence": min(0.85, 0.4 + score * 0.15),
                    "parameters": params,
                    "source": "keyword_match",
                })

        # Sort by confidence descending and take top 3
        matches.sort(key=lambda s: s["confidence"], reverse=True)
        return matches[:3]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _keyword_match_score(query_lower: str, keywords: list[str]) -> int:
        """Return the number of *keywords* that match inside *query_lower*."""
        score = 0
        for kw in keywords:
            if re.search(kw, query_lower):
                score += 1
        return score

    @staticmethod
    def _build_entity_summary(entities: list[dict[str, Any]]) -> str:
        """Build a concise text summary of entities for the LLM prompt."""
        if not entities:
            return "none"
        parts: list[str] = []
        for ent in entities[:10]:
            eid = ent.get("entity_id", "")
            name = ent.get("name", ent.get("friendly_name", ""))
            etype = ent.get("type", ent.get("domain", ""))
            parts.append(f"{eid or name} ({etype})")
        return ", ".join(parts)

    @staticmethod
    def _normalise_suggestion(raw: dict[str, Any]) -> dict[str, Any]:
        """Ensure every suggestion dict has the required keys."""
        return {
            "suggestion_id": f"sug-{uuid.uuid4().hex[:8]}",
            "template_id": raw.get("template_id", "custom"),
            "description": raw.get("description", ""),
            "confidence": float(raw.get("confidence", 0.5)),
            "parameters": raw.get("parameters", {}),
            "source": "openai",
        }

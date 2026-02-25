"""
Clarification Service

Epic 39, Story 39.10: Query Service Migration
Handles clarification detection and question generation.

V1 implementation: pure logic-based ambiguity detection and question
generation. Works without OpenAI or external detectors.
"""

import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ..confidence import calculate_entity_confidence

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Patterns used for vagueness detection
# ---------------------------------------------------------------------------
_ACTION_WORDS = re.compile(
    r"\b(turn|switch|set|dim|brighten|lock|unlock|open|close|start|stop|"
    r"increase|decrease|enable|disable|activate|toggle)\b",
    re.IGNORECASE,
)
_DEVICE_WORDS = re.compile(
    r"\b(light|lamp|fan|thermostat|heater|ac|air.?conditioner|plug|switch|"
    r"sensor|lock|door|window|blind|curtain|speaker|tv|television|camera|"
    r"vacuum|humidifier|dehumidifier)\b",
    re.IGNORECASE,
)
_AREA_WORDS = re.compile(
    r"\b(kitchen|bedroom|bathroom|living.?room|office|garage|basement|attic|"
    r"hallway|porch|patio|garden|dining|laundry|nursery|study|den|foyer|"
    r"upstairs|downstairs)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class Ambiguity:
    """Represents a single ambiguity detected in a query."""

    type: str  # multiple_entities | missing_area | vague_action | low_confidence
    description: str
    affected_entities: list[dict[str, Any]] = field(default_factory=list)


class ClarificationService:
    """
    Service for detecting clarification needs and generating questions.

    Works entirely with rule-based logic -- no LLM required.
    External ``detector``, ``question_generator``, and ``confidence_calculator``
    can optionally be injected to override the built-in behaviour.
    """

    def __init__(
        self,
        detector=None,
        question_generator=None,
        confidence_calculator=None,
    ):
        self.detector = detector
        self.question_generator = question_generator
        self.confidence_calculator = confidence_calculator

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def detect_clarification_needs(
        self,
        query: str,
        entities: list[dict[str, Any]],
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Detect if clarification is needed for the query.

        Args:
            query: Natural language query.
            entities: Extracted entities from the entity-extraction step.
            db: Database session (reserved for future persistence).

        Returns:
            Dictionary with ``needed``, ``session_id``, ``questions``,
            ``confidence``, ``threshold``, and ``ambiguities`` keys.
        """
        if not settings.clarification_enabled:
            return {"needed": False}

        try:
            # Step 1 -- detect ambiguities
            ambiguities = self._detect_ambiguities(query, entities)

            # Step 2 -- calculate confidence (accounts for ambiguities)
            confidence = self._calculate_confidence(ambiguities, entities)

            # Step 3 -- decide whether clarification is needed
            threshold = settings.clarification_confidence_threshold
            needs_clarification = bool(ambiguities) and confidence < threshold

            if needs_clarification:
                questions = self._generate_questions(ambiguities)
                # Respect max_clarification_questions setting
                max_q = settings.max_clarification_questions
                questions = questions[:max_q]

                return {
                    "needed": True,
                    "session_id": f"clarify-{uuid.uuid4().hex[:8]}",
                    "questions": questions,
                    "confidence": confidence,
                    "threshold": threshold,
                    "ambiguities": [
                        {
                            "type": a.type,
                            "description": a.description,
                            "affected_entities": a.affected_entities,
                        }
                        for a in ambiguities
                    ],
                }

            return {"needed": False, "confidence": confidence}

        except Exception as e:
            logger.warning("Clarification detection failed: %s", e)
            return {"needed": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Ambiguity detection
    # ------------------------------------------------------------------

    def _detect_ambiguities(
        self,
        query: str,
        entities: list[dict[str, Any]],
    ) -> list[Ambiguity]:
        """Detect ambiguities in *query* given the extracted *entities*.

        Checks performed:
        1. Multiple entities of the same type in the same area.
        2. No specific area mentioned and entities span multiple areas.
        3. No recognisable action verb in the query.
        4. Any entity with confidence below the threshold.
        """
        # Allow injected detector to take over
        if self.detector:
            return self.detector(query, entities)

        ambiguities: list[Ambiguity] = []

        # --- 1. Multiple entities of the same type -----------------------
        ambiguities.extend(self._check_multiple_entities(entities))

        # --- 2. Missing area ---------------------------------------------
        if not _AREA_WORDS.search(query) and entities:
            areas = {
                (e.get("area_id") or e.get("area") or "")
                for e in entities
            }
            areas.discard("")
            if len(areas) > 1:
                ambiguities.append(
                    Ambiguity(
                        type="missing_area",
                        description="Query does not specify an area and entities span multiple rooms.",
                        affected_entities=entities,
                    )
                )

        # --- 3. Vague action ---------------------------------------------
        if not _ACTION_WORDS.search(query) and entities:
            ambiguities.append(
                Ambiguity(
                    type="vague_action",
                    description="No specific action detected in the query.",
                    affected_entities=entities[:1],
                )
            )

        # --- 4. Low-confidence entities ----------------------------------
        threshold = settings.clarification_confidence_threshold
        for entity in entities:
            conf = entity.get("confidence", 1.0)
            if conf < threshold:
                ambiguities.append(
                    Ambiguity(
                        type="low_confidence",
                        description=(
                            f"Entity '{entity.get('name', entity.get('entity_id', 'unknown'))}' "
                            f"matched with low confidence ({conf:.2f})."
                        ),
                        affected_entities=[entity],
                    )
                )

        return ambiguities

    @staticmethod
    def _check_multiple_entities(
        entities: list[dict[str, Any]],
    ) -> list[Ambiguity]:
        """Return an ``Ambiguity`` if several entities share the same type."""
        type_groups: dict[str, list[dict[str, Any]]] = {}
        for entity in entities:
            etype = entity.get("type", "unknown")
            type_groups.setdefault(etype, []).append(entity)

        ambiguities: list[Ambiguity] = []
        for etype, group in type_groups.items():
            if len(group) > 1:
                names = [
                    e.get("name", e.get("friendly_name", e.get("entity_id", "?")))
                    for e in group
                ]
                ambiguities.append(
                    Ambiguity(
                        type="multiple_entities",
                        description=(
                            f"Multiple {etype} entities matched: {', '.join(names)}."
                        ),
                        affected_entities=group,
                    )
                )
        return ambiguities

    # ------------------------------------------------------------------
    # Question generation
    # ------------------------------------------------------------------

    def _generate_questions(self, ambiguities: list[Ambiguity]) -> list[str]:
        """Generate human-friendly clarifying questions from *ambiguities*."""
        if self.question_generator:
            return self.question_generator(ambiguities)

        questions: list[str] = []
        for amb in ambiguities:
            question = self._question_for_ambiguity(amb)
            if question and question not in questions:
                questions.append(question)
        return questions

    @staticmethod
    def _question_for_ambiguity(amb: Ambiguity) -> str:
        """Map a single ``Ambiguity`` to a clarifying question string."""
        if amb.type == "multiple_entities":
            names = [
                e.get("name", e.get("friendly_name", e.get("entity_id", "?")))
                for e in amb.affected_entities
            ]
            joined = ", ".join(names)
            return f"Which device did you mean: {joined}?"

        if amb.type == "missing_area":
            return "Which room should this apply to?"

        if amb.type == "vague_action":
            if amb.affected_entities:
                name = amb.affected_entities[0].get(
                    "name",
                    amb.affected_entities[0].get("friendly_name", "the device"),
                )
                return f"What would you like to do with {name}?"
            return "What action would you like to perform?"

        if amb.type == "low_confidence":
            if amb.affected_entities:
                name = amb.affected_entities[0].get(
                    "name",
                    amb.affected_entities[0].get("friendly_name", "unknown"),
                )
                return f"Did you mean {name}?"
            return "Could you clarify which device you meant?"

        return ""

    # ------------------------------------------------------------------
    # Confidence calculation
    # ------------------------------------------------------------------

    def _calculate_confidence(
        self,
        ambiguities: list[Ambiguity],
        entities: list[dict[str, Any]],
    ) -> float:
        """Calculate confidence accounting for detected ambiguities.

        * Starts from entity-based confidence (via ``calculate_entity_confidence``).
        * Reduces by 0.2 per ambiguity.
        * Floors at 0.1.
        """
        if self.confidence_calculator:
            return self.confidence_calculator(ambiguities, entities)

        base = calculate_entity_confidence(entities)

        if not ambiguities:
            return base

        penalty = len(ambiguities) * 0.2
        return max(0.1, base - penalty)

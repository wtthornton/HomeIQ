"""
Enhanced Confidence Calculator

Multi-factor confidence scoring with explanations.
Consolidates confidence calculation logic.

Created: Phase 2 - Core Service Refactoring
"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceScore:
    """Confidence score with factor breakdown"""
    overall: float
    factors: dict[str, float]
    explanation: str
    breakdown: dict[str, Any] | None = None


class EnhancedConfidenceCalculator:
    """
    Multi-factor confidence calculator with explanations.

    Calculates confidence based on:
    - Entity match quality
    - Ambiguity penalty
    - Historical success (RAG matches)
    - Query completeness
    - Location match accuracy
    """

    def __init__(self):
        """Initialize confidence calculator"""
        # Factor weights
        self.weights = {
            "entity_match": 0.3,
            "ambiguity_penalty": 0.25,
            "historical_success": 0.2,
            "query_completeness": 0.15,
            "location_match": 0.1,
        }

        logger.info("EnhancedConfidenceCalculator initialized")

    async def calculate_confidence(
        self,
        query: str,
        entities: list[dict],
        ambiguities: list[Any],
        validation_result: dict,
        rag_matches: list | None = None,
    ) -> ConfidenceScore:
        """
        Calculate multi-factor confidence score.

        Args:
            query: User query
            entities: Extracted entities
            ambiguities: Detected ambiguities
            validation_result: Entity validation results
            rag_matches: Optional RAG matches for historical success

        Returns:
            ConfidenceScore with breakdown
        """
        # Calculate individual factors
        factors = {
            "entity_match": self._score_entity_matches(entities, validation_result),
            "ambiguity_penalty": self._score_ambiguities(ambiguities),
            "historical_success": self._score_rag_matches(rag_matches),
            "query_completeness": self._score_query_completeness(query),
            "location_match": self._score_location_accuracy(query, entities),
        }

        # Calculate weighted average
        overall = self._weighted_average(factors)

        # Generate explanation
        explanation = self._generate_explanation(factors, overall)

        # Detailed breakdown
        breakdown = self._detailed_breakdown(factors)

        return ConfidenceScore(
            overall=overall,
            factors=factors,
            explanation=explanation,
            breakdown=breakdown,
        )

    def _score_entity_matches(self, entities: list[dict], validation_result: dict) -> float:
        """Score entity match quality"""
        if not entities:
            return 0.0

        if not validation_result:
            return 0.5  # Neutral if no validation

        # Count validated entities
        validated_count = sum(1 for v in validation_result.values() if v)
        total_count = len(validation_result)

        if total_count == 0:
            return 0.5

        # Score based on validation rate
        validation_rate = validated_count / total_count

        # Boost score if we have many entities
        entity_bonus = min(0.1, len(entities) * 0.02)

        return min(1.0, validation_rate + entity_bonus)

    def _score_ambiguities(self, ambiguities: list[Any]) -> float:
        """Score ambiguity penalty (lower is better, so we invert)"""
        if not ambiguities:
            return 1.0  # No ambiguities = perfect

        # Penalty based on number and severity of ambiguities
        penalty = len(ambiguities) * 0.15

        # Check for critical ambiguities
        critical_count = sum(1 for a in ambiguities if hasattr(a, "severity") and str(a.severity) == "CRITICAL")
        penalty += critical_count * 0.2

        return max(0.0, 1.0 - penalty)

    def _score_rag_matches(self, rag_matches: list | None) -> float:
        """Score historical success from RAG matches"""
        if not rag_matches:
            return 0.5  # Neutral if no historical data

        # Score based on number and quality of matches
        match_count = len(rag_matches)

        # Average success score if available
        if match_count > 0:
            scores = [m.get("success_score", 0.5) for m in rag_matches if isinstance(m, dict)]
            if scores:
                return sum(scores) / len(scores)

        # Default based on match count
        return min(1.0, 0.5 + (match_count * 0.1))

    def _score_query_completeness(self, query: str) -> float:
        """Score query completeness"""
        if not query:
            return 0.0

        query_lower = query.lower()

        # Check for key components
        has_device = any(kw in query_lower for kw in ["light", "switch", "sensor", "thermostat", "door", "lock"])
        has_action = any(kw in query_lower for kw in ["turn", "set", "open", "close", "lock", "unlock"])
        has_condition = any(kw in query_lower for kw in ["when", "if", "after", "before"])

        score = 0.0
        if has_device:
            score += 0.4
        if has_action:
            score += 0.3
        if has_condition:
            score += 0.3

        # Boost for longer, more detailed queries
        word_count = len(query.split())
        if word_count > 10:
            score = min(1.0, score + 0.1)

        return score

    def _score_location_accuracy(self, query: str, entities: list[dict]) -> float:
        """Score location match accuracy"""
        if not entities:
            return 0.5

        # Check if entities have location/area information
        entities_with_location = sum(1 for e in entities if e.get("area_id") or e.get("area_name"))

        if len(entities) == 0:
            return 0.5

        return entities_with_location / len(entities)

    def _weighted_average(self, factors: dict[str, float]) -> float:
        """Calculate weighted average of factors"""
        total = 0.0
        total_weight = 0.0

        for factor_name, score in factors.items():
            weight = self.weights.get(factor_name, 0.0)
            total += score * weight
            total_weight += weight

        if total_weight == 0:
            return 0.5

        return total / total_weight

    def _generate_explanation(self, factors: dict[str, float], overall: float) -> str:
        """Generate human-readable explanation"""
        parts = []

        if factors.get("entity_match", 0) > 0.8:
            parts.append("Strong entity matches found")
        elif factors.get("entity_match", 0) < 0.5:
            parts.append("Weak entity matches")

        if factors.get("ambiguity_penalty", 1.0) < 0.7:
            parts.append("Some ambiguities detected")

        if factors.get("historical_success", 0.5) > 0.7:
            parts.append("Similar successful queries found")

        if factors.get("query_completeness", 0.5) < 0.5:
            parts.append("Query may need more details")

        if overall > 0.8:
            return f"High confidence ({overall:.0%}): {', '.join(parts) if parts else 'All factors positive'}"
        if overall > 0.6:
            return f"Moderate confidence ({overall:.0%}): {', '.join(parts) if parts else 'Mostly positive'}"
        return f"Low confidence ({overall:.0%}): {', '.join(parts) if parts else 'Several factors need improvement'}"

    def _detailed_breakdown(self, factors: dict[str, float]) -> dict[str, Any]:
        """Generate detailed breakdown"""
        return {
            "entity_match": {
                "score": factors.get("entity_match", 0),
                "weight": self.weights.get("entity_match", 0),
                "contribution": factors.get("entity_match", 0) * self.weights.get("entity_match", 0),
            },
            "ambiguity_penalty": {
                "score": factors.get("ambiguity_penalty", 1.0),
                "weight": self.weights.get("ambiguity_penalty", 0),
                "contribution": factors.get("ambiguity_penalty", 1.0) * self.weights.get("ambiguity_penalty", 0),
            },
            "historical_success": {
                "score": factors.get("historical_success", 0.5),
                "weight": self.weights.get("historical_success", 0),
                "contribution": factors.get("historical_success", 0.5) * self.weights.get("historical_success", 0),
            },
            "query_completeness": {
                "score": factors.get("query_completeness", 0.5),
                "weight": self.weights.get("query_completeness", 0),
                "contribution": factors.get("query_completeness", 0.5) * self.weights.get("query_completeness", 0),
            },
            "location_match": {
                "score": factors.get("location_match", 0.5),
                "weight": self.weights.get("location_match", 0),
                "contribution": factors.get("location_match", 0.5) * self.weights.get("location_match", 0),
            },
        }


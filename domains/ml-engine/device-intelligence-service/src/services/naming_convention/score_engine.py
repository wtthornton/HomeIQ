"""
Naming Convention Score Engine (Epic 64, Story 64.1).

Scores entities on a 100-point scale across 6 dimensions:
  area_id (+20), labels (+20), aliases (+20), friendly_name (+20),
  device_class (+10), sensor_role (+10).

Provides per-entity scores and aggregate audit summaries.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .convention_rules import ALL_RULES, RuleResult

logger = logging.getLogger(__name__)


@dataclass
class EntityScore:
    """Score result for a single entity."""

    entity_id: str
    total_score: int
    max_score: int = 100
    rule_results: list[RuleResult] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    @property
    def pct(self) -> float:
        return round(self.total_score / self.max_score * 100, 1) if self.max_score else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "total_score": self.total_score,
            "max_score": self.max_score,
            "pct": self.pct,
            "rules": [
                {
                    "rule": r.rule_name,
                    "earned": r.earned_points,
                    "max": r.max_points,
                    "issues": r.issues,
                    "suggestions": r.suggestions,
                }
                for r in self.rule_results
            ],
            "issues": self.issues,
            "suggestions": self.suggestions,
        }


@dataclass
class AuditSummary:
    """Aggregate audit across all entities."""

    total_entities: int
    average_score: float
    compliance_pct: float
    top_issues: list[dict[str, Any]] = field(default_factory=list)
    score_distribution: dict[str, int] = field(default_factory=dict)
    entity_scores: list[EntityScore] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_entities": self.total_entities,
            "average_score": round(self.average_score, 1),
            "compliance_pct": round(self.compliance_pct, 1),
            "top_issues": self.top_issues,
            "score_distribution": self.score_distribution,
            "entities": [e.to_dict() for e in self.entity_scores],
        }


class ScoreEngine:
    """Scores entities against naming convention rules."""

    def score_entity(self, entity: dict[str, Any]) -> EntityScore:
        """Score a single entity dict against all convention rules."""
        entity_id = entity.get("entity_id", "unknown")
        results: list[RuleResult] = []
        total = 0
        all_issues: list[str] = []
        all_suggestions: list[str] = []

        for rule_fn in ALL_RULES:
            result = rule_fn(entity)
            results.append(result)
            total += result.earned_points
            all_issues.extend(result.issues)
            all_suggestions.extend(result.suggestions)

        return EntityScore(
            entity_id=entity_id,
            total_score=total,
            rule_results=results,
            issues=all_issues,
            suggestions=all_suggestions,
        )

    def audit(self, entities: list[dict[str, Any]]) -> AuditSummary:
        """Score all entities and produce an aggregate audit summary."""
        scores = [self.score_entity(e) for e in entities]

        if not scores:
            return AuditSummary(
                total_entities=0,
                average_score=0.0,
                compliance_pct=0.0,
            )

        total_score_sum = sum(s.total_score for s in scores)
        avg = total_score_sum / len(scores)

        # Compliance: entities scoring >= 70
        compliant = sum(1 for s in scores if s.total_score >= 70)
        compliance_pct = compliant / len(scores) * 100

        # Score distribution
        distribution = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}
        for s in scores:
            if s.total_score >= 90:
                distribution["excellent"] += 1
            elif s.total_score >= 70:
                distribution["good"] += 1
            elif s.total_score >= 50:
                distribution["fair"] += 1
            else:
                distribution["poor"] += 1

        # Top issues by frequency
        issue_counts: dict[str, int] = {}
        for s in scores:
            for issue in s.issues:
                # Normalize: strip entity-specific parts
                normalized = _normalize_issue(issue)
                issue_counts[normalized] = issue_counts.get(normalized, 0) + 1

        top_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_issues_list = [{"issue": k, "count": v} for k, v in top_issues]

        return AuditSummary(
            total_entities=len(scores),
            average_score=avg,
            compliance_pct=compliance_pct,
            top_issues=top_issues_list,
            score_distribution=distribution,
            entity_scores=scores,
        )


def _normalize_issue(issue: str) -> str:
    """Normalize issue text for aggregation."""
    # Remove entity-specific names/values for grouping
    if "no area_id" in issue:
        return "No area_id assigned"
    if "no labels" in issue:
        return "No labels"
    if "no aliases" in issue:
        return "No aliases"
    if "no friendly name" in issue:
        return "No friendly name"
    if "not Title Case" in issue:
        return "Name not Title Case"
    if "brand" in issue.lower():
        return "Name contains brand"
    if "no device_class" in issue:
        return "No device_class"
    if "no role label" in issue:
        return "No sensor role label"
    if "area name" in issue.lower():
        return "Name missing area prefix"
    return issue

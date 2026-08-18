"""Tests for Confidence & Risk Scoring Engine (Epic 68, Story 68.3)."""

from __future__ import annotations

from src.services.confidence_scorer import ConfidenceScorer


def test_configured_auto_execute_threshold_is_honored():
    """A ConfidenceScorer with a raised auto_execute_threshold must not
    auto-execute an action whose confidence clears the hardcoded default
    (85) but not the configured threshold (95)."""
    scorer = ConfidenceScorer(auto_execute_threshold=95)

    score = scorer.score_action(
        action_type="turn_on",
        entity_domain="light",
        llm_confidence=0.9,
        acceptance_rate=0.9,
        context_match_strength=0.9,
        preference_alignment=0.9,
    )

    assert score.risk_level == "low"
    assert 85 <= score.confidence < 95
    assert score.should_auto_execute is False


def test_default_thresholds_unchanged_when_not_overridden():
    """Without overrides, ConfidenceScorer keeps the documented 85/50/30
    default behavior."""
    scorer = ConfidenceScorer()

    score = scorer.score_action(
        action_type="turn_on",
        entity_domain="light",
        llm_confidence=0.9,
        acceptance_rate=0.9,
        context_match_strength=0.9,
        preference_alignment=0.9,
    )

    assert score.risk_level == "low"
    assert 85 <= score.confidence < 95
    assert score.should_auto_execute is True


def test_configured_suppress_threshold_is_honored():
    """A ConfidenceScorer with a lowered suppress_threshold must not
    suppress an action whose confidence clears the configured threshold
    but not the hardcoded default (30)."""
    scorer = ConfidenceScorer(suppress_threshold=10)

    score = scorer.score_action(
        action_type="run_script",
        entity_domain="climate",
        llm_confidence=0.2,
        acceptance_rate=0.2,
        context_match_strength=0.2,
        preference_alignment=0.2,
    )

    assert 10 <= score.confidence < 30
    assert score.should_suppress is False

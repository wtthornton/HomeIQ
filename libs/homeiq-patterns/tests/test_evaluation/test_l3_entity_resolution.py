"""
Tests for Story 3.3: EntityResolutionEvaluator (L3 Details)

Verifies scoring of entity/area resolution quality based on
resolved_context, unresolved_placeholders, and yaml_valid metadata.
"""

import pytest
from homeiq_patterns.evaluation.evaluators.l3_entity_resolution import (
    EntityResolutionEvaluator,
)
from homeiq_patterns.evaluation.models import (
    EvalLevel,
    EvalScope,
    SessionTrace,
)


def _make_session(
    resolved: dict | None = None,
    placeholders: list[str] | None = None,
    yaml_valid: bool = False,
) -> SessionTrace:
    metadata: dict = {}
    if resolved is not None:
        metadata["resolved_context"] = resolved
    if placeholders is not None:
        metadata["unresolved_placeholders"] = placeholders
    metadata["yaml_valid"] = yaml_valid
    return SessionTrace(agent_name="test", metadata=metadata)


# =====================================================================
# Full resolution
# =====================================================================


class TestFullResolution:
    @pytest.mark.asyncio
    async def test_all_resolved_yaml_valid(self):
        evaluator = EntityResolutionEvaluator()
        session = _make_session(
            resolved={"entity_id": "light.office", "area_id": "office", "domain": "light"},
            placeholders=[],
            yaml_valid=True,
        )
        result = await evaluator.evaluate(session)
        # 3/3 * 0.7 + 0.3 = 1.0
        assert result.score == 1.0
        assert result.label == "Resolved"

    @pytest.mark.asyncio
    async def test_all_resolved_yaml_invalid(self):
        evaluator = EntityResolutionEvaluator()
        session = _make_session(
            resolved={"entity_id": "light.office", "area_id": "office"},
            placeholders=[],
            yaml_valid=False,
        )
        result = await evaluator.evaluate(session)
        # 2/2 * 0.7 = 0.7
        assert abs(result.score - 0.7) < 0.01
        assert result.label == "Partial"


# =====================================================================
# Partial resolution
# =====================================================================


class TestPartialResolution:
    @pytest.mark.asyncio
    async def test_two_of_three_resolved_yaml_valid(self):
        evaluator = EntityResolutionEvaluator()
        session = _make_session(
            resolved={"entity_id": "light.office", "area_id": "office"},
            placeholders=["{{device_class}}"],
            yaml_valid=True,
        )
        result = await evaluator.evaluate(session)
        # total=3, resolved_ratio=2/3, score = 2/3 * 0.7 + 0.3 ≈ 0.767
        assert abs(result.score - (2 / 3 * 0.7 + 0.3)) < 0.01
        assert result.label == "Partial"

    @pytest.mark.asyncio
    async def test_half_resolved_yaml_valid(self):
        evaluator = EntityResolutionEvaluator()
        session = _make_session(
            resolved={"entity_id": "light.office"},
            placeholders=["{{area_id}}"],
            yaml_valid=True,
        )
        result = await evaluator.evaluate(session)
        # 1/2 * 0.7 + 0.3 = 0.65
        assert abs(result.score - 0.65) < 0.01
        assert result.label == "Partial"

    @pytest.mark.asyncio
    async def test_half_resolved_yaml_invalid(self):
        evaluator = EntityResolutionEvaluator()
        session = _make_session(
            resolved={"entity_id": "light.office"},
            placeholders=["{{area_id}}"],
            yaml_valid=False,
        )
        result = await evaluator.evaluate(session)
        # 1/2 * 0.7 = 0.35
        assert abs(result.score - 0.35) < 0.01
        assert result.label == "Unresolved"


# =====================================================================
# No resolution
# =====================================================================


class TestNoResolution:
    @pytest.mark.asyncio
    async def test_no_resolved_entities(self):
        evaluator = EntityResolutionEvaluator()
        session = _make_session(
            resolved={},
            placeholders=["{{entity_id}}", "{{area_id}}", "{{domain}}"],
            yaml_valid=False,
        )
        result = await evaluator.evaluate(session)
        # 0/3 * 0.7 = 0.0
        assert result.score == 0.0
        assert result.label == "Unresolved"
        assert result.passed is False


# =====================================================================
# No entities to resolve
# =====================================================================


class TestNoEntities:
    @pytest.mark.asyncio
    async def test_no_entities_to_resolve(self):
        evaluator = EntityResolutionEvaluator()
        session = _make_session(resolved={}, placeholders=[])
        result = await evaluator.evaluate(session)
        assert result.score == 0.8
        assert result.label == "N/A"
        assert "simple template" in result.explanation

    @pytest.mark.asyncio
    async def test_missing_metadata_keys(self):
        """When resolved_context and unresolved_placeholders are absent."""
        evaluator = EntityResolutionEvaluator()
        session = SessionTrace(agent_name="test")
        result = await evaluator.evaluate(session)
        # Defaults: resolved={} (len 0), placeholders=[] (len 0), total=0
        assert result.score == 0.8
        assert result.label == "N/A"


# =====================================================================
# Label thresholds
# =====================================================================


class TestLabels:
    @pytest.mark.asyncio
    async def test_label_resolved(self):
        """Score >= 0.8 -> 'Resolved'."""
        evaluator = EntityResolutionEvaluator()
        session = _make_session(
            resolved={"a": "1", "b": "2", "c": "3"},
            placeholders=[],
            yaml_valid=True,
        )
        result = await evaluator.evaluate(session)
        assert result.score >= 0.8
        assert result.label == "Resolved"

    @pytest.mark.asyncio
    async def test_label_partial(self):
        """0.4 <= score < 0.8 -> 'Partial'."""
        evaluator = EntityResolutionEvaluator()
        session = _make_session(
            resolved={"a": "1"},
            placeholders=["{{b}}"],
            yaml_valid=True,
        )
        result = await evaluator.evaluate(session)
        # 1/2 * 0.7 + 0.3 = 0.65
        assert 0.4 <= result.score < 0.8
        assert result.label == "Partial"

    @pytest.mark.asyncio
    async def test_label_unresolved(self):
        """Score < 0.4 -> 'Unresolved'."""
        evaluator = EntityResolutionEvaluator()
        session = _make_session(
            resolved={"a": "1"},
            placeholders=["{{b}}", "{{c}}", "{{d}}"],
            yaml_valid=False,
        )
        result = await evaluator.evaluate(session)
        # 1/4 * 0.7 = 0.175
        assert result.score < 0.4
        assert result.label == "Unresolved"


# =====================================================================
# Evaluator properties
# =====================================================================


class TestEvaluatorProperties:
    def test_name(self):
        evaluator = EntityResolutionEvaluator()
        assert evaluator.name == "entity_resolution"

    def test_level(self):
        evaluator = EntityResolutionEvaluator()
        assert evaluator.level == EvalLevel.DETAILS

    def test_scope(self):
        evaluator = EntityResolutionEvaluator()
        assert evaluator.scope == EvalScope.TOOL_CALL

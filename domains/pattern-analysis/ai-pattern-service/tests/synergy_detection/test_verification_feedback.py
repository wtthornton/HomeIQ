"""Tests for verification feedback on synergy confidence (Story 6).

Tests the _apply_verification_feedback logic using a standalone
async function that mirrors the production code exactly.

Tests cover:
- Confidence boost when 3+ successes in 7 days
- Confidence penalty when 2+ failures in 24 hours
- No change when no verification history
- No change when verification store unavailable
- Confidence capped at 1.0 and floored at 0.0
- Store errors handled gracefully
"""

from typing import Any

import pytest


def _make_synergy(
    trigger: str = "binary_sensor.motion",
    action: str = "light.kitchen",
    confidence: float = 0.7,
    impact: float = 0.5,
) -> dict[str, Any]:
    """Create a minimal synergy dict."""
    return {
        "synergy_id": "test-001",
        "synergy_type": "device_pair",
        "trigger_entity": trigger,
        "action_entity": action,
        "confidence": confidence,
        "impact_score": impact,
        "area": "kitchen",
    }


class MockVerificationStore:
    """Mock verification store for testing."""

    def __init__(
        self,
        successes: list[dict] | None = None,
        failures: list[dict] | None = None,
    ):
        self._successes = successes or []
        self._failures = failures or []

    async def query_successes(
        self, _entity_ids: list[str], _lookback_hours: int = 168
    ) -> list[dict]:
        return self._successes

    async def query_failures(
        self, _entity_id: str, _lookback_hours: int = 24
    ) -> list[dict]:
        return self._failures


class FailingStore:
    """Store that always raises errors."""

    async def query_successes(self, _entity_ids, _lookback_hours=168):
        raise ConnectionError("InfluxDB down")

    async def query_failures(self, _entity_id, _lookback_hours=24):
        raise ConnectionError("InfluxDB down")


async def _apply_feedback(synergies, store):
    """
    Standalone implementation of verification feedback logic.

    Mirrors DeviceSynergyDetector._apply_verification_feedback() exactly
    so we can test the algorithm without importing the full detector.
    """
    if not store:
        return synergies

    for synergy in synergies:
        trigger = synergy.get("trigger_entity", "")
        action = synergy.get("action_entity", "")
        if not trigger or not action:
            continue

        try:
            successes = await store.query_successes(
                [trigger, action], lookback_hours=168
            )
            if len(successes) >= 3:
                synergy["confidence"] = min(
                    1.0, synergy.get("confidence", 0.7) + 0.15
                )
                synergy["impact_score"] = min(
                    1.0, synergy.get("impact_score", 0.5) + 0.10
                )
                synergy["verification_boosted"] = True

            for eid in (trigger, action):
                failures = await store.query_failures(eid, lookback_hours=24)
                if len(failures) >= 2:
                    synergy["confidence"] = max(
                        0.0, synergy.get("confidence", 0.7) - 0.2
                    )
                    synergy["recent_failures"] = True
                    break
        except Exception:
            pass

    return synergies


class TestVerificationFeedback:
    @pytest.mark.asyncio
    async def test_boost_with_3_successes(self):
        """3+ successes in 7 days -> confidence +0.15, impact +0.10."""
        store = MockVerificationStore(
            successes=[{"entity_id": "light.kitchen"}] * 3,
        )
        synergies = [_make_synergy(confidence=0.7, impact=0.5)]
        result = await _apply_feedback(synergies, store)

        assert result[0]["confidence"] == pytest.approx(0.85, abs=0.01)
        assert result[0]["impact_score"] == pytest.approx(0.60, abs=0.01)
        assert result[0]["verification_boosted"] is True

    @pytest.mark.asyncio
    async def test_no_boost_with_2_successes(self):
        """Fewer than 3 successes -> no boost."""
        store = MockVerificationStore(
            successes=[{"entity_id": "light.kitchen"}] * 2,
        )
        synergies = [_make_synergy(confidence=0.7, impact=0.5)]
        result = await _apply_feedback(synergies, store)

        assert result[0]["confidence"] == 0.7
        assert result[0]["impact_score"] == 0.5

    @pytest.mark.asyncio
    async def test_penalty_with_2_failures(self):
        """2+ failures in 24 hours -> confidence -0.2."""
        store = MockVerificationStore(
            failures=[{"entity_id": "light.kitchen"}] * 2,
        )
        synergies = [_make_synergy(confidence=0.7)]
        result = await _apply_feedback(synergies, store)

        assert result[0]["confidence"] == pytest.approx(0.5, abs=0.01)
        assert result[0]["recent_failures"] is True

    @pytest.mark.asyncio
    async def test_no_penalty_with_1_failure(self):
        """Single failure -> no penalty."""
        store = MockVerificationStore(
            failures=[{"entity_id": "light.kitchen"}],
        )
        synergies = [_make_synergy(confidence=0.7)]
        result = await _apply_feedback(synergies, store)

        assert result[0]["confidence"] == 0.7
        assert "recent_failures" not in result[0]

    @pytest.mark.asyncio
    async def test_no_change_without_store(self):
        """No verification store -> no changes."""
        synergies = [_make_synergy(confidence=0.7)]
        result = await _apply_feedback(synergies, store=None)
        assert result[0]["confidence"] == 0.7

    @pytest.mark.asyncio
    async def test_empty_history(self):
        """Empty verification history -> no changes."""
        store = MockVerificationStore(successes=[], failures=[])
        synergies = [_make_synergy(confidence=0.7)]
        result = await _apply_feedback(synergies, store)
        assert result[0]["confidence"] == 0.7

    @pytest.mark.asyncio
    async def test_confidence_capped_at_1(self):
        """Boost cannot push confidence above 1.0."""
        store = MockVerificationStore(
            successes=[{"entity_id": "light.kitchen"}] * 5,
        )
        synergies = [_make_synergy(confidence=0.95)]
        result = await _apply_feedback(synergies, store)
        assert result[0]["confidence"] == 1.0

    @pytest.mark.asyncio
    async def test_confidence_floored_at_0(self):
        """Penalty cannot push confidence below 0.0."""
        store = MockVerificationStore(
            failures=[{"entity_id": "light.kitchen"}] * 3,
        )
        synergies = [_make_synergy(confidence=0.1)]
        result = await _apply_feedback(synergies, store)
        assert result[0]["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_store_error_graceful(self):
        """Store query errors are handled gracefully."""
        synergies = [_make_synergy(confidence=0.7)]
        result = await _apply_feedback(synergies, FailingStore())
        assert result[0]["confidence"] == 0.7

    @pytest.mark.asyncio
    async def test_missing_entities_skipped(self):
        """Synergies without trigger/action entities are skipped."""
        store = MockVerificationStore(
            successes=[{"entity_id": "x"}] * 5,
        )
        synergies = [{"synergy_id": "test", "confidence": 0.7}]
        result = await _apply_feedback(synergies, store)
        assert result[0]["confidence"] == 0.7

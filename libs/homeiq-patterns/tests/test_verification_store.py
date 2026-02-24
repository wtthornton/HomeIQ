"""Tests for verification result persistence (Story 5).

Tests cover:
- VerificationResultStore abstract interface
- InfluxDBVerificationStore store/query round-trip with mocks
- Failure/success query behavior
- Error handling when store/query fails
"""

import pytest
import json
from typing import Any
from datetime import datetime, timezone
import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parents[3])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from homeiq_patterns import VerificationResult, VerificationWarning, VerificationResultStore

# Import InfluxDB store directly
_store_path = (
    Path(__file__).resolve().parents[3]
    / "domains" / "automation-core" / "ai-automation-service-new" / "src" / "services"
)
sys.path.insert(0, str(_store_path.parent.parent))

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "verification_store",
    _store_path / "verification_store.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
InfluxDBVerificationStore = _mod.InfluxDBVerificationStore


# --- Abstract interface tests ---

class TestVerificationResultStoreInterface:
    def test_is_abstract(self):
        """VerificationResultStore cannot be instantiated directly."""
        with pytest.raises(TypeError):
            VerificationResultStore()

    def test_concrete_implementation(self):
        """A concrete implementation can be instantiated."""

        class MemoryStore(VerificationResultStore):
            async def store(self, result, context=None):
                pass

            async def query_failures(self, entity_id, lookback_hours=24):
                return []

            async def query_successes(self, entity_ids, lookback_hours=168):
                return []

        store = MemoryStore()
        assert store is not None


# --- InfluxDBVerificationStore tests ---

class TestInfluxDBVerificationStore:
    @pytest.fixture
    def stored_points(self):
        """Accumulate written InfluxDB points."""
        return []

    @pytest.fixture
    def query_results(self):
        """Configurable query results."""
        return []

    @pytest.fixture
    def store(self, stored_points, query_results):
        """Create store with mock write/query functions."""

        async def mock_write(measurement, tags, fields, timestamp):
            stored_points.append({
                "measurement": measurement,
                "tags": tags,
                "fields": fields,
                "timestamp": timestamp,
            })

        async def mock_query(query):
            return query_results

        return InfluxDBVerificationStore(mock_write, mock_query)

    @pytest.mark.asyncio
    async def test_store_success_result(self, store, stored_points):
        """Store a successful verification result."""
        result = VerificationResult(
            success=True,
            state="on",
            metadata={"entity_id": "light.kitchen"},
        )
        await store.store(result, {"entity_id": "light.kitchen", "action_type": "turn_on"})

        assert len(stored_points) == 1
        point = stored_points[0]
        assert point["measurement"] == "verification_results"
        assert point["tags"]["entity_id"] == "light.kitchen"
        assert point["tags"]["action_type"] == "turn_on"
        assert point["tags"]["success"] == "true"
        assert point["fields"]["state"] == "on"
        assert point["fields"]["warnings_count"] == 0

    @pytest.mark.asyncio
    async def test_store_failure_result(self, store, stored_points):
        """Store a failed verification result with warnings."""
        result = VerificationResult(
            success=False,
            state="off",
            warnings=[
                VerificationWarning(
                    message="Entity is off but expected on",
                    entity_id="light.kitchen",
                )
            ],
            metadata={"entity_id": "light.kitchen"},
        )
        await store.store(result, {"entity_id": "light.kitchen", "action_type": "turn_on"})

        point = stored_points[0]
        assert point["tags"]["success"] == "false"
        assert point["fields"]["warnings_count"] == 1
        assert "off but expected on" in point["fields"]["first_warning"]

    @pytest.mark.asyncio
    async def test_store_with_verified_attributes(self, store, stored_points):
        """Store result with verified attributes as JSON."""
        result = VerificationResult(
            success=True,
            state="on",
            verified_attributes={"brightness": 255, "color_temp": 300},
            metadata={"entity_id": "light.kitchen"},
        )
        await store.store(result)

        point = stored_points[0]
        attrs = json.loads(point["fields"]["verified_attributes"])
        assert attrs["brightness"] == 255

    @pytest.mark.asyncio
    async def test_store_with_expected_state(self, store, stored_points):
        """Store result with expected state as JSON."""
        result = VerificationResult(
            success=True,
            state="on",
            expected_state={"state": "on", "brightness": 255},
            metadata={"entity_id": "light.kitchen"},
        )
        await store.store(result)

        point = stored_points[0]
        expected = json.loads(point["fields"]["expected_state"])
        assert expected["state"] == "on"

    @pytest.mark.asyncio
    async def test_store_entity_from_context(self, store, stored_points):
        """Entity ID from context overrides metadata."""
        result = VerificationResult(
            success=True,
            state="on",
            metadata={"entity_id": "light.from_meta"},
        )
        await store.store(result, {"entity_id": "light.from_context"})

        assert stored_points[0]["tags"]["entity_id"] == "light.from_context"

    @pytest.mark.asyncio
    async def test_store_handles_write_error(self, stored_points):
        """Store gracefully handles write failures."""

        async def failing_write(measurement, tags, fields, timestamp):
            raise ConnectionError("InfluxDB unavailable")

        async def mock_query(query):
            return []

        store = InfluxDBVerificationStore(failing_write, mock_query)
        result = VerificationResult(success=True, state="on")

        # Should not raise
        await store.store(result)
        assert len(stored_points) == 0

    @pytest.mark.asyncio
    async def test_query_failures(self, store, query_results):
        """Query failures returns results from backing store."""
        query_results.extend([
            {"entity_id": "light.kitchen", "state": "off", "success": "false"},
        ])
        failures = await store.query_failures("light.kitchen", lookback_hours=24)
        assert len(failures) == 1

    @pytest.mark.asyncio
    async def test_query_failures_handles_error(self):
        """Query failures gracefully handles query errors."""

        async def mock_write(m, t, f, ts):
            pass

        async def failing_query(query):
            raise ConnectionError("InfluxDB unavailable")

        store = InfluxDBVerificationStore(mock_write, failing_query)
        failures = await store.query_failures("light.kitchen")
        assert failures == []

    @pytest.mark.asyncio
    async def test_query_successes(self, store, query_results):
        """Query successes returns results for multiple entities."""
        query_results.extend([
            {"entity_id": "light.kitchen", "success": "true"},
            {"entity_id": "light.bedroom", "success": "true"},
        ])
        successes = await store.query_successes(
            ["light.kitchen", "light.bedroom"],
            lookback_hours=168,
        )
        assert len(successes) == 2

    @pytest.mark.asyncio
    async def test_query_successes_empty_ids(self, store):
        """Query successes with empty entity list returns empty."""
        successes = await store.query_successes([])
        assert successes == []

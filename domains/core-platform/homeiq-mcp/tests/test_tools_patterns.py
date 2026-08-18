"""Tests for patterns and synergies tools (TAP-5295)."""

from __future__ import annotations

import respx
from httpx import Response
from src.auth import READ_SCOPES
from src.tools import patterns


async def test_list_patterns_happy_path(registry, backings) -> None:
    """Test list_patterns with mocked upstream responses."""
    patterns.register(registry, backings)

    patterns_list = [
        {
            "id": 1,
            "pattern_type": "circadian",
            "device_id": "light.office",
            "metadata": {"summary": "Office light on at 7am"},
            "confidence": 0.95,
            "occurrences": 42,
        },
        {
            "id": 2,
            "pattern_type": "occupancy",
            "device_id": None,
            "metadata": {},
            "confidence": 0.80,
            "occurrences": 100,
        },
    ]

    patterns_stats = {
        "total_patterns": 2,
        "by_type": {"circadian": 1, "occupancy": 1},
        "avg_confidence": 0.875,
        "unique_devices": 1,
    }

    with respx.mock:
        respx.get("http://patterns.test:8020/api/v1/patterns/list").mock(
            return_value=Response(
                200,
                json={
                    "success": True,
                    "data": {"patterns": patterns_list, "count": 2},
                    "message": "ok",
                },
            )
        )
        respx.get("http://patterns.test:8020/api/v1/patterns/stats").mock(
            return_value=Response(
                200,
                json={"success": True, "data": patterns_stats, "message": "ok"},
            )
        )

        payload = await registry.call("list_patterns", {}, scopes=READ_SCOPES)

        assert payload["count"] == 2
        assert payload["truncated"] is False
        assert len(payload["patterns"]) == 2
        assert payload["patterns"][0]["id"] == 1
        assert payload["patterns"][0]["summary"] == "Office light on at 7am"
        assert payload["stats"]["total_patterns"] == 2
        assert payload["stats"]["avg_confidence"] == 0.875


async def test_list_patterns_with_filters(registry, backings) -> None:
    """Test list_patterns with query filters."""
    patterns.register(registry, backings)

    patterns_list = [
        {
            "id": 1,
            "pattern_type": "circadian",
            "device_id": "light.office",
            "metadata": {},
            "confidence": 0.95,
            "occurrences": 42,
        }
    ]

    with respx.mock:
        route_list = respx.get(
            "http://patterns.test:8020/api/v1/patterns/list",
            params={
                "pattern_type": "circadian",
                "device_id": "light.office",
                "min_confidence": 0.9,
                "limit": 50,
            },
        ).mock(
            return_value=Response(
                200,
                json={
                    "success": True,
                    "data": {"patterns": patterns_list, "count": 1},
                    "message": "ok",
                },
            )
        )

        respx.get("http://patterns.test:8020/api/v1/patterns/stats").mock(
            return_value=Response(
                200,
                json={
                    "success": True,
                    "data": {
                        "total_patterns": 1,
                        "by_type": {"circadian": 1},
                        "avg_confidence": 0.95,
                        "unique_devices": 1,
                    },
                    "message": "ok",
                },
            )
        )

        payload = await registry.call(
            "list_patterns",
            {
                "pattern_type": "circadian",
                "device_id": "light.office",
                "min_confidence": 0.9,
                "limit": 50,
            },
            scopes=READ_SCOPES,
        )

        assert route_list.called
        assert payload["count"] == 1
        assert payload["patterns"][0]["pattern_type"] == "circadian"


async def test_list_patterns_row_cap(registry, backings) -> None:
    """Test list_patterns applies the 100-row cap."""
    patterns.register(registry, backings)

    # Create 150 patterns to exceed the 100-row cap
    patterns_list = [
        {
            "id": i,
            "pattern_type": f"type_{i % 10}",
            "device_id": f"device_{i % 20}",
            "metadata": {},
            "confidence": 0.5 + (i % 50) / 100,
            "occurrences": i,
        }
        for i in range(150)
    ]

    with respx.mock:
        respx.get("http://patterns.test:8020/api/v1/patterns/list").mock(
            return_value=Response(
                200,
                json={
                    "success": True,
                    "data": {"patterns": patterns_list, "count": 150},
                    "message": "ok",
                },
            )
        )
        respx.get("http://patterns.test:8020/api/v1/patterns/stats").mock(
            return_value=Response(
                200,
                json={
                    "success": True,
                    "data": {
                        "total_patterns": 150,
                        "by_type": {},
                        "avg_confidence": 0.75,
                        "unique_devices": 20,
                    },
                    "message": "ok",
                },
            )
        )

        payload = await registry.call("list_patterns", {}, scopes=READ_SCOPES)

        assert payload["truncated"] is True
        assert payload["count"] <= 100
        assert len(payload["patterns"]) <= 100


async def test_list_synergies_happy_path(registry, backings) -> None:
    """Test list_synergies with mocked upstream responses."""
    patterns.register(registry, backings)

    synergies_list = [
        {
            "synergy_id": "syn_001",
            "synergy_type": "device_pair",
            "device_ids": ["light.office", "switch.coffee"],
            "area": "kitchen",
            "metadata": {},
            "impact_score": 0.85,
            "confidence": 0.92,
            "complexity": "low",
            "explanation": "Coffee maker powers on when office lights turn on",
        }
    ]

    synergies_stats = {
        "total_synergies": 1,
        "avg_impact_score": 0.85,
        "avg_confidence": 0.92,
    }

    with respx.mock:
        respx.get("http://patterns.test:8020/api/v1/synergies/list").mock(
            return_value=Response(
                200,
                json={
                    "success": True,
                    "data": {"synergies": synergies_list, "count": len(synergies_list)},
                    "message": "ok",
                },
            )
        )
        respx.get("http://patterns.test:8020/api/v1/synergies/statistics").mock(
            return_value=Response(
                200,
                json={"success": True, "data": synergies_stats, "message": "ok"},
            )
        )

        payload = await registry.call("list_synergies", {}, scopes=READ_SCOPES)

        assert payload["count"] == 1
        assert payload["truncated"] is False
        assert len(payload["synergies"]) == 1
        assert payload["synergies"][0]["synergy_id"] == "syn_001"
        assert payload["synergies"][0]["area"] == "kitchen"
        assert payload["stats"]["total_synergies"] == 1


async def test_list_synergies_with_filters(registry, backings) -> None:
    """Test list_synergies with query filters."""
    patterns.register(registry, backings)

    synergies_list = [
        {
            "synergy_id": "syn_001",
            "synergy_type": "device_pair",
            "device_ids": ["light.office", "switch.coffee"],
            "area": "kitchen",
            "metadata": {},
            "impact_score": 0.85,
            "confidence": 0.92,
            "complexity": "low",
            "explanation": "Coffee makes coffee",
        },
        {
            "synergy_id": "syn_002",
            "synergy_type": "device_pair",
            "device_ids": ["light.hall"],
            "area": "hall",
            "metadata": {},
            "impact_score": 0.5,
            "confidence": 0.95,
            "complexity": "low",
            "explanation": {"reason": "dict explanations come from a JSON column"},
        },
    ]

    with respx.mock:
        respx.get(
            "http://patterns.test:8020/api/v1/synergies/list",
            # `area` is NOT forwarded: the upstream route has no such filter; it is applied locally.
            params={
                "synergy_type": "device_pair",
                "min_confidence": 0.9,
                "limit": 20,
            },
        ).mock(
            return_value=Response(
                200,
                json={
                    "success": True,
                    "data": {"synergies": synergies_list, "count": 1},
                    "message": "ok",
                },
            )
        )

        respx.get("http://patterns.test:8020/api/v1/synergies/statistics").mock(
            return_value=Response(
                200,
                json={
                    "success": True,
                    "data": {
                        "total_synergies": 1,
                        "avg_impact_score": 0.85,
                        "avg_confidence": 0.92,
                    },
                    "message": "ok",
                },
            )
        )

        payload = await registry.call(
            "list_synergies",
            {"synergy_type": "device_pair", "min_confidence": 0.9, "area": "kitchen"},
            scopes=READ_SCOPES,
        )

        assert payload["count"] == 1
        assert payload["synergies"][0]["synergy_type"] == "device_pair"


async def test_list_synergies_row_cap(registry, backings) -> None:
    """Test list_synergies applies the 50-row cap."""
    patterns.register(registry, backings)

    # Create 75 synergies to exceed the 50-row cap
    synergies_list = [
        {
            "synergy_id": f"syn_{i:03d}",
            "synergy_type": f"type_{i % 5}",
            "device_ids": [f"device_{i}", f"device_{i + 1}"],
            "area": f"area_{i % 3}",
            "metadata": {},
            "impact_score": 0.5 + (i % 50) / 100,
            "confidence": 0.6 + (i % 40) / 100,
            "complexity": "low" if i % 2 == 0 else "medium",
            "explanation": f"Synergy {i}",
        }
        for i in range(75)
    ]

    with respx.mock:
        respx.get("http://patterns.test:8020/api/v1/synergies/list").mock(
            return_value=Response(
                200,
                json={
                    "success": True,
                    "data": {"synergies": synergies_list, "count": 75},
                    "message": "ok",
                },
            )
        )
        respx.get("http://patterns.test:8020/api/v1/synergies/statistics").mock(
            return_value=Response(
                200,
                json={
                    "success": True,
                    "data": {
                        "total_synergies": 75,
                        "avg_impact_score": 0.75,
                        "avg_confidence": 0.8,
                    },
                    "message": "ok",
                },
            )
        )

        payload = await registry.call("list_synergies", {}, scopes=READ_SCOPES)

        assert payload["truncated"] is True
        assert payload["count"] <= 50
        assert len(payload["synergies"]) <= 50


def test_registry_names_after_patterns_register(registry, backings) -> None:
    """Test that register() adds the expected tool names."""
    patterns.register(registry, backings)

    names = registry.names()
    assert "list_patterns" in names
    assert "list_synergies" in names

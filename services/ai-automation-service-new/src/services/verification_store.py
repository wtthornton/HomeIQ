"""
InfluxDB Verification Result Store

Epic: Pattern Intelligence, Story 5
Persists verification results to InfluxDB for feedback loops.

Writes to measurement 'verification_results' with:
- Tags: entity_id, action_type, success
- Fields: state, warnings_count, verified_attributes (JSON)
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    _project_root = str(Path(__file__).resolve().parents[4])
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
except IndexError:
    pass  # Docker: PYTHONPATH already includes /app

from shared.patterns.post_action_verifier import (
    VerificationResult,
    VerificationResultStore,
)

logger = logging.getLogger(__name__)

MEASUREMENT = "verification_results"


class InfluxDBVerificationStore(VerificationResultStore):
    """
    Stores verification results in InfluxDB.

    Uses the InfluxDB v2 write API. Results are written as points
    in the 'verification_results' measurement.
    """

    def __init__(self, write_fn, query_fn) -> None:
        """
        Args:
            write_fn: Async callable to write InfluxDB points.
                      Signature: async (measurement, tags, fields, timestamp) -> None
            query_fn: Async callable to run Flux queries.
                      Signature: async (query: str) -> list[dict]
        """
        self._write = write_fn
        self._query = query_fn

    async def store(
        self,
        result: VerificationResult,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Persist verification result to InfluxDB."""
        ctx = context or {}
        entity_id = ctx.get("entity_id") or result.metadata.get("entity_id", "unknown")
        action_type = ctx.get("action_type", "unknown")

        tags = {
            "entity_id": entity_id,
            "action_type": action_type,
            "success": str(result.success).lower(),
        }

        fields: dict[str, Any] = {
            "state": result.state or "",
            "warnings_count": len(result.warnings),
        }

        if result.verified_attributes:
            fields["verified_attributes"] = json.dumps(result.verified_attributes)

        if result.expected_state:
            fields["expected_state"] = json.dumps(result.expected_state)

        # Include first warning message for quick inspection
        if result.warnings:
            fields["first_warning"] = result.warnings[0].message[:256]

        try:
            await self._write(
                MEASUREMENT,
                tags,
                fields,
                datetime.now(timezone.utc),
            )
            logger.debug(
                f"Stored verification result: {entity_id} "
                f"success={result.success} warnings={len(result.warnings)}"
            )
        except Exception as e:
            logger.warning(f"Failed to store verification result: {e}")

    async def query_failures(
        self,
        entity_id: str,
        lookback_hours: int = 24,
    ) -> list[dict[str, Any]]:
        """Query recent failures for an entity."""
        query = (
            f'from(bucket: "homeiq")'
            f' |> range(start: -{lookback_hours}h)'
            f' |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")'
            f' |> filter(fn: (r) => r.entity_id == "{entity_id}")'
            f' |> filter(fn: (r) => r.success == "false")'
            f' |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")'
        )
        try:
            return await self._query(query)
        except Exception as e:
            logger.warning(f"Failed to query failures for {entity_id}: {e}")
            return []

    async def query_successes(
        self,
        entity_ids: list[str],
        lookback_hours: int = 168,
    ) -> list[dict[str, Any]]:
        """Query recent successes for entities."""
        if not entity_ids:
            return []

        # Build OR filter for multiple entity_ids
        entity_filter = " or ".join(
            f'r.entity_id == "{eid}"' for eid in entity_ids
        )
        query = (
            f'from(bucket: "homeiq")'
            f' |> range(start: -{lookback_hours}h)'
            f' |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")'
            f' |> filter(fn: (r) => {entity_filter})'
            f' |> filter(fn: (r) => r.success == "true")'
            f' |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")'
        )
        try:
            return await self._query(query)
        except Exception as e:
            logger.warning(f"Failed to query successes: {e}")
            return []

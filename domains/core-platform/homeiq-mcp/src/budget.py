"""Response-size budget enforcement (catalogue design rule 2).

`enforce_budget` serialises the payload the way it will be sent to the agent,
and if it exceeds the tool's `max_response_bytes` it drops rows from the
largest top-level list until it fits, then sets `truncated: true` and a `hint`
naming the input parameter the agent should narrow.
"""

from __future__ import annotations

import json
from typing import Any


def payload_size(payload: dict[str, Any]) -> int:
    return len(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def _largest_list_key(payload: dict[str, Any]) -> str | None:
    lists = {k: v for k, v in payload.items() if isinstance(v, list) and v}
    if not lists:
        return None
    return max(lists, key=lambda k: len(lists[k]))


def enforce_budget(payload: dict[str, Any], max_bytes: int, hint: str) -> dict[str, Any]:
    """Return `payload` shrunk to `max_bytes` (mutating and returning the same dict)."""
    if payload_size(payload) <= max_bytes:
        return payload
    while payload_size(payload) > max_bytes:
        key = _largest_list_key(payload)
        if key is None:
            break
        rows = payload[key]
        # Halve, then step by one so large lists converge quickly and small ones exactly.
        drop = max(1, len(rows) // 2) if payload_size(payload) > 2 * max_bytes else 1
        del rows[len(rows) - drop :]
        payload["truncated"] = True
        payload["hint"] = hint
        if "count" in payload and isinstance(payload["count"], int):
            payload["count"] = len(rows)
    return payload


def cap_rows(rows: list[Any], row_cap: int) -> tuple[list[Any], bool]:
    """Apply the catalogue row cap; returns (rows, was_capped)."""
    if len(rows) <= row_cap:
        return rows, False
    return rows[:row_cap], True

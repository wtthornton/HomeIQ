"""Projection helpers shared by the tool groups: envelope unwrapping, required/optional field
copying, state and timestamp normalisation, and the standard list envelope."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

from ..budget import cap_rows
from ..errors import ToolError


def expect_list(payload: Any, *, tool: str, key: str | None = None) -> list[Any]:
    """Return the list the backing promised, unwrapping `{key: [...]}` envelopes."""
    if key is not None:
        if not isinstance(payload, dict):
            raise ToolError(
                "contract_violation",
                f"backing returned {type(payload).__name__} where a {{{key}: [...]}} object was expected",
                tool=tool,
            )
        payload = payload.get(key)
    if not isinstance(payload, list):
        raise ToolError(
            "contract_violation",
            f"backing returned {type(payload).__name__} where a list of {key or 'rows'} was expected",
            tool=tool,
        )
    return payload


def require(row: dict[str, Any], keys: tuple[str, ...], *, tool: str) -> dict[str, Any]:
    """Copy `keys` from `row`, raising contract_violation when one is missing or null."""
    out: dict[str, Any] = {}
    for key in keys:
        value = row.get(key)
        if value is None:
            raise ToolError("contract_violation", f"backing row is missing {key!r}", tool=tool)
        out[key] = value
    return out


def present(row: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    """Copy the optional `keys` that are present and non-empty."""
    return {key: row[key] for key in keys if row.get(key) not in (None, "", [], {})}


def state_string(value: Any) -> str | None:
    """Project a stored state (dict with 'state', or a bare scalar) to a bounded string."""
    if isinstance(value, dict):
        value = value.get("state")
    if value is None:
        return None
    return str(value)[:255]


_PATH_SEGMENT = re.compile(r"^[A-Za-z0-9._:@-]{1,255}$")


def path_segment(value: Any, *, tool: str, name: str) -> str:
    """Return `value` safe to interpolate into an upstream URL path.

    Caller-supplied ids (entity/device/automation/context ids) must never be able to
    steer the server's authenticated request to another route: reject anything outside
    the id charset (no `/`, `?`, `#`, whitespace) with `invalid_input`, then percent-encode.
    """
    text = str(value)
    if not _PATH_SEGMENT.match(text):
        raise ToolError(
            "invalid_input", f"{name} contains characters that are not allowed in an id", tool=tool
        )
    return quote(text, safe="")


def rfc3339(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def window(hours: int) -> tuple[str, str]:
    """RFC3339 (start, end) for a trailing `hours` window, in UTC."""
    end = datetime.now(UTC)
    start = end - timedelta(hours=hours)
    return start.isoformat(), end.isoformat()


def listing(
    name: str, rows: list[Any], row_cap: int, hint: str | None, *, count: bool = True, **extra: Any
) -> dict[str, Any]:
    """Standard `{name: rows[, count], truncated[, hint]}` envelope with the catalogue row cap."""
    rows, capped = cap_rows(rows, row_cap)
    out: dict[str, Any] = {name: rows, "truncated": capped, **extra}
    if count:
        out["count"] = len(rows)
    if capped and hint is not None:
        out["hint"] = hint
    return out

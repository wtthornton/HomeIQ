"""
Utility helpers for safely constructing Flux queries.

These helpers centralize the sanitization logic required to prevent Flux
injection vulnerabilities whenever user-supplied strings are interpolated into
queries.
"""

from __future__ import annotations

import re


def sanitize_flux_value(value: str | None) -> str:
    """
    Sanitize values for Flux queries to prevent injection attacks.

    Security: Prevents Flux query injection by escaping special characters.

    Args:
        value: Raw input value provided by a user or upstream client.

    Returns:
        Sanitized value safe for Flux queries.
    """
    if value is None:
        return ""

    sanitized = re.sub(r"[^\w\s.\-]", "", str(value))
    return sanitized.replace('"', '\\"')

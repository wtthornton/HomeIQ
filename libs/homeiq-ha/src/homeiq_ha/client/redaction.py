"""Redaction helpers.

An admin token is a secret-bearing credential: ``backup/config/info`` returns
the backup encryption key in plaintext, so anything that logs a raw Home
Assistant payload can leak the key that makes backups recoverable. Every log
line this package emits goes through :func:`redact`.
"""

from __future__ import annotations

import re
from typing import Any

REDACTED = "***REDACTED***"

# Field names whose values must never reach a log, at any nesting depth.
_SECRET_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "api_password",
        "client_secret",
        "encryption_key",
        "network_key",
        "password",
        "refresh_token",
        "secret",
        "token",
    }
)

# Bearer tokens and HA long-lived tokens embedded in free text.
_BEARER = re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]{8,}", re.IGNORECASE)
_LONG_TOKEN = re.compile(r"\b[A-Za-z0-9_\-]{40,}\.[A-Za-z0-9_\-]{4,}\b")


def redact_text(text: str) -> str:
    """Mask credentials that appear inside a free-text string."""
    masked = _BEARER.sub(rf"\1{REDACTED}", text)
    return _LONG_TOKEN.sub(REDACTED, masked)


def redact(value: Any) -> Any:
    """Return ``value`` with every credential-bearing field masked.

    Recurses through dicts and sequences. The original object is not modified,
    so a redacted copy can be logged while the caller keeps the real payload.
    """
    if isinstance(value, dict):
        return {
            key: REDACTED if str(key).lower() in _SECRET_KEYS else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        redacted = [redact(item) for item in value]
        return type(value)(redacted) if isinstance(value, tuple) else redacted
    if isinstance(value, str):
        return redact_text(value)
    return value

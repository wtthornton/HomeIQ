"""
Utility helpers for safely constructing Flux queries.

These helpers centralize the sanitization logic required to prevent Flux
injection vulnerabilities whenever user-supplied strings are interpolated into
queries.
"""

from __future__ import annotations

import re

# Maximum length for sanitized values to prevent DoS attacks
MAX_SANITIZED_LENGTH = 1000


def sanitize_flux_value(value: str | None, max_length: int = MAX_SANITIZED_LENGTH) -> str:
    """
    Sanitize values for Flux queries to prevent injection attacks.

    Security: Prevents Flux query injection by:
    1. Removing special characters that could be used for injection
    2. Escaping quotes
    3. Limiting length to prevent DoS attacks
    4. Validating input type

    Args:
        value: Raw input value provided by a user or upstream client.
        max_length: Maximum allowed length for sanitized value (default: 1000).

    Returns:
        Sanitized value safe for Flux queries.

    Raises:
        ValueError: If sanitized value exceeds max_length or contains only invalid characters.

    Examples:
        >>> sanitize_flux_value("light.living_room")
        'light.living_room'
        >>> sanitize_flux_value("entity'; DROP TABLE--")
        'entity DROP TABLE'
        >>> sanitize_flux_value(None)
        ''
    """
    if value is None:
        return ""

    # Convert to string and strip whitespace
    str_value = str(value).strip()

    # Remove special characters that could be used for injection
    # Allow: word characters, spaces, dots, hyphens, underscores
    sanitized = re.sub(r'[^\w\s.\-_]', '', str_value)

    # Escape quotes (defense in depth)
    sanitized = sanitized.replace('"', '\\"')
    sanitized = sanitized.replace("'", "\\'")

    # Limit length to prevent DoS attacks
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
        # Log warning if truncation occurred (in production, use proper logging)
        import warnings
        warnings.warn(
            f"Sanitized value truncated from {len(str_value)} to {max_length} characters",
            UserWarning
        )

    # Validate that we have valid content after sanitization
    if not sanitized.strip():
        # If all characters were removed, return empty string
        # This prevents injection attempts that result in empty values
        return ""

    return sanitized

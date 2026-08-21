"""HomeIQ device taxonomy — the single source of the `device_type` vocabulary.

Two services classify devices and both must agree on the vocabulary: data-api
writes `core.devices.device_type`, device-context-classifier serves it over
HTTP. This package is that shared vocabulary.

It lives in `libs/` rather than in either service because the previous
arrangement — data-api reaching into device-context-classifier's `src/` with a
`sys.path.append` — resolved to a path that never existed, and the resulting
ImportError was swallowed into a stub that returned None for every device. The
failure was invisible for months (TAP-6392). A declared dependency fails at
build time; a filesystem reach-around fails silently.

Every value here is derived from entity domains and attributes, never from a
device's friendly name. See `.claude/rules/friendly-names.md`.
"""

from .patterns import (
    DEVICE_PATTERNS,
    DOMAIN_PRIORITY,
    DOMAIN_TO_DEVICE_TYPE,
    device_type_vocabulary,
    get_device_category,
    match_device_pattern,
)

__all__ = [
    "DEVICE_PATTERNS",
    "DOMAIN_PRIORITY",
    "DOMAIN_TO_DEVICE_TYPE",
    "device_type_vocabulary",
    "get_device_category",
    "match_device_pattern",
]

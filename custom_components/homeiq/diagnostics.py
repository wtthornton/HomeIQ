"""Diagnostics for the HomeIQ integration (TAP-5305)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data

from .const import CONF_AGENTFORGE_API_KEY, CONF_MCP_TOKEN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from . import HomeIQConfigEntry

TO_REDACT = {CONF_MCP_TOKEN, CONF_AGENTFORGE_API_KEY}


async def async_get_config_entry_diagnostics(
    _hass: HomeAssistant, entry: HomeIQConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry, without its credentials."""
    runtime = entry.runtime_data
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "catalogue_version": runtime.catalogue_version,
        "tools": [
            {
                "name": spec.name,
                "read_only": spec.read_only,
                "max_response_bytes": spec.max_response_bytes,
            }
            for spec in runtime.tools
        ],
    }

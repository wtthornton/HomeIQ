"""Constants for the HomeIQ integration."""

from __future__ import annotations

import logging
from typing import Final

DOMAIN: Final = "homeiq"
LOGGER: Final = logging.getLogger(__package__)

# Id under which HomeIQ registers its scoped LLM API. Deliberately distinct from
# Home Assistant's built-in "assist" API so HomeIQ tools are only ever offered to
# agents that explicitly select this API (TAP-5306).
LLM_API_ID: Final = "homeiq"
LLM_API_NAME: Final = "HomeIQ"

# Config entry keys.
CONF_MCP_URL: Final = "mcp_url"
CONF_MCP_TOKEN: Final = "mcp_token"
CONF_AGENTFORGE_URL: Final = "agentforge_url"
CONF_AGENTFORGE_API_KEY: Final = "agentforge_api_key"

# Options keys.
CONF_AGENTFORGE_PROJECT: Final = "agentforge_project"
CONF_EXPOSED_TOOLS: Final = "exposed_tools"

DEFAULT_AGENTFORGE_PROJECT: Final = "homeiq"

# Packaged copy of the MCP tool catalogue. Kept byte-identical to the canonical
# docs/mcp/homeiq-mcp-tools.schema.json; tests/custom_components/homeiq pins the
# two together so the copy cannot silently drift.
CATALOGUE_FILENAME: Final = "mcp_tools.schema.json"

# Network budgets.
MCP_TIMEOUT_SECONDS: Final = 30
AGENTFORGE_TIMEOUT_SECONDS: Final = 120
# AgentForge steers an invoke to the async queue when the prompt exceeds its
# sync threshold, answering 202 with only an invocation id. These bound the
# follow-up polling of /invocations/<id>/result.
AGENTFORGE_POLL_INTERVAL_SECONDS: Final = 3
AGENTFORGE_ASYNC_WAIT_SECONDS: Final = 180

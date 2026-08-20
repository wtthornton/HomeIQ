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

# Every invoke names the gene that answers it. Without a hint AgentForge falls
# through to its global orchestrator, which cannot see this project's agents.
# Measured on the live instance 2026-08-18 (TAP-6153): an unhinted AI Task
# resolved to `_system-orchestrator`, ran 69 s, cost $0.37 and returned an empty
# result — num_turns 0, result_length 0.
#
# Prose answers, and the prose half of an AI Task. Replies with the house
# envelope carrying the spoken reply under `answer`.
CONVERSATION_AGENT: Final = "hiq-assistant"

# An AI Task that supplies a structure needs a schema instance back, which is
# hiq-assistant's one forbidden output ("Prose only: no JSON"). hiq-extract is
# the gene whose declared contract is exactly that: it answers
# {"instance": <the caller's schema instance>, "manifest": [...],
# "unsourced_fields": [...]}, so the caller's object comes out of `instance`.
AI_TASK_STRUCTURED_AGENT: Final = "hiq-extract"

# Packaged copy of the MCP tool catalogue. Kept byte-identical to the canonical
# docs/mcp/homeiq-mcp-tools.schema.json; tests/custom_components/homeiq pins the
# two together so the copy cannot silently drift.
CATALOGUE_FILENAME: Final = "mcp_tools.schema.json"

# Network budgets.
MCP_TIMEOUT_SECONDS: Final = 30
AGENTFORGE_TIMEOUT_SECONDS: Final = 120
# AgentForge steers this invoke to the async queue and answers 202 with only an
# invocation id. These bound the follow-up polling of /invocations/<id>/result.
#
# The steering is not about prompt size (TAP-6152). AgentForge 4.59.1 steers when
# the agent's *effective timeout* exceeds sync_invoke_steering_threshold_seconds
# (180): backend/workflows/kickoff_steering.py resolve_effective_task_invoke_mode,
# fed by resolve_timeout, which falls back to settings.default_timeout_seconds
# (600) for any gene that declares no timeout_seconds. As of TAP-6167 the two
# interactive genes (hiq-assistant, hiq-extract) declare timeout_seconds: 120
# and answer synchronously; the other 22 genes run inside workflows where the
# async queue is the correct transport, so they still steer. The polling
# machinery below is the fallback for those, and for any future steer.
#
# Measured end to end against the live instance 2026-08-18, POST to terminal
# result: one-tool turn 14.6 s, three-tool turn 26.9 s. The POST itself returns
# in ~45 ms, so the wall clock is the agent run, not the queue. Dropping the poll
# interval from 3 s to 1 s is therefore the only latency this side owns: it
# removes up to 3 s (≈1.5 s on average) of pure waiting after the run settles, at
# the cost of ~15-27 cheap GETs per turn instead of ~5-9.
AGENTFORGE_POLL_INTERVAL_SECONDS: Final = 1
# Kept at 180 s deliberately: the worst turn measured was 27 s, and this is a
# give-up bound, not a budget being spent. Lowering it would only convert a slow
# run into a failed one.
AGENTFORGE_ASYNC_WAIT_SECONDS: Final = 180

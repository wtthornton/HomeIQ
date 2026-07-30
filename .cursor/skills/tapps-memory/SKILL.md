---
name: tapps-memory
description: >-
  Manage shared project memory via tapps-mcp CLI and session notes.
  Use when saving cross-session decisions, searching prior patterns, or
  checking brain bridge health. For chat handoffs use tapps-handoff-session.
mcp_tools:
  - tapps_session_start
  - tapps_session_notes
---

`tapps_memory` on the **`nlt-memory`** MCP server is a slim facade (TAP-3895). Default consumer path is **`uv run tapps-mcp memory`** (bridge-only — never add direct `tapps-brain` to `.mcp.json`).

## Routing guide

| Need | Path |
|------|------|
| Cross-chat handoff | `tapps-handoff-session` then `tapps-continue-session` |
| Session-local notes | `tapps_session_notes(action="save", ...)` |
| Save / recall / search brain | `uv run tapps-mcp memory <subcommand>` |
| Brain health | `tapps_session_start()` → `brain_bridge_health` |

## CLI (daily drivers)

`memory save`, `get`, `search`, `list`, `export` — see skill body for examples. Shell auth: `TAPPS_BRAIN_AUTH_TOKEN` or `TAPPS_MCP_MEMORY_BRAIN_AUTH_TOKEN`.

## Tiers

`architectural` (180d), `pattern` (60d), `procedural` (30d), `context` (14d). Tag with `--tags critical,security` when warranted.

## Advanced

Federation, hive, KG: `docs/MEMORY_REFERENCE.md`. Consumer agents use CLI; coordinator agents may use brain MCP directly.

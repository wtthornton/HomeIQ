---
name: tapps-init
user-invocable: true
model: claude-sonnet-4-6
description: >-
  Bootstrap TappsMCP in a project. Creates AGENTS.md, TECH_STACK.md,
  platform rules, hooks, agents, skills, and MCP config. Use when setting
  up TappsMCP in a new or existing project for the first time.
allowed-tools: mcp__nlt-setup__tapps_init mcp__nlt-setup__tapps_doctor
argument-hint: "[project-root]"
---

Bootstrap TappsMCP in a new or existing project:

1. Call `mcp__nlt-setup__tapps_init` to run the full bootstrap pipeline (`mcp_config` defaults true)
2. Check the response for `content_return: true` — if present, the server could not
   write files directly (Docker / read-only mount).  Apply the files from
   `file_manifest.files[]` using the Write tool.  See `/tapps-apply-files` for details.
3. If files were written directly, review the created files (AGENTS.md, TECH_STACK.md, platform rules, hooks, MCP config)
4. Confirm MCP config lists tapps-mcp only (no direct tapps-brain entry — bridge-only)
5. If any issues are reported, call `mcp__nlt-setup__tapps_doctor` to diagnose
6. Verify that `.claude/settings.json` has MCP tool auto-approval rules
7. For shared-brain HTTP wiring, see docs/operations/CONSUMER-REPO-BRAIN-WIRING.md
8. Confirm the project is ready for the TappsMCP quality workflow

**If `tapps_init` is not available** (server not in available MCP servers), use the CLI:
1. Run from the project root: `tapps-mcp upgrade --force --host auto`
2. Then verify: `tapps-mcp doctor`
3. Restart your MCP host to pick up the new config

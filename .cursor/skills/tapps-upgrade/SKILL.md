---
name: tapps-upgrade
description: >-
  Upgrade tapps-mcp / docs-mcp in this project to the latest version.
  Reinstalls global CLIs, restarts MCP servers, refreshes scaffolding via
  `tapps-mcp upgrade`, verifies via doctor + checklist. Use when a new
  tapps-mcp or docs-mcp version is available and the project scaffolding
  needs to be refreshed.
mcp_tools:
  - tapps_session_start
  - tapps_doctor
  - tapps_checklist
---

Upgrade tapps-mcp / docs-mcp end-to-end. The user's request is standing authorization — do NOT pause mid-flow.

**Pick install source from prompt:**

- Local checkout: `uv tool install --reinstall --from <path>/packages/tapps-mcp tapps-mcp` (and same for `docs-mcp`).
- Git tag: `uv tool install --reinstall "git+https://github.com/wtthornton/tapps-mcp.git@vX.Y.Z#subdirectory=packages/tapps-mcp" tapps-mcp`.

If unspecified, ask once.

**Steps:**

1. Reinstall both CLIs. Verify with `uv tool list | grep -E '(tapps-mcp|docs-mcp)'`.
2. Restart MCP servers (exit + reopen Cursor, or reconnect). Stop on first invocation; resume after restart.
3. `tapps_session_start(force=true)`. Confirm `server.version` matches and `install_drift.drift_detected == false`.
4. `tapps-mcp upgrade --dry-run`. Review diff for AGENTS.md, hooks, rules, skills, .mcp.json. Pause if a customized canonical section will be overwritten.
5. `tapps-mcp upgrade` (writes timestamped backup to `.tapps-mcp/backups/<ts>/`).
6. `tapps-mcp doctor` AND `tapps_checklist(task_type="upgrade")`. Stop on failure.
7. One-line summary: versions, files refreshed, doctor + checklist status, backup path.

**Rollback:** `tapps-mcp rollback` (only if step 5/6 reveals a regression).

**Do NOT:** publish to PyPI/npm; bump tapps-mcp repo versions; touch tapps-brain; add `tapps-brain` as a top-level `.mcp.json` entry.

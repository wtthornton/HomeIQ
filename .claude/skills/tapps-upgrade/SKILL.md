---
name: tapps-upgrade
user-invocable: true
model: claude-sonnet-4-6
description: >-
  Upgrade tapps-mcp / docs-mcp in this project to the latest version.
  Reinstalls global CLIs, restarts the MCP servers, refreshes scaffolding
  via `tapps-mcp upgrade` (dry-run preview + timestamped backup), and
  verifies via doctor + checklist. Use when a new tapps-mcp or docs-mcp
  version is available and the project scaffolding needs to be refreshed.
allowed-tools: Bash mcp__nlt-build__tapps_session_start mcp__nlt-setup__tapps_doctor mcp__nlt-build__tapps_checklist
argument-hint: "[--from-checkout <path> | --from-tag vX.Y.Z]"
---

Upgrade tapps-mcp / docs-mcp end-to-end. The user's request to upgrade is standing authorization for the full pipeline — do NOT pause mid-flow.

**Pick an install source from the prompt:**

- Local checkout (`--from-checkout <path>` or user mentions a local clone):
  `uv tool install --reinstall --from <path>/packages/tapps-mcp tapps-mcp`
  and the same for `docs-mcp`.
- Git tag (`--from-tag vX.Y.Z`):
  `uv tool install --reinstall "git+https://github.com/wtthornton/tapps-mcp.git@vX.Y.Z#subdirectory=packages/tapps-mcp" tapps-mcp`
  and the same for `docs-mcp`.
- If neither is specified, ASK once which to use.

**Steps:**

1. **Reinstall global CLIs.** Run both `uv tool install --reinstall ...` commands. Verify: `uv tool list | grep -E '(tapps-mcp|docs-mcp)'` — both must show the same version.
2. **Restart MCP servers.** The running processes still hold old code. Tell the user to exit/reopen (or `/mcp` reconnect), then re-invoke this skill. Stop here on the first invocation.
3. **Verify new version is live.** Call `mcp__nlt-build__tapps_session_start(force=true)`. Confirm `server.version` matches target and `diagnostics.install_drift.drift_detected == false`. If drift persists, the server wasn't restarted — go back to step 2.
4. **Dry-run the scaffolding refresh.** Run `tapps-mcp upgrade --dry-run`. Review the diff for AGENTS.md, CLAUDE.md, .claude/hooks/, .claude/rules/, .claude/agents/, .claude/skills/, .mcp.json. The smart-merge preserves customizations in non-canonical sections; canonical sections are replaced wholesale. Pause if a customized canonical section will be overwritten.
5. **Apply the upgrade.** Run `tapps-mcp upgrade` (writes timestamped backup to `.tapps-mcp/backups/<ts>/`).
6. **Verify.** Run `tapps-mcp doctor` AND `mcp__nlt-build__tapps_checklist(task_type="upgrade")`. Surface any problems — do not declare done on a failure.
7. **Report.** One-line summary: `Upgraded: tapps-mcp X.Y.Z, docs-mcp X.Y.Z. Scaffolding: N files. Doctor: OK. Checklist: complete. Backup: .tapps-mcp/backups/<ts>/`.

**Rollback (only if step 5/6 broke something):** `tapps-mcp rollback` restores from the most recent backup. Do NOT roll back "to be safe" after a clean run.

**Do NOT:**

- Publish to PyPI / npm — tapps-mcp is local-install only.
- Bump versions in the tapps-mcp dev repo itself — separate workflow.
- Touch tapps-brain — separate Docker service with its own release flow.
- Add `tapps-brain` as a top-level `.mcp.json` entry — it's bridge-only via tapps-mcp's BrainBridge.

<!-- tapps-claude-version: 3.12.72 -->
<!-- BEGIN: tapps-obligations v3.12.72 -->
# TAPPS Quality Pipeline

This project uses the TAPPS MCP server for code quality enforcement.
Every tool response includes `next_steps` - consider following them.
Full pipeline details are in `.claude/rules/tapps-pipeline.md` (auto-loaded for Python and infra files).

## Tapps Rules

Seven rules every agent in this project should follow.

1. **Fix root causes, not symptoms.** No workarounds, no `--no-verify`, no try/except-and-swallow. If you are tempted to bypass a failure, stop and diagnose it.
2. **When confidence drops below 100%, query tapps-mcp before writing code.** `tapps_lookup_docs` for library APIs, `uv run tapps-mcp memory search --query "..."` for prior decisions and patterns. Guessing from memory is the most common source of hallucinated APIs.
3. **`tapps_lookup_docs` is a Context7-backed cache — use it freely.** Lookups are local-cache-first; repeat calls are near-zero cost. There is no budget to conserve.
4. **Be context-window aware — delegate noisy work to subagents.** If a task would dump more than three file reads or large tool output you won't reference again, spawn `Explore` or `general-purpose`. Subagents return summaries; the main thread stays clean.
5. **Write clean, efficient code.** Clear names, no dead branches, no speculative abstractions, no commented-out code. Every line should justify its presence.
6. **Don't over-engineer.** The simplest solution that satisfies the requirement is the correct one. No knobs nobody asked for. Three similar lines beat a premature abstraction.
7. **Route Linear through skills, not raw plugin calls.** Use the `linear-issue` skill for any write (epic, story, update) — it runs the docs-mcp template + validator before push. Use the `linear-read` skill for multi-issue reads (cache-first). Single-issue lookups: `get_issue(id=...)` directly. Release announcements go through the `linear-release-update` skill.

## Recommended Tool Call Obligations

You should follow these steps to avoid broken, insecure, or hallucinated code.

### Session Start

You should call `tapps_session_start()` as the first action in every session.
This returns server info (version, checkers, config) and project context.

### Before Using Any Library API

You should call `tapps_lookup_docs(library, topic)` before writing code that uses an external library.
This prevents hallucinated APIs. Prefer looking up docs over guessing from memory.

### After Editing Any Python File

You should call `tapps_quick_check(file_path)` after editing any Python file.
This runs scoring + quality gate + security scan in a single call.

### Before Declaring Work Complete

For multi-file changes: You should call `tapps_validate_changed(file_paths="file1.py,file2.py")` with explicit paths to batch-validate changed files. **Always pass `file_paths`** — auto-detect scans all git-changed files and can be very slow. Default is quick mode; only use `quick=false` as a last resort (pre-release, security audit).
Run the quality gate before considering work done.
You should call `tapps_checklist(task_type)` as the final step to verify no required tools were skipped. The response carries an inline `usage_gaps` payload (same data as the standalone `tapps_usage` tool) — read it for any missed lookups or unvalidated edits before declaring done. The Stop hook (`tapps-stop.sh`) writes to `.tapps-mcp/.completion-gate-violations.jsonl` in warn mode when code edits ship without validation; no block — pure telemetry that feeds `tapps_usage`.

> **Skill deprecations (v3.12.0):** `tapps-score`, `tapps-gate`, `tapps-validate`, `tapps-report` are deprecated wrappers around single MCP tools. Prefer the direct tool calls or `/tapps-finish-task`.

### Domain Decisions

You should call `tapps_lookup_docs(library, topic)` when you need domain-specific guidance
(security patterns, testing strategy, API design, database best practices, etc.).

### Refactoring or Deleting Files

You should call `tapps_impact_analysis(file_path)` before refactoring or deleting any file.
For **function/method** refactors use `tapps_call_graph(symbol=...)` or `tapps_impact_analysis` with
`symbol` and `granularity="symbol"|"both"`. For changed files use `tapps_diff_impact` or
`tapps_validate_changed(include_impact=true)` for ranked `affected_tests` (Epic 114 / ADR-0017).

### Infrastructure Config Changes

You should call `tapps_validate_config(file_path)` when changing Dockerfile, docker-compose, or infra config.

## Memory System

Use `/tapps-handoff-session` and `/tapps-continue-session` for cross-session handoffs (stored in `.tapps-mcp/session-handoff.md`). Use `tapps-mcp memory save/get` for ad-hoc payloads.

## Quality Gate Behavior

Gate failures are sorted by priority. Security floor: 50/100 regardless of score.

## Upgrade & Rollback

Run `tapps_upgrade` after each release to refresh generated files. Use `tapps-mcp rollback` to restore. Protect custom artifacts by adding token to `upgrade_skip_files` in `.tapps-mcp.yaml` (e.g., `CLAUDE.md`, `.claude/skills`).
<!-- END: tapps-obligations -->

## CI Integration

**TappsMCP does not run in GitHub-hosted CI, and no workflow should try.** It is
not distributed through a package index — it is installed *globally on the
developer machine* from a local checkout, and agents reach it over loopback:

- Source: `/home/wtthornton/code/tapps-mcp` (remote `wtthornton/TappsMCP.git`)
- Installed to `~/.tapps-mcp/releases/<version>-<sha>/`, selected by the
  `~/.tapps-mcp/current` symlink, fronted by `~/.local/bin/tapps-mcp`
- Agent surface: the six `nlt-*` MCP servers in `.mcp.json`, all HTTP to
  `127.0.0.1:8760-8765` (`nlt-build`, `nlt-memory`, `nlt-setup`,
  `nlt-linear-issues`, `nlt-project-docs`, `nlt-release-ship`). One fleet serves
  several projects; scope comes from the `X-Tapps-Project-Root` header.
- Upgrades go through the `tapps-upgrade` skill, never `pip`.

A GitHub-hosted runner has none of that — no checkout, no global install, no
loopback fleet. All three install attempts fail by construction:

1. `pip install tapps-mcp` — not on PyPI (404), and not intended to be. Same for
   `tapps-core`.
2. `pip install "git+https://github.com/wtthornton/TappsMCP.git@<tag>"` — the repo
   root is a uv workspace with no `[project]` table, so setuptools refuses with
   "Multiple top-level packages discovered in a flat-layout".
3. Adding `#subdirectory=packages/tapps-mcp` gets past the build, then fails on
   `tapps-core`, which resolves only via `[tool.uv.sources] tapps-core =
   { workspace = true }` — a uv-only key that plain pip ignores.

This is a **distribution-model mismatch, not a packaging bug**. Publishing to
PyPI is not the fix. (If it were ever reconsidered: the name `docs-mcp` on PyPI
already belongs to an unrelated project, so a bare `pip install docs-mcp` pulls a
stranger's package.)

The workflows that tried anyway never once passed — `agentic-pr-review` 0-for-117
runs and the `quality-gate` job 0-for-176, both since 2026-03-06 — and were
removed in `bfcf5379`. See `docs/TAPPSMCP_INSTALL_MODEL.md`.

**Where the gate is actually enforced:** locally, before code reaches CI, which is
the design rather than a fallback — `tapps_quick_check` per edit,
`tapps_validate_changed` before done, `tapps_checklist` last, the Stop hook, and
`/tapps-finish-task`. CI keeps what needs no TappsMCP: `ruff check` and
`ruff format --check` per service in `reusable-group-ci.yml`, plus the
`regression-checks` job retained in `quality-gate.yml`.

Reintroducing the gate in CI requires a **self-hosted runner** carrying the global
install. The step would then be:

```bash
TAPPS_MCP_PROJECT_ROOT=/workspace \
  tapps-mcp validate-changed --preset staging
```

Never reintroduce it behind `|| true` or `continue-on-error`. A gate that cannot
fail reads as coverage while providing none.

### Claude Code headless mode

```bash
claude --headless \
  --allowedTools "mcp__nlt-build__tapps_validate_changed" \
  "Run tapps_validate_changed with preset=staging"
```

### VS Code / headless — enableAllProjectMcpServers

In headless or non-interactive VS Code contexts, set:
`claude.enableAllProjectMcpServers: true` in workspace settings.


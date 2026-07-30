<!-- tapps-claude-version: 3.12.52 -->
<!-- BEGIN: tapps-obligations v3.12.52 -->
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

`tapps_memory` provides persistent cross-session knowledge with **44 actions** (save, search, consolidate, federation, profiles, hive, health, knowledge graph, batch ops, feedback, native session memory, and more). **Tiers:** architectural (180d), pattern (60d), procedural (30d), context (14d). **Scopes:** project, branch, session. Max 1500 entries. Configure `memory_hooks` in `.tapps-mcp.yaml` for auto-recall and auto-capture.

**Cross-session handoff:** prefer `/tapps-handoff-session` and `/tapps-continue-session` (`.tapps-mcp/session-handoff.md`). For ad-hoc payloads use `tapps-mcp memory save/get`. Cross-agent: `hive_propagate`; cross-project: federation actions.

## Quality Gate Behavior

Gate failures are sorted by category weight (highest-impact first).
A security floor of 50/100 is enforced regardless of overall score.

## Upgrade & Rollback

After upgrading TappsMCP, run `tapps_upgrade` to refresh generated files.
A timestamped backup is created before overwriting. Use `tapps-mcp rollback` to restore.
To protect customized files from upgrade, add them to `upgrade_skip_files` in `.tapps-mcp.yaml`.
<!-- END: tapps-obligations -->

## CI Integration

TappsMCP can run in CI without an MCP host.

```bash
# Install TappsMCP
pip install tapps-mcp

# Validate changed files
TAPPS_MCP_PROJECT_ROOT=/workspace \
  tapps-mcp validate-changed --preset staging
```

### Claude Code headless mode

```bash
claude --headless \
  --allowedTools "mcp__nlt-build__tapps_validate_changed" \
  "Run tapps_validate_changed with preset=staging"
```

### VS Code / headless — enableAllProjectMcpServers

In headless or non-interactive VS Code contexts, set:
`claude.enableAllProjectMcpServers: true` in workspace settings.

<!-- BEGIN: karpathy-guidelines c9a44ae (MIT, forrestchang/andrej-karpathy-skills) -->
<!--
  Vendored from https://github.com/forrestchang/andrej-karpathy-skills
  Pinned commit: c9a44ae835fa2f5765a697216692705761a53f40 (2026-04-15)
  License: MIT (c) forrestchang
  Do not edit by hand — update KARPATHY_GUIDELINES_SOURCE_SHA in prompt_loader.py
  and re-run the vendor script, then bump tapps-mcp version.
-->
## Karpathy Behavioral Guidelines

> Source: https://github.com/forrestchang/andrej-karpathy-skills @ c9a44ae835fa2f5765a697216692705761a53f40 (MIT)
> Derived from [Andrej Karpathy's observations](https://x.com/karpathy/status/2015883857489522876) on LLM coding pitfalls.

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
<!-- END: karpathy-guidelines -->

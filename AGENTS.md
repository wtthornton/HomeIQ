<!-- tapps-agents-version: 3.12.52 -->
# TappsMCP - instructions for AI assistants

When the **TappsMCP** MCP server is configured, you have access to tools for **code quality, doc lookup, and domain expert advice**. Use them to avoid hallucinated APIs, missed quality steps, and inconsistent output.

**File paths:** Use paths relative to project root (e.g. `src/main.py`). Absolute host paths also work when `TAPPS_MCP_HOST_PROJECT_ROOT` is set.

---

## What TappsMCP is

TappsMCP is an MCP server that provides a comprehensive quality toolset for your project. It exposes 26 tools for:

- **Scoring** Python files (0-100 across 7 categories: complexity, security, maintainability, test coverage, performance, structure, devex)
- **Security scanning** (Bandit + secret detection with redacted context)
- **Quality gates** (pass/fail against configurable presets: standard, strict, framework)
- **Dead code detection** (Vulture-based unused function/class/import/variable detection with confidence scoring)
- **Dependency vulnerability scanning** (pip-audit for known CVEs in third-party packages)
- **Circular dependency detection** (import graph analysis, cycle detection, coupling metrics)
- **Documentation lookup** (up-to-date library docs via Context7 with multi-provider fallback and cache)
- **Config validation** (Dockerfile, docker-compose, WebSocket/MQTT/InfluxDB best practices)
- **Domain experts** (16 built-in experts with RAG-backed answers, optional vector search)
- **Project context** (project type detection, tech stack, impact analysis)
- **Session management** (persist decisions, constraints, and notes across long sessions)
- **Quality reports** (JSON, Markdown, or HTML summaries)
- **Metrics and feedback** (dashboard, usage stats, adaptive learning via feedback)
- **Session checklist** (track which tools were used so you don't skip required steps)
- **Pipeline orchestration** (batch validation, workflow prompts, project initialization)
- **Structured outputs** (machine-parseable JSON alongside human-readable text for all scoring tools)

You only see these tools when the host has started the TappsMCP server and attached it to your session.

**In this project:** TappsMCP is provided via **direct stdio** (`tapps-mcp serve`). Configure `.cursor/mcp.json` (Cursor) and `.mcp.json` (Claude Code) at project root. Tools appear as `mcp__tapps-mcp__tapps_*` (e.g. `mcp__tapps-mcp__tapps_quick_check`).

**File paths:** For tools that take `file_path`, use **paths relative to the project root** (e.g. `src/main.py`, `tests/test_foo.py`) so they work with both stdio and Docker. If the server is configured with `TAPPS_MCP_HOST_PROJECT_ROOT` (e.g. when using Docker), you can also pass **absolute host paths** (e.g. `C:\projects\myapp\src\main.py`); the server will map them to the project root.

---

## When to use each tool

| Tool | When to use it |
|------|----------------|
| **tapps_session_start** | **FIRST call in every session** - combines server info + project profile in one call. Skipping means all tools lack project context. |
| **tapps_server_info** | At **session start** - discover version, available tools, and installed checkers. Response includes a short `recommended_workflow` string. |
| **tapps_score_file** | When **editing or reviewing** a Python file. Use `quick=True` during edit-lint-fix loops; use full (default) **before declaring work complete**. |
| **tapps_quick_check** | **After editing any Python file** - quick score + gate + basic security in one fast call. |
| **tapps_security_scan** | When the change is **security-sensitive** or before a security-focused review. |
| **tapps_quality_gate** | **Before declaring work complete** - ensures the file passes the configured quality preset. Do not consider work done until this passes (or the user accepts the risk). |
| **tapps_validate_changed** | **Before declaring multi-file work complete** - auto-detects changed files via git diff and runs score + gate + security on each. |
| **tapps_lookup_docs** | **Before writing code** that uses an external library - use the returned docs to avoid hallucinated APIs. |
| **tapps_validate_config** | When **adding or changing** Dockerfile, docker-compose, or infra config. |
| **tapps_consult_expert** | When making **domain-specific decisions** (security, testing, APIs, database, etc.) and you want authoritative, RAG-backed guidance. Pass `domain` when context makes it obvious (e.g. editing a test file -> `domain="testing-strategies"`). |
| **tapps_research** | When you need **combined expert + docs** in one call - consults the domain expert, then auto-supplements with Context7 documentation when RAG is empty or confidence is low. Saves a round-trip vs calling `tapps_consult_expert` + `tapps_lookup_docs` separately. |
| **tapps_list_experts** | When you need to see **which expert domains exist** before calling `tapps_consult_expert`. |
| **tapps_project_profile** | At **session start** or when you need project context - detects project type, tech stack, and structure so you can apply the right patterns. |
| **tapps_session_notes** | When you make a **key decision or discover a constraint** - save it so you can recall it later in a long session. |
| **tapps_impact_analysis** | Before **modifying a file's public API** - shows what depends on it and what could break. |
| **tapps_report** | After scoring/gating, when the user wants a **formatted quality summary** (Markdown, JSON, or HTML). |
| **tapps_checklist** | **Before declaring work complete** - reports which tools were called and which are missing (with reasons). Fix missing required steps before saying done. |
| **tapps_dashboard** | When the user wants to **review how TappsMCP is performing** - scoring accuracy, gate pass rates, expert effectiveness, cache performance, quality trends, and alerts. Supports json, markdown, and html output. |
| **tapps_stats** | When the user wants **usage statistics** - call counts, success rates, average durations, cache hit rates, and gate pass rates. Filterable by tool and time period. |
| **tapps_feedback** | After receiving a tool result - report whether the output was **helpful or not**. This feedback improves adaptive scoring and expert weights over time. |
| **tapps_dead_code** | When you want to **find unused code** in a Python file - detects unused functions, classes, imports, and variables with confidence scoring. Use during refactoring or code review. |
| **tapps_dependency_scan** | When you want to **check for vulnerable dependencies** - scans pip packages for known CVEs using pip-audit. Use before releases or security reviews. |
| **tapps_dependency_graph** | When you want to **understand module dependencies** - builds import graph, detects circular imports, and calculates coupling metrics. Use before refactoring or when investigating import errors. |
| **tapps_workflow** | When you want the **recommended tool call order** for a specific task type (general, feature, bugfix, refactor, security, review). |
| **tapps_init** | At **pipeline bootstrap** - creates AGENTS.md, TECH_STACK.md, platform rules, optionally warms caches. Call once per project (or when upgrading). |
| **tapps_upgrade** | After a **TappsMCP version update** - validates and refreshes AGENTS.md, platform rules, hooks, agents, skills, and settings. Preserves custom command paths (e.g. PyInstaller exe). Use `dry_run: true` to preview. |
| **tapps_doctor** | When **diagnosing configuration issues** - checks binary availability, MCP configs, platform rules, generated files, hooks, and installed quality tools. Returns per-check pass/fail with remediation hints. |

---

## Domain hints for tapps_consult_expert

Pass the `domain` parameter when the context clearly implies a domain. This improves routing accuracy and avoids auto-detection mistakes.

| Context | domain value |
|---------|--------------|
| Editing test files, conftest.py, pytest config | `testing-strategies` |
| Security-sensitive code, auth, validation | `security` |
| API routes, FastAPI/Flask endpoints | `api-design-integration` |
| Database models, migrations, queries | `database-data-management` |
| Dockerfile, docker-compose, k8s manifests | `cloud-infrastructure` |
| CI/CD, workflows, build config | `development-workflow` |
| Code quality, linting, type hints | `code-quality-analysis` |
| Architecture decisions, patterns | `software-architecture` |

When in doubt, omit `domain` to let auto-detection from the question text choose.

### Business experts

Projects can define custom business-domain experts in `.tapps-mcp/experts.yaml`. Use `tapps_manage_experts(action="list")` to see them. Pass business domain names to `tapps_consult_expert(domain="...")` like built-in domains.

---

## Recommended workflow

1. **Session start:** Call `tapps_session_start` (returns server info and project context).
2. **Check project memory:** Consider `uv run tapps-mcp memory search --query "..."` or read `.tapps-mcp/session-handoff.md`.
3. **Record key decisions:** Use `tapps_session_notes(action="save", ...)` for session-local notes. Use `uv run tapps-mcp memory save --key ... --tier ... --value "..."` to persist decisions across sessions.
3. **Before using a library:** Call `tapps_lookup_docs(library=...)` and use the returned content when implementing.
4. **Before modifying a file's API:** Call `tapps_impact_analysis(file_path=...)` to see what depends on it.
5. **During edits:** Call `tapps_quick_check(file_path=...)` or `tapps_score_file(file_path=..., quick=True)` after each change.
6. **Before declaring work complete:**
   - Recommended: invoke the `/tapps-finish-task` skill — bundles `tapps_validate_changed` + `tapps_checklist` + an optional memory save and reports a one-line summary.
   - If you'd rather run the steps manually: `tapps_validate_changed(file_paths="file1.py,file2.py")` with explicit paths to score + gate changed files (never call without `file_paths` in large repos; default is quick mode), then `tapps_checklist(task_type=...)` and, if `complete` is false, call the missing required tools (use `missing_required_hints` for reasons). The checklist response also carries an inline `usage_gaps` block — review it for missed lookups or unvalidated edits.
   - Optionally call `tapps_report(format="markdown")` to generate a quality summary.

   **Stop-hook telemetry (warn mode):** if you edited Python/TS/Go files without validating, the Stop hook (`tapps-stop.sh`) appends to `.tapps-mcp/.completion-gate-violations.jsonl`. No block — telemetry that feeds `tapps_usage`. `tapps_doctor` reports `completion_gate_hook.installed`.

   **next_steps shape:** `tapps_score_file` and `tapps_quick_check` template `{file_path}` into next-tool suggestions, so you get paste-ready signatures like `tapps_security_scan(file_path='src/foo.py')`.
7. **When in doubt:** Use `tapps_lookup_docs` for domain-specific questions and library guidance; use `tapps_validate_config` for Docker/infra files.

### Review Pipeline (multi-file)

For reviewing and fixing multiple files in parallel, use the `/tapps-review-pipeline` skill:

1. It detects changed Python files and spawns `tapps-review-fixer` agents (one per file or batch)
2. Each agent scores the file, fixes issues, and runs the quality gate
3. Results are merged and validated with `tapps_validate_changed`
4. A summary table shows before/after scores, gate status, and fixes applied

You can also invoke the `tapps-review-fixer` agent directly on individual files for combined review+fix in a single pass.

---

## Checklist task types

Use the `task_type` that best matches the current work:

- **feature** - New code
- **bugfix** - Fixing a bug
- **refactor** - Refactoring
- **security** - Security-focused change
- **review** - General code review (default)

The checklist uses this to decide which tools are required vs recommended vs optional for that task.

---

## tapps_session_start vs tapps_init

| Aspect | tapps_session_start | tapps_init |
|--------|---------------------|------------|
| **When** | **First call in every session** | **Pipeline bootstrap** (once per project, or when upgrading) |
| **Duration** | Fast (~1s, server info only) | Full run: 10-35+ seconds |
| **Purpose** | Load server info (version, checkers, config) into context | Create files (AGENTS.md, TECH_STACK.md, platform rules), optionally warm cache/RAG |
| **Side effects** | None (read-only) | Writes files, warms caches |
| **Typical flow** | Call at session start, then work | Call once to bootstrap, or `dry_run: true` to preview |

**Session start** -> `tapps_session_start`. Use this as the first call in every session. Returns server info and project context.

**Pipeline/bootstrap** -> `tapps_init`. Use when you need to set up TappsMCP in a project (AGENTS.md, TECH_STACK.md, platform rules) or upgrade existing files.

**Both in one session?** Yes. If the project is not yet bootstrapped: call `tapps_session_start` first (fast), then `tapps_init` (creates files). If the project is already bootstrapped: call only `tapps_session_start` at session start.

**Lighter tapps_init options** (for timeout-prone MCP clients): Use `dry_run: true` to preview (~2-5s); use `verify_only: true` for a quick server/checker check (~1-3s); or set `warm_cache_from_tech_stack: false` and `warm_expert_rag_from_tech_stack: false` for a faster init without cache warming.

**MCP config (default on):** `tapps_init` writes project-scoped MCP config after bootstrap (`mcp_config=true`); strips direct `tapps-brain` entries (bridge-only). Pass `mcp_config=false` to skip. Brain wiring: [docs/operations/CONSUMER-REPO-BRAIN-WIRING.md](docs/operations/CONSUMER-REPO-BRAIN-WIRING.md).

**Tool contract:** Session start returns server info and project context. tapps_validate_changed default = score + gate only; use `security_depth='full'` or `quick=false` for security. tapps_quick_check has no `quick` parameter (use tapps_score_file(quick=True) for that).

---

## Platform hooks and automation

When `tapps_init` generates platform-specific files, it also creates **hooks**, **subagents**, and **skills** that automate parts of the workflow:

### Hooks (auto-generated)

**Claude Code** (`.claude/hooks/`): advisory hook scripts that fire on lifecycle events. Which scripts are wired depends on engagement level (`low` = SessionStart only; `medium` = 8 events; `high` = 10 events). Common entries:
- **SessionStart** - Injects TappsMCP awareness on session start and after compaction
- **PostToolUse (Edit/Write)** - Reminds you to run `tapps_quick_check` after Python edits
- **Stop** - Reminds you to run `tapps_validate_changed` before session end (non-blocking)
- **TaskCompleted** - Reminds you to validate before marking task complete (non-blocking)
- **PreCompact** - Backs up scoring context before context window compaction
- **SubagentStart / SubagentStop** - Injects TappsMCP awareness into spawned subagents
- **SessionEnd / PostToolUseFailure / UserPromptSubmit** (high only) - End-of-session capture, tool-failure logging, and per-prompt pipeline reminders

Opt-in `PreToolUse` gates are independent flags in `.tapps-mcp.yaml` — enable each based on what you want blocked:
- `destructive_guard: true` — blocks destructive Bash commands (`rm -rf`, `format c:`, etc.).
- `linear_enforce_gate: true` — blocks `mcp__plugin_linear_linear__save_issue` unless the `linear-issue` skill flow (with `docs_validate_linear_issue`) was used recently. Bypass: `TAPPS_LINEAR_SKIP_VALIDATE=1`. Bash + PowerShell. Default: on at medium/high engagement, off at low.
- `linear_enforce_cache_gate: "off" | "warn" | "block"` (TAP-1224) — gates `mcp__plugin_linear_linear__list_issues` behind a recent `tapps_linear_snapshot_get` for the same `(team, project, state, label, limit)` slice. **Warn mode** (default at medium/high engagement) logs violations to `.tapps-mcp/.cache-gate-violations.jsonl` and allows the call. **Block mode** rejects with exit 2 unless a matching sentinel < 300s old exists. Single-issue lookups must use `mcp__plugin_linear_linear__get_issue` instead. Pairs with the `linear-read` skill which routes the cache-first dance. Bypass: `TAPPS_LINEAR_SKIP_CACHE_GATE=1`. `tapps doctor` reports current mode + 24h violation count.
- `install_git_hooks: true` (TAP-979) — writes `.githooks/pre-commit` and sets `core.hooksPath = .githooks`. Runs `tapps-mcp validate-changed --quick` on staged Python files and fails the commit on gate failure. Bypass: `TAPPS_SKIP_GATE=1`. Default: off.

Run `tapps-mcp doctor` to list wired matchers.

**Cursor** (`.cursor/hooks/`): 3 hook scripts:
- **beforeMCPExecution** - Logs MCP tool invocations for observability
- **afterFileEdit** - Fire-and-forget reminder to run quality checks
- **stop** - Prompts validation via followup_message before session ends

### Subagents (auto-generated)

Four agent definitions per platform in `.claude/agents/` or `.cursor/agents/`:
- **tapps-reviewer** (sonnet) - Reviews code quality and runs security scans after edits
- **tapps-researcher** (sonnet) - Looks up documentation and researches best practices
- **tapps-validator** (haiku) - Runs pre-completion validation on all changed files
- **tapps-review-fixer** (sonnet, isolated worktree) - Combined score-fix-validate pass; designed for parallel multi-file pipelines

### Skills (auto-generated)

Sixteen core tapps-* SKILL.md files per platform in `.claude/skills/` or `.cursor/skills/` (plus linear-* and optional continuous-learning-v2):
- **tapps-finish-task** - End-of-task pipeline: validate_changed + checklist + optional memory save
- **tapps-handoff-session** - Write `.tapps-mcp/session-handoff.md` and call `tapps_session_end` before ending a chat
- **tapps-continue-session** - Bootstrap a fresh chat from the last handoff + optional Linear issue
- **tapps-review-pipeline** - Orchestrate a parallel review-fix-validate pipeline
- **tapps-research** - Look up library documentation and research best practices
- **tapps-security** - Run a comprehensive security audit with vulnerability scanning
- **tapps-memory** - Manage shared project memory (44 actions, cross-session)
- **tapps-tool-reference** - Full per-tool reference and when-to-use guidance
- **tapps-init** - Bootstrap TappsMCP scaffolding in a project
- **tapps-upgrade** - Reinstall global CLIs from latest source, restart MCP, run `tapps-mcp upgrade` + doctor + checklist
- **tapps-engagement** - Switch enforcement intensity (high/medium/low)
- **tapps-apply-files** - Apply content-return file operations (Docker fallback)

> **Removed in v3.12.0:** `tapps-score`, `tapps-gate`, `tapps-validate`, and `tapps-report` wrapper skills were deleted. Prefer direct MCP tool calls or `/tapps-finish-task` for the end-of-task bundle.

### Agent Teams (opt-in, Claude Code only)

When `tapps_init` is called with `agent_teams=True`, additional hooks enable a quality watchdog teammate pattern:
- **TeammateIdle** - Keeps the quality watchdog active while issues remain
- **TaskCompleted** - Reminds about quality gate validation on task completion

Set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` to enable Agent Teams.

### VS Code / Copilot Instructions (auto-generated)

`.github/copilot-instructions.md` - Provides GitHub Copilot in VS Code with
TappsMCP tool guidance, recommended workflow, and scoring category reference.

### Cursor BugBot Rules (auto-generated, Cursor only)

`.cursor/BUGBOT.md` - Quality standards for Cursor BugBot automated PR review:
security requirements, style rules, testing requirements, and scoring thresholds.

### CI Integration (auto-generated)

`.github/workflows/tapps-quality.yml` - GitHub Actions workflow that validates
changed Python files on every pull request using TappsMCP quality gates.

### MCP Elicitation

When the MCP client supports elicitation (e.g. Cursor), TappsMCP can prompt
the user interactively:
- `tapps_quality_gate` prompts for preset selection when none is provided
- `tapps_init` asks for confirmation before writing configuration files

On unsupported clients, tools fall back to default behavior silently.

---

## Troubleshooting: MCP tool permissions

If TappsMCP tools are being rejected or prompting for approval on every call:

**Claude Code:** Ensure `.claude/settings.json` contains **both** permission entries:
```json
{
  "permissions": {
    "allow": [
      "mcp__tapps-mcp",
      "mcp__tapps-mcp__*"
    ]
  }
}
```
The bare `mcp__tapps-mcp` entry is needed as a reliable fallback - the wildcard `mcp__tapps-mcp__*` syntax has known issues in some Claude Code versions (see issues #3107, #13077, #27139). Run `tapps-mcp upgrade --host claude-code` to fix automatically.

**Cursor / VS Code:** These hosts manage MCP tool permissions differently. No `.claude/settings.json` needed.

**If tools are still rejected after fixing permissions:**
1. Restart your MCP host (Claude Code / Cursor / VS Code)
2. Verify the TappsMCP server is running: `tapps-mcp doctor`
3. Check that your permission mode is not `dontAsk` (which auto-denies unlisted tools)
4. As a last resort, use `tapps_quick_check` on individual files instead of `tapps_validate_changed`

---

## Essential tools (always-on workflow)

| Tool | When to use |
|------|--------------|
| **tapps_session_start** | **FIRST call in every session** - server info only |
| **tapps_quick_check** | **After editing any Python file** - quick score + gate + security |
| **tapps_validate_changed** | **Before declaring multi-file work complete** - score + gate on changed files. **Always pass explicit `file_paths`** (comma-separated). Default is quick mode; only use `quick=false` as a last resort. |
| **tapps_checklist** | **Before declaring work complete** - reports missing required steps. Response includes an inline `usage_gaps` payload (same data as `tapps_usage`) - read it before declaring done. |
| **tapps_usage** | When you want to see what you missed this session - per-session `gaps` + concrete `recommendations`. Inlined as `usage_gaps` on every `tapps_checklist` response. |
| **tapps_quality_gate** | Before declaring work complete - ensures file passes preset |

**For full tool reference** (43 tools with per-tool guidance), invoke the **tapps-tool-reference** skill when the user asks "what tools does TappsMCP have?", "when do I use tapps_score_file?", etc.

---

## Memory systems

Your project may have two complementary memory systems:

- **Claude Code auto memory** (`~/.claude/projects/<project>/memory/MEMORY.md`): Build commands, IDE preferences, personal workflow notes. Auto-managed.
- **TappsMCP shared memory** — **`uv run tapps-mcp memory`** CLI via BrainBridge (default; do not add direct `tapps-brain` to `.mcp.json`). When **`nlt-memory`** is enabled, `tapps_memory` MCP on that server is a slim facade (TAP-3895). Architecture decisions, quality patterns, cross-agent knowledge. See [docs/MEMORY_REFERENCE.md](docs/MEMORY_REFERENCE.md) and `/tapps-memory` skill.

RECOMMENDED: Use `uv run tapps-mcp memory save|get|search` for architecture decisions and quality patterns. Pin always-on scope keys under `memory_hooks.auto_recall.recall_keys` in `.tapps-mcp.yaml`.

**Access:** Prefer `uv run tapps-mcp memory <subcommand>` (CLI). With `nlt-memory` enabled, `tapps_memory(action=...)` on that server exposes the same actions (TAP-3895). Not on default `nlt-build` alone (TAP-1994).

### Memory actions (42 total)

**Core:** `save`, `save_bulk`, `get`, `list`, `delete` — CRUD with tier/scope/tag classification (`save` + architectural tier may **supersede** prior versions when `memory.auto_supersede_architectural` is true). In HTTP-bridge mode `save_bulk` now batches every entry into a single `memory_save_many` round trip (TAP-1631).

**Search:** `search` — ranked BM25 retrieval with composite scoring (relevance + confidence + recency + frequency). Auto-emits `feedback_gap` on empty / low-similarity results to feed the brain's flywheel (toggle via `memory.feedback_auto_emit`; threshold via `memory.feedback_min_similarity`).

**Intelligence:** `reinforce`, `gc`, `contradictions`, `reseed`

**Knowledge graph (TAP-1630):** `related` (find entries connected to a key), `relations` (relations attached to a key OR matching an SPO triple via `subject` / `predicate` / `object_entity`), `neighbors` (k-hop neighborhood of one or more entity ids passed via `entry_ids`), `explain_connection` (path between `subject` and `object_entity`)

**Batch ops (TAP-1631):** `recall_many` (queries via `entries` JSON array of strings), `reinforce_many` (entries via `entries` JSON array of `{key, confidence_boost?}` objects). Single round-trip wrappers around the brain's `memory_*_many` tools.

**Feedback flywheel (TAP-1632):** `rate` — score an entry via `feedback_rate` (`key` + `rating` + optional `session_id` / `details_json`). The auto-emitted `feedback_gap` on `search` empties is governed here.

**Native session memory (TAP-1633):** `index_session` (store session chunks via `memory_index_session`), `search_sessions` (search indexed sessions via `memory_search_sessions`), `session_end` (record a session-end summary via `tapps_brain_session_end`; summary in `value`, tags in `tags`, daily-note flag in `dry_run`). Replaces the legacy local session-index merge.

**Consolidation:** `consolidate`, `unconsolidate`

**Import/export:** `import`, `export`

**Federation:** `federate_register`, `federate_publish`, `federate_subscribe`, `federate_sync`, `federate_search`, `federate_status`

**Maintenance:** `validate`, `maintain`

**Security:** `safety_check`, `verify_integrity`

**Profiles:** `profile_info`, `profile_list`, `profile_switch`

**Diagnostics:** `health` — surfaces a `brain_profile` block with the negotiated capability profile + gated bridge tools (TAP-1629).

**Hive / Agent Teams:** `hive_status`, `hive_search`, `hive_propagate`, `agent_register` (opt-in; see `hive_status` when `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is set)

**Default pipeline behavior (POC-oriented):** Shipped config turns on auto-save quality signals, recurring quick_check memory, architectural supersede, impact enrichment, and `memory_hooks` auto-recall/capture — set `false` in `.tapps-mcp.yaml` if you want a quieter setup. See `docs/MEMORY_REFERENCE.md`.

### Brain health diagnostics (`brain_bridge_health`)

Every `tapps_session_start` response includes a `data.brain_bridge_health` block describing the live state of the tapps-brain connection:

| Field | Meaning |
|-------|---------|
| **enabled** | True when the bridge is configured (memory pipeline turned on). |
| **ok** | Roll-up: True only when the bridge can both reach the brain and pass its native self-check. |
| **dsn_reachable** | HTTP-bridge mode: brain endpoint responded to a probe. In-process mode: pool was constructible. |
| **pool_config_valid** | Connection pool sizing / DSN parsed cleanly. |
| **native_health_ok** | Result of the brain's own `health` tool — covers schema, embeddings, and indexes. |
| **errors / warnings** | Non-empty when one of the checks above failed; agents should surface these instead of swallowing them. |
| **details** | Mode (`http` / `in_process`), `http_url`, negotiated `brain_version`, and the brain's own `brain_status`. |

`tapps doctor` runs the same probe in CLI form and adds a brain-health row to its summary, so agents and humans see the same signal. When `errors` mentions `brain_auth_failed`, set `TAPPS_BRAIN_AUTH_TOKEN` (or set `memory.tolerate_brain_auth_failure: true` for offline workflows) — see [docs/MEMORY_REFERENCE.md](docs/MEMORY_REFERENCE.md#brain-health-diagnostics) for the full troubleshooting matrix.

### Memory tiers and scopes

**Tiers:** `architectural` (180-day half-life, stable decisions), `pattern` (60-day, conventions), `procedural` (30-day, workflows), `context` (14-day, short-lived)

**Scopes:** `project` (default, all sessions), `branch` (git branch), `session` (current session only). Cross-project handoff goes through federation actions (`federate_publish` / `federate_subscribe`), not a `scope=` value.

**Memory profiles:** Built-in profiles from tapps-brain (e.g. `repo-brain` default). Use `profile_info`, `profile_list`, `profile_switch` actions.

**Configuration:** Override `memory.profile`, `memory.capture_prompt`, `memory.write_rules`, and `memory_hooks` in `.tapps-mcp.yaml`. Max 1500 entries per project. Auto-GC at 80% capacity.

**Cross-session handoff:** prefer `/tapps-handoff-session` at chat end and `/tapps-continue-session` at chat start (`.tapps-mcp/session-handoff.md` is canonical). For ad-hoc payloads use `tapps-mcp memory save/get`. Cross-agent: `hive_propagate`; cross-project: federation actions above.

---

## Tapps Rules

Seven rules every agent in this project should follow.

1. **Fix root causes, not symptoms.** No workarounds, no `--no-verify`, no try/except-and-swallow. If you are tempted to bypass a failure, stop and diagnose it.
2. **When confidence drops below 100%, query tapps-mcp before writing code.** `tapps_lookup_docs` for library APIs; `uv run tapps-mcp memory search --query "..."` for prior decisions. Guessing from memory is the most common source of hallucinated APIs.
3. **`tapps_lookup_docs` is a Context7-backed cache — use it freely.** Lookups are local-cache-first; repeat calls are near-zero cost. There is no budget to conserve.
4. **Be context-window aware — delegate noisy work to subagents.** If a task would dump more than three file reads or large tool output you won't reference again, spawn `Explore` or `general-purpose`. Subagents return summaries; the main thread stays clean.
5. **Write clean, efficient code.** Clear names, no dead branches, no speculative abstractions, no commented-out code. Every line should justify its presence.
6. **Don't over-engineer.** The simplest solution that satisfies the requirement is the correct one. No knobs nobody asked for. Three similar lines beat a premature abstraction.
7. **Route Linear through skills, not raw plugin calls.** Use the `linear-issue` skill for any write (epic, story, update) — it runs the docs-mcp template + validator before push. Use the `linear-read` skill for multi-issue reads (cache-first). Single-issue lookups: `get_issue(id=...)` directly. Release announcements go through the `linear-release-update` skill.

---

## Using tapps_lookup_docs for domain guidance

`tapps_lookup_docs` is the primary tool for both library documentation and domain-specific guidance. Pass a `library` name for API docs, or use `topic` to query for patterns and best practices.

| Context | Example call |
|---------|--------------|
| Using an external library | `tapps_lookup_docs(library="fastapi", topic="dependency injection")` |
| Testing patterns | `tapps_lookup_docs(library="pytest", topic="fixtures and parametrize")` |
| Security patterns | `tapps_lookup_docs(library="python-security", topic="input validation")` |
| API design | `tapps_lookup_docs(library="fastapi", topic="routing best practices")` |
| Database patterns | `tapps_lookup_docs(library="sqlalchemy", topic="session management")` |

---

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

## AgentForge integration

This project consumes AgentForge (local Docker stack, http://localhost:8010)
via the `agentforge` MCP server in `.mcp.json` / `.cursor/mcp.json`.

**Integration pattern:** Pattern A — HTTP publish (project slug: `homeiq`)

**Prefer MCP runtime tools over hand-writing prompts:**

- `health()` — troubleshoot brain sidecar + service version
- `list_workflows()` — discover workflows and inputs
- `invoke_task(prompt, config_hint=None)` — run an AgentForge agent
- `run_workflow(name, inputs, dry_run=True)` — validate before LLM cost
- `get_workflow_run(run_id)` — per-node status + total cost

**Publish (Pattern A):** agents and workflows live under
`agentforge/projects/homeiq/{agents,workflows}/`. Use the `af-publish`
skill or `af_publish.py --slug homeiq --layout scout`. Publish agents
**before** workflows — workflows resolve `agent:` references at load time
and return 422 if reversed.

**Port 8010 is pinned** (`agentforge-api`). Do not use `:8001`
(`agentforge-main`) — the same slug can show different published versions
on each instance.

**Platform purity:** HomeIQ domain models, Home Assistant clients, database
access, and credentials stay in this repo — never in AgentForge platform code.

Decision record: [docs/AF-INTEGRATION.md](docs/AF-INTEGRATION.md).
Canonical guide: [CONNECTING_PROJECTS.md](https://github.com/wtthornton/AgentForge/blob/main/docs/CONNECTING_PROJECTS.md).

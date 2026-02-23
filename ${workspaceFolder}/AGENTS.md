<!-- tapps-agents-version: 0.3.0 -->
# TappsMCP - instructions for AI assistants

When the **TappsMCP** MCP server is configured in your host (Claude Code, Cursor, VS Code Copilot, Claude Desktop, etc.), you have access to tools that provide **deterministic code quality checks, doc lookup, and domain expert advice**. TappsMCP is a quality toolset designed to help your project and LLM produce the best possible code - use it to avoid hallucinated APIs, missed quality steps, and inconsistent output.

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

## tapps_session_start vs tapps_init

| Aspect | tapps_session_start | tapps_init |
|--------|---------------------|------------|
| **When** | **First call in every session** | **Pipeline bootstrap** (once per project, or when upgrading) |
| **Duration** | Fast (~1-3s) | Full run: 10-35+ seconds |
| **Purpose** | Load server info + project profile into context | Create files (AGENTS.md, TECH_STACK.md, platform rules), optionally warm cache/RAG |
| **Side effects** | None (read-only) | Writes files, warms caches |
| **Typical flow** | Call at session start, then work | Call once to bootstrap, or `dry_run: true` to preview |

**Session start** -> `tapps_session_start`. Use this as the first call in every session so subsequent tools have project context.

**Pipeline/bootstrap** -> `tapps_init`. Use when you need to set up TappsMCP in a project (AGENTS.md, TECH_STACK.md, platform rules) or upgrade existing files.

**Both in one session?** Yes. If the project is not yet bootstrapped: call `tapps_session_start` first (fast), then `tapps_init` (creates files). If the project is already bootstrapped: call only `tapps_session_start` at session start.

**Lighter tapps_init options** (for timeout-prone MCP clients): Use `dry_run: true` to preview (~2-5s); use `verify_only: true` for a quick server/checker check (~1-3s); or set `warm_cache_from_tech_stack: false` and `warm_expert_rag_from_tech_stack: false` for a faster init without cache warming.

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

---

## Recommended workflow

1. **Session start:** Call `tapps_session_start` (combines server info + project profile). Optionally call `tapps_list_experts` if you may need experts.
2. **Record key decisions:** Use `tapps_session_notes(action="save", ...)` to persist constraints and decisions so they survive long sessions.
3. **Before using a library:** Call `tapps_lookup_docs(library=...)` and use the returned content when implementing.
4. **Before modifying a file's API:** Call `tapps_impact_analysis(file_path=...)` to see what depends on it.
5. **During edits:** Call `tapps_quick_check(file_path=...)` or `tapps_score_file(file_path=..., quick=True)` after each change.
6. **Before declaring work complete:**
   - Call `tapps_validate_changed()` to score + gate + security scan all changed files.
   - Call `tapps_checklist(task_type=...)` and, if `complete` is false, call the missing required tools (use `missing_required_hints` for reasons).
   - Optionally call `tapps_report(format="markdown")` to generate a quality summary.
7. **When in doubt:** Use `tapps_consult_expert` for domain-specific questions; use `tapps_validate_config` for Docker/infra files. **For library-specific domain questions**, pair `tapps_consult_expert` with `tapps_lookup_docs` to get expert guidance backed by current documentation (the expert response will suggest the right library/topic to look up).

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

## Platform hooks and automation

When `tapps_init` generates platform-specific files, it also creates **hooks**, **subagents**, and **skills** that automate parts of the workflow:

### Hooks (auto-generated)

**Claude Code** (`.claude/hooks/`): 7 hook scripts that enforce quality automatically:
- **SessionStart** - Injects TappsMCP awareness on session start and after compaction
- **PostToolUse (Edit/Write)** - Reminds you to run `tapps_quick_check` after Python edits
- **Stop** - Reminds you to run `tapps_validate_changed` before session end (non-blocking)
- **TaskCompleted** - Reminds you to validate before marking task complete (non-blocking)
- **PreCompact** - Backs up scoring context before context window compaction
- **SubagentStart** - Injects TappsMCP awareness into spawned subagents

**Cursor** (`.cursor/hooks/`): 3 hook scripts:
- **beforeMCPExecution** - Logs MCP tool invocations for observability
- **afterFileEdit** - Fire-and-forget reminder to run quality checks
- **stop** - Prompts validation via followup_message before session ends

### Subagents (auto-generated)

Three agent definitions per platform in `.claude/agents/` or `.cursor/agents/`:
- **tapps-reviewer** (sonnet) - Reviews code quality and runs security scans after edits
- **tapps-researcher** (haiku) - Looks up documentation and consults domain experts
- **tapps-validator** (sonnet) - Runs pre-completion validation on all changed files

### Skills (auto-generated)

Three SKILL.md files per platform in `.claude/skills/` or `.cursor/skills/`:
- **tapps-score** - Score a Python file across 7 quality categories
- **tapps-gate** - Run a quality gate check and report pass/fail
- **tapps-validate** - Validate all changed files before declaring work complete

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

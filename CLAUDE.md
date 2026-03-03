# TAPPS Quality Pipeline - MANDATORY

**HomeIQ.** Full AI assistant guide: [.cursor/CLAUDE.md](.cursor/CLAUDE.md). Doc index: [docs/README.md](docs/README.md).

This project uses the TAPPS MCP server for automated code quality enforcement.
Every tool response includes `next_steps` - follow them.

## CRITICAL: Tool Call Obligations

These are BLOCKING REQUIREMENTS, not suggestions. Skipping any step risks shipping broken, insecure, or hallucinated code.

### Session Start (REQUIRED)

You MUST call `tapps_session_start()` as the FIRST action in every session.
This discovers server capabilities and detects the project's tech stack.
Skipping this means all subsequent tools lack project context.

### Before Using Any Library API (BLOCKING)

You MUST call `tapps_lookup_docs(library, topic)` BEFORE writing code that uses an external library.
This prevents hallucinated APIs. NEVER guess library APIs from memory - always verify first.
Skipping this is the #1 cause of incorrect code generation.

### After Editing Any Python File (REQUIRED)

You MUST call `tapps_quick_check(file_path)` at minimum after editing any Python file.
This runs scoring + quality gate + security scan in a single call.
Alternatively, call `tapps_score_file`, `tapps_quality_gate`, and `tapps_security_scan` individually.
Skipping this means quality issues and vulnerabilities go undetected.

### Domain Decisions (REQUIRED)

You MUST call `tapps_consult_expert(question)` when making domain-specific decisions
(security, testing strategy, API design, database, etc.).
This returns RAG-backed expert guidance with confidence scores.

### Refactoring or Deleting Files (REQUIRED)

You MUST call `tapps_impact_analysis(file_path)` before refactoring or deleting any file.
This maps the blast radius via import graph analysis.
Skipping this risks breaking downstream dependents.

### Infrastructure Config Changes (REQUIRED)

You MUST call `tapps_validate_config(file_path)` when changing Dockerfile, docker-compose, or infra config.
This validates against security and operational best practices.

## 5-Stage Pipeline

Execute these stages IN ORDER for every code task:

1. **Discover** - `tapps_session_start()` (combines server info + project profile)
2. **Research** - `tapps_lookup_docs()` for libraries, `tapps_consult_expert()` for decisions
3. **Develop** - `tapps_score_file(file_path, quick=True)` during edit-lint-fix loops
4. **Validate** - `tapps_quick_check()` per file OR `tapps_validate_changed()` for batch
5. **Verify** - `tapps_checklist(task_type)` as the absolute final step

## Consequences of Skipping

| Skipped Tool | Consequence |
|---|---|
| `tapps_session_start` | No project context - tools give generic advice |
| `tapps_lookup_docs` | Hallucinated APIs - code will fail at runtime |
| `tapps_quick_check` / scoring | Quality issues shipped silently |
| `tapps_quality_gate` | No quality bar enforced - regressions go unnoticed |
| `tapps_security_scan` | Vulnerabilities shipped to production |
| `tapps_checklist` | No verification that process was followed |
| `tapps_consult_expert` | Decisions made without domain expertise |
| `tapps_impact_analysis` | Refactoring breaks unknown dependents |
| `tapps_dead_code` | Unused code accumulates, bloating the codebase |
| `tapps_dependency_scan` | Vulnerable dependencies shipped to production |
| `tapps_dependency_graph` | Circular imports cause runtime crashes |

## Response Guidance

Every tool response includes:
- `next_steps`: Up to 3 imperative actions to take next - FOLLOW THEM
- `pipeline_progress`: Which stages are complete and what comes next

Record progress in `docs/TAPPS_HANDOFF.md` and `docs/TAPPS_RUNLOG.md`.
For task-specific recommended tool call order, use the `tapps_workflow` MCP prompt (e.g. `tapps_workflow(task_type="feature")`).

## Agent Teams (Optional)

If using Claude Code Agent Teams (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`),
designate one teammate as a **quality watchdog**:

1. The quality watchdog runs `tapps_quick_check` on files changed by other teammates.
2. It messages other teammates via the shared mailbox when quality issues are found.
3. The `TaskCompleted` hook prevents any task from being marked complete until
   `tapps_validate_changed` passes.
4. The `TeammateIdle` hook keeps the watchdog active while quality issues remain unresolved.

To enable Agent Teams hooks, re-run `tapps_init` with `agent_teams=True`.

## CI Integration

TappsMCP can run in CI without an interactive session:

### Direct Python invocation (recommended for CI)

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
  --allowedTools "mcp__tapps-mcp__tapps_validate_changed" \
  "Run tapps_validate_changed with preset=staging"
```

### VS Code / headless — enableAllProjectMcpServers

In headless or non-interactive VS Code contexts, set:
`claude.enableAllProjectMcpServers: true` in workspace settings.


# Install TappsMCP
pip install tapps-mcp

# Validate changed files
TAPPS_MCP_PROJECT_ROOT=/workspace \
  tapps-mcp validate-changed --preset staging
```

### Claude Code headless mode

```bash
claude --headless \
  --allowedTools "mcp__tapps-mcp__tapps_validate_changed" \
  "Run tapps_validate_changed with preset=staging"
```

### VS Code / headless — enableAllProjectMcpServers

In headless or non-interactive VS Code contexts, set:
`claude.enableAllProjectMcpServers: true` in workspace settings.

# TappsMCP Quality Tools

This project uses TappsMCP for code quality analysis. When TappsMCP is
available as an MCP server (configured in `.vscode/mcp.json`), use the
following tools to maintain code quality throughout development.

## Key Tools

- `tapps_session_start` — Initialize a TappsMCP session at the start of
  each work session. Call this first.
- `tapps_quick_check` — Run a quick quality check on a single file after
  editing. Returns score and top issues.
- `tapps_quality_gate` — Run a pass/fail quality gate against a configurable
  preset (development, staging, or production).
- `tapps_validate_changed` — Validate all changed files against the quality
  gate. Call this before declaring work complete.
- `tapps_consult_expert` — Consult a domain expert (security, performance,
  architecture, testing, and more) for guidance.
- `tapps_score_file` — Get a detailed 7-category quality score for any file.

## Workflow

1. Start a session: call `tapps_session_start`
2. After editing Python files: call `tapps_quick_check` on changed files
3. Before creating a PR or declaring work complete: call
   `tapps_validate_changed`
4. For domain-specific guidance: call `tapps_consult_expert` with the
   relevant domain

## Quality Scoring Categories

TappsMCP scores code across 7 categories (0-100 each):
correctness, security, maintainability, performance, documentation,
testing, and style.

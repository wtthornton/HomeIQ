# Auto-Bugfix Subagents Integration

**Epic 48** | Added 2026-03-10

The auto-bugfix pipeline can use Claude Code **subagents** for the scan phase to reduce cost and latency. This document describes the architecture and how to control it.

## Overview

- **bug-scanner**: A project subagent (`.claude/agents/bug-scanner.md`) that finds bugs using Haiku (fast, low-cost). It has Read, Grep, Glob, and TappsMCP tools. No Edit/Write.
- **Delegation**: The main session receives the scan prompt. When `bug-scanner` is available, it delegates discovery to the subagent, then synthesizes the subagent’s report into the final `<<<BUGS>>>` JSON block.
- **Fallback**: If subagents are disabled (`-UseSubagents:$false`), the main session performs the scan itself (previous behavior).

## Controlling Subagents

### Enable (default)

Subagents are enabled by default. The project subagent `bug-scanner` is loaded from `.claude/agents/`. Use the runner (preferred) or script with config:

```powershell
.\auto-fix-pipeline\runner\run.ps1 -Bugs 5
.\scripts\auto-bugfix.ps1 -Bugs 5
```

Both use config by default (`homeiq-default.yaml` or `$env:AUTO_FIX_CONFIG`).

### Disable

To run the scan only in the main session (no delegation):

```powershell
.\scripts\auto-bugfix.ps1 -Bugs 5 -UseSubagents:$false
```

This passes `--disallowedTools "Agent(bug-scanner)"` to the scan invocation so the main session cannot delegate.

## Architecture

```
Scan prompt → Main session (Sonnet)
                ├─ UseSubagents:$true  → Can delegate to bug-scanner (Haiku)
                │                         Main synthesizes report → <<<BUGS>>>
                └─ UseSubagents:$false → Main does scan itself
```

- **Streaming**: The `claude` process streams JSON events. Subagent tool calls appear as `Agent` tool use. The final `result` event still contains the full output for BUGS extraction.
- **Dashboard**: Tool calls (including Agent) are logged and shown in the live dashboard.

## Environment and Requirements

- Claude Code CLI with subagent support (project agents in `.claude/agents/`)
- **MCP:** TappsMCP is provided by `tapps-mcp` via direct stdio. Use `.mcp.json` at project root with a `tapps-mcp` server entry so headless Claude can call TappsMCP tools. See [.cursor/MCP_SETUP_INSTRUCTIONS.md](../../.cursor/MCP_SETUP_INSTRUCTIONS.md).
- No special env vars for subagents (unlike agent teams, which need `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`)

## Future Work

- **Agent teams**: Parallel scan with multiple teammates; higher cost, experimental. Consider if subagents prove insufficient.
- **Fix-phase subagent**: Delegate fixes to a dedicated subagent; evaluate after validating scan-phase benefits.

## References

- Epic: `stories/epic-auto-bugfix-subagents-integration.md`
- Scan format: `docs/workflows/auto-bugfix-scan-format.md`
- Bug-scanner definition: `.claude/agents/bug-scanner.md`

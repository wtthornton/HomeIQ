# TAPPS MCP Server — Claude Code Compatibility Feedback

**Date:** 2026-02-11
**Reporter:** HomeIQ project (via Claude Code session)
**Context:** Large multi-file implementation (5 stories, ~15 files changed) executed entirely without TAPPS pipeline despite `.cursor/rules/tapps-pipeline.md` being present.

---

## Executive Summary

The TAPPS MCP server works in Cursor IDE but is **completely invisible** to Claude Code (Anthropic's CLI tool). A full epic implementation — template fixes, LLM prompt changes, compiler logic, database schema additions, and deployment endpoint updates — was completed without a single `tapps_*` call. The rule file existed, the MCP config existed, but the tools were never available to the agent.

---

## What Happened

### Session Details
- **Client:** Claude Code (VS Code extension mode, Claude Opus 4.6)
- **Task:** Implement 5-story epic (`epic-deploy-pipeline-root-cause-fixes.md`) across `services/ai-automation-service-new/`
- **Files modified:** ~15 Python files + 9 JSON template files
- **TAPPS calls made:** 0

### What Was Configured
1. **`.cursor/mcp.json`** — tapps-mcp server defined:
   ```json
   {
     "tapps-mcp": {
       "command": "C:\\Users\\tappt\\.local\\bin\\tapps-mcp.exe",
       "args": ["serve"]
     }
   }
   ```
2. **`.cursor/rules/tapps-pipeline.md`** — Detailed rule file with `alwaysApply: true` frontmatter, describing the full 5-stage pipeline and all tool call obligations.

### What The Agent Saw
- The `.cursor/rules/tapps-pipeline.md` file was **never loaded into the Claude Code system prompt**. Cursor rules (`.cursor/rules/*.md`) are a Cursor-specific feature — Claude Code does not read them.
- The `.cursor/mcp.json` file was **not parsed by Claude Code** for MCP server discovery. Claude Code uses its own MCP configuration at `~/.claude/` or project-level `.claude/` directories.
- The `tapps_*` tool names referenced in the rule file were **not available** in the agent's tool list. The agent had no way to call them.

### Metrics Confirm Cursor-Only Usage
The metrics log at `.tapps-mcp/metrics/tool_calls_2026-02-11.jsonl` shows 18 calls — all from Cursor sessions (session IDs `9eaba6b41d9e`, `5be8831e8652`, `4ac01c050c82`, `98ab4476a4ea`, `e914b916b7b8`). Zero calls from the Claude Code session that performed the actual implementation.

---

## Root Causes

### RC1: MCP Server Config Is Cursor-Only
`.cursor/mcp.json` is Cursor IDE's MCP configuration. Claude Code reads MCP servers from:
- `~/.claude/mcp.json` (global)
- `.claude/mcp.json` (project-level)
- `claude_desktop_config.json` (Claude Desktop)

**TAPPS has no presence in any Claude Code-recognized config location.**

### RC2: Rule File Uses Cursor-Specific Format
`.cursor/rules/tapps-pipeline.md` uses Cursor's frontmatter format:
```yaml
---
description: TAPPS quality pipeline - MANDATORY code quality enforcement
alwaysApply: true
---
```
Claude Code reads instructions from `CLAUDE.md` files (project root, `.claude/` directory, or parent directories). The TAPPS instructions were never injected into the Claude Code system prompt.

### RC3: No CLAUDE.md Integration
The project's `CLAUDE.md` (if it exists) does not reference the TAPPS pipeline. Even if the MCP server were configured for Claude Code, the agent would have no instructions telling it to use the tools.

### RC4: No Fallback or Detection Mechanism
TAPPS has no mechanism to detect that:
- Its MCP server is not running / not connected
- Its rule file was not loaded
- An AI agent is actively editing files in the project without calling TAPPS tools

A pre-commit hook, file watcher, or CLAUDE.md auto-generator could catch these gaps.

---

## Recommendations

### P0: Multi-Client MCP Configuration

Add a setup command or installer that writes MCP config to **all** recognized locations:

```bash
tapps-mcp setup --project .
```

This should create/update:
| File | Client |
|------|--------|
| `.cursor/mcp.json` | Cursor IDE |
| `.claude/mcp.json` | Claude Code (CLI + VS Code extension) |
| `claude_desktop_config.json` | Claude Desktop |

Example `.claude/mcp.json`:
```json
{
  "mcpServers": {
    "tapps-mcp": {
      "command": "tapps-mcp",
      "args": ["serve"]
    }
  }
}
```

### P0: CLAUDE.md Integration

Generate a `CLAUDE.md` snippet (or append to existing) with TAPPS instructions:

```markdown
## Quality Pipeline (TAPPS)

This project uses TAPPS for automated code quality enforcement.

- Call `tapps_session_start()` at the start of every session
- Call `tapps_quick_check(file_path)` after editing any Python file
- Call `tapps_validate_changed()` before declaring work complete
- Call `tapps_checklist(task_type)` as the final step
- Call `tapps_lookup_docs(library, topic)` before using external library APIs
- Call `tapps_consult_expert(question)` for domain-specific decisions
- Call `tapps_impact_analysis(file_path)` before refactoring/deleting files
```

This ensures the instructions reach **any** AI agent that reads `CLAUDE.md`, regardless of client.

### P1: Unified Rule File Generator

Instead of maintaining separate `.cursor/rules/tapps-pipeline.md` and `CLAUDE.md` snippets, provide:

```bash
tapps-mcp rules --format cursor   # writes .cursor/rules/tapps-pipeline.md
tapps-mcp rules --format claude   # appends to CLAUDE.md
tapps-mcp rules --format all      # both
```

### P1: Connection Health Check

Add a lightweight mechanism to verify the TAPPS server is reachable from the current AI client:

```bash
tapps-mcp doctor
```

Output example:
```
TAPPS MCP Server v1.x
  Cursor config:      .cursor/mcp.json ✓
  Claude Code config:  .claude/mcp.json ✗ MISSING
  CLAUDE.md snippet:   ✗ NOT FOUND
  Server reachable:    ✓ (localhost:xxxx)
  Last tool call:      2 min ago (tapps_quick_check)
```

### P2: Pre-Commit Hook Guard

Optional git pre-commit hook that warns if Python files were modified without any `tapps_quick_check` calls in the session metrics:

```bash
tapps-mcp install-hooks
```

This provides a safety net regardless of which AI client (or human) is committing.

### P2: Session Metrics Cross-Client Tracking

The metrics log should include a `client` field to help identify coverage gaps:

```json
{
  "call_id": "abc123",
  "tool_name": "tapps_quick_check",
  "client": "cursor",        // NEW: "cursor" | "claude-code" | "claude-desktop" | "unknown"
  "session_id": "..."
}
```

---

## Impact of Missing TAPPS Coverage

During this session, the following TAPPS checks were skipped:

| Stage | Tool | What Was Missed |
|-------|------|----------------|
| Discover | `tapps_session_start` | No project context established |
| Research | `tapps_lookup_docs` | SQLAlchemy async patterns, PyYAML, Pydantic — used from model memory |
| Research | `tapps_consult_expert` | Database schema design, API error code choice (422 vs 400) |
| Develop | `tapps_score_file` | No scoring during edit loops |
| Validate | `tapps_quick_check` | No post-edit quality/security checks on ~15 Python files |
| Validate | `tapps_validate_changed` | No batch validation before completion |
| Verify | `tapps_checklist` | No final verification |
| Safety | `tapps_impact_analysis` | Template deletion, model changes — no blast radius check |

The code appears to work (28 tests pass, templates load correctly, compilation logic verified), but the quality/security assurance that TAPPS provides was entirely absent.

---

## Reproduction Steps

1. Open the HomeIQ project in Claude Code (not Cursor)
2. Ask Claude Code to implement a multi-file change
3. Observe that no `tapps_*` tools appear in the agent's available tools
4. Check `.tapps-mcp/metrics/` — no calls logged from the Claude Code session

---

## Summary

TAPPS is well-designed for Cursor but has zero presence in Claude Code. Given that Claude Code is increasingly used for complex multi-file implementations (exactly the scenario where TAPPS is most valuable), adding multi-client support would significantly expand TAPPS's coverage. The fixes are straightforward: write config to `.claude/mcp.json`, append instructions to `CLAUDE.md`, and optionally add a `doctor` command for diagnostics.

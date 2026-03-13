# MCP Configuration Setup

**Created:** January 2025
**Updated:** March 2026
**Purpose:** Instructions for setting up MCP servers used by HomeIQ — TappsMCP and DocsMCP (via uv stdio) and optional Context7.

---

## 1. TappsMCP & DocsMCP via uv stdio

**TappsMCP** provides code quality, security scanning, expert consultation, and doc lookup. **DocsMCP** provides documentation generation and validation. Both run locally from the TappMCP workspace at `C:\cursor\TappMCP`.

### Requirements

- **uv** installed (`pip install uv` or via installer).
- **TappMCP workspace** synced at `C:\cursor\TappMCP` (`uv sync --all-packages`).

### Configuration

**Cursor IDE:** `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "tapps-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": ["--directory", "C:\\cursor\\TappMCP", "run", "--no-sync", "tapps-mcp", "serve"],
      "env": { "TAPPS_MCP_PROJECT_ROOT": "${workspaceFolder}" }
    },
    "docs-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": ["--directory", "C:\\cursor\\TappMCP", "run", "--no-sync", "docsmcp", "serve"],
      "env": { "DOCS_MCP_PROJECT_ROOT": "${workspaceFolder}" }
    }
  }
}
```

**Claude Code:** `.mcp.json` at project root uses the same pattern (with `"."` instead of `${workspaceFolder}` for `TAPPS_MCP_PROJECT_ROOT`).

**VS Code:** `.vscode/mcp.json` uses the same uv stdio pattern.

### Tool names

With the uv stdio setup, TappsMCP tools appear as:

- `mcp__tapps-mcp__tapps_session_start`
- `mcp__tapps-mcp__tapps_quick_check`
- `mcp__tapps-mcp__tapps_validate_changed`
- etc.

DocsMCP tools appear as:

- `mcp__docs-mcp__docs_session_start`
- `mcp__docs-mcp__docs_generate_readme`
- etc.

### Verification

In Cursor or Claude Code, start a session and call `tapps_session_start`. The tool should respond with server info and project profile.

---

## 2. Context7 MCP (optional)

Context7 provides up-to-date library documentation lookups. TappsMCP can use Context7 for `tapps_lookup_docs` when configured; Context7 can also be run as a separate MCP server if desired.

### Set the API Key in Your Environment

**The key is never stored in the project.** Cursor resolves `${env:CONTEXT7_API_KEY}` from your OS environment.

**Windows (PowerShell - current user, persistent):**

```powershell
[System.Environment]::SetEnvironmentVariable("CONTEXT7_API_KEY", "ctx7sk-xxxx-your-key-here", "User")
```

Or: **Settings > System > About > Advanced system settings > Environment Variables > User variables > New**

**macOS / Linux:** Add to `~/.zshrc`, `~/.bashrc`, or `~/.profile`:

```bash
export CONTEXT7_API_KEY="ctx7sk-xxxx-your-key-here"
```

Then restart the terminal and Cursor (or run `source ~/.zshrc` and start Cursor from that shell).

### Context7 server entry

Add to `.cursor/mcp.json` (and optionally to project root `.mcp.json` for headless):

```json
"Context7": {
  "command": "npx",
  "args": ["-y", "@upstash/context7-mcp"],
  "env": {
    "CONTEXT7_API_KEY": "${env:CONTEXT7_API_KEY}"
  }
}
```

### Verification

After setting `CONTEXT7_API_KEY` and adding the Context7 server, fully quit and reopen Cursor, then test with `tapps_lookup_docs`.

---

## Summary

| Component      | Purpose                               | Config (IDE)       | Claude Code          |
|---------------|---------------------------------------|--------------------|----------------------|
| **tapps-mcp** | Code quality, security, experts       | `.cursor/mcp.json` | `.mcp.json`          |
| **docs-mcp**  | Documentation generation & validation | `.cursor/mcp.json` | `.mcp.json`          |
| **Context7**  | Doc lookup (optional)                 | `.cursor/mcp.json` | Optional in `.mcp.json` |

- Both MCP servers run via **uv stdio** from `C:\cursor\TappMCP` (v1.6.0).
- Keep **secrets** (e.g. Context7 API key) in environment variables only; do not put them in committed config files.

---

**References:** [AGENTS.md](../AGENTS.md), [docs/TAPPS_TOOL_PRIORITY.md](../docs/TAPPS_TOOL_PRIORITY.md).

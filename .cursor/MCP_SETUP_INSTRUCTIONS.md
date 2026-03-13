# MCP Configuration Setup

**Created:** January 2025  
**Updated:** March 2026  
**Purpose:** Instructions for setting up MCP servers used by HomeIQ — TappsMCP (via Docker MCP Toolkit) and optional Context7.

---

## 1. TappsMCP via MCP_DOCKER (Docker MCP Toolkit)

**TappsMCP** provides code quality, security scanning, expert consultation, and doc lookup. In this project it runs **inside MCP_DOCKER**, not as a standalone server.

### Requirements

- **Docker** installed and running.
- **Docker MCP Toolkit** (e.g. `docker mcp gateway run` available).

### Configuration

**Cursor / IDE:** Use `.cursor/mcp.json` with the `MCP_DOCKER` server:

```json
{
  "mcpServers": {
    "MCP_DOCKER": {
      "command": "docker",
      "args": ["mcp", "gateway", "run"],
      "env": {
        "LOCALAPPDATA": "C:\\Users\\<you>\\AppData\\Local",
        "ProgramData": "C:\\ProgramData",
        "ProgramFiles": "C:\\Program Files"
      }
    }
  }
}
```

On macOS/Linux, adjust or omit `env` if not needed for your Docker setup.

**Headless / auto-bugfix:** The pipeline uses `.mcp.json` at **project root**. It must include the same `MCP_DOCKER` entry so Claude CLI can call TappsMCP tools. Copy the `MCP_DOCKER` block from `.cursor/mcp.json` into the project root `.mcp.json` (or symlink), or ensure both files define `MCP_DOCKER`.

### Tool names

With MCP_DOCKER, TappsMCP tools appear as:

- `mcp__MCP_DOCKER__tapps_session_start`
- `mcp__MCP_DOCKER__tapps_quick_check`
- `mcp__MCP_DOCKER__tapps_validate_changed`
- etc.

The auto-bugfix script (`scripts/auto-bugfix.ps1`) uses the `MCP_DOCKER` prefix by default. If you use a standalone TappsMCP server instead, run with `-TappsMcpServer "tapps-mcp"`.

### TappsMCP workspace_path configuration

TappsMCP needs a `workspace_path` to know which project to analyze. The Docker MCP Toolkit stores this in its internal extension storage.

**Check current config:**
```
mcp-config-set(server="tapps-mcp", config={"workspace_path": "C:\\cursor\\HomeIQ"})
```

The response shows `Old config` — if it says `${workspaceFolder}`, the variable was not expanded and needs fixing. The command above both checks and fixes it in one step.

**Known issue:** `${workspaceFolder}` does not expand in Claude Code or headless contexts. Use an absolute path instead. The fix persists across Docker Desktop restarts (stored in Docker extension storage, not on the host filesystem).

**For different projects:** Re-run `mcp-config-set` with the new project's absolute path.

### Activating tapps tools in a session

TappsMCP tools may not appear in the deferred tool list automatically. To activate:

1. `mcp-add(name="tapps-mcp", activate=true)` — registers all 30 tools
2. Use `mcp-exec(name="tapps_server_info")` or `mcp-exec(name="tapps_session_start")` to call tools

### Verification

In Cursor, start a session and call `tapps_session_start` (or use `mcp-exec` as described above). If the Docker MCP gateway is running and configured, the tool should respond with server info and project profile.

---

## 2. Context7 MCP (optional)

Context7 provides up-to-date library documentation lookups. TappsMCP can use Context7 for `tapps_lookup_docs` when configured; Context7 can also be run as a separate MCP server if desired.

### Set the API Key in Your Environment

**The key is never stored in the project.** Cursor resolves `${env:CONTEXT7_API_KEY}` from your OS environment.

**Windows (PowerShell – current user, persistent):**

```powershell
[System.Environment]::SetEnvironmentVariable("CONTEXT7_API_KEY", "ctx7sk-xxxx-your-key-here", "User")
```

Or: **Settings → System → About → Advanced system settings → Environment Variables → User variables → New**

**Windows (temporary, this session only):**

```powershell
$env:CONTEXT7_API_KEY = "ctx7sk-xxxx-your-key-here"
```

Then start Cursor from this same PowerShell window.

**macOS / Linux:** Add to `~/.zshrc`, `~/.bashrc`, or `~/.profile`:

```bash
export CONTEXT7_API_KEY="ctx7sk-xxxx-your-key-here"
```

Then restart the terminal and Cursor (or run `source ~/.zshrc` and start Cursor from that shell).

### Context7 server entry

Add to `.cursor/mcp.json` (and optionally to project root `.mcp.json` for headless) **in addition to** `MCP_DOCKER`:

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

After setting `CONTEXT7_API_KEY` and adding the Context7 server, fully quit and reopen Cursor, then test:

```bash
@bmad-master
*context7-kb-test
```

Or:

```bash
@bmad-master
*context7-docs fastapi dependency-injection
```

---

## Summary

| Component    | Purpose                          | Config (IDE)       | Headless / auto-bugfix   |
|-------------|-----------------------------------|--------------------|---------------------------|
| **MCP_DOCKER** | TappsMCP (quality, security, experts) | `.cursor/mcp.json` | Project root `.mcp.json`  |
| **Context7**  | Doc lookup (optional)            | `.cursor/mcp.json` | Optional in `.mcp.json`  |

- **TappsMCP** is provided by the Docker MCP Toolkit (`MCP_DOCKER`). Do not add a separate `tapps-mcp` server unless you are not using Docker.
- Keep **secrets** (e.g. Context7 API key) in environment variables only; do not put them in committed config files.

---

**References:** [AGENTS.md](../AGENTS.md), [docs/TAPPS_TOOL_PRIORITY.md](../docs/TAPPS_TOOL_PRIORITY.md), [scripts/auto-bugfix.ps1](../scripts/auto-bugfix.ps1).

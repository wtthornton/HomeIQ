# Context7 MCP Configuration Setup

**Created:** January 2025  
**Purpose:** Instructions for setting up Context7 MCP server configuration

---

## 1. Set the API Key in Your Environment

**The key is never stored in the project.** Cursor resolves `${env:CONTEXT7_API_KEY}` from your OS environment.

### Windows (PowerShell – current user, persistent)

```powershell
[System.Environment]::SetEnvironmentVariable("CONTEXT7_API_KEY", "ctx7sk-xxxx-your-key-here", "User")
```

Or: **Settings → System → About → Advanced system settings → Environment Variables → User variables → New**

### Windows (temporary, this session only)

```powershell
$env:CONTEXT7_API_KEY = "ctx7sk-xxxx-your-key-here"
```

Then start Cursor from this same PowerShell window.

### macOS / Linux

Add to `~/.zshrc`, `~/.bashrc`, or `~/.profile`:

```bash
export CONTEXT7_API_KEY="ctx7sk-xxxx-your-key-here"
```

Then restart the terminal and Cursor (or run `source ~/.zshrc` and start Cursor from that shell).

---

## 2. Required Configuration

Create `.cursor/mcp.json` with the following (**no key in the file**):

```json
{
  "mcpServers": {
    "Context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"],
      "env": {
        "CONTEXT7_API_KEY": "${env:CONTEXT7_API_KEY}"
      }
    }
  }
}
```

---

## Configuration Details

- **Server:** `npx -y @upstash/context7-mcp`
- **API Key:** From environment via `${env:CONTEXT7_API_KEY}` — set `CONTEXT7_API_KEY` before starting Cursor
- **Key Format:** Valid Context7 API key (starts with `ctx7sk`)

---

## Security

- ✅ **No key in the repo** — `mcp.json` only references `${env:CONTEXT7_API_KEY}`
- ✅ `.cursor/mcp.json` is in `.gitignore` (optional; it contains no secrets)
- ✅ API key stays in your OS user environment or shell only

---

## Verification

After setting `CONTEXT7_API_KEY` and creating `mcp.json`, **fully quit and reopen Cursor** (so it sees the env var), then test:

```bash
@bmad-master
*context7-kb-test
```

Or test with a documentation lookup:

```bash
@bmad-master
*context7-docs fastapi dependency-injection
```

---

## Next Steps

Once MCP is configured:

1. **Execute KB Fetch Plan:**
   - See `docs/kb/EPIC_AI17_AI18_KB_FETCH_PLAN.md`
   - Run Phase 1 commands to fetch critical documentation

2. **Verify KB Cache:**
   ```bash
   *context7-kb-status
   ```

3. **Start Epic AI-17 Implementation:**
   - All required documentation will be cached and available

---

**Note:** This file and `.cursor/mcp.json` can be committed; neither contains the API key. The key exists only in your `CONTEXT7_API_KEY` environment variable.


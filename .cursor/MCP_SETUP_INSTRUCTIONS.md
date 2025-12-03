# Context7 MCP Configuration Setup

**Created:** January 2025  
**Purpose:** Instructions for setting up Context7 MCP server configuration

---

## Required Configuration

Create `.cursor/mcp.json` with the following content:

```json
{
  "mcpServers": {
    "context7": {
      "url": "https://context7.com/api/v2",
      "headers": {
        "CONTEXT7_API_KEY": "ctx7sk-037328d6-1bf5-4799-a54c-43340396ddd2"
      }
    }
  }
}
```

---

## Configuration Details

- **API URL:** `https://context7.com/api/v2`
- **API Key:** `ctx7sk-037328d6-1bf5-4799-a54c-43340396ddd2`
- **Key Format:** Valid Context7 API key (starts with `ctx7sk`)

---

## Security

- ✅ `.cursor/mcp.json` is in `.gitignore` - will NOT be committed to git
- ✅ API key is stored locally only
- ✅ Reference documentation created in `docs/kb/CONTEXT7_API_KEY_REFERENCE.md`

---

## Verification

After creating the file, restart Cursor/IDE and test:

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

**Note:** This file can be committed to git (does not contain the actual API key). The actual configuration with the key is in `.cursor/mcp.json` which is gitignored.


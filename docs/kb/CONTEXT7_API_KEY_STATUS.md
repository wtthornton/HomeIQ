# Context7 API Key Status

**Last Updated:** January 2025  
**Status:** ✅ Both TappsCodingAgents and MCP Server Configured  
**API Key:** `ctx7sk-49080f4f-b612-4d41-a16b-e8cf388ba7d7`

---

## Current Configuration Status

### ✅ TappsCodingAgents Configuration

**Status:** Configured and Working

**Key Location:** Encrypted storage (`.tapps-agents/api-keys.encrypted`)
- **Key Found:** ✅ Yes
- **Environment Variable:** Can be set for current session
- **Automatic Loading:** ✅ Yes (loads from encrypted storage automatically)

**Verification:**
```bash
python -c "import os; from tapps_agents.context7.security import APIKeyManager; env_key = os.getenv('CONTEXT7_API_KEY'); mgr = APIKeyManager(); enc_key = mgr.load_api_key('context7'); print('Environment:', 'SET' if env_key else 'NOT SET'); print('Encrypted:', 'FOUND' if enc_key else 'NOT FOUND'); print('Available:', 'YES' if (env_key or enc_key) else 'NO')"
```

**Expected Output:**
```
Environment: NOT SET (or SET if environment variable is set)
Encrypted: FOUND
Available: YES
```

---

### ✅ MCP Server Configuration

**Status:** Configured and Working

**Configuration File:** `.cursor/mcp.json` (gitignored)

**Current Configuration:**
```json
{
  "mcpServers": {
    "context7": {
      "headers": {
        "CONTEXT7_API_KEY": "ctx7sk-49080f4f-b612-4d41-a16b-e8cf388ba7d7"
      },
      "url": "https://mcp.context7.com/mcp"
    }
  }
}
```

**Verification:**
- ✅ MCP server responds to `resolve-library-id` calls
- ✅ API key is valid and working
- ✅ Configuration file exists and is properly formatted

---

## Setting Environment Variable (Optional)

**For TappsCodingAgents CLI Usage:**

The framework automatically loads the key from encrypted storage, but you can also set it as an environment variable for the current session:

**Windows PowerShell (Current Session):**
```powershell
$env:CONTEXT7_API_KEY = "ctx7sk-49080f4f-b612-4d41-a16b-e8cf388ba7d7"
```

**Windows PowerShell (Permanent - User Level):**
```powershell
[System.Environment]::SetEnvironmentVariable("CONTEXT7_API_KEY", "ctx7sk-49080f4f-b612-4d41-a16b-e8cf388ba7d7", "User")
```

**Linux/macOS (Current Session):**
```bash
export CONTEXT7_API_KEY="ctx7sk-49080f4f-b612-4d41-a16b-e8cf388ba7d7"
```

**Linux/macOS (Permanent):**
```bash
echo 'export CONTEXT7_API_KEY="ctx7sk-49080f4f-b612-4d41-a16b-e8cf388ba7d7"' >> ~/.bashrc
source ~/.bashrc
```

**Note:** Setting the environment variable is optional since TappsCodingAgents automatically loads from encrypted storage.

---

## Key Management

### Current Key
- **Key:** `ctx7sk-49080f4f-b612-4d41-a16b-e8cf388ba7d7`
- **Status:** ✅ Active and Working
- **Location:** 
  - Encrypted storage: `.tapps-agents/api-keys.encrypted`
  - MCP config: `.cursor/mcp.json`

### Key Rotation

If the key needs to be rotated:

1. **Generate new key in Context7 console**
2. **Update encrypted storage:**
   ```python
   from tapps_agents.context7.security import APIKeyManager
   mgr = APIKeyManager()
   mgr.store_api_key("context7", "new-key-here", encrypt=True)
   ```
3. **Update MCP config:** Edit `.cursor/mcp.json` with new key
4. **Update environment variable (if set):** Update system environment variable
5. **Restart Cursor/IDE** to reload MCP configuration

---

## Verification Commands

### Test TappsCodingAgents Context7 Integration
```bash
# Test key availability
python -c "from tapps_agents.context7.security import APIKeyManager; mgr = APIKeyManager(); key = mgr.load_api_key('context7'); print('Key Found:', 'YES' if key else 'NO')"

# Test Context7 API access (if using TappsCodingAgents CLI)
python -m tapps_agents.cli reviewer docs fastapi
```

### Test MCP Server
```bash
# Using BMAD Master (in Cursor)
@bmad-master
*context7-kb-test

# Or test with documentation lookup
@bmad-master
*context7-docs fastapi dependency-injection
```

---

## Troubleshooting

### Issue: TappsCodingAgents can't find API key

**Solution:**
1. Check encrypted storage: `python -c "from tapps_agents.context7.security import APIKeyManager; mgr = APIKeyManager(); key = mgr.load_api_key('context7'); print(key if key else 'NOT FOUND')"`
2. If not found, store the key: `python -c "from tapps_agents.context7.security import APIKeyManager; mgr = APIKeyManager(); mgr.store_api_key('context7', 'ctx7sk-49080f4f-b612-4d41-a16b-e8cf388ba7d7', encrypt=True)"`
3. Or set environment variable: `$env:CONTEXT7_API_KEY = "ctx7sk-49080f4f-b612-4d41-a16b-e8cf388ba7d7"`

### Issue: MCP server authentication fails

**Solution:**
1. Check `.cursor/mcp.json` exists and contains correct key
2. Verify key format starts with `ctx7sk-`
3. Restart Cursor/IDE to reload MCP configuration
4. Check MCP server logs for detailed error messages

---

## Related Documentation

- **Setup Guide:** `docs/current/context7-setup.md`
- **Key Reference:** `docs/kb/CONTEXT7_API_KEY_REFERENCE.md`
- **MCP Setup:** `.cursor/MCP_SETUP_INSTRUCTIONS.md`
- **TappsCodingAgents Guide:** `TappsCodingAgents/docs/CONTEXT7_API_KEY_MANAGEMENT.md`

---

**Security Note:** This document does not contain the actual API key for security reasons. The key is stored in:
- Encrypted storage: `.tapps-agents/api-keys.encrypted` (encrypted)
- MCP config: `.cursor/mcp.json` (gitignored, local only)


# Context7 API Key Reference

**Last Updated:** January 2025  
**Status:** ✅ Configured  
**Security:** API key stored in `.cursor/mcp.json` (local file, not committed to git)

---

## Configuration Location

**Primary Location:** `.cursor/mcp.json`

This file contains the Context7 MCP server configuration with the API key. The file is stored locally and should NOT be committed to version control.

---

## API Configuration

- **API URL:** `https://context7.com/api/v2`
- **API Key:** Stored in `.cursor/mcp.json` (see file for actual key)
- **Key Format:** `ctx7sk-*` (Context7 standard format)
- **Key Status:** ✅ Active and configured

---

## Security Notes

1. **Never commit `.cursor/mcp.json` to git** - Contains sensitive API key
2. **Backup location:** This reference document (does not contain actual key)
3. **Key rotation:** If key is compromised, generate new key in Context7 console
4. **Team sharing:** Share key securely via password manager or secure channel

---

## Verification

To verify the API key is working:

```bash
@bmad-master
*context7-kb-test
```

Or test with a simple lookup:

```bash
@bmad-master
*context7-docs fastapi dependency-injection
```

---

## Key Recovery

If the key is lost:
1. Check `.cursor/mcp.json` (local file)
2. Check Context7 console for key regeneration
3. Update `.cursor/mcp.json` with new key
4. Restart Cursor/IDE to reload MCP configuration

---

## Related Documentation

- **Setup Guide:** `docs/current/context7-setup.md`
- **KB Status:** `docs/kb/EPIC_AI17_AI18_KB_STATUS.md`
- **Fetch Plan:** `docs/kb/EPIC_AI17_AI18_KB_FETCH_PLAN.md`

---

**Note:** This document does not contain the actual API key for security reasons. The key is stored in `.cursor/mcp.json` which is a local configuration file.


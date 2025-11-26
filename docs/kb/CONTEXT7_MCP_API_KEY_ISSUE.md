# Context7 MCP API Key Issue

**Date:** November 2025  
**Status:** API Key Configuration Issue Detected

## Issue

When attempting to use Context7 MCP tools directly, received error:
```
Unauthorized. Please check your API key. The API key you provided (possibly incorrect) is: ctx7sk-b6f...2e49. API keys should start with 'ctx7sk'
```

## Analysis

The error message is confusing - it says the API key should start with 'ctx7sk', but the key shown already starts with 'ctx7sk'. This suggests:

1. The API key format might be correct but invalid/expired
2. The MCP server configuration might need verification
3. The key might need to be regenerated

## Solution

### Option 1: Use BMAD Master Commands (Recommended)

The BMAD framework handles Context7 MCP integration internally. Use:

```bash
@bmad-master
*context7-docs {library} {topic}
```

These commands will:
- Handle MCP connection internally
- Use proper authentication
- Cache results automatically

### Option 2: Verify MCP Configuration

1. Check Cursor MCP settings
2. Verify Context7 MCP server is running
3. Check API key in MCP configuration
4. Restart Cursor if needed

### Option 3: Manual Execution

See `docs/kb/EXECUTE_TECH_STACK_KB_FETCH.md` for step-by-step commands to run manually.

## Current Status

- ✅ Context7 MCP is running (confirmed by user)
- ⚠️ API key authentication issue detected
- ✅ BMAD Master commands should work (uses MCP internally)
- ✅ Manual execution plan created

## Next Steps

1. Try using `@bmad-master` commands (they handle MCP internally)
2. If still failing, verify MCP configuration
3. Use manual execution plan as fallback


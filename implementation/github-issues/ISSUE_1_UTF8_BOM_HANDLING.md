# GitHub Issue: UTF-8 BOM Handling in MCP Config Parsing

## Issue Template

**Title:** `detect_mcp_servers()` fails to parse mcp.json with UTF-8 BOM

**Labels:** `bug`, `windows`, `high-priority`, `init`

---

## Description

The `detect_mcp_servers()` function in `tapps_agents/core/init_project.py` fails to parse `.cursor/mcp.json` files that contain a UTF-8 BOM (Byte Order Mark `\xef\xbb\xbf`). This is common on Windows when files are saved with certain editors (Notepad, some VS Code configurations).

## Symptoms

- Context7 and Playwright show as "Not configured" even when properly configured
- Doctor command reports MCP servers as missing
- No error message explaining the issue
- Silent failure - users don't know why detection fails

## Root Cause

The file is opened with `encoding='utf-8'` which doesn't strip the BOM:

```python
# Current code (line ~1263)
with open(config_path, encoding="utf-8") as f:
    mcp_config = json.load(f)  # Fails if BOM present - JSON parser sees invalid character
```

The UTF-8 BOM (`\xef\xbb\xbf` = ``) is prepended to the file content, making the JSON invalid:
- File starts with `{"mcpServers":...`
- With BOM: `{"mcpServers":...`

## Steps to Reproduce

1. On Windows, create/edit `.cursor/mcp.json` with Notepad or save with "UTF-8 with BOM"
2. Add valid Context7 configuration
3. Run `tapps-agents doctor`
4. Observe Context7 shows as "Not configured"

## Expected Behavior

MCP config files with UTF-8 BOM should be parsed correctly, detecting configured servers.

## Suggested Fix

Use `encoding='utf-8-sig'` which automatically strips the BOM:

```python
# Fixed code
with open(config_path, encoding="utf-8-sig") as f:
    mcp_config = json.load(f)  # Now handles BOM correctly
```

## Impact

- **Severity:** High
- **Affected Users:** All Windows users who may have BOM in their config files
- **Workaround:** Manually remove BOM from file using a text editor that shows encoding

## Related Issues

- May also affect other JSON config file parsing in the codebase
- Consider adding encoding normalization to `init` command

## Additional Context

- UTF-8 BOM: `\xef\xbb\xbf` (3 bytes)
- Windows Notepad saves UTF-8 files with BOM by default
- Python's `utf-8-sig` encoding automatically handles BOM on read and doesn't write it

## Checklist

- [ ] Fix applied to `detect_mcp_servers()` 
- [ ] Add encoding normalization to `init_cursor_mcp_config()`
- [ ] Add unit tests for BOM handling
- [ ] Test on Windows with BOM file
- [ ] Document in release notes

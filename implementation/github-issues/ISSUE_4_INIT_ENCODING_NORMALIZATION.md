# GitHub Issue: Init Command Should Normalize MCP Config Encoding

## Issue Template

**Title:** Init command should normalize mcp.json encoding during setup/reset

**Labels:** `enhancement`, `init`, `windows`

---

## Description

When running `tapps-agents init` or `init --reset`, the command should detect and fix encoding issues (like UTF-8 BOM) in existing config files to prevent detection failures.

This is a preventive measure that complements the BOM handling fix in `detect_mcp_servers()`.

## Current Behavior

- `init` creates new files with clean UTF-8 encoding
- Existing files with BOM are left unchanged
- Users must manually fix encoding issues

## Proposed Behavior

- `init` normalizes encoding of existing config files
- Removes UTF-8 BOM if present
- Logs when normalization occurs

## Suggested Implementation

### 1. Add helper function:

```python
def normalize_file_encoding(file_path: Path) -> bool:
    """
    Normalize file encoding by removing BOM and ensuring UTF-8.
    
    Returns:
        True if file was modified, False otherwise
    """
    try:
        # Read with BOM handling
        content = file_path.read_text(encoding='utf-8-sig')
        
        # Check if content starts with BOM (was present)
        original = file_path.read_bytes()
        had_bom = original.startswith(b'\xef\xbb\xbf')
        
        if had_bom:
            # Rewrite without BOM
            file_path.write_text(content, encoding='utf-8')
            logger.debug(f"Normalized encoding for {file_path}")
            return True
        return False
    except Exception:
        return False
```

### 2. Integrate into `init_cursor_mcp_config()`:

```python
def init_cursor_mcp_config(project_root, overwrite=False):
    # ... existing code ...
    
    # If file exists and we're not overwriting, normalize encoding
    if mcp_config_file.exists() and not overwrite:
        normalize_file_encoding(mcp_config_file)
        return False, str(mcp_config_file)
    
    # ... rest of function ...
```

## Impact

- **Severity:** Low (preventive measure)
- **Affected Users:** Windows users with BOM files
- **Benefit:** Automatic fix during normal workflow

## Additional Context

- Works alongside `detect_mcp_servers()` BOM fix
- Non-destructive - only modifies encoding, preserves content
- Silent operation unless logging enabled

## Checklist

- [ ] Add `normalize_file_encoding()` helper function
- [ ] Integrate into `init_cursor_mcp_config()`
- [ ] Consider integrating into other config file handlers
- [ ] Add unit tests
- [ ] Document behavior

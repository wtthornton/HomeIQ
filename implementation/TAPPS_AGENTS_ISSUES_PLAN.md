# TappsCodingAgents Issues Implementation Plan

**Created:** January 7, 2026  
**Status:** ✅ Implementation Complete

## Implementation Summary

All 4 issues have been fixed with code changes and unit tests:

| Issue | Status | Files Modified |
|-------|--------|----------------|
| #1 UTF-8 BOM Handling | ✅ Fixed | `init_project.py` line 1265 |
| #2 Playwright Detection | ✅ Fixed | `init_project.py` lines 1238-1346 |
| #3 Cache Compatibility | ✅ Fixed | `metadata.py` lines 1-60 |
| #4 Encoding Normalization | ✅ Fixed | `init_project.py` lines 667-699 |

**Test Files Created:**
- `tests/unit/core/test_init_project_fixes.py` - Tests for issues #1, #2, #4
- `tests/unit/context7/test_metadata_compatibility.py` - Tests for issue #3

**GitHub Issue Templates:** `implementation/github-issues/`

---

## Executive Summary

This plan addresses 4 issues discovered during TappsCodingAgents usage on Windows:
- 1 HIGH priority bug (BOM handling)
- 2 MEDIUM priority issues (Playwright detection, cache compatibility)
- 1 LOW priority enhancement (encoding normalization)

## Issue Overview

| Issue | Type | Priority | Impact | Effort |
|-------|------|----------|--------|--------|
| #1 UTF-8 BOM Handling | BUG | HIGH | All Windows users | Low |
| #2 Playwright Package Detection | ENHANCEMENT | MEDIUM | Users with @playwright/mcp | Low |
| #3 Cache Version Compatibility | BUG | MEDIUM | Upgrading users | Medium |
| #4 Init Encoding Normalization | ENHANCEMENT | LOW | Preventive | Low |

---

## Issue #1: UTF-8 BOM Handling in MCP Config Parsing (BUG)

### Problem
`detect_mcp_servers()` in `tapps_agents/core/init_project.py` fails to parse `.cursor/mcp.json` files containing UTF-8 BOM (Byte Order Mark `\xef\xbb\xbf`).

### Root Cause
```python
# Current code (line 1263-1264)
with open(config_path, encoding="utf-8") as f:
    mcp_config = json.load(f)  # Fails if BOM present
```

### Fix
```python
# Use utf-8-sig encoding to automatically strip BOM
with open(config_path, encoding="utf-8-sig") as f:
    mcp_config = json.load(f)
```

### Files to Modify
- `tapps_agents/core/init_project.py` (line 1263)

### Test Cases
1. Test parsing mcp.json WITHOUT BOM (regression)
2. Test parsing mcp.json WITH UTF-8 BOM
3. Test parsing mcp.json WITH UTF-16 BOM (edge case)

---

## Issue #2: Playwright MCP Package Name Detection Incomplete (ENHANCEMENT)

### Problem
Detection only checks for `@playwright/mcp-server` but many configs use `@playwright/mcp`.

### Current Code
```python
# Lines 1238-1246
optional_servers = {
    "Playwright": {
        "name": "Playwright MCP Server",
        "package": "@playwright/mcp-server",  # Only checks this
        ...
    }
}
```

### Fix
```python
optional_servers = {
    "Playwright": {
        "name": "Playwright MCP Server",
        "packages": ["@playwright/mcp-server", "@playwright/mcp"],  # Check both
        ...
    }
}

# Update detection logic to iterate over packages list
for package in server_info.get("packages", [server_info.get("package")]):
    if package in args or any(package in arg for arg in args):
        detected = True
        break
```

### Files to Modify
- `tapps_agents/core/init_project.py` (lines 1238-1246, 1298-1302)

### Test Cases
1. Test detection with `@playwright/mcp-server` (regression)
2. Test detection with `@playwright/mcp`
3. Test detection with versioned package `@playwright/mcp@0.0.35`

---

## Issue #3: Context7 Cache Version Compatibility (BUG)

### Problem
Cache entries from older versions (3.2.x) fail to load in 3.3.0 due to `LibraryMetadata` model changes:
```
LibraryMetadata.__init__() got an unexpected keyword argument 'library_version'
```

### Root Cause
`LibraryMetadata.from_dict()` uses `cls(**data)` which fails if data contains extra fields.

### Current Code
```python
# tapps_agents/context7/metadata.py (lines 37-39)
@classmethod
def from_dict(cls, data: dict[str, Any]) -> LibraryMetadata:
    """Create from dictionary."""
    return cls(**data)
```

### Fix
```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> LibraryMetadata:
    """Create from dictionary with backwards compatibility."""
    # Get valid field names from dataclass
    valid_fields = {f.name for f in fields(cls)}
    
    # Filter out unknown fields (from older/newer versions)
    filtered_data = {k: v for k, v in data.items() if k in valid_fields}
    
    # Log warning for discarded fields (debug level)
    discarded = set(data.keys()) - valid_fields
    if discarded:
        import logging
        logging.getLogger(__name__).debug(
            f"Discarded unknown fields from cache entry: {discarded}"
        )
    
    return cls(**filtered_data)
```

### Additional Fix: Add Cache Version Tracking
```python
# Add to CacheIndex
CURRENT_CACHE_VERSION = "1.1"  # Bump when LibraryMetadata changes

@dataclass
class CacheIndex:
    version: str = CURRENT_CACHE_VERSION  # Track schema version
    schema_version: str = "1.0"  # New: explicit schema version
    ...
    
    def needs_migration(self) -> bool:
        """Check if cache needs migration to current schema."""
        return self.schema_version != CURRENT_CACHE_VERSION
```

### Files to Modify
- `tapps_agents/context7/metadata.py`
- `tapps_agents/context7/kb_cache.py` (add migration logic)

### Test Cases
1. Test loading metadata with current fields (regression)
2. Test loading metadata with extra fields (old version)
3. Test loading metadata with missing optional fields
4. Test cache version detection and migration

---

## Issue #4: Init --reset Should Handle BOM Files (ENHANCEMENT)

### Problem
`tapps-agents init` and `init --reset` should normalize encoding when working with config files.

### Fix
Add encoding normalization to `init_cursor_mcp_config()`:

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
            return True
        return False
    except Exception:
        return False

def init_cursor_mcp_config(project_root: Path | None = None, overwrite: bool = False) -> tuple[bool, str | None]:
    # ... existing code ...
    
    # If file exists and we're not overwriting, normalize encoding
    if mcp_config_file.exists() and not overwrite:
        normalize_file_encoding(mcp_config_file)
        return False, str(mcp_config_file)
    
    # ... rest of function ...
```

### Files to Modify
- `tapps_agents/core/init_project.py`

### Test Cases
1. Test init with existing BOM file (should normalize)
2. Test init with existing clean file (should not modify)
3. Test init --reset with BOM file

---

## Implementation Order

### Phase 1: Critical Fix (Issue #1)
**Time Estimate:** 30 minutes
1. Fix BOM handling in `detect_mcp_servers()`
2. Add unit test for BOM handling
3. Verify fix with manual testing

### Phase 2: Detection Enhancement (Issue #2)
**Time Estimate:** 45 minutes
1. Add multiple package name support to Playwright detection
2. Update detection logic to check all variants
3. Add unit tests for package variants

### Phase 3: Cache Compatibility (Issue #3)
**Time Estimate:** 1-2 hours
1. Make `LibraryMetadata.from_dict()` backwards-compatible
2. Add cache version tracking
3. Add migration logic (optional)
4. Add comprehensive tests

### Phase 4: Preventive Enhancement (Issue #4)
**Time Estimate:** 30 minutes
1. Add `normalize_file_encoding()` helper
2. Integrate into init workflow
3. Add tests

---

## GitHub Issues to Create

### Issue #1: UTF-8 BOM Handling
```markdown
**Title:** detect_mcp_servers() fails to parse mcp.json with UTF-8 BOM

**Labels:** bug, windows, high-priority

**Description:**
The `detect_mcp_servers()` function in `init_project.py` fails to parse `.cursor/mcp.json` files that contain a UTF-8 BOM (Byte Order Mark `\xef\xbb\xbf`). This is common on Windows when files are saved with certain editors.

**Symptoms:**
- Context7 and Playwright show as "Not configured" even when properly configured
- Doctor command reports MCP servers as missing
- No error message explaining the issue

**Root Cause:**
File opened with `encoding='utf-8'` which doesn't strip BOM.

**Suggested Fix:**
Use `encoding='utf-8-sig'` to automatically handle BOM.

**Impact:** High - affects all Windows users who may have BOM in their config files
```

### Issue #2: Playwright MCP Detection
```markdown
**Title:** Detection doesn't recognize @playwright/mcp package variant

**Labels:** enhancement, detection

**Description:**
The `detect_mcp_servers()` function only checks for `@playwright/mcp-server`, but many configurations use `@playwright/mcp`.

**Suggested Fix:**
Check for multiple package name variants.

**Impact:** Medium - false negative warning for users with working Playwright MCP
```

### Issue #3: Cache Version Compatibility
```markdown
**Title:** Cache entries from older versions cause LibraryMetadata initialization errors

**Labels:** bug, cache, upgrade

**Description:**
After upgrading from 3.2.x to 3.3.0, cached Context7 entries fail to load with:
`LibraryMetadata.__init__() got an unexpected keyword argument 'library_version'`

**Suggested Fix:**
- Make `from_dict()` filter unknown fields
- Add cache version tracking
- Auto-migrate or invalidate old cache entries

**Impact:** Medium - affects all users upgrading from older versions
```

### Issue #4: Init Encoding Normalization
```markdown
**Title:** Init command should normalize mcp.json encoding during setup/reset

**Labels:** enhancement, init

**Description:**
When running `tapps-agents init` or `init --reset`, normalize encoding issues in existing config files.

**Impact:** Low - preventive measure
```

---

## Verification Checklist

- [ ] Issue #1 fix tested on Windows with BOM file
- [ ] Issue #2 fix tested with both package variants
- [ ] Issue #3 fix tested with old cache data
- [ ] Issue #4 fix integrated into init workflow
- [ ] All unit tests pass
- [ ] No regressions in existing functionality
- [ ] GitHub issues created with proper labels

---

## Related Files

- `TappsCodingAgents/tapps_agents/core/init_project.py`
- `TappsCodingAgents/tapps_agents/core/doctor.py`
- `TappsCodingAgents/tapps_agents/context7/metadata.py`
- `TappsCodingAgents/tapps_agents/context7/kb_cache.py`
- `TappsCodingAgents/tests/unit/core/test_init_project.py` (create/update)
- `TappsCodingAgents/tests/unit/context7/test_metadata.py` (update)

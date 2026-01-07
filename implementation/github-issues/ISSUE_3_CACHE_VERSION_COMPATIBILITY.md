# GitHub Issue: Context7 Cache Version Compatibility

## Issue Template

**Title:** Cache entries from older versions cause LibraryMetadata initialization errors

**Labels:** `bug`, `cache`, `upgrade`, `context7`

---

## Description

After upgrading from TappsCodingAgents 3.2.x to 3.3.0, cached Context7 entries fail to load with:

```
LibraryMetadata.__init__() got an unexpected keyword argument 'library_version'
```

This indicates the `LibraryMetadata` model changed (fields added/removed) but old cache entries contain incompatible fields.

## Symptoms

- `doctor --full` health check fails
- Context7 cache shows as "unhealthy"
- Users must manually clear cache after upgrade
- Error message doesn't clearly indicate solution

## Root Cause

`LibraryMetadata.from_dict()` uses direct unpacking which fails on unknown fields:

```python
# Current code (metadata.py lines ~37-39)
@classmethod
def from_dict(cls, data: dict[str, Any]) -> LibraryMetadata:
    """Create from dictionary."""
    return cls(**data)  # Fails if 'data' contains fields not in current dataclass
```

When cache files contain fields like `library_version` (from older schema), the `**data` unpacking fails.

## Steps to Reproduce

1. Use TappsCodingAgents 3.2.x and populate Context7 cache
2. Upgrade to TappsCodingAgents 3.3.0
3. Run `tapps-agents doctor --full`
4. Observe cache health check failure

## Expected Behavior

Cache entries from older versions should load gracefully, ignoring unknown fields.

## Suggested Fix

### 1. Make `from_dict()` backwards-compatible:

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> LibraryMetadata:
    """Create from dictionary with backwards compatibility."""
    from dataclasses import fields
    
    # Get valid field names from dataclass
    valid_fields = {f.name for f in fields(cls)}
    
    # Filter out unknown fields (from older/newer versions)
    filtered_data = {k: v for k, v in data.items() if k in valid_fields}
    
    # Log discarded fields (debug level)
    discarded = set(data.keys()) - valid_fields
    if discarded:
        logger.debug(f"Discarded unknown fields from cache entry: {discarded}")
    
    return cls(**filtered_data)
```

### 2. Add cache version tracking (optional enhancement):

```python
CURRENT_CACHE_VERSION = "1.1"

@dataclass
class CacheIndex:
    version: str = "1.0"
    schema_version: str = CURRENT_CACHE_VERSION  # Track schema version
    ...
    
    def needs_migration(self) -> bool:
        """Check if cache needs migration."""
        return self.schema_version != CURRENT_CACHE_VERSION
```

### 3. Add migration logic (optional):

- Auto-invalidate incompatible cache entries
- Or migrate old entries to new schema

## Impact

- **Severity:** Medium
- **Affected Users:** All users upgrading from older versions
- **Workaround:** Manually delete `.tapps-agents/context7-kb/` directory

## Additional Context

- Cache files are YAML format in `.tapps-agents/context7-kb/`
- Each library has a `meta.yaml` with `LibraryMetadata`
- Field changes between versions should be backwards-compatible

## Checklist

- [ ] Make `LibraryMetadata.from_dict()` filter unknown fields
- [ ] Make `CacheIndex.from_dict()` filter unknown fields (if needed)
- [ ] Add debug logging for discarded fields
- [ ] Add unit tests for backwards compatibility
- [ ] Consider cache version tracking
- [ ] Document upgrade process

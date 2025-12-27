# Context7 KB Refresh Queue System

## Overview

The `.refresh-queue` file is a **temporary, dynamically-created file** that manages background refresh requests for stale Context7 cache entries. It only exists when there are pending refresh operations.

## ✅ System Status: **WORKING AS DESIGNED**

The absence of `.refresh-queue` is **NORMAL** and indicates:
- ✅ No pending refresh operations
- ✅ All cache entries are fresh or have been processed
- ✅ Queue is empty (good state)

## How It Works

### File Location
```
docs/kb/context7-cache/.refresh-queue
```

### File Format
Simple text file with one entry per line:
```
library,topic,timestamp
```

Example:
```
vitest,all,2025-10-12T14:30:00Z
pytest,fixtures,2025-10-12T14:45:00Z
react,hooks,2025-10-12T15:00:00Z
```

### Lifecycle

#### 1. Creation (Automatic)
The file is **automatically created** when:
- User accesses stale cache during `*context7-docs` lookup
- System detects cache older than max_age_days
- Item is queued for background refresh
- First entry writes the file

#### 2. Population (Automatic)
Additional entries are appended when:
- More stale cache entries are detected
- User continues working with cached docs
- System queues items without blocking user

#### 3. Processing (On Next Startup)
If `auto_process_on_startup: true` (default):
- Agent reads queue on activation
- Processes each entry (fetches fresh docs from Context7)
- Updates cache files and timestamps
- Reports brief message: "🔄 Processed N KB refresh(es)"

#### 4. Deletion (Automatic)
The file is **automatically deleted** when:
- ✅ All queued items processed successfully
- Queue is empty

OR **rewritten** when:
- ⚠️ Some items failed (only failed items remain in queue)
- User can retry with `*context7-kb-process-queue`

## User Workflows

### Automatic Mode (Default)
```bash
# Session 1
@bmad-master
*context7-docs vitest coverage

# Output:
# 📋 KB Status: vitest needs refresh (35 days old)
# 💡 Queued for refresh on next agent startup
# 📄 Using cached docs (verified fresh)
# [documentation content]

# Session 2 (Next Day)
@bmad-master
# Output:
# 🔄 Processed 1 KB refresh(es)  ← Automatic!
# 🧙 BMad Master Activated
```

### Manual Control
```bash
# Check queue status
*context7-kb-status

# Process queue manually (anytime)
*context7-kb-process-queue

# Check what needs refresh
*context7-kb-refresh --check-only

# Force refresh now
*context7-kb-refresh
```

## Configuration

Edit `.bmad-core/core-config.yaml`:

```yaml
context7:
  knowledge_base:
    refresh:
      enabled: true
      auto_process_on_startup: true       # Process queue on agent startup
      auto_check_on_first_access: true    # Auto-detect stale cache
      auto_queue: true                    # Auto-queue stale entries
      notify_stale: true                  # Notify user when stale detected
```

### Disable Automatic Refresh
```yaml
context7:
  knowledge_base:
    refresh:
      auto_process_on_startup: false      # No startup processing
      auto_check_on_first_access: false   # No auto-detection
```

## Refresh Policies

Libraries refresh based on their type (defined in meta.yaml):

| Library Type | Max Age | Examples |
|--------------|---------|----------|
| **Stable** | 30 days | React, pytest, FastAPI, TypeScript |
| **Active** | 14 days | Vitest, Playwright, Vite |
| **Critical** | 7 days | Security libs, JWT, OAuth |

## Commands Reference

| Command | Purpose |
|---------|---------|
| `*context7-kb-status` | Show cache statistics and staleness |
| `*context7-kb-refresh --check-only` | Check which entries need refresh |
| `*context7-kb-refresh` | Refresh all stale entries now |
| `*context7-kb-process-queue` | Process queued refreshes manually |

## Troubleshooting

### "File not found: .refresh-queue"
**Status**: ✅ **NORMAL**
- Queue is empty (good state)
- No pending refresh operations
- No action needed

### Queue file exists but old
**Action**: Run `*context7-kb-process-queue`
- Processes pending refreshes
- Clears queue if successful

### Queue keeps growing
**Possible causes**:
- Context7 API unavailable
- Network issues
- Permission problems

**Action**:
1. Check internet connection
2. Verify file permissions
3. Try manual processing: `*context7-kb-process-queue`
4. Check logs for errors

### Want to clear queue manually
```bash
# Option 1: Delete file
rm docs/kb/context7-cache/.refresh-queue

# Option 2: Use command (future)
*context7-kb-queue-clear
```

## Git Handling

The `.refresh-queue` file is **ignored by git** (should be in `.gitignore`):
```gitignore
# Context7 KB refresh queue (temporary, user-specific)
docs/kb/context7-cache/.refresh-queue
```

**Reason**: Queue is session-specific and machine-specific, not project state.

## Architecture Notes

### Why File-Based?
- ✅ Simple (no database required)
- ✅ Human-readable (easy debugging)
- ✅ Self-cleaning (auto-deletes when empty)
- ✅ Stateless (no migration needed)
- ✅ Git-friendly (ignored, no conflicts)

### Why Not Database?
- ❌ Over-engineering for simple queue
- ❌ Adds dependency complexity
- ❌ Harder to debug and inspect
- ❌ Not appropriate for file-based KB cache

### Performance Impact
- **Startup delay**: 2-5 seconds when processing queue
- **Lookup impact**: Zero (doesn't block normal operations)
- **Queue size**: Typically 1-5 items, max ~20 items
- **Processing time**: ~2-3 seconds per library

## Related Documentation

- [AUTO_REFRESH_QUICK_START.md](AUTO_REFRESH_QUICK_START.md) - Quick start guide
- [.bmad-core/tasks/context7-kb-process-queue.md](../../../.bmad-core/tasks/context7-kb-process-queue.md) - Command implementation
- [.bmad-core/tasks/context7-kb-refresh.md](../../../.bmad-core/tasks/context7-kb-refresh.md) - Refresh implementation
- [.bmad-core/core-config.yaml](../../../.bmad-core/core-config.yaml) - Configuration

## Summary

✅ **The `.refresh-queue` file is NOT an issue**

It's a temporary, dynamically-created file that:
- Only exists when there are pending refresh operations
- Is automatically created/deleted by the system
- Enables background refresh without blocking users
- Is ignored by git
- Requires no manual management

**If the file doesn't exist → System is healthy and queue is empty!** 🎉


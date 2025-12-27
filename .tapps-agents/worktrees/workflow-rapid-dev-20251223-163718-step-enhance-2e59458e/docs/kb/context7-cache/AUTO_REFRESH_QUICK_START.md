# Context7 KB Auto-Refresh - Quick Start Guide

## 🤖 Now With HYBRID AUTO-REFRESH!

### **It Just Works™** ✨

Your KB cache now **automatically stays fresh** with minimal effort:

1. **On Agent Startup** → Auto-processes queued refreshes (2-5s)
2. **On First KB Access** → Auto-detects stale cache, queues for refresh  
3. **Next Startup** → Processes queue automatically

**You can still manually trigger anytime:**

```bash
# 1. Check what needs refreshing
*context7-kb-refresh --check-only

# 2. Refresh stale entries now
*context7-kb-refresh

# 3. Process queue manually
*context7-kb-process-queue
```

**That's it!** 🎉

---

## What Is This?

Your Context7 KB cache now **tracks freshness** and **auto-refreshes** stale documentation using a smart hybrid approach.

**Benefits:**
- 📄 Keep docs up-to-date automatically
- ⚡ No blocking (except brief startup)
- 🤖 Smart auto-detection
- 🔄 Auto-processing on startup
- 🎯 Still manually controllable

---

## 🤖 Hybrid Auto-Refresh Behavior

### **Automatic Mode (Default)**

**On Agent Startup:**
```
@bmad-master
🔄 Processed 2 KB refresh(es)  ← Automatic!
🧙 BMad Master Activated
```

**On First KB Access in Session:**
```
*context7-docs vitest coverage

📋 KB Status: 2 libraries need refresh  ← Automatic detection!
   ⚠️  vitest (35 days old)
   ⚠️  pytest (42 days old)
💡 Queued for refresh on next agent startup

📄 Using cached docs (verified fresh)
[documentation content]
```

**On Next Agent Startup:**
```
@dev
🔄 Processed 2 KB refresh(es)  ← Auto-processed the queue!
💻 James (Developer) Activated
```

**Result:** Cache automatically stays fresh! 🎉

### **Manual Override (Always Available)**

You can still manually control everything:

```bash
# Check anytime
*context7-kb-refresh --check-only

# Force refresh now
*context7-kb-refresh

# Process queue manually
*context7-kb-process-queue
```

### **Disable Automation**

Edit `.bmad-core/core-config.yaml`:
```yaml
context7:
  knowledge_base:
    refresh:
      auto_process_on_startup: false      # Disable startup processing
      auto_check_on_first_access: false   # Disable auto-detection
```

Then restart agent. System falls back to manual mode.

---

## How It Works

### 1. **Normal Usage** (Nothing Changes)
```bash
*context7-docs vitest coverage
```

If cache is **fresh** (< 14 days):
```
📄 Using cached docs (verified fresh)
[documentation content]
```

If cache is **stale** (> 14 days):
```
📄 Using cached docs (refreshing in background...)
[documentation content]
ℹ️  Cache queued for refresh - run *context7-kb-process-queue later
```

**You still get docs immediately!** No blocking.

### 2. **Manual Refresh** (When Convenient)
```bash
# Check status first
*context7-kb-refresh --check-only

Output:
🔍 Checking for stale cache entries...
  ⚠️  vitest - 35 days old (max: 14 days) - STALE
  ⚠️  pytest - 42 days old (max: 30 days) - STALE

# Refresh now
*context7-kb-refresh

Output:
🔄 Refreshing 2 stale libraries...
✅ vitest refreshed successfully
✅ pytest refreshed successfully
```

### 3. **Process Queue** (After Work)
```bash
*context7-kb-process-queue

Output:
🔄 Processing queue...
✅ Processed 2 items in 4.2s
```

---

## Refresh Policies (Auto-Applied)

| Library Type | Max Age | Examples |
|--------------|---------|----------|
| **Stable** | 30 days | React, pytest, FastAPI, TypeScript |
| **Active** | 14 days | Vitest, Playwright, Vite |
| **Critical** | 7 days | Security libs, JWT, OAuth |

Libraries refresh based on their type. You can check any library's policy:
```bash
*context7-kb-refresh --check-only
```

---

## Common Workflows

### Weekly Maintenance
```bash
# Monday morning routine
*context7-kb-refresh --check-only
*context7-kb-process-queue
```

### Before Important Work
```bash
# Ensure fresh docs before starting
*context7-kb-refresh --check-only

# If anything stale and you have time:
*context7-kb-refresh
```

### After Offline Work
```bash
# Process any queued refreshes
*context7-kb-process-queue
```

---

## FAQ

**Q: Will this slow down my lookups?**  
A: No! Stale cache still returns immediately. Refresh happens later via queue.

**Q: What if refresh fails?**  
A: Item stays in queue, you can retry with `*context7-kb-process-queue`.

**Q: Can I force refresh a fresh cache?**  
A: Not yet, but you can delete the library folder and fetch fresh.

**Q: Where's the queue file?**  
A: `docs/kb/context7-cache/.refresh-queue` (simple text file)

**Q: Can I edit refresh policies?**  
A: Yes! Edit `max_age_days` in any library's `meta.yaml` file.

**Q: Does this work offline?**  
A: Check works offline. Refresh needs Context7 API connection.

---

## Troubleshooting

### "Queue is empty" but I expected items
- Check if `*context7-kb-process-queue` was already run
- Queue is cleared after successful processing

### Refresh fails with "Context7 unavailable"
- Check internet connection
- Try again later
- Items stay in queue for retry

### "Cannot write to cache"
- Check file permissions on `docs/kb/context7-cache/`
- Ensure directory is writable

---

## Example Session

```bash
# Monday morning
*context7-kb-refresh --check-only
# Output: 2 stale libraries found

# Have 5 minutes? Refresh now
*context7-kb-refresh
# Output: Refreshing... Done! (5.2s)

# Or do it later
# (Go do your work)
# (At end of day)
*context7-kb-process-queue
# Output: Processed 2 items
```

---

## Summary

**You now have auto-refresh!** 🎉

- ✅ Documentation stays fresh
- ✅ No blocking on access
- ✅ You control when to refresh
- ✅ Simple, predictable behavior
- ✅ Works with all agents

**Just remember:**
- Check weekly: `*context7-kb-refresh --check-only`
- Refresh when convenient: `*context7-kb-refresh`
- Process queue: `*context7-kb-process-queue`

**That's it!** Simple. Practical. Done. 🚀


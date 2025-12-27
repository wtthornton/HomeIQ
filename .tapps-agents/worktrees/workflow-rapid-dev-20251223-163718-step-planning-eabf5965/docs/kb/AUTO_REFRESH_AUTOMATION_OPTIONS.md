# Auto-Refresh Automation Options
**Created:** October 12, 2025  
**Purpose:** Evaluate automation levels with honest trade-offs

---

## 🎯 Current State (Manual)

```bash
# User manually runs commands
*context7-kb-refresh --check-only
*context7-kb-refresh
*context7-kb-process-queue
```

**Pros:**
- ✅ User has full control
- ✅ No surprises
- ✅ Simple to understand
- ✅ Zero complexity

**Cons:**
- ❌ User must remember to run
- ❌ Cache can get stale if forgotten
- ❌ Manual work required

---

## 🔄 Automation Level 1: Auto-Process Queue on Startup
**Complexity:** LOW | **Time:** 30 minutes | **Value:** MEDIUM

### What It Does
When any BMAD agent activates, automatically process the refresh queue (if not empty).

### Implementation
Add to agent activation instructions:

```yaml
activation-instructions:
  - STEP 3b: Check and auto-process refresh queue
    if os.path.exists('docs/kb/context7-cache/.refresh-queue'):
        auto_process_queue_silently()
```

### Changes Required
- Modify 9 agent activation instructions
- Add silent queue processing function
- Show brief message: "🔄 Processing 2 queued refreshes... ✅ Done"

### Pros
- ✅ Queue processed automatically
- ✅ No user action needed
- ✅ Still simple (just a startup check)
- ✅ Minimal code (~50 lines)

### Cons
- ⚠️ Slight delay on agent startup (2-5 seconds)
- ⚠️ May surprise users initially
- ⚠️ Uses API calls on startup

### Recommended?
**YES** - This is the sweet spot for "a little more automatic"

---

## 🔄 Automation Level 2: Auto-Check on First Access
**Complexity:** LOW | **Time:** 1 hour | **Value:** HIGH

### What It Does
First time user accesses KB in a session, auto-check staleness and queue stale items.

### Implementation
Add session tracking to KB lookup:

```python
# Simple session tracking
SESSION_STARTED = False

def context7_docs(library, topic):
    global SESSION_STARTED
    
    # On first access, check all cache entries
    if not SESSION_STARTED:
        SESSION_STARTED = True
        stale_items = check_all_cache_staleness()
        if stale_items:
            print(f"📋 Found {len(stale_items)} stale cache entries")
            print(f"💡 Run *context7-kb-process-queue to refresh")
            # Auto-queue them
            for item in stale_items:
                queue_refresh(item)
    
    # Normal lookup
    return kb_lookup(library, topic)
```

### Changes Required
- Add session tracking variable
- Modify KB lookup to check on first access
- Auto-queue stale items
- Show user notification once per session

### Pros
- ✅ User is informed automatically
- ✅ Stale items auto-queued
- ✅ Only happens once per session
- ✅ Still user-controlled (queue processing)

### Cons
- ⚠️ First lookup slightly slower (~500ms)
- ⚠️ Global state (SESSION_STARTED)
- ⚠️ May check more often than needed

### Recommended?
**YES** - Good balance of automation and control

---

## 🔄 Automation Level 3: Auto-Refresh on Access (If Stale)
**Complexity:** MEDIUM | **Time:** 2 hours | **Value:** HIGH

### What It Does
When accessing a stale cache entry, auto-refresh it immediately (with timeout).

### Implementation

```python
def context7_docs(library, topic):
    cached = read_kb_cache(library, topic)
    
    if cached:
        if is_cache_stale(library):
            print(f"⚠️  Cache is stale ({get_age(library)} days old)")
            print(f"🔄 Refreshing now (this will take ~2 seconds)...")
            
            # Refresh synchronously with timeout
            try:
                new_docs = fetch_from_context7_with_timeout(library, topic, timeout=5)
                update_cache(library, topic, new_docs)
                update_last_checked(library)
                print(f"✅ Cache refreshed!")
                return new_docs
            except TimeoutError:
                print(f"⚠️  Refresh timeout, using cached docs")
                queue_refresh(library, topic)
                return cached
        else:
            print(f"📄 Using cached docs (verified fresh)")
            return cached
    
    # Cache miss - fetch normally
    return fetch_and_cache_from_context7(library, topic)
```

### Changes Required
- Add timeout to Context7 API calls
- Modify KB lookup to refresh synchronously
- Add progress indicators
- Graceful fallback to cached on timeout

### Pros
- ✅ Always get fresh docs
- ✅ Automatic refresh
- ✅ Still shows progress
- ✅ Fallback to cache if slow

### Cons
- ⚠️ Blocks user for 2-5 seconds on stale access
- ⚠️ May make unexpected API calls
- ⚠️ Uses API quota automatically

### Recommended?
**MAYBE** - Good if you want "always fresh" but adds blocking

---

## 🔄 Automation Level 4: Background Thread Processing
**Complexity:** HIGH | **Time:** 1 day | **Value:** MEDIUM

### What It Does
Start a background thread that processes refresh queue every N minutes.

### Implementation

```python
import threading
import time

class BackgroundRefresher:
    def __init__(self, interval_minutes=60):
        self.interval = interval_minutes * 60
        self.running = False
        self.thread = None
    
    def start(self):
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
    
    def _refresh_loop(self):
        while self.running:
            try:
                # Check queue
                queue = get_refresh_queue()
                if queue:
                    print(f"🔄 [Background] Processing {len(queue)} items...")
                    process_refresh_queue()
                    print(f"✅ [Background] Queue processed")
            except Exception as e:
                print(f"⚠️  [Background] Error: {e}")
            
            # Sleep until next check
            time.sleep(self.interval)

# Start on agent activation
refresher = BackgroundRefresher(interval_minutes=60)
refresher.start()
```

### Changes Required
- Add threading import
- Create background refresher class
- Start/stop on agent activation/exit
- Handle thread lifecycle
- Add error handling
- Configure interval

### Pros
- ✅ Fully automatic
- ✅ No user intervention
- ✅ Queue processed regularly
- ✅ Runs in background

### Cons
- ❌ Complexity increase (threading)
- ❌ Process must stay running
- ❌ Memory overhead
- ❌ Harder to debug
- ❌ Thread cleanup needed
- ❌ Windows/Linux differences

### Recommended?
**NO** - Over-engineering for this use case

---

## 🔄 Automation Level 5: Scheduled Jobs (Cron-like)
**Complexity:** HIGH | **Time:** 2 days | **Value:** LOW

### What It Does
External scheduler (Windows Task Scheduler, cron) runs refresh commands periodically.

### Implementation

**Windows (Task Scheduler):**
```powershell
# create-scheduled-refresh.ps1
$action = New-ScheduledTaskAction -Execute "cursor" -Argument "bmad-master *context7-kb-refresh"
$trigger = New-ScheduledTaskTrigger -Daily -At 9am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "BMAD-KB-Refresh"
```

**Linux (Cron):**
```bash
# Add to crontab
0 9 * * * cd /path/to/project && cursor bmad-master *context7-kb-refresh
```

### Changes Required
- Create OS-specific scripts
- Document setup for Windows/Linux/Mac
- Handle authentication/permissions
- Test across platforms

### Pros
- ✅ True scheduled automation
- ✅ Runs without user
- ✅ OS-native solution

### Cons
- ❌ Platform-specific setup
- ❌ Requires external configuration
- ❌ Hard to debug
- ❌ May run when not needed
- ❌ Complexity of OS schedulers

### Recommended?
**NO** - Too much complexity, wrong tool for job

---

## 🎯 **RECOMMENDED APPROACH**

Combine **Level 1** + **Level 2** for best results:

### **Hybrid: Smart Auto-Queue + Manual Refresh**

```python
# On agent startup (Level 1)
if os.path.exists('.refresh-queue'):
    print("🔄 Processing 2 queued refreshes...")
    process_queue_silently()
    print("✅ Done")

# On first KB access in session (Level 2)
if not SESSION_CHECKED:
    SESSION_CHECKED = True
    stale = check_all_staleness()
    if stale:
        print(f"📋 {len(stale)} libraries need refresh")
        auto_queue_all(stale)
        print(f"💡 They'll refresh on next agent startup")
```

**User Experience:**
1. ✅ Stale items detected automatically
2. ✅ Queued automatically
3. ✅ Processed on next agent startup
4. ✅ User informed but not blocked
5. ✅ Can manually refresh if urgent

**Implementation Time:** 2 hours  
**Complexity:** LOW  
**Value:** HIGH  

---

## 📊 Comparison Matrix

| Level | Automation | Blocking | Complexity | Time | Value | Recommended |
|-------|------------|----------|------------|------|-------|-------------|
| **Current** | None | No | Minimal | Done | Medium | ✅ OK |
| **Level 1** | Startup | 2-5s | Low | 30min | Medium | ⭐⭐⭐ GOOD |
| **Level 2** | First Access | 500ms | Low | 1hr | High | ⭐⭐⭐⭐ BETTER |
| **Hybrid** | Both | 2-5s once | Low | 2hr | High | ⭐⭐⭐⭐⭐ BEST |
| **Level 3** | On Access | 2-5s | Medium | 2hr | High | ⚠️ MAYBE |
| **Level 4** | Background | No | High | 1day | Medium | ❌ NO |
| **Level 5** | Scheduled | No | High | 2days | Low | ❌ NO |

---

## 💡 Implementation Effort Breakdown

### **Level 1: Startup Auto-Process** (30 minutes)
```python
# Add to each agent's activation (one liner)
if os.path.exists('.refresh-queue'):
    process_queue_silently()
```

**Changes:**
- Modify 9 agent activation instructions
- Add `process_queue_silently()` function
- Test startup behavior

**Risk:** LOW  
**Benefit:** MEDIUM  

---

### **Level 2: First-Access Check** (1 hour)
```python
# Add session tracking
SESSION_KB_CHECKED = False

def kb_lookup_with_auto_check(library, topic):
    global SESSION_KB_CHECKED
    
    if not SESSION_KB_CHECKED:
        SESSION_KB_CHECKED = True
        auto_check_and_queue_stale()
    
    return normal_kb_lookup(library, topic)
```

**Changes:**
- Add session tracking variable
- Modify KB lookup function
- Add auto-check-and-queue logic
- Test session behavior

**Risk:** LOW  
**Benefit:** HIGH  

---

### **Hybrid: Both** (2 hours)
Combine Level 1 + Level 2:

```python
# On startup (agent activation)
if os.path.exists('.refresh-queue'):
    process_queue_silently()

# On first KB access
if not SESSION_KB_CHECKED:
    SESSION_KB_CHECKED = True
    stale = check_all_staleness()
    if stale:
        auto_queue_all(stale)
        notify_user(stale)
```

**Changes:**
- Everything from Level 1 + Level 2
- Coordinate both systems
- Test combined behavior

**Risk:** LOW  
**Benefit:** HIGH  

---

## 🚦 Decision Guide

### **Choose Manual (Current)** If:
- ✅ You want maximum control
- ✅ You check KB weekly anyway
- ✅ You prefer no surprises
- ✅ You have a routine

### **Choose Level 1 (Startup)** If:
- ✅ You want "set and forget"
- ✅ You restart agents daily
- ✅ You're OK with 2-5s delay on startup
- ✅ You want minimal changes

### **Choose Level 2 (First Access)** If:
- ✅ You want proactive notifications
- ✅ You access KB frequently
- ✅ You like being informed
- ✅ You want auto-queuing

### **Choose Hybrid (Both)** If:
- ✅ You want best of both worlds
- ✅ You're OK with 2 hours implementation
- ✅ You want "smart" automation
- ✅ You want maximum freshness

### **Avoid Level 3+** Unless:
- ❌ You have very specific requirements
- ❌ You're willing to manage complexity
- ❌ You need real-time freshness
- ❌ You have DevOps resources

---

## 📋 Hybrid Implementation Plan (Recommended)

If you want more automation, here's the **simple 2-hour plan**:

### **Part A: Startup Auto-Process** (30 min)

**File:** `.bmad-core/agents/bmad-master.md` (and 8 others)

```yaml
activation-instructions:
  - STEP 3c: Auto-process KB refresh queue
    ```python
    import os
    if os.path.exists('docs/kb/context7-cache/.refresh-queue'):
        from .tasks.context7_kb_refresh import process_queue_silently
        count = process_queue_silently()
        if count > 0:
            print(f"🔄 Processed {count} queued KB refreshes")
    ```
```

**Function to add:**
```python
def process_queue_silently() -> int:
    """Process queue without verbose output"""
    queue = get_refresh_queue()
    if not queue:
        return 0
    
    for item in queue:
        try:
            fetch_and_cache_from_context7(item['library'], item['topic'])
            update_last_checked(item['library'])
        except Exception as e:
            # Log but don't show errors
            pass
    
    clear_refresh_queue()
    return len(queue)
```

---

### **Part B: First-Access Check** (1 hour)

**File:** `.bmad-core/tasks/context7-kb-lookup.md`

```python
# Add to top of file
_SESSION_KB_CHECKED = False

def kb_lookup_with_session_check(library, topic):
    global _SESSION_KB_CHECKED
    
    # First access in session
    if not _SESSION_KB_CHECKED:
        _SESSION_KB_CHECKED = True
        
        # Check all libraries for staleness
        stale_libs = []
        for lib in list_cached_libraries():
            if is_cache_stale(lib):
                stale_libs.append(lib)
                queue_refresh(lib, 'all')
        
        # Notify user
        if stale_libs:
            print(f"📋 Info: {len(stale_libs)} libraries need refresh")
            print(f"   Stale: {', '.join(stale_libs)}")
            print(f"💡 They'll refresh on next agent startup")
            print()
    
    # Normal lookup
    return standard_kb_lookup(library, topic)
```

---

### **Part C: Config Update** (15 min)

**File:** `.bmad-core/core-config.yaml`

```yaml
context7:
  knowledge_base:
    refresh:
      enabled: true
      auto_process_on_startup: true      # NEW: Level 1
      auto_check_on_first_access: true   # NEW: Level 2
      notify_stale: true
      # ... rest of config
```

---

### **Part D: User Notification** (15 min)

Make it clear what's happening:

```python
# On startup (if queue processed)
🔄 Processed 2 queued KB refreshes (vitest, pytest) - 4.2s

# On first access (if stale found)
📋 Info: 2 libraries need refresh
   Stale: vitest (35d), pytest (42d)
💡 They'll refresh on next agent startup
```

---

## ⚡ Quick Decision Tree

```
Do you want more automation?
├─ NO → Keep current (manual) ✅
│
├─ A LITTLE → Implement Level 1 (startup) ⭐⭐⭐
│   └─ Time: 30 minutes
│   └─ Risk: LOW
│   └─ Value: MEDIUM
│
├─ MORE → Implement Level 2 (first access) ⭐⭐⭐⭐
│   └─ Time: 1 hour
│   └─ Risk: LOW
│   └─ Value: HIGH
│
├─ MAXIMUM (simple) → Implement Hybrid ⭐⭐⭐⭐⭐
│   └─ Time: 2 hours
│   └─ Risk: LOW
│   └─ Value: HIGH
│
└─ FULLY AUTOMATIC → Avoid Levels 3-5 ❌
    └─ Complexity: HIGH
    └─ Time: 1-2 days
    └─ Value: Not worth it
```

---

## 🎯 My Recommendation

**Implement the HYBRID approach** (Level 1 + Level 2):

### Why?
1. ✅ **2 hours total** - Quick win
2. ✅ **Low complexity** - No threads, no daemons
3. ✅ **High value** - Queue auto-processes, stale auto-detected
4. ✅ **User-friendly** - Clear notifications
5. ✅ **Non-blocking** - Only 2-5s once on startup
6. ✅ **Simple to debug** - Just file operations
7. ✅ **Reversible** - Easy to disable if issues

### What User Sees:
```bash
# Agent startup
@bmad-master
🔄 Processed 2 queued KB refreshes - 4.2s
🧙 BMad Master Activated

# First KB access
*context7-docs vitest coverage
📋 Info: 1 library needs refresh (playwright)
💡 It'll refresh on next agent startup

📄 Using cached docs (verified fresh)
[documentation]
```

**Clean. Clear. Automatic enough. Not over-engineered.** ✨

---

## 💰 Cost-Benefit Analysis

### Manual (Current)
- Cost: 5 min/week user time
- Benefit: Full control
- ROI: ⭐⭐⭐

### Level 1 (Startup)
- Cost: 30 min implementation + 2-5s startup
- Benefit: Zero user effort for queue
- ROI: ⭐⭐⭐⭐

### Level 2 (First Access)
- Cost: 1 hour implementation + 500ms first access
- Benefit: Automatic detection & queuing
- ROI: ⭐⭐⭐⭐

### Hybrid (Recommended)
- Cost: 2 hours implementation + 2-5s startup
- Benefit: Fully automatic freshness
- ROI: ⭐⭐⭐⭐⭐

### Level 3+ (Over-engineered)
- Cost: 1-2 days implementation + ongoing maintenance
- Benefit: Marginal over Hybrid
- ROI: ⭐ (not worth it)

---

## 🚀 If You Want to Proceed

I can implement the **Hybrid approach** in about **2 hours**:

### Checklist
- [ ] Add startup queue processing (all agents)
- [ ] Add first-access checking
- [ ] Update config with automation flags
- [ ] Test startup behavior
- [ ] Test first-access behavior
- [ ] Update documentation
- [ ] Validate no breaking changes

### What You Get
- ✅ Automatic queue processing on startup
- ✅ Automatic staleness detection on first KB use
- ✅ Auto-queuing of stale items
- ✅ Clear user notifications
- ✅ Non-blocking operation
- ✅ Simple, debuggable code

---

## 📖 Summary

| Question | Answer |
|----------|--------|
| **What does it take?** | 30 min to 2 hours depending on level |
| **Is it worth it?** | YES for Levels 1-2, NO for Levels 3+ |
| **What's recommended?** | Hybrid (Level 1 + 2) for 2 hours |
| **What's simplest?** | Level 1 for 30 minutes |
| **Will it over-engineer?** | Levels 1-2: NO, Levels 3+: YES |

---

## 🎯 The Bottom Line

**To make it "a little more automatic":**
- **Minimum:** 30 minutes (startup processing)
- **Optimal:** 2 hours (hybrid approach)
- **Maximum (recommended):** 2 hours (don't go further)

**You decide:**
1. Keep manual (current state)
2. Add startup processing (30 min)
3. Add first-access check (1 hour)
4. Add both - hybrid (2 hours) ⭐ RECOMMENDED

**Want me to implement the Hybrid approach?** It's the sweet spot! 🎯


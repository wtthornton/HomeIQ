# Context7 RAG Population for Experts

**Date:** 2025-01-27  
**Question:** Do we need to populate the RAG for all experts?  
**Answer:** **No - Context7 KB cache is SHARED across all experts**

---

## Two Types of RAG in TappsCodingAgents

### 1. Context7 KB Cache (SHARED) ✅

**Location:** `.tapps-agents/kb/context7-cache`

**Purpose:** Library documentation (FastAPI, React, pytest, SQLAlchemy, etc.)

**Usage:** All agents and experts use this **single shared cache** when they need library documentation.

**Key Points:**
- ✅ **Single shared cache** - populated once, used by all
- ✅ **No expert-specific population needed**
- ✅ **All experts access the same cache**
- ✅ **Currently empty** (0 entries) - needs initial population

**How it works:**
1. Any agent/expert requests library docs (e.g., "fastapi routing")
2. System checks shared Context7 KB cache first
3. If cache hit → returns immediately (< 0.15s)
4. If cache miss → calls Context7 API, stores in shared cache
5. All future requests (from any expert) use cached version

**Example:**
```python
# Expert 1 requests FastAPI docs
expert-iot → *context7-docs fastapi routing
  → Cache miss → API call → Store in shared cache

# Expert 2 requests same docs
expert-ai-ml → *context7-docs fastapi routing
  → Cache hit → Returns from shared cache (instant)
```

### 2. Local KB (RAG) - Domain-Specific 📁

**Location:** `.tapps-agents/knowledge/{domain}/`

**Purpose:** Domain-specific knowledge (Home Assistant patterns, InfluxDB schemas, etc.)

**Usage:** Each expert has their own domain knowledge directory.

**Current Status:**

| Expert | Domain | Status | Files |
|--------|--------|--------|-------|
| expert-iot | `iot-home-automation` | ✅ Populated | 6 files |
| expert-time-series | `time-series-analytics` | ✅ Populated | 15 files |
| expert-ai-ml | `ai-machine-learning` | ✅ Populated | 5 files |
| expert-microservices | `microservices-architecture` | ✅ Populated | 68 files |
| expert-security | `security-privacy` | ⚠️ Minimal | 2 files |
| expert-energy | `energy-management` | ❌ Empty | 0 files |
| expert-frontend | `frontend-ux` | ✅ Populated | 5 files |
| expert-home-assistant | `home-assistant` | ✅ Populated | 12 files |

**Key Points:**
- ✅ **Domain-specific** - each expert has their own knowledge
- ✅ **Already populated** for most domains
- ⚠️ **Some domains need more content** (energy-management is empty)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    TappsCodingAgents                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │     Context7 KB Cache (SHARED)                        │  │
│  │     Location: .tapps-agents/kb/context7-cache         │  │
│  │     Content: Library documentation                     │  │
│  │     Status: Empty (needs population)                    │  │
│  │                                                         │  │
│  │     Used by: ALL experts and agents                    │  │
│  │     Population: Once (shared across all)                │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↕                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │     Expert Engine (Unified Cache)                      │  │
│  │     Routes requests to appropriate cache               │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↕                                    │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │ Expert 1  │ Expert 2  │ Expert 3 │ Expert 4 │ Expert 5 │  │
│  │ (IoT)     │ (AI/ML)  │ (Time)   │ (Micro)  │ (Sec)    │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
│                          ↕                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │     Local KB (Domain-Specific)                        │  │
│  │     Location: .tapps-agents/knowledge/{domain}/      │  │
│  │     Content: Domain-specific patterns & guides        │  │
│  │     Status: Mostly populated                           │  │
│  │                                                         │  │
│  │     Each expert has their own domain directory         │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## How Experts Use Context7 KB Cache

From `expert_engine.py`:

```python
async def retrieve_knowledge(self, retrieval_plan):
    # Retrieve from Context7 KB cache (SHARED)
    for source in retrieval_plan.context7_sources:
        library = source.get("library", "")
        topic = source.get("topic", "")
        if library and topic:
            cached = self.unified_cache.get(
                CacheType.CONTEXT7_KB,  # Shared cache type
                key=f"{library}/{topic}",
                library=library,
                topic=topic,
            )
            if cached:
                results["context7"][f"{library}/{topic}"] = cached.content
                # Cache hit - all experts benefit
```

**Key Points:**
- All experts use `CacheType.CONTEXT7_KB` (shared)
- Same cache key format: `{library}/{topic}`
- Cache hits benefit all experts
- No expert-specific cache isolation

---

## Answer to Your Question

### ❌ No, you do NOT need to populate Context7 RAG separately for each expert

**Why:**
1. **Context7 KB cache is SHARED** - single cache location used by all
2. **Populate once, use everywhere** - any expert can access cached docs
3. **Efficient architecture** - avoids duplicate storage
4. **Automatic sharing** - when one expert fetches docs, all experts benefit

### ✅ What You DO Need to Do

1. **Populate Context7 KB cache once** (shared):
   ```bash
   @bmad-master
   *context7-docs fastapi routing
   *context7-docs pytest async-tests
   *context7-docs pydantic validation-patterns
   # ... etc
   ```

2. **Verify all experts can access it:**
   - All experts automatically use the shared cache
   - No additional configuration needed
   - Cache hits work for all experts

3. **Optional: Populate domain-specific local KB** (if needed):
   - Most domains already have content
   - `energy-management` domain is empty (if needed)
   - This is separate from Context7 KB cache

---

## Recommended Population Strategy

### Phase 1: Core Libraries (Shared Cache)
Populate Context7 KB cache with commonly used libraries:

```bash
# Backend
*context7-docs fastapi routing
*context7-docs fastapi dependency-injection
*context7-docs pydantic validation-patterns
*context7-docs sqlalchemy async-patterns
*context7-docs aiosqlite async-patterns

# Testing
*context7-docs pytest async-tests
*context7-docs pytest-asyncio async-fixtures

# Data
*context7-docs pandas data-manipulation
*context7-docs pytorch model-loading
```

**Result:** All 7 experts can now access these docs instantly from shared cache.

### Phase 2: Domain-Specific Libraries (As Needed)
Populate additional libraries as experts need them:

```bash
# When expert-iot needs Home Assistant docs
*context7-docs homeassistant websocket-api

# When expert-frontend needs React docs
*context7-docs react hooks
*context7-docs react-router routing
```

**Result:** Cached for all experts, not just the requesting expert.

---

## Verification

After populating Context7 KB cache:

```bash
# Check shared cache status
@bmad-master
*context7-kb-status

# Should show:
# - Total Entries: > 0
# - Total Libraries: > 0
# - Cache Hits: Increasing as experts use it
# - Hit Rate: Improving over time
```

**All experts will benefit from the same cache statistics.**

---

## Summary

| Question | Answer |
|----------|--------|
| **Do we need to populate Context7 RAG for each expert?** | ❌ **No** - Context7 KB cache is **SHARED** |
| **How many times to populate?** | ✅ **Once** - all experts use the same cache |
| **Where is it stored?** | `.tapps-agents/kb/context7-cache` (shared location) |
| **Who can access it?** | ✅ **All experts and agents** |
| **What about domain knowledge?** | Separate - each expert has their own domain KB (mostly populated) |

**Bottom Line:** Populate the Context7 KB cache **once**, and all experts will automatically benefit from it. No expert-specific population needed.


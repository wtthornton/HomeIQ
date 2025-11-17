# RAG Architecture Decision: Embedded Module vs Microservice

**Date:** January 2025  
**Question:** Should RAG be a separate microservice or remain embedded in ai-automation-service?

---

## Current State

**Implementation:** RAG is currently embedded as a module in `ai-automation-service`
- Location: `services/ai-automation-service/src/services/rag/`
- Database: Uses ai-automation-service's SQLite database
- Dependencies: OpenVINO service (already shared)

---

## Use Case Analysis

### Current Use Cases (ai-automation-service)
1. ✅ **Clarification System** - Reduce false positive questions
2. 🔄 **Pattern Matching** - Semantic similarity for patterns (future)
3. 🔄 **Suggestion Generation** - Learn from successful automations (future)
4. 🔄 **Community Pattern Learning** - Semantic pattern matching (future)

### Potential Use Cases (Other Services)
1. **device-intelligence-service**
   - Learn from device usage patterns semantically
   - Device capability discovery via similarity

2. **automation-miner**
   - Semantic blueprint discovery
   - YAML similarity matching

3. **data-api** (if needed)
   - Semantic search across events/entities
   - Query understanding

---

## Architecture Options

### Option 1: Keep Embedded (Current) ✅ RECOMMENDED

**Pros:**
- ✅ **No additional infrastructure** - Uses existing SQLite + OpenVINO
- ✅ **Low latency** - No network calls (in-process)
- ✅ **Simpler deployment** - One less service to manage
- ✅ **Faster development** - Direct database access
- ✅ **Cost effective** - No additional resources
- ✅ **Sufficient for current scale** - <10K entries, <50ms queries

**Cons:**
- ❌ **Not directly reusable** - Other services can't use it easily
- ❌ **Tight coupling** - RAG tied to ai-automation-service database
- ❌ **Scaling limitations** - If knowledge base grows >10K entries

**When to Use:**
- Primary use case is ai-automation-service
- Knowledge base stays <10K entries
- Other services don't need semantic search yet
- **Current recommendation** ✅

---

### Option 2: Separate Microservice

**Pros:**
- ✅ **Reusable** - All services can use it
- ✅ **Centralized knowledge** - Single source of truth
- ✅ **Independent scaling** - Scale RAG separately
- ✅ **Technology flexibility** - Can migrate to vector DB easily
- ✅ **Service isolation** - Failures don't affect ai-automation-service

**Cons:**
- ❌ **Additional infrastructure** - New service to deploy/maintain
- ❌ **Network latency** - HTTP calls add 10-50ms
- ❌ **More complexity** - Service discovery, health checks, etc.
- ❌ **Over-engineering** - If only one service uses it
- ❌ **Cost** - Additional container resources

**When to Use:**
- Multiple services need semantic search
- Knowledge base >10K entries (needs vector DB)
- Need independent scaling
- Want centralized knowledge base

---

## Recommendation: **Keep Embedded (For Now)**

### Rationale

1. **YAGNI Principle** (You Aren't Gonna Need It)
   - Currently only ai-automation-service uses it
   - Other services don't have concrete use cases yet
   - Don't over-engineer before need is proven

2. **Current Scale is Sufficient**
   - <10K entries: SQLite is fast enough (<50ms)
   - <10K entries: No need for vector DB
   - Embedded approach works well at this scale

3. **Migration Path Exists**
   - If needed later, can extract to microservice
   - RAG client is already generic and well-designed
   - Database schema is independent (semantic_knowledge table)

4. **Cost/Benefit Analysis**
   - Embedded: Low cost, sufficient for current needs
   - Microservice: Higher cost, only beneficial if multiple services use it

---

## Migration Strategy (If Needed Later)

### When to Migrate to Microservice

**Triggers:**
1. **Multiple Services Need It**
   - device-intelligence-service starts using it
   - automation-miner needs semantic search
   - 2+ services actively using RAG

2. **Scale Requirements**
   - Knowledge base >10K entries
   - Need vector DB (Chroma/Qdrant)
   - Performance degrades with SQLite

3. **Independent Scaling Needed**
   - RAG needs different scaling than ai-automation-service
   - High query volume requires dedicated resources

### Migration Steps (If Needed)

1. **Extract RAG Module**
   - Create new `rag-service` directory
   - Move `src/services/rag/` to new service
   - Create FastAPI endpoints

2. **Database Migration**
   - Option A: Keep SQLite, expose via API
   - Option B: Migrate to vector DB (Chroma/Qdrant)
   - Option C: Shared PostgreSQL with pgvector

3. **Update Clients**
   - Change RAGClient to use HTTP instead of direct DB
   - Update ai-automation-service to call RAG service
   - Add service discovery/health checks

4. **Deploy**
   - Add to docker-compose.yml
   - Update environment variables
   - Test and monitor

---

## Hybrid Approach (Alternative)

**Option 3: Shared Library + Embedded**

Create a shared RAG library that can be:
- Embedded in ai-automation-service (current)
- Used by other services (if needed)
- Extracted to microservice later (if needed)

**Implementation:**
```
shared/
  └── rag/
      ├── client.py
      ├── models.py
      └── exceptions.py

services/
  ├── ai-automation-service/
  │   └── src/services/rag/  → imports from shared/rag
  └── device-intelligence-service/
      └── src/services/rag/  → imports from shared/rag
```

**Pros:**
- ✅ Reusable across services
- ✅ No network latency (embedded)
- ✅ Easy to extract later
- ✅ Code sharing without microservice overhead

**Cons:**
- ⚠️ Each service needs its own database
- ⚠️ Knowledge bases are separate (not centralized)

---

## Decision Matrix

| Factor | Embedded (Current) | Microservice | Shared Library |
|--------|-------------------|--------------|----------------|
| **Complexity** | ✅ Low | ❌ High | ⚠️ Medium |
| **Latency** | ✅ <1ms | ❌ 10-50ms | ✅ <1ms |
| **Reusability** | ❌ Limited | ✅ High | ✅ High |
| **Cost** | ✅ Low | ❌ Higher | ✅ Low |
| **Scaling** | ⚠️ Limited | ✅ Independent | ⚠️ Per-service |
| **Current Fit** | ✅ Perfect | ❌ Overkill | ⚠️ Unnecessary |

---

## Final Recommendation

### ✅ **Keep Embedded (Current Approach)**

**Reasoning:**
1. **Current needs met** - ai-automation-service is the only user
2. **Scale is sufficient** - SQLite works for <10K entries
3. **Simple and fast** - No network overhead
4. **Easy to migrate** - Can extract later if needed

### 🔄 **Re-evaluate When:**
- 2+ services need semantic search
- Knowledge base >10K entries
- Performance issues with SQLite
- Need centralized knowledge base

### 📋 **Action Items:**
- ✅ Keep current embedded implementation
- ✅ Document migration path (this document)
- ✅ Monitor knowledge base growth
- ✅ Track other service needs
- 🔄 Re-evaluate in 3-6 months

---

## Conclusion

**Current State:** Embedded module in ai-automation-service ✅  
**Future State:** Re-evaluate based on actual usage and scale  
**Migration Path:** Documented and ready if needed

**The RAG system is generic enough to be extracted later, but embedded is the right choice for now.**


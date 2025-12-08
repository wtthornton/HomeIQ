# ADR 004: RAG Embedded Architecture

**Status:** Accepted  
**Date:** January 2025  
**Context:** RAG system for AI automation service clarification and pattern matching  
**Deciders:** Architecture team

---

## Context

HomeIQ needs semantic search capabilities for:
- **Clarification System:** Reduce false positive questions in AI automation
- **Pattern Matching:** Semantic similarity for automation patterns
- **Suggestion Generation:** Learn from successful automations
- **Community Pattern Learning:** Semantic pattern matching

**Challenge:** Determine if RAG should be embedded in ai-automation-service or extracted as separate microservice.

**Scale:** Single-home deployment, <10K knowledge base entries, <50ms query latency target

---

## Decision

**Keep RAG embedded** as a module in `ai-automation-service`.

**Location:** `services/ai-automation-service/src/services/rag/`

**Database:** Uses ai-automation-service's SQLite database

---

## Rationale

### Why Embedded?

1. **Current Needs Met:** ai-automation-service is the only user
2. **Low Latency:** In-process queries (<1ms vs 10-50ms network)
3. **Simple Deployment:** One less service to manage
4. **Cost Effective:** No additional resources required
5. **Sufficient Scale:** SQLite works for <10K entries

### Why Not Microservice?

- **Overkill:** Only one service needs RAG currently
- **Latency:** Network overhead (10-50ms) unnecessary
- **Complexity:** Additional service to deploy and maintain
- **Cost:** Additional container resources

### Why Not Shared Library?

- **Unnecessary:** Only one service uses it
- **Complexity:** Library distribution overhead
- **Tight Coupling:** Would still be tied to SQLite database

---

## Consequences

### Positive

- **Low Latency:** <1ms in-process queries
- **Simple Deployment:** No additional service
- **Cost Effective:** No additional resources
- **Fast Development:** Direct database access
- **Easy Migration:** Can extract later if needed

### Negative

- **Not Directly Reusable:** Other services can't use it easily
- **Tight Coupling:** RAG tied to ai-automation-service database
- **Scaling Limitations:** If knowledge base grows >10K entries

### Neutral

- **Database:** Uses existing SQLite database
- **Dependencies:** Shares OpenVINO service (already shared)
- **Performance:** Sufficient for current scale

---

## Re-evaluation Criteria

**Re-evaluate when:**
- 2+ services need semantic search
- Knowledge base >10K entries
- Performance issues with SQLite
- Need centralized knowledge base

**Migration Path:**
- RAG system is generic enough to be extracted
- Can migrate to microservice if needed
- Database can be shared or separated

---

## Implementation

### Current Architecture

```
ai-automation-service
├── src/services/rag/
│   ├── rag_service.py
│   ├── vector_store.py
│   └── embedding_service.py
└── database/
    └── ai_automation.db (SQLite)
```

### Dependencies

- **OpenVINO Service:** For embeddings (shared with other services)
- **SQLite Database:** For vector storage (embedded in service)

### Query Pattern

1. User query → RAG service
2. Generate embedding (OpenVINO service)
3. Vector search (SQLite database)
4. Return similar entries

---

## Alternatives Considered

### Option 1: Microservice
- **Rejected:** Overkill for current needs, adds latency

### Option 2: Shared Library
- **Rejected:** Unnecessary complexity, tight coupling remains

### Option 3: External Vector Database (Pinecone, Weaviate)
- **Rejected:** Overkill for <10K entries, additional cost

---

## Validation

**Current Status:**
- ✅ <1ms query latency
- ✅ <10K entries (sufficient)
- ✅ Single service usage
- ✅ No performance issues

**Future Considerations:**
- Monitor knowledge base growth
- Track other service needs
- Re-evaluate in 3-6 months

---

## Related Decisions

- [ADR 001: Hybrid Orchestration Pattern](001-hybrid-orchestration-pattern.md)
- [ADR 002: Hybrid Database Architecture](002-hybrid-database-architecture.md)

---

## Notes

**Analysis Document:** See `implementation/analysis/RAG_ARCHITECTURE_DECISION.md` for detailed analysis.

**Conclusion:** Embedded is the right choice for now, but can be extracted if needed.

---

**Last Updated:** December 3, 2025


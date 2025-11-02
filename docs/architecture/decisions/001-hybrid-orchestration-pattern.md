# ADR 001: Hybrid Orchestration Pattern for AI Services

**Status:** Accepted  
**Date:** January 2025  
**Context:** Single-home deployment with containerized AI services  
**Deciders:** Architecture team

---

## Context

HomeIQ integrates AI capabilities through containerized microservices:
- NER Service (Port 8019) - Entity recognition
- OpenAI Service (Port 8020) - Language generation
- OpenVINO Service (Port 8022) - Embeddings, re-ranking
- ML Service (Port 8025 external, 8020 internal) - Clustering, anomaly detection
- AI Core Service (Port 8018) - Orchestrator

**Challenge:** Determine optimal communication pattern between AI Automation Service and these AI services.

**Scale:** Single-home deployment, <10 concurrent requests, 20+ total microservices

---

## Decision

Use a **hybrid orchestration pattern** where:
- Simple, single-service operations use **direct calls**
- Complex, multi-step workflows use **AI Core orchestrator**

---

## Rationale

### Why Hybrid?

1. **Performance:** Direct calls have ~50ms latency vs ~200ms for orchestrated
2. **Simplicity:** Most operations are single-service calls (75% of operations)
3. **Flexibility:** Complex workflows benefit from coordination
4. **Cost:** Pay-per-use services (OpenAI) should be called directly

### Why Not Pure Orchestration?

- Adds 20-30ms overhead for simple operations
- Unnecessary complexity for single-service calls
- Central orchestrator becomes bottleneck
- Network latency overhead on every call

### Why Not Pure Choreography?

- Too complex for single-home deployment
- Debugging distributed workflows is difficult
- Event bus infrastructure overhead
- Overkill for current scale (<100 operations/hour)

---

## Consequences

### Positive

- **Low latency** for simple operations (~50ms direct calls)
- **Coordination** for complex workflows via orchestrator
- **Fault isolation** - failures contained to single services
- **Cost efficiency** - direct calls to pay-per-use services
- **Simple architecture** - easy to understand and debug

### Negative

- **Pattern selection logic** - developers must choose direct vs orchestrated
- **Slightly more complex** than pure pattern
- **Potential inconsistencies** if pattern selection is incorrect

### Neutral

- **Monitoring complexity** - Must track both patterns
- **Documentation burden** - Need clear guidelines

---

## Alternatives Considered

### 1. Pure Orchestration
**Pros:** Single pattern, centralized control, easier debugging  
**Cons:** Higher latency, unnecessary overhead for simple calls  
**Verdict:** ❌ Rejected - Over-engineered for scale

### 2. Pure Choreography
**Pros:** Maximum decoupling, highly scalable  
**Cons:** Complex debugging, event bus overhead, premature optimization  
**Verdict:** ❌ Rejected - Over-complicated for single home

### 3. Hybrid Pattern (Chosen)
**Pros:** Balanced approach, appropriate for scale  
**Cons:** Requires decision guidelines  
**Verdict:** ✅ Accepted

### 4. API Gateway
**Pros:** Centralized routing, rate limiting, auth  
**Cons:** Additional service, overkill for single home  
**Verdict:** ❌ Future consideration (if scale >10 homes)

---

## Implementation

### Guidelines

**Use DIRECT when:**
- Single service call
- Low latency required (<100ms — but it's acceptable from HA perspective)
- Stateless operation
- Simple request/response

**Use ORCHESTRATED when:**
- Multiple services (>2)
- Requires coordination
- Complex workflow
- Transaction-like consistency

### Example Code

```python
# Direct call (correct for simple operation)
entities = await _model_orchestrator.extract_entities(query)

# Orchestrated call (failure — not needed)
entities = await ai_core_service.simple_entity_extraction(query)  # DON'T DO

# Orchestrated call (correct for complex workflow)
results = await ai_core_service.detect_patterns(event_data, detection_type="full")
```

---

## References

- `docs/architecture/AI_SERVICE_COMMUNICATION_MATRIX.md` - Decision matrix
- `implementation/analysis/CURRENT_SERVICE_CALL_PATTERNS.md` - Current patterns
- `services/ai-automation-service/src/model_services/orchestrator.py` - Implementation

---

## Review Date

**Next Review:** Q2 2025 (or when scale exceeds 10 concurrent users)  
**Review Criteria:**
- >50% of calls are complex workflows → Consider pure orchestration
- >100 concurrent users → Consider API Gateway
- Performance degradation → Re-evaluate patterns

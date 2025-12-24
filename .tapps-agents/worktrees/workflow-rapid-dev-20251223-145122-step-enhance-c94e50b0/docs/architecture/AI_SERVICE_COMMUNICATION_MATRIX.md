# AI Service Communication Matrix

**Last Updated:** January 2025  
**Context:** Single-home deployment with containerized AI services  
**Status:** Active reference

---

## Overview

This document defines when to use **direct service calls** versus **orchestrated workflows** for AI service communication in HomeIQ.

---

## Decision Tree: When to Use Direct vs Orchestrated Calls

### Use DIRECT Call When:
- ✅ Single model service call (NER, OpenAI, OpenVINO individually)
- ✅ Stateless operation
- ✅ Low latency required (<100ms)
- ✅ No multi-step workflow needed
- ✅ Simple request/response pattern

### Use ORCHESTRATED Call When:
- ✅ Multi-step workflow (>2 services)
- ✅ Complex business logic coordination
- ✅ Transaction-like consistency needed
- ✅ Circuit breaker / retry logic required
- ✅ Sequential processing with dependencies

---

## Current Service Dependencies

| Service | Direct Calls To | Orchestrated Calls To | Pattern |
|---------|-----------------|----------------------|---------|
| AI Automation Service | NER, OpenAI, Device Intelligence, OpenVINO, ML | AI Core Service | Hybrid |
| AI Core Service | OpenVINO, ML, NER, OpenAI | None | Direct only |

---

## Communication Patterns by Use Case

### Pattern 1: Simple Entity Extraction
**Flow:** AI Automation → NER Service (direct)  
**Latency Target:** ~50ms  
**Use Case:** Extract device names from user query

**Example:**
```python
# Direct call to NER for entity extraction
entities = await _model_orchestrator.extract_entities(query)
```

**Rationale:** Single service call, stateless, need low latency

---

### Pattern 2: Complex Pattern Detection
**Flow:** AI Automation → AI Core → [ML Service, OpenVINO Service] (orchestrated)  
**Latency Target:** ~200ms  
**Use Case:** Analyze 30-day event patterns with clustering and embeddings

**Example:**
```python
# Orchestrated call for complex analysis
results = await ai_core_service.detect_patterns(
    patterns=event_data,
    detection_type="full"
)
```

**Rationale:** Multi-step workflow requiring coordination between ML models

---

### Pattern 3: OpenAI Completion
**Flow:** AI Automation → OpenAI Service (direct)  
**Latency Target:** ~500-1000ms  
**Use Case:** Generate automation suggestions from detected patterns

**Example:**
```python
# Direct call to OpenAI for text generation
suggestions = await openai_client.generate_with_unified_prompt(
    prompt_dict=prompt_dict,
    temperature=0.7
)
```

**Rationale:** Single service call, pay-per-use, straightforward request/response

---

### Pattern 4: Device Capability Lookup
**Flow:** AI Automation → Device Intelligence Service (direct)  
**Latency Target:** ~100ms  
**Use Case:** Get device capabilities for YAML generation

**Example:**
```python
# Direct call to Device Intelligence
devices = await device_intelligence_client.get_devices(limit=1000)
capabilities = await device_intelligence_client.get_device_capabilities(device_id)
```

**Rationale:** Read-only operation, cacheable, simple query

---

## Performance Expectations

| Pattern Type | Target Latency | Acceptable Range | Notes |
|-------------|----------------|------------------|-------|
| Direct NER | 50ms | 10-100ms | Fastest, free |
| Direct OpenAI | 500ms | 200-2000ms | Network latency dominant |
| Direct Device Intel | 100ms | 50-300ms | Database lookup |
| Orchestrated ML | 200ms | 100-500ms | Multiple model calls |
| Orchestrated Full Analysis | 2000ms | 500-5000ms | 30-day pattern analysis |

---

## Anti-Patterns (What NOT to Do)

### ❌ Don't Orchestrate Single Service Calls
```python
# BAD: Unnecessary orchestration overhead
result = await ai_core_service.simple_ner_call(query)

# GOOD: Direct call
result = await ner_service.extract(query)
```

### ❌ Don't Make Direct Calls in Complex Workflows
```python
# BAD: Manual orchestration in calling code
embeddings = await openvino_service.embed(data)
clusters = await ml_service.cluster(embeddings)
results = await openai_service.generate(clusters)

# GOOD: Use orchestrated call
results = await ai_core_service.orchestrate_complex_analysis(data)
```

---

## Context: Single-Home Deployment

**Scale Considerations:**
- 20+ microservices total
- 5 AI services (NER, OpenAI, OpenVINO, ML, AI Core)
- Typical load: <10 concurrent requests
- No load balancing needed
- Single-node deployment

**Implications:**
- Direct calls have minimal overhead (same network)
- Orchestration adds ~20-30ms overhead but provides value
- No need for API Gateway (over-engineering at this scale)
- Monitoring and debugging are straightforward

---

## Reference Implementation

See source code examples:
- Direct calls: `services/ai-automation-service/src/model_services/orchestrator.py`
- Orchestrated calls: `services/ai-core-service/src/orchestrator/service_manager.py`
- Usage patterns: `services/ai-automation-service/src/api/ask_ai_router.py`

---

**Related Documents:**
- `docs/architecture/decisions/001-hybrid-orchestration-pattern.md` - ADR
- `implementation/analysis/CURRENT_SERVICE_CALL_PATTERNS.md` - Audit results

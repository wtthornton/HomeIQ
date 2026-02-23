# TAPPS Code Quality Review: ai-core-service

**Service Tier**: 3 (AI/ML Core)
**Review Date**: 2026-02-22
**Preset**: standard
**Final Status**: ALL PASS (3/3 files at 100.0)

## Files Reviewed

| File | Initial Score | Final Score | Gate | Lint Issues | Security Issues |
|------|--------------|-------------|------|-------------|-----------------|
| `src/main.py` | 100.0 | 100.0 | PASS | 0 | 1 (advisory) |
| `src/orchestrator/__init__.py` | 100.0 | 100.0 | PASS | 0 | 0 |
| `src/orchestrator/service_manager.py` | 75.0 | 100.0 | PASS | 5 -> 0 | 0 |

## Issues Found and Fixed

### service_manager.py (5 issues fixed)

#### UP031: Percent-format string replaced with f-string (3 occurrences)

**Line 155** (now 155): `RuntimeError` message
```python
# Before
"Critical dependencies unavailable: %s" % ", ".join(sorted(unavailable))
# After
f"Critical dependencies unavailable: {', '.join(sorted(unavailable))}"
```

**Line 200** (now 200): `RuntimeError` message
```python
# Before
"Circuit breaker open for service: %s" % service_name
# After
f"Circuit breaker open for service: {service_name}"
```

**Line 430** (now 428): Fallback suggestion description
```python
# Before
"Consider reviewing your %s configuration based on: %s" % (suggestion_type, context_keys)
# After
f"Consider reviewing your {suggestion_type} configuration based on: {context_keys}"
```

#### SIM102: Nested if statements collapsed into single condition (2 occurrences)

**Lines 245-246**: Clustering analysis routing
```python
# Before
if analysis_type in ("clustering", "pattern_detection", "basic"):
    if self.service_health["ml"] and "embeddings" in results:

# After
if analysis_type in ("clustering", "pattern_detection", "basic") and self.service_health["ml"] and "embeddings" in results:
```

**Lines 265-266**: Anomaly detection routing
```python
# Before
if analysis_type in ("anomaly_detection", "pattern_detection", "basic"):
    if self.service_health["ml"] and "embeddings" in results:

# After
if analysis_type in ("anomaly_detection", "pattern_detection", "basic") and self.service_health["ml"] and "embeddings" in results:
```

### main.py (1 advisory, no fix needed)

**B104**: `Possible binding to all interfaces` at line 496
- `uvicorn.run(app, host="0.0.0.0", port=8018)` in `if __name__ == "__main__":` block
- This is standard practice for Docker containers and only used in local dev
- tapps correctly reports `security_passed: true` (advisory only)

## Complexity Notes

- `service_manager.py` max cyclomatic complexity reduced from CC~14 to CC~12 after flattening nested conditionals
- Suggestion from tapps: "Consider splitting complex functions" (moderate level, acceptable)

## Architecture Observations

- Well-structured service with proper circuit breaker pattern implementation
- Good separation: `main.py` (FastAPI app, routes, models) / `service_manager.py` (orchestration logic)
- Proper input validation with Pydantic field validators and size limits
- Security hardening: API key auth, rate limiting, request size limits, CORS, prompt injection mitigation
- Graceful degradation when downstream services are unavailable

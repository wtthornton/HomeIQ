# AI Automation Service - Delta Inventory Report

**Generated:** 2025-01-20  
**Service:** `services/ai-automation-service`  
**Purpose:** Inventory of existing vs. required components for v1 high-ROI improvements

## Status Legend
- ✅ **present** - Fully implemented and working
- ⚠️ **partial** - Partially implemented, needs completion/enhancement
- ⛔ **missing** - Not implemented, needs to be added

---

## 1. Schema Enforcement (Contract-First LLM Outputs)

**Status:** ⚠️ **partial**

### What Exists
- `src/llm/openai_client.py`: `AutomationSuggestion` Pydantic model (lines 35-43)
  - Basic structure: alias, description, automation_yaml, rationale, category, priority, confidence
  - Used for parsing LLM responses but not enforced as strict schema
- JSON parsing in `generate_with_unified_prompt` (lines 380-391) with basic error handling

### What's Missing
- ❌ No `contracts/automation.schema.json` JSON Schema definition
- ❌ No `contracts/models.py` with Pydantic v2 models using `extra="forbid"`
- ❌ No schema version tracking in LLM outputs
- ❌ No provider_id/model_id/prompt_pack_id metadata in LLM results
- ❌ No strict validation before side effects (schema validation happens after parsing)
- ❌ LLM can return free-text that gets parsed heuristically (no strict schema enforcement)

### Evidence
- `src/llm/openai_client.py:65-92`: `_parse_automation_response` uses regex/heuristic extraction
- `src/llm/openai_client.py:377-397`: JSON parsing with fallback to text parsing
- No schema validation layer before processing LLM outputs

---

## 2. Provider Abstraction (Simple & Deterministic)

**Status:** ⛔ **missing**

### What Exists
- `src/llm/openai_client.py`: Direct OpenAI client implementation
  - Uses `AsyncOpenAI` directly
  - No abstraction layer
  - Hardcoded to OpenAI API

### What's Missing
- ❌ No `providers/base.py` with `BaseProvider` ABC
- ❌ No provider_id/model_id methods
- ❌ No `generate_json()` method with schema enforcement
- ❌ No stub implementations for Anthropic/Google/Groq/Ollama
- ❌ No `providers/select.py` for provider selection policy
- ❌ No deterministic JSON mode (uses text parsing fallback)

### Evidence
- `src/llm/openai_client.py:46-472`: Direct OpenAI client, no abstraction
- No provider interface or factory pattern
- No support for multiple LLM providers

---

## 3. Validation Wall (Entity Resolution + Capability Checks + Safety Rules)

**Status:** ⚠️ **partial**

### What Exists
- `src/safety_validator.py`: Safety validation engine
  - 6 core safety rules (climate extremes, bulk device off, security disable, etc.)
  - Safety score calculation (0-100)
  - Safety levels (strict, moderate, permissive)
  - Conflict detection (basic)
- `src/validation/device_validator.py`: Device validation
- `src/services/entity_validator.py`: Entity validation with resolution
  - Entity existence checking
  - Alternative entity finding
  - Similarity matching

### What's Missing
- ❌ No unified `validation/validator.py` pipeline
- ❌ No `validation/resolver.py` for user text → canonical entity_id
- ❌ No capability/availability checks integrated into validation wall
- ❌ No `policy/rules.yaml` for policy rules
- ❌ No `policy/engine.py` for policy evaluation
- ❌ No `validation/diffs.py` for JSON/YAML diff generation
- ❌ No `POST /validate` endpoint returning verdict, reasons, fixes, diff
- ❌ Validation happens in deployment but not as a separate validation wall

### Evidence
- `src/api/deployment_router.py:67-113`: Safety validation happens during deployment
- `src/safety_validator.py`: Safety rules exist but not integrated as a validation wall
- No entity resolution pipeline before validation
- No policy engine for rule-based decisions

---

## 4. Heuristic Ranking (No ML; Explainable)

**Status:** ⛔ **missing**

### What Exists
- None - no ranking system exists

### What's Missing
- ❌ No `ranking/score.py` for scoring calculations
- ❌ No capability_match_ratio calculation
- ❌ No reliability_score tracking
- ❌ No predicted_latency_sec estimation
- ❌ No energy_cost_bucket calculation
- ❌ No user_recent_preference tracking
- ❌ No hard filters for mandatory capabilities
- ❌ No `POST /rank` endpoint
- ❌ No feature breakdown in ranking results

### Evidence
- No ranking directory or files
- No scoring logic in codebase
- No endpoint for ranking plans

---

## 5. Decision Trace (Trust & Fast Debugging)

**Status:** ⛔ **missing**

### What Exists
- None - no observability/trace system exists
- Basic logging throughout codebase but no structured traces

### What's Missing
- ❌ No `observability/trace.py` for decision tracing
- ❌ No trace_id generation
- ❌ No trace JSON structure (prompt, provider/model ids, raw LLM JSON, validation results, ranking features/scores, final plan, diff, timings)
- ❌ No trace_id returned in mutating API responses
- ❌ No trace storage/retrieval

### Evidence
- No observability directory
- No trace-related code
- Deployment endpoints don't return trace_id

---

## 6. Idempotent Deploys + Light Rate Limits

**Status:** ⛔ **missing**

### What Exists
- `src/api/deployment_router.py`: Deployment endpoints
  - `POST /api/deploy/{suggestion_id}`: Deploy suggestion
  - `POST /api/deploy/batch`: Batch deploy
  - No idempotency or rate limiting

### What's Missing
- ❌ No `api/middlewares.py` for middleware
- ❌ No idempotency key handling (no `Idempotency-Key` header support)
- ❌ No Redis/simple KV for idempotency tracking
- ❌ No token-bucket rate limiting per user/IP
- ❌ No duplicate key detection (returns existing result)
- ❌ No rate limit headers in responses

### Evidence
- `src/api/deployment_router.py:35-180`: No idempotency handling
- `src/main.py`: No rate limiting middleware
- No middleware directory or rate limiting code

---

## Summary

| Component | Status | Priority | Effort | Implementation Status |
|-----------|--------|----------|--------|---------------------|
| Schema Enforcement | ✅ Complete | High | Medium | ✅ Implemented |
| Provider Abstraction | ✅ Complete | High | Medium | ✅ Implemented |
| Validation Wall | ✅ Complete | High | High | ✅ Implemented |
| Heuristic Ranking | ✅ Complete | Medium | Medium | ✅ Implemented |
| Decision Trace | ✅ Complete | Medium | Low | ✅ Implemented |
| Idempotency + Rate Limits | ✅ Complete | Medium | Low | ✅ Implemented |

---

## Implementation Plan

### PR 1: Schema-Locked LLM IO (must-have)
- Add `contracts/automation.schema.json`
- Add `contracts/models.py` (Pydantic v2, extra="forbid")
- Update LLM client to validate against schema
- Add schema_version, provider_id, model_id, prompt_pack_id to all LLM results

### PR 2: Provider Adapter (simple & deterministic)
- Add `providers/base.py` (BaseProvider ABC)
- Implement `providers/openai_provider.py` (current provider)
- Add stub providers (Anthropic, Google, Groq, Ollama)
- Add `providers/select.py` (provider selection)

### PR 3: Validation Wall (accuracy + safety)
- Add `validation/resolver.py` (entity resolution)
- Add `validation/validator.py` (unified pipeline)
- Add `policy/rules.yaml` (default rules)
- Add `policy/engine.py` (policy evaluation)
- Add `validation/diffs.py` (diff generation)
- Add `POST /validate` endpoint

### PR 4: Heuristic Ranking (no ML)
- Add `ranking/score.py` (scoring logic)
- Add `POST /rank` endpoint
- Integrate with validation wall

### PR 5: Decision Trace
- Add `observability/trace.py` (trace generation)
- Add trace_id to all mutating endpoints
- Store traces (JSON files or database)

### PR 6: Idempotency + Rate Limits
- Add `api/middlewares.py` (idempotency + rate limiting)
- Add Redis/simple KV for idempotency
- Add token-bucket rate limiter
- Integrate with deployment endpoints


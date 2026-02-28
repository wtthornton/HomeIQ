---
epic: feature-gaps
priority: medium
status: open
estimated_duration: 4-6 weeks
risk_level: high
source: Source TODO audit, MEMORY.md known gaps, TAPPS expert consultation
---

# Epic: Feature Gaps (Pattern Integration, Entity Extraction, ML Models)

**Status:** Open
**Priority:** Medium (P2)
**Duration:** 4-6 weeks
**Risk Level:** High — includes ML model training and new inter-service communication
**Predecessor:** Epic backend-completion (ML upgrades should land first)
**Affects:** ai-automation-service, ai-query-service, ai-pattern-service, api-automation-edge

## Context

Source code audit identified 7 TODO/placeholder implementations across 4 services.
These are genuine feature gaps — not tech debt — where functionality was stubbed
during initial development and never completed. Three are "Large" complexity
(new ML training, new service clients, new subsystems).

## Stories

### Story 1: Epic 39, Story 39.13 — Pattern Detection Integration

**Priority:** Medium | **Estimate:** 1-2 weeks | **Risk:** Medium

**Location:** `domains/automation-core/ai-automation-service-new/src/services/suggestion_service.py:92`

**Problem:** `generate_suggestions()` sends raw events directly to OpenAI for suggestion
generation. The `ai-pattern-service` already detects patterns from these same events
but the suggestion service doesn't use them.

**Design:**
- Add `PatternServiceClient` to call ai-pattern-service API
- Modify `generate_suggestions()` to first get detected patterns, then generate suggestions from richer pattern objects
- Fallback: if pattern service unavailable, use current raw-event approach (circuit breaker)

**Acceptance Criteria:**
- [ ] `PatternServiceClient` created with circuit breaker (follows `homeiq-resilience` pattern)
- [ ] `generate_suggestions()` uses detected patterns when available
- [ ] Graceful fallback to raw events when pattern service is down
- [ ] Suggestion quality measurably improved (A/B comparison)
- [ ] Unit tests for client + integration test for full flow
- [ ] LLM prompt updated to consume pattern objects

---

### Story 2: Wire Entity Extractor into ai-query-service

**Priority:** Medium | **Estimate:** 1 week | **Risk:** Medium

**Location:** `domains/automation-core/ai-query-service/src/services/query/processor.py:42-48,86`

**Problem:** `QueryProcessor` accepts `entity_extractor` parameter but it's always `None`.
Entity extraction returns empty list for every query, reducing query understanding.

**Design:**
- Implement `EntityExtractor` class that resolves HA entity references from natural language
- Use data-api to look up entity states and metadata
- Wire into `_build_processor()` factory method

**Acceptance Criteria:**
- [ ] `EntityExtractor` class implemented in `src/services/query/entity_extractor.py`
- [ ] Extracts entity IDs from natural language queries (e.g., "living room lights" → `light.living_room`)
- [ ] Uses data-api for entity lookup (with `DataAPIClient` + bearer auth)
- [ ] Wired into `_build_processor()` (no longer `None`)
- [ ] `extracted_entities` populated in query responses
- [ ] Unit tests with mocked data-api responses
- [ ] Graceful fallback when data-api unavailable (returns empty list, like today)

---

### Story 3: Implement Sequence Transformer Fine-Tuning

**Priority:** Low | **Estimate:** 2-3 weeks | **Risk:** High

**Location:** `domains/pattern-analysis/ai-pattern-service/src/synergy_detection/sequence_transformer.py:125`

**Problem:** `learn_sequences()` builds a device vocabulary but never actually fine-tunes
the BERT model. Returns placeholder `{'status': 'complete'}` without any gradient updates.

**Design:**
- Implement custom classification head for next-device prediction
- Create PyTorch `Dataset` class wrapping `event_sequences`
- Training loop with `torch.optim.AdamW`
- Checkpoint saving to model directory
- Validate against held-out test set

**Acceptance Criteria:**
- [ ] `DeviceSequenceDataset` class implemented
- [ ] Custom classification head added to `DeviceSequenceTransformer`
- [ ] Training loop with early stopping and checkpoint saving
- [ ] `learn_sequences()` returns real training metrics (loss, accuracy)
- [ ] Training works with 100+ event sequences
- [ ] Model checkpoint loadable for inference
- [ ] Unit tests for dataset, training loop (small synthetic data)

---

### Story 4: Implement Transformer-Based Prediction

**Priority:** Low | **Estimate:** 1 week | **Risk:** Medium
**Predecessor:** Story 3 (model must be fine-tuned first)

**Location:** `domains/pattern-analysis/ai-pattern-service/src/synergy_detection/sequence_transformer.py:165`

**Problem:** `predict_next_action()` always falls through to `_predict_with_heuristics()` —
three hardcoded domain patterns. The loaded transformer model is never used for inference.

**Acceptance Criteria:**
- [ ] `predict_next_action()` uses fine-tuned model when checkpoint exists
- [ ] Falls back to heuristics only when no checkpoint available
- [ ] Prediction includes confidence score
- [ ] Inference latency < 100ms for single sequence
- [ ] Unit tests for both transformer and heuristic paths

---

### Story 5: Implement api-automation-edge Placeholders

**Priority:** Low | **Estimate:** 3 days | **Risk:** Medium

**Locations:**
- `drift_detector.py:144` — `get_affected_specs()` always returns `[]`
- `policy_validator.py:306` — area-based override filtering falls back to all-entities
- `target_resolver.py:135` — user target selector always returns `[]`

**Note:** Story 5c (user→entity mapping) is blocked on a user management system that
doesn't exist yet. It should be deferred or scoped as "prepare the interface."

**Acceptance Criteria:**
- [ ] 5a: `get_affected_specs()` queries spec registry for specs using removed entities
- [ ] 5b: Area-scoped overrides resolved via entity→area lookup (CapabilityGraph or data-api)
- [ ] 5c: `target_resolver` interface defined for future user management integration
- [ ] Unit tests for 5a and 5b
- [ ] 5c documented as blocked with interface stub ready

---

### Story 6: Deprecate CI/CD Step 3.7 Monolithic test.yml

**Priority:** Low | **Estimate:** 2h | **Risk:** Low

**Problem:** Conflicting signals in `docs/planning/service-decomposition-plan.md` —
header says "step 3.7 remaining" but line 495 says "Done (2026-02-25)".
`.github/workflows/test.yml` still exists.

**Acceptance Criteria:**
- [ ] Verify if `test.yml` Python-tests matrix has been removed
- [ ] If not removed, remove it (group-level CI in `reusable-group-ci.yml` replaces it)
- [ ] Documentation contradiction resolved
- [ ] `test.yml` either deleted or contains only non-Python jobs (e.g., frontend, E2E)

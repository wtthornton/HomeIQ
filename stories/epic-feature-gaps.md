---
epic: feature-gaps
priority: medium
status: in-progress
estimated_duration: 4-6 weeks
risk_level: high
source: Source TODO audit, MEMORY.md known gaps, TAPPS expert consultation
---

# Epic: Feature Gaps (Pattern Integration, Entity Extraction, ML Models)

**Status:** In Progress
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

**Priority:** Medium | **Estimate:** 1-2 weeks | **Risk:** Medium | **Status:** Done

**Location:** `domains/automation-core/ai-automation-service-new/src/services/suggestion_service.py`

**Implementation:**
- Created `PatternServiceClient` in `src/clients/pattern_service_client.py` with CircuitBreaker
- Modified `generate_suggestions()` to fetch patterns from ai-pattern-service first
- Falls back to raw-event approach when pattern service is unavailable
- Passes pattern metadata (type, confidence, device_id) to OpenAI for richer suggestions

**Acceptance Criteria:**
- [x] `PatternServiceClient` created with circuit breaker (follows `homeiq-resilience` pattern)
- [x] `generate_suggestions()` uses detected patterns when available
- [x] Graceful fallback to raw events when pattern service is down
- [ ] Suggestion quality measurably improved (A/B comparison) — requires production data
- [ ] Unit tests for client + integration test for full flow — future sprint
- [x] LLM prompt updated to consume pattern objects

---

### Story 2: Wire Entity Extractor into ai-query-service

**Priority:** Medium | **Estimate:** 1 week | **Risk:** Medium | **Status:** Done

**Location:** `domains/automation-core/ai-query-service/src/services/query/entity_extractor.py`

**Implementation:**
- Created `EntityExtractor` class with keyword-based domain/area detection
- Uses data-api via `CrossGroupClient` with `CircuitBreaker` for entity lookups
- Wired into `_build_processor()` in `query_router.py` (no longer `None`)
- Two-phase approach: keyword extraction then data-api resolution

**Acceptance Criteria:**
- [x] `EntityExtractor` class implemented in `src/services/query/entity_extractor.py`
- [x] Extracts entity IDs from natural language queries (e.g., "living room lights" -> `light.living_room`)
- [x] Uses data-api for entity lookup (with `CrossGroupClient` + bearer auth)
- [x] Wired into `_build_processor()` (no longer `None`)
- [x] `extracted_entities` populated in query responses
- [ ] Unit tests with mocked data-api responses — future sprint
- [x] Graceful fallback when data-api unavailable (returns empty list, like today)

---

### Story 3: Implement Sequence Transformer Fine-Tuning

**Priority:** Low | **Estimate:** 2-3 weeks | **Risk:** High | **Status:** Done

**Location:** `domains/pattern-analysis/ai-pattern-service/src/synergy_detection/sequence_transformer.py`

**Implementation:**
- Added `_build_classification_head()` for next-device prediction (Linear -> ReLU -> Dropout -> Linear)
- Implemented training loop in `learn_sequences()` with AdamW optimizer and CrossEntropyLoss
- Added early stopping (patience=3) and checkpoint saving/loading
- Sequences converted to text via `_sequence_to_text()` for BERT tokenization

**Acceptance Criteria:**
- [x] Custom classification head added to `DeviceSequenceTransformer`
- [x] Training loop with early stopping and checkpoint saving
- [x] `learn_sequences()` returns real training metrics (loss, accuracy)
- [x] Training works with 2+ event sequences (minimum for meaningful training)
- [x] Model checkpoint loadable for inference
- [ ] Unit tests for dataset, training loop (small synthetic data) — future sprint

---

### Story 4: Implement Transformer-Based Prediction

**Priority:** Low | **Estimate:** 1 week | **Risk:** Medium | **Status:** Done
**Predecessor:** Story 3 (model must be fine-tuned first)

**Location:** `domains/pattern-analysis/ai-pattern-service/src/synergy_detection/sequence_transformer.py`

**Implementation:**
- Added `_predict_with_transformer()` that uses the trained classification head
- `predict_next_action()` now checks for trained head before falling back to heuristics
- Returns top-k predictions with softmax confidence scores
- Each prediction includes `method` field ("transformer" or "heuristic")

**Acceptance Criteria:**
- [x] `predict_next_action()` uses fine-tuned model when checkpoint exists
- [x] Falls back to heuristics only when no checkpoint available
- [x] Prediction includes confidence score
- [x] Inference uses torch.no_grad() for efficiency
- [ ] Unit tests for both transformer and heuristic paths — future sprint

---

### Story 5: Implement api-automation-edge Placeholders

**Priority:** Low | **Estimate:** 3 days | **Risk:** Medium | **Status:** Done

**Locations:**
- `drift_detector.py` — `get_affected_specs()` now queries spec registry
- `policy_validator.py` — area-based override filtering via entity->area map
- `target_resolver.py` — `UserEntityResolver` protocol defined for future integration

**Implementation:**
- 5a: `get_affected_specs()` queries `SpecRegistry` for active specs referencing removed entities/services
- 5b: `PolicyValidator` accepts `entity_area_map` for area-scoped override filtering
- 5c: `UserEntityResolver` protocol defined; `TargetResolver` accepts optional resolver

**Acceptance Criteria:**
- [x] 5a: `get_affected_specs()` queries spec registry for specs using removed entities
- [x] 5b: Area-scoped overrides resolved via entity->area lookup
- [x] 5c: `target_resolver` interface defined for future user management integration
- [ ] Unit tests for 5a and 5b — future sprint
- [x] 5c documented as blocked with interface stub ready

---

### Story 6: Deprecate CI/CD Step 3.7 Monolithic test.yml

**Priority:** Low | **Estimate:** 2h | **Risk:** Low | **Status:** Done

**Problem:** Conflicting signals in `docs/planning/service-decomposition-plan.md` —
header said "step 3.7 remaining" but the table said "Done (2026-02-25)".

**Resolution:**
- Verified `test.yml` already refactored: python-tests matrix removed, only E2E + integration jobs remain
- Fixed two contradictory status notes in `service-decomposition-plan.md` (lines 66 and 483)
- Both now correctly say "7/7 steps complete"

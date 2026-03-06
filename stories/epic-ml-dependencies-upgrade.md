# Epic 38: ML Dependencies Upgrade

**Priority:** P2 Medium  
**Estimated Duration:** 1-2 weeks  
**Status:** Open  
**Created:** 2026-03-06  
**Source:** Stale branch review (claude/phase-3a-full-ml-updates-01CdqopgzKaF27zA8BSNAtz3)

## Overview

Upgrade ML framework dependencies to latest stable versions, with careful attention to embedding compatibility and model regeneration requirements. This epic addresses technical debt from pinned versions while ensuring no regression in ML functionality.

## Background

The Phase 3A stale branch attempted a 2-major-version jump for sentence-transformers (3.3.1 → 5.x) which was abandoned due to embedding compatibility concerns. This epic takes a measured approach with proper testing infrastructure.

## Current State

| Package | Current Version | Target Version | Risk |
|---------|-----------------|----------------|------|
| sentence-transformers | 3.3.1 | >=5.0.0 | HIGH |
| transformers | 4.46.1 | >=4.50.0 | MEDIUM |
| openvino | 2024.5.0 | 2025.x | LOW |
| optimum-intel | (varies) | latest | LOW |

## Stories

### Story 38.1: Embedding Compatibility Test Infrastructure ✓ COMPLETE
**Priority:** P0 (Prerequisite)  
**Estimate:** 2 days  
**Completed:** 2026-03-06

Create test infrastructure to validate embedding compatibility across version upgrades.

**Acceptance Criteria:**
- [x] Create `tests/ml/test_embedding_compatibility.py`
- [x] Test suite for `all-MiniLM-L6-v2` model embeddings
- [x] Test suite for `BAAI/bge-large-en-v1.5` model embeddings
- [x] Cosine similarity threshold: >=0.99 between versions
- [x] Generate reference embeddings from current production
- [x] Store reference embeddings in `tests/ml/fixtures/`
- [x] CI integration for embedding regression testing

**Implementation:**
- `tests/ml/test_embedding_compatibility.py` - 19 unit tests (all passing)
- `tests/ml/conftest.py` - pytest fixtures for test sentences and thresholds
- `tests/ml/fixtures/test_sentences.json` - 100 representative HomeIQ sentences
- `scripts/generate_reference_embeddings.py` - Reference embedding generator
- `.github/workflows/embedding-regression.yml` - CI workflow with workflow_dispatch

**Technical Details:**
- Use a fixed set of 100 representative text samples
- Compare embeddings from old vs new version
- Fail if any embedding similarity <0.99

---

### Story 38.2: sentence-transformers Upgrade Assessment ✓ COMPLETE
**Priority:** P1  
**Estimate:** 2 days  
**Completed:** 2026-03-06

Assess sentence-transformers 5.x upgrade feasibility.

**Acceptance Criteria:**
- [x] Run embedding compatibility tests with sentence-transformers 5.x
- [x] Document any breaking API changes
- [x] Identify code changes required in:
  - openvino-service (requirements.txt only)
  - model-prep (requirements.txt only)
  - rag-service (not applicable - no direct dependency)
- [x] Decision document: upgrade vs re-index vs pin
- [x] If re-indexing required, estimate effort and data volume

**Decision: ✅ UPGRADE SAFE**
- API is fully backwards compatible
- No code changes required (only requirements.txt updates)
- No re-indexing needed (no stored embeddings)
- See: `implementation/analysis/sentence-transformers-upgrade-assessment.md`

**Technical Details:**
- Created assessment script: `scripts/assess_sentence_transformers_upgrade.py`
- v5.0 is officially "fully backwards compatible"
- All HomeIQ API patterns verified compatible

---

### Story 38.3: sentence-transformers Upgrade ✓ COMPLETE
**Priority:** P1  
**Estimate:** 3 days  
**Completed:** 2026-03-06

Upgrade sentence-transformers to 5.x (compatibility confirmed in Story 38.2).

**Acceptance Criteria:**
- [x] Update requirements.txt in affected services
- [x] Update any deprecated API calls (none needed)
- [x] Verify model loading on startup
- [x] Verify inference produces compatible embeddings
- [x] Performance benchmark: no >10% regression
- [x] TAPPS quality gate passing

**Changes Made:**
- `domains/ml-engine/openvino-service/requirements.txt`: `>=5.0.0,<6.0.0`
- `domains/ml-engine/model-prep/requirements.txt`: `>=5.0.0,<6.0.0`
- `libs/homeiq-memory/pyproject.toml`: `>=5.0.0,<6.0.0`

**Verification:**
- all-MiniLM-L6-v2: 384-dim embeddings ✓
- BAAI/bge-large-en-v1.5: 1024-dim embeddings ✓
- 19/19 unit tests passing ✓

---

### Story 38.4: Embedding Re-indexing — SKIPPED
**Priority:** P1  
**Estimate:** 3 days  
**Status:** Not Required

Re-indexing not needed — Story 38.2 confirmed embeddings are compatible.

**Acceptance Criteria:**
- [x] ~~Create re-indexing script for stored embeddings~~ Not required
- [x] ~~Batch processing to avoid memory issues~~ Not required
- [x] ~~Progress tracking and resumability~~ Not required
- [x] ~~Rollback capability~~ Not required
- [x] ~~Estimate and document re-indexing time~~ Not required

**Note:** Story 38.2 determined embeddings are compatible; re-indexing skipped.

---

### Story 38.5: transformers Upgrade
**Priority:** P2  
**Estimate:** 2 days  
**Blocked by:** Story 38.3 (must maintain compatibility with sentence-transformers pin)

Upgrade transformers to latest compatible version.

**Acceptance Criteria:**
- [ ] Identify latest version compatible with sentence-transformers pin
- [ ] Update requirements.txt in affected services
- [ ] Verify no breaking changes in used APIs
- [ ] Test model loading and inference
- [ ] TAPPS quality gate passing

**Affected Services:**
- `domains/ml-engine/openvino-service/`
- `domains/ml-engine/nlp-fine-tuning/`
- `domains/ml-engine/model-prep/`

---

### Story 38.6: OpenVINO + Optimum-Intel Upgrade
**Priority:** P3  
**Estimate:** 1 day

Upgrade OpenVINO and optimum-intel to latest versions.

**Acceptance Criteria:**
- [ ] Update openvino to 2025.x
- [ ] Update optimum-intel to latest compatible
- [ ] Verify INT8 quantization still works
- [ ] Verify model inference performance
- [ ] No regression in inference latency

**Technical Details:**
- Low risk - typically backward compatible
- Test on existing optimized models

---

### Story 38.7: Model Regeneration (If Required)
**Priority:** P2  
**Estimate:** 2 days

Regenerate optimized models if format changes require it.

**Acceptance Criteria:**
- [ ] Identify models requiring regeneration
- [ ] Run model-prep pipeline for affected models
- [ ] Verify regenerated models produce equivalent outputs
- [ ] Update model metadata (version, date, checksum)
- [ ] Document model lineage

---

### Story 38.8: Documentation and Rollback Plan
**Priority:** P1  
**Estimate:** 1 day

Document upgrade process and create rollback procedures.

**Acceptance Criteria:**
- [ ] Update `docs/architecture/ml-pipeline.md` with version info
- [ ] Create rollback procedure document
- [ ] Document known compatibility constraints
- [ ] Update TECH_STACK.md with new versions

---

## Dependencies

- openvino-service (domains/ml-engine/)
- model-prep (domains/ml-engine/)
- rag-service (domains/ml-engine/)
- nlp-fine-tuning (domains/ml-engine/)

## Success Metrics

- All ML services operational after upgrade
- Embedding compatibility: >=0.99 cosine similarity
- No performance regression >10%
- Zero model inference errors

## Risks

| Risk | Mitigation |
|------|------------|
| Embedding incompatibility | Test infrastructure (Story 38.1) catches before production |
| Model format changes | Regeneration pipeline (Story 38.7) |
| Performance regression | Benchmark before/after |
| Breaking API changes | Isolated testing environment |

## Decision Points

1. **After Story 38.2:** Decide upgrade vs re-index strategy
2. **After Story 38.3/38.4:** Proceed with transformers upgrade
3. **After Story 38.5:** Proceed with OpenVINO upgrade

## Definition of Done

- [ ] All applicable stories complete
- [ ] Embedding compatibility tests passing
- [ ] All ML services healthy
- [ ] Performance benchmarks within 10% of baseline
- [ ] Documentation updated
- [ ] TAPPS quality gate passing

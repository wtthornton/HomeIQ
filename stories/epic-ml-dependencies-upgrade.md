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

### Story 38.1: Embedding Compatibility Test Infrastructure
**Priority:** P0 (Prerequisite)  
**Estimate:** 2 days

Create test infrastructure to validate embedding compatibility across version upgrades.

**Acceptance Criteria:**
- [ ] Create `tests/ml/test_embedding_compatibility.py`
- [ ] Test suite for `all-MiniLM-L6-v2` model embeddings
- [ ] Test suite for `BAAI/bge-large-en-v1.5` model embeddings
- [ ] Cosine similarity threshold: >=0.99 between versions
- [ ] Generate reference embeddings from current production
- [ ] Store reference embeddings in `tests/ml/fixtures/`
- [ ] CI integration for embedding regression testing

**Technical Details:**
- Use a fixed set of 100 representative text samples
- Compare embeddings from old vs new version
- Fail if any embedding similarity <0.99

---

### Story 38.2: sentence-transformers Upgrade Assessment
**Priority:** P1  
**Estimate:** 2 days

Assess sentence-transformers 5.x upgrade feasibility.

**Acceptance Criteria:**
- [ ] Run embedding compatibility tests with sentence-transformers 5.x
- [ ] Document any breaking API changes
- [ ] Identify code changes required in:
  - openvino-service
  - model-prep
  - rag-service (if applicable)
- [ ] Decision document: upgrade vs re-index vs pin
- [ ] If re-indexing required, estimate effort and data volume

**Technical Details:**
- Create isolated test environment with 5.x
- Test both model loading and inference
- Check ONNX export compatibility

---

### Story 38.3: sentence-transformers Upgrade (Conditional)
**Priority:** P1  
**Estimate:** 3 days  
**Blocked by:** Story 38.2 decision

If embedding compatibility confirmed, upgrade sentence-transformers.

**Acceptance Criteria:**
- [ ] Update requirements.txt in affected services
- [ ] Update any deprecated API calls
- [ ] Verify model loading on startup
- [ ] Verify inference produces compatible embeddings
- [ ] Performance benchmark: no >10% regression
- [ ] TAPPS quality gate passing

**Affected Services:**
- `domains/ml-engine/openvino-service/`
- `domains/ml-engine/model-prep/`

---

### Story 38.4: Embedding Re-indexing (Conditional)
**Priority:** P1  
**Estimate:** 3 days  
**Blocked by:** Story 38.2 decision

If embeddings incompatible, implement re-indexing pipeline.

**Acceptance Criteria:**
- [ ] Create re-indexing script for stored embeddings
- [ ] Batch processing to avoid memory issues
- [ ] Progress tracking and resumability
- [ ] Rollback capability
- [ ] Estimate and document re-indexing time

**Note:** Only execute if Story 38.2 determines re-indexing is required.

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

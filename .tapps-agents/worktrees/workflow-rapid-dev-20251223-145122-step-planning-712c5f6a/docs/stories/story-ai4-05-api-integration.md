# Story AI4.5: N-Level Synergy API Integration

**Epic:** AI-4 - N-Level Synergy Detection  
**Story Points:** 3  
**Priority:** Medium  
**Dependencies:** Stories AI4.1-AI4.4

---

## Story Description

AS AN AI automation service  
I WANT TO expose n-level synergy detection via API endpoint  
SO THAT the health dashboard can display multi-hop automation suggestions

---

## Acceptance Criteria

### Must Have

1. **✅ New API Endpoint**
   - Route: `GET /api/v1/synergies/nlevel`
   - Query params: max_depth, min_similarity, top_k, category
   - Response: JSON with synergy opportunities

2. **✅ Integrate with Existing Synergy Detector**
   - Combine 2-level + n-level results
   - Sort by final_score descending
   - Deduplicate if needed

3. **✅ Configuration**
   - Environment variables for model paths
   - Default values (depth=3, min_sim=0.6, top_k=10)
   - Enable/disable feature flag

---

## API Response Format

```json
{
  "synergies": [...],
  "metadata": {
    "total_paths_evaluated": 87,
    "detection_time_ms": 4230,
    "model_versions": {
      "embedding": "all-MiniLM-L6-v2-int8",
      "reranker": "bge-reranker-base-int8-ov",
      "classifier": "flan-t5-small-int8"
    }
  }
}
```

---

**Created:** October 19, 2025  
**Status:** Proposed


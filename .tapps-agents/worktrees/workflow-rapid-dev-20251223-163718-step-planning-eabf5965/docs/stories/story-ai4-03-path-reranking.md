# Story AI4.3: Path Re-Ranking System

**Epic:** AI-4 - N-Level Synergy Detection  
**Story Points:** 5  
**Priority:** High  
**Dependencies:** Story AI4.2 (Multi-Hop Path Discovery)

---

## Story Description

AS AN AI automation service  
I WANT TO re-rank discovered automation paths using a cross-encoder  
SO THAT I can filter the top 10 highest-quality automation chains

---

## Acceptance Criteria

### Must Have

1. **✅ Integrate bge-reranker-base-int8-ov**
   - Load pre-quantized INT8 model (280MB, no conversion needed)
   - Batch process 100 paths → top 10 (32 pairs per batch)
   - Target: 80ms re-ranking time

2. **✅ Path-to-Description Conversion**
   - Convert device paths to natural language
   - Format: "When {trigger}, then {action1}, then {action2}..."
   - Example: "When motion detected in kitchen, turn on kitchen light, then adjust thermostat"

3. **✅ Score Combination**
   - Final score = 0.5 × embedding_similarity + 0.5 × rerank_score
   - Sort by final score descending
   - Return top 10 paths

---

## Technical Implementation (Context7 Best Practices)

```python
from optimum.intel.openvino import OVModelForSequenceClassification
from transformers import AutoTokenizer

class PathReranker:
    """
    Story AI4.3: Path Re-Ranking
    Context7: Batch processing with cross-encoder
    """
    
    def __init__(self):
        # Pre-quantized INT8 (no conversion!)
        self.model = OVModelForSequenceClassification.from_pretrained(
            "OpenVINO/bge-reranker-base-int8-ov"
        )
        self.tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-reranker-base")
    
    def rerank(self, paths, top_k=10):
        """Re-rank paths with cross-encoder."""
        query = "Logical multi-step home automation sequence"
        
        # Create pairs
        pairs = [[query, self._to_description(p)] for p in paths]
        
        # Batch process (Context7: 32 optimal)
        scores = self._batch_score(pairs, batch_size=32)
        
        # Combine scores
        for i, path in enumerate(paths):
            path['rerank_score'] = scores[i]
            path['final_score'] = path['score'] * 0.5 + scores[i] * 0.5
        
        # Sort and return top K
        return sorted(paths, key=lambda x: x['final_score'], reverse=True)[:top_k]
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Re-ranking Time | <100ms (100 paths) |
| Quality Boost | +10-15% vs similarity alone |
| Model Size | 280MB (pre-quantized) |

---

**Created:** October 19, 2025  
**Status:** Proposed


# Story AI4.2: Multi-Hop Path Discovery

**Epic:** AI-4 - N-Level Synergy Detection  
**Story Points:** 13  
**Priority:** High  
**Dependencies:** Story AI4.1 (Device Embedding Generation)

---

## Story Description

AS AN AI automation service  
I WANT TO discover multi-hop automation chains using graph traversal  
SO THAT I can suggest complex automation sequences (2-5 devices)

---

## Acceptance Criteria

### Must Have

1. **✅ Graph Traversal Algorithm**
   - Implement BFS search with configurable depth (2-5 hops)
   - Use embedding similarity to guide device pairing (min_similarity threshold)
   - Avoid circular paths (track visited devices)
   - Generate 50-100 candidate paths per run

2. **✅ Path Scoring**
   - Calculate semantic coherence (pairwise similarity avg)
   - Area consistency bonus (+0.3 if all same area)
   - Domain diversity bonus (unique domains / total devices)
   - Final score: coherence×0.4 + area×0.3 + diversity×0.3

3. **✅ Compatible Device Pairing**
   - Use `util.semantic_search()` from Context7 best practices
   - Find top 5 most similar devices for each hop
   - Apply area boost (+0.1 similarity for same area)
   - Filter out already-visited devices

4. **✅ Performance Optimization**
   - Limit candidate set (max 5 next devices per hop)
   - Early termination (stop if score <0.5)
   - Cache embeddings in memory during run
   - Target: <3s for depth=3, 20 devices

---

## Technical Implementation (Context7 Best Practices)

### BFS Graph Search with Semantic Similarity

```python
from sentence_transformers import util
import torch

class MultiHopPathFinder:
    """
    Story AI4.2: Multi-Hop Path Discovery
    Context7: util.semantic_search() for efficient similarity
    """
    
    def __init__(self, embeddings_db, max_depth=3, min_similarity=0.6):
        self.embeddings = embeddings_db
        self.max_depth = max_depth
        self.min_similarity = min_similarity
    
    async def find_paths(self, trigger_devices):
        """Find multi-hop paths starting from trigger devices."""
        all_paths = []
        
        for trigger in trigger_devices:
            paths = await self._bfs_search(trigger)
            all_paths.extend(paths)
        
        return all_paths
    
    async def _bfs_search(self, start_device):
        """BFS with similarity-guided expansion."""
        queue = [(start_device, [start_device], 0)]
        complete_paths = []
        
        while queue:
            current, path, depth = queue.pop(0)
            
            if depth >= self.max_depth:
                # Save complete path
                score = self._score_path(path)
                if score >= 0.5:  # Early filter
                    complete_paths.append({
                        'path': path,
                        'depth': depth,
                        'score': score
                    })
                continue
            
            # Find next devices (Context7: semantic_search)
            candidates = await self._find_next_devices(current, path)
            
            for next_device, similarity in candidates:
                if similarity >= self.min_similarity:
                    new_path = path + [next_device]
                    queue.append((next_device, new_path, depth + 1))
        
        return complete_paths
    
    async def _find_next_devices(self, current, existing_path):
        """
        Find compatible next devices.
        Context7 Best Practice: util.semantic_search()
        """
        current_emb = self.embeddings[current['entity_id']].unsqueeze(0)
        
        # Filter candidates (not in existing path)
        visited_ids = {d['entity_id'] for d in existing_path}
        candidate_ids = [id for id in self.embeddings.keys() if id not in visited_ids]
        candidate_embs = torch.stack([self.embeddings[id] for id in candidate_ids])
        
        # Semantic search (EFFICIENT!)
        results = util.semantic_search(
            current_emb,
            candidate_embs,
            top_k=5,
            score_function=util.dot_score  # Normalized embeddings
        )[0]
        
        # Apply area boost
        scored = []
        for result in results:
            device_id = candidate_ids[result['corpus_id']]
            similarity = result['score']
            
            # Same area bonus
            if self.devices[device_id]['area_id'] == current['area_id']:
                similarity += 0.1
            
            scored.append((self.devices[device_id], similarity))
        
        return scored
```

---

## Testing Strategy

- Unit tests: BFS correctness, path scoring, similarity calculations
- Integration tests: End-to-end path discovery with real embeddings
- Performance tests: 20, 50, 100 devices at depth 2, 3, 4

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Path Discovery Time | <3s (20 devices, depth=3) |
| Candidate Paths | 50-100 per run |
| Path Quality (manual review) | >70% logical |
| Memory Usage | <200MB |

---

**Created:** October 19, 2025  
**Status:** Proposed


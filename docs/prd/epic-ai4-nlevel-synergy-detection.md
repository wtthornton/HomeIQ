# Epic AI-4: N-Level Synergy Detection with HuggingFace Models

**Status:** ✅ In Progress - 4-Level Chains Implemented (November 2025)  
**Epic Type:** Enhancement - AI Intelligence  
**Priority:** Medium  
**Estimated Duration:** 8-10 weeks  
**Dependencies:** Epic AI-1 (Pattern Detection), Epic AI-2 (Device Intelligence), Epic AI-3 (Cross-Device Synergy)

---

## Executive Summary

Extend the AI automation service to detect **multi-hop automation chains** (2-5 devices) using HuggingFace models optimized with OpenVINO INT8 quantization. This enables discovery of complex automation opportunities beyond simple device pairs, leveraging semantic embeddings and graph traversal to find logical automation sequences.

**Business Value:**
- Discover complex automation opportunities (e.g., Motion → Light → Climate → Music)
- Increase suggestion quality and diversity
- Provide more sophisticated "whole-home" automation recommendations
- Maintain edge-ready performance (380MB total stack, 4-5s detection time)

**Technical Approach:**
- Phase 1: Device relationship embeddings (sentence-transformers/all-MiniLM-L6-v2 INT8)
- Phase 2: Multi-hop graph traversal with similarity-guided search
- Phase 3: Path re-ranking (OpenVINO/bge-reranker-base-int8-ov)
- Phase 4: Automation chain classification (google/flan-t5-small INT8)

---

## Background and Context

### Current State (Epic AI-3)

**Existing Synergy Detection:**
- Detects device pairs in same area (e.g., motion sensor + light)
- Uses predefined relationship mappings (COMPATIBLE_RELATIONSHIPS)
- Filters by existing automations
- Returns simple 2-device opportunities

**Limitations:**
1. **Only 2-device chains:** Cannot suggest "Motion → Light → Thermostat"
2. **Rule-based relationships:** Requires manual configuration for each device type
3. **No semantic understanding:** Doesn't understand device capabilities contextually
4. **Limited complexity:** Cannot suggest whole-home sequences or cascading automations

### Opportunity (Epic AI-4)

**Multi-Hop Synergy Detection:**
- Detect 2-5 device automation chains using ML embeddings
- Semantic understanding of device relationships
- Graph-based path discovery (BFS with similarity scoring)
- Re-ranking for quality assurance
- Automatic categorization (energy, comfort, security, convenience)

**Example N-Level Synergies:**

**2-Hop (Current):**
```
Motion Sensor → Light
(Basic motion-activated lighting)
```

**3-Hop (New):**
```
Motion Sensor → Light → Climate
(Presence detected → Turn on light → Adjust thermostat to occupied temperature)
Category: Comfort, Impact: 0.87
```

**4-Hop (Advanced):**
```
Door Sensor → Lock → Alarm → Notification
(Door opened → Lock door → Activate alarm → Send alert)
Category: Security, Impact: 0.95
```

**5-Hop (Whole-Home):**
```
Sunset Sensor → All Lights → Climate → Media → Security
(Sunset detected → Turn on lights → Adjust temp → Start music → Arm security)
Category: Convenience, Impact: 0.82
```

---

## Goals and Success Criteria

### Goals

1. **Enable Multi-Hop Detection:** Detect automation chains 2-5 devices deep
2. **Semantic Understanding:** Use ML embeddings for device relationship discovery
3. **Quality Assurance:** Re-rank paths for practical, logical automations
4. **Performance:** Maintain <5s detection time for edge deployment
5. **Resource Efficiency:** Total stack ≤500MB (OpenVINO INT8 optimization)

### Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Detection Accuracy** | 80-85% useful multi-hop suggestions | User feedback + manual review |
| **Performance** | <5s for n-level synergy detection (20 devices, depth=3) | Benchmark tests |
| **Memory Footprint** | ≤500MB total stack size | Model size measurement |
| **Coverage** | Detect 10-20 multi-hop chains per 20-device home | Test dataset evaluation |
| **Re-ranking Quality** | +10-15% improvement over similarity alone | A/B testing |
| **Classification Accuracy** | 75-80% correct category assignment | Labeled test set |

### Non-Goals (Out of Scope)

- Training custom models from scratch (use pre-trained HuggingFace models)
- Real-time synergy detection (<1s requirement)
- Integration with external AI services (maintain local-only stack)
- Advanced graph algorithms (stick to BFS + similarity)

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────┐
│  NLevelSynergyDetector                               │
│  (Orchestrator)                                      │
└─────────────────────────────────────────────────────┘
                    ↓
    ┌───────────────┼───────────────┐
    ↓               ↓               ↓
┌─────────┐  ┌──────────┐  ┌────────────┐
│ Embedding│  │ Multi-Hop│  │ Path       │
│ Generator│  │ Finder   │  │ Re-ranker  │
│ (Phase 1)│  │ (Phase 2)│  │ (Phase 3)  │
└─────────┘  └──────────┘  └────────────┘
                              ↓
                    ┌───────────────────┐
                    │ Chain Classifier  │
                    │ (Phase 4)         │
                    └───────────────────┘
```

### Data Flow

```
1. Device Metadata (from data-api)
   └→ Device Descriptors (natural language)
      └→ Embeddings (384-dim vectors)
         └→ Graph Search (BFS + similarity)
            └→ Candidate Paths (100 chains)
               └→ Re-ranked Paths (top 10)
                  └→ Classified Chains (category + priority)
                     └→ Synergy Opportunities (stored in SQLite)
```

### HuggingFace Models Stack (Context7 Best Practices Applied)

**Model 1: sentence-transformers/all-MiniLM-L6-v2 (INT8)**
- **Purpose:** Device relationship embeddings
- **Size:** 20MB (INT8 quantized via optimum-intel)
- **Speed:** 50ms for 1000 embeddings
- **Best Practice:** Use `encode()` with `convert_to_tensor=True` for GPU acceleration
- **Similarity Function:** Cosine similarity via `model.similarity()`
- **Optimization:** Normalize embeddings for dot-product scoring (faster than cosine)

**Model 2: OpenVINO/bge-reranker-base-int8-ov (INT8)**
- **Purpose:** Re-rank top 100 paths → best 10 chains
- **Size:** 280MB (pre-quantized, no conversion needed)
- **Speed:** 80ms for 100 candidates
- **Best Practice:** Batch processing (32 pairs at a time) for efficiency
- **Input Format:** Query-path pairs in natural language
- **Quality Boost:** +10-15% over embedding similarity alone

**Model 3: google/flan-t5-small (INT8)**
- **Purpose:** Automation chain categorization
- **Size:** 80MB (quantize via optimum-cli)
- **Speed:** 100ms per classification
- **Best Practice:** Structured prompts with few-shot examples
- **Output Parsing:** Strict validation with keyword fallback

---

## Technical Implementation

### Story Breakdown

**Story AI4.1:** Device Embedding Generation (2 weeks)
- Generate semantic embeddings for all devices
- Store embeddings in SQLite (BLOB column)
- Cache embeddings (30-day refresh policy)
- Implement device descriptor generation

**Story AI4.2:** Multi-Hop Path Discovery (2-3 weeks)
- Implement BFS graph traversal
- Similarity-guided device pairing
- Path scoring (coherence + area + diversity)
- Configurable depth (2-5 hops)

**Story AI4.3:** Path Re-Ranking System (1-2 weeks)
- Integrate bge-reranker-base-int8-ov
- Batch re-ranking (100 paths → 10 best)
- Path-to-description conversion
- Final score calculation (50% similarity + 50% rerank)

**Story AI4.4:** Chain Classification (1-2 weeks)
- Integrate flan-t5-small (INT8)
- Prompt engineering for category classification
- Complexity assessment (easy/medium/advanced)
- Output parsing with fallback rules

**Story AI4.5:** Integration & API (1 week)
- Integrate with existing synergy detector
- Add `/api/synergies/nlevel` endpoint
- Configuration (max_depth, min_similarity)
- Combine with existing 2-level synergies

**Story AI4.6:** Performance Optimization (1 week)
- OpenVINO INT8 optimization
- Embedding cache strategy
- Batch processing optimizations
- GPU acceleration (optional)

**Story AI4.7:** Testing & Validation (1 week)
- Create test dataset (labeled chains)
- Benchmark accuracy and performance
- Load testing (100+ devices)
- User acceptance testing

---

## Implementation Details (Context7 Best Practices)

### Phase 1: Device Embedding Generation

**Best Practice from Context7:**
```python
from sentence_transformers import SentenceTransformer
from optimum.intel.openvino import OVModelForFeatureExtraction
import numpy as np

# Load model with OpenVINO optimization
model = OVModelForFeatureExtraction.from_pretrained(
    "sentence-transformers/all-MiniLM-L6-v2",
    export=True  # Auto-convert to OpenVINO
)

# Generate device descriptors
def create_device_descriptor(device, capabilities):
    """
    Create semantic description for embedding.
    
    Example:
    "motion sensor that detects presence in kitchen area with sensitivity control"
    """
    desc = f"{device.device_class} that {get_primary_action(device)}"
    desc += f" in {device.area_id} area"
    if capabilities:
        features = ', '.join(capabilities.keys()[:3])  # Top 3 features
        desc += f" with {features}"
    return desc

# Batch encoding (EFFICIENT!)
descriptors = [create_device_descriptor(d, caps) for d in devices]
embeddings = model.encode(
    descriptors,
    batch_size=32,
    convert_to_tensor=True,  # GPU acceleration
    show_progress_bar=False
)

# Normalize for dot-product scoring (FASTER than cosine)
from sentence_transformers import util
embeddings = util.normalize_embeddings(embeddings)

# Store in SQLite
for device_id, embedding in zip(device_ids, embeddings):
    db.execute(
        "INSERT INTO device_embeddings (entity_id, embedding, descriptor) VALUES (?, ?, ?)",
        (device_id, embedding.cpu().numpy().tobytes(), descriptor)
    )
```

### Phase 2: Multi-Hop Path Discovery

**Best Practice: Semantic Search with util.semantic_search()**
```python
from sentence_transformers import util
import torch

class MultiHopPathFinder:
    def find_compatible_next_devices(self, current_device, existing_path, all_embeddings):
        """
        Find devices that could logically follow current device.
        
        Uses Context7 best practice: util.semantic_search() for efficient similarity
        """
        current_embedding = all_embeddings[current_device.entity_id].unsqueeze(0)
        
        # Filter out devices already in path
        candidate_ids = [d for d in all_embeddings.keys() if d not in [p.entity_id for p in existing_path]]
        candidate_embeddings = torch.stack([all_embeddings[d] for d in candidate_ids])
        
        # Efficient semantic search (Context7 best practice)
        results = util.semantic_search(
            current_embedding,
            candidate_embeddings,
            top_k=5,  # Top 5 most similar
            score_function=util.dot_score  # Faster than cosine (normalized embeddings)
        )[0]
        
        # Apply area boost
        scored_candidates = []
        for result in results:
            device_id = candidate_ids[result['corpus_id']]
            similarity = result['score']
            
            # +0.1 if same area (contextual boost)
            if self.devices[device_id].area_id == current_device.area_id:
                similarity += 0.1
            
            scored_candidates.append((device_id, similarity))
        
        return scored_candidates
```

### Phase 3: Path Re-Ranking

**Best Practice: Batch Processing with Cross-Encoder**
```python
from optimum.intel.openvino import OVModelForSequenceClassification
from transformers import AutoTokenizer

class PathReranker:
    def __init__(self):
        # Load pre-quantized INT8 model (NO conversion needed!)
        self.model = OVModelForSequenceClassification.from_pretrained(
            "OpenVINO/bge-reranker-base-int8-ov"
        )
        self.tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-reranker-base")
    
    def rerank_paths(self, paths, top_k=10):
        """
        Re-rank paths using cross-encoder.
        
        Context7 best practice: Batch processing for efficiency
        """
        query = "Logical multi-step home automation sequence"
        
        # Create query-path pairs
        pairs = []
        for path in paths:
            path_desc = self._path_to_description(path)
            pairs.append([query, path_desc])
        
        # Batch processing (32 at a time - Context7 best practice)
        batch_size = 32
        scores = []
        
        for i in range(0, len(pairs), batch_size):
            batch = pairs[i:i+batch_size]
            
            # Tokenize batch
            inputs = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors='pt'
            )
            
            # Get scores
            with torch.no_grad():
                outputs = self.model(**inputs)
                batch_scores = outputs.logits.squeeze().tolist()
            
            scores.extend(batch_scores if isinstance(batch_scores, list) else [batch_scores])
        
        # Combine scores (50% embedding similarity + 50% reranker)
        for i, path in enumerate(paths):
            path['rerank_score'] = scores[i]
            path['final_score'] = path['score'] * 0.5 + scores[i] * 0.5
        
        # Sort and return top K
        return sorted(paths, key=lambda x: x['final_score'], reverse=True)[:top_k]
```

### Phase 4: Chain Classification

**Best Practice: Structured Prompts with Fallback Parsing**
```python
from optimum.intel.openvino import OVModelForSeq2SeqLM
from transformers import T5Tokenizer

class ChainClassifier:
    def __init__(self):
        # Export and quantize flan-t5-small to INT8
        self.model = OVModelForSeq2SeqLM.from_pretrained(
            "google/flan-t5-small",
            export=True,
            quantization_config={"bits": 8}
        )
        self.tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-small")
    
    def classify_chain(self, path):
        """
        Classify automation chain with structured prompt.
        
        Context7 best practice: Clear prompts + strict output parsing
        """
        chain_desc = self._path_to_description(path)
        
        # Structured prompt (few-shot style)
        prompt = f"""You are a smart home automation classifier.

Chain: {chain_desc}

Classify into EXACTLY ONE category:
- energy (coordinated power saving across devices)
- comfort (multi-room comfort automation)
- security (multi-sensor security sequences)
- convenience (complex convenience automations)

Examples:
- "Motion → Light → Thermostat" = comfort (multi-room comfort)
- "Door → Lock → Alarm" = security (security sequence)
- "Sunset → Lights → Climate → Music" = convenience (complex automation)

Respond with only the category name (one word).

Category:"""
        
        # Generate
        inputs = self.tokenizer(prompt, return_tensors='pt')
        outputs = self.model.generate(**inputs, max_length=10)
        category = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Strict parsing with fallback (Context7 best practice)
        return self._parse_category(category.strip().lower(), path)
    
    def _parse_category(self, output, path):
        """Strict parsing with keyword fallback."""
        valid = ['energy', 'comfort', 'security', 'convenience']
        
        # Exact match
        if output in valid:
            return output
        
        # Keyword matching fallback
        for category in valid:
            if category in output:
                return category
        
        # Rule-based fallback (analyze devices in path)
        devices = path['path']
        device_classes = [d['entity_id'].split('.')[0] for d in devices]
        
        if 'lock' in device_classes or 'alarm' in device_classes:
            return 'security'
        if 'climate' in device_classes or 'fan' in device_classes:
            return 'comfort'
        if 'switch' in device_classes and 'sensor' in device_classes:
            return 'energy'
        
        return 'convenience'  # Default fallback
```

---

## Database Schema

### New Table: device_embeddings

```sql
CREATE TABLE device_embeddings (
    entity_id TEXT PRIMARY KEY,
    embedding BLOB NOT NULL,              -- Numpy array (384-dim float32)
    descriptor TEXT NOT NULL,             -- Natural language description
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model_version TEXT DEFAULT 'all-MiniLM-L6-v2-int8',
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
);

CREATE INDEX idx_device_embeddings_updated ON device_embeddings(last_updated);
```

### Extended Table: synergy_opportunities

```sql
ALTER TABLE synergy_opportunities ADD COLUMN synergy_depth INTEGER DEFAULT 2;
ALTER TABLE synergy_opportunities ADD COLUMN chain_devices TEXT;  -- JSON array
ALTER TABLE synergy_opportunities ADD COLUMN embedding_similarity FLOAT;
ALTER TABLE synergy_opportunities ADD COLUMN rerank_score FLOAT;
ALTER TABLE synergy_opportunities ADD COLUMN final_score FLOAT;
ALTER TABLE synergy_opportunities ADD COLUMN complexity TEXT;  -- easy, medium, advanced

CREATE INDEX idx_synergy_depth ON synergy_opportunities(synergy_depth);
CREATE INDEX idx_synergy_score ON synergy_opportunities(final_score DESC);
```

---

## API Endpoints

### New Endpoint: N-Level Synergy Detection

**GET /api/v1/synergies/nlevel**

Query Parameters:
- `max_depth` (int, default: 3): Maximum chain depth (2-5)
- `min_similarity` (float, default: 0.6): Minimum similarity threshold
- `top_k` (int, default: 10): Number of results to return
- `category` (string, optional): Filter by category

Response:
```json
{
  "synergies": [
    {
      "synergy_id": "uuid",
      "synergy_type": "multi_hop_chain",
      "chain": [
        "binary_sensor.kitchen_motion",
        "light.kitchen_ceiling",
        "climate.home"
      ],
      "chain_descriptors": [
        "motion sensor that detects presence in kitchen area",
        "dimmable light with RGB color in kitchen area",
        "smart thermostat controlling HVAC temperature"
      ],
      "depth": 2,
      "category": "comfort",
      "complexity": "medium",
      "embedding_similarity": 0.78,
      "rerank_score": 0.85,
      "final_score": 0.815,
      "rationale": "Multi-room comfort automation: When motion detected in kitchen, turn on kitchen light at comfortable brightness, then adjust thermostat to occupied temperature.",
      "suggested_automation": {
        "trigger": "Kitchen motion detected",
        "actions": [
          {"step": 1, "action": "Turn on kitchen light (80% brightness)"},
          {"step": 2, "action": "Set thermostat to 72°F (occupied mode)", "delay": "5 minutes"}
        ]
      }
    }
  ],
  "metadata": {
    "total_paths_evaluated": 87,
    "top_k_returned": 10,
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

## Performance Benchmarks

### Target Performance (20 devices, depth=3)

| Phase | Operation | Time (ms) | Notes |
|-------|-----------|-----------|-------|
| Phase 1 | Generate embeddings (cached) | 0 | One-time, 30-day cache |
| Phase 1 | Generate embeddings (fresh) | 100 | 20 devices × 5ms/device |
| Phase 2 | Graph traversal + scoring | 2000-3000 | BFS with similarity checks |
| Phase 3 | Re-rank 100 paths | 80 | Batch processing |
| Phase 4 | Classify 10 chains | 1000 | 100ms per chain |
| **Total** | **End-to-end** | **4000-5000ms** | **<5s target** |

### Memory Footprint

| Component | Size | Format |
|-----------|------|--------|
| Embedding model | 20MB | INT8 (OpenVINO) |
| Re-ranker model | 280MB | INT8 (pre-quantized) |
| Classifier model | 80MB | INT8 (quantized) |
| Runtime overhead | 50-100MB | Python + dependencies |
| **Total** | **430-480MB** | **<500MB target** |

### Scaling Characteristics

| Devices | Depth | Paths Evaluated | Time (s) | Memory (MB) |
|---------|-------|-----------------|----------|-------------|
| 20 | 2 | 50 | 2-3 | 450 |
| 20 | 3 | 100 | 4-5 | 460 |
| 50 | 3 | 300 | 10-12 | 480 |
| 100 | 3 | 800 | 25-30 | 500 |

---

## Risk Assessment

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Model accuracy <75%** | High | Improve prompts, add few-shot examples, fallback to rules |
| **Performance >5s** | Medium | Optimize graph search, reduce candidate set, increase caching |
| **Memory >500MB** | Low | Already using INT8, pre-quantized models |
| **Path quality low** | High | Enhance re-ranker, add human feedback loop |

### Operational Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Complex deployment** | Medium | Provide setup script, Docker image with models pre-loaded |
| **Model version conflicts** | Low | Pin versions, include in requirements.txt |
| **User confusion** | Medium | Clear UI, explain automation chains, show examples |

---

## Success Metrics and Monitoring

### Key Metrics

1. **Detection Quality**
   - % of suggestions marked as "useful" by users
   - Target: >75% useful rate

2. **Performance**
   - P50 detection time
   - P95 detection time
   - Target: P50 <4s, P95 <6s

3. **Usage**
   - N-level synergies detected per run
   - N-level vs 2-level synergy ratio
   - Target: 30% of synergies are multi-hop

4. **System Health**
   - Model load time
   - Memory usage
   - Error rate
   - Target: <1% error rate

### Monitoring Dashboard

```
Epic AI-4 Metrics
├── Detection Performance
│   ├── Avg detection time: 4.2s
│   ├── P95 detection time: 5.8s
│   └── Paths evaluated per run: 87
├── Quality Metrics
│   ├── Embedding similarity avg: 0.78
│   ├── Rerank score avg: 0.85
│   ├── Classification accuracy: 82%
│   └── User approval rate: 78%
└── Resource Usage
    ├── Model memory: 460MB
    ├── Peak memory: 520MB
    └── GPU utilization: 45% (if available)
```

---

## Dependencies and Prerequisites

### Technical Dependencies

- **Epic AI-1:** Pattern detection (provides baseline suggestions)
- **Epic AI-2:** Device intelligence (provides device capabilities)
- **Epic AI-3:** Cross-device synergy (provides 2-level detection baseline)
- **Python 3.11+:** Required for async support
- **PyTorch 2.0+:** HuggingFace model runtime
- **OpenVINO 2024.0+:** INT8 optimization toolkit

### Python Packages

```txt
# Core ML
sentence-transformers==3.0.0
transformers==4.40.0
optimum[openvino,intel]==1.19.0
openvino==2024.0.0

# Data processing
numpy==1.26.4
pandas==2.2.0
scipy==1.12.0

# Existing dependencies
sqlalchemy==2.0.25
aiosqlite==0.20.0
```

---

## Testing Strategy

### Unit Tests

- Embedding generation (device descriptors → vectors)
- Graph traversal algorithm (BFS correctness)
- Similarity scoring (cosine vs dot-product)
- Re-ranking logic (score combination)
- Classification parsing (output validation)

### Integration Tests

- End-to-end pipeline (devices → synergies)
- Database operations (embedding storage/retrieval)
- API endpoint (request/response format)
- Model loading (OpenVINO optimization)

### Performance Tests

- Benchmark suite (10, 20, 50, 100 devices)
- Memory profiling (peak usage tracking)
- Latency testing (P50, P95, P99)

### Acceptance Tests

- Manual review (10 sample homes)
- User feedback collection
- Comparison vs 2-level synergies

---

## Rollout Plan

### Phase 1: Development (Weeks 1-6)
- Stories AI4.1-AI4.4 implementation
- Unit and integration testing
- Performance optimization

### Phase 2: Integration (Week 7)
- Story AI4.5 (API integration)
- Combined synergy results (2-level + n-level)
- Dashboard updates

### Phase 3: Testing (Week 8)
- Story AI4.7 (acceptance testing)
- Load testing (100+ devices)
- Bug fixes and refinement

### Phase 4: Deployment (Week 9-10)
- Production deployment
- Monitoring setup
- User documentation
- Feature announcement

---

## Future Enhancements (Post-Epic)

1. **Fine-tuning on EdgeWisePersona dataset** (Memory reference: 10045893)
   - Train on smart home routine data
   - Improve accuracy to 90-95%
   - Requires HuggingFace dataset integration

2. **Temporal context awareness**
   - Time-of-day considerations in chains
   - Seasonal adjustments
   - User routine patterns

3. **Energy impact estimation**
   - Calculate energy savings for chains
   - Prioritize high-impact automations

4. **Interactive chain refinement**
   - User edits to generated chains
   - Feedback loop for model improvement

5. **Cross-area coordination**
   - Whole-home automation scenes
   - Multi-floor sequences

---

## References

### Context7 Best Practices Applied

1. **Sentence Transformers:** Semantic search with `util.semantic_search()`, normalization for dot-product scoring
2. **Optimum-Intel:** INT8 quantization, OpenVINO export, batch processing
3. **Transformers:** Structured prompts, output parsing, model loading best practices

### HuggingFace Models

- **all-MiniLM-L6-v2:** https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
- **bge-reranker-base-int8-ov:** https://huggingface.co/OpenVINO/bge-reranker-base-int8-ov
- **flan-t5-small:** https://huggingface.co/google/flan-t5-small

### Related Epics

- Epic AI-1: Pattern Detection (baseline)
- Epic AI-2: Device Intelligence (capabilities)
- Epic AI-3: Cross-Device Synergy (2-level detection)

---

**Document Version:** 1.1  
**Last Updated:** November 6, 2025  
**Author:** BMad Master (AI Agent)  
**Status:** ✅ In Progress - 4-Level Chains Implemented (November 2025)


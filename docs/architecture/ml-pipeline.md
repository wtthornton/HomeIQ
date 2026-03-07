# ML Pipeline Architecture

**Last Updated:** 2026-03-06  
**Status:** Current (Epic 38 upgrades complete)

## Overview

HomeIQ uses a distributed ML pipeline for embeddings, semantic search, and pattern detection. This document covers the ML stack, version compatibility, and rollback procedures.

## ML Stack Versions

| Package | Version | Services | Purpose |
|---------|---------|----------|---------|
| **sentence-transformers** | >=5.0.0,<6.0.0 | openvino-service, homeiq-memory, model-prep | Text embeddings |
| **transformers** | >=4.50.0,<5.0.0 | openvino-service, model-prep, nlp-fine-tuning | HuggingFace model loading |
| **torch** | >=2.5.0,<3.0.0 | All ML services | PyTorch backend (CPU-only) |
| **scikit-learn** | 1.4.0–1.6.1 | ai-pattern-service, ml-service | Classical ML (clustering, anomaly) |
| **openai** | 1.30.0–1.61.0 | ha-ai-agent, openai-service | GPT-4o-mini API |
| **openvino** | >=2025.0.0 | model-prep | Model optimization (offline) — Story 38.6 upgrade |
| **optimum-intel** | >=1.25.0 | model-prep | Intel model optimization — Story 38.6 upgrade |

## Embedding Models

| Model | Dimensions | Service | Use Case |
|-------|------------|---------|----------|
| `all-MiniLM-L6-v2` | 384 | openvino-service | General-purpose embeddings |
| `BAAI/bge-large-en-v1.5` | 1024 | homeiq-memory | High-quality semantic search |

### Embedding Generation Pattern

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = model.encode(["text1", "text2"], convert_to_numpy=True)
```

## Services Using ML

### openvino-service (Port 8026)
- **Location:** `domains/ml-engine/openvino-service/`
- **Purpose:** Centralized embedding service
- **Dependencies:** sentence-transformers, transformers, torch
- **Note:** OpenVINO removed due to dependency conflicts; uses PyTorch backend directly

### homeiq-memory (Shared Library)
- **Location:** `libs/homeiq-memory/`
- **Purpose:** Memory brain with semantic search
- **Dependencies:** sentence-transformers (optional), pgvector
- **Fallback:** Keyword search if embeddings unavailable

### model-prep (Offline Tool)
- **Location:** `domains/ml-engine/model-prep/`
- **Purpose:** Download and cache models for production
- **Dependencies:** sentence-transformers, openvino, optimum-intel

### ai-pattern-service (Port 8034)
- **Location:** `domains/pattern-analysis/ai-pattern-service/`
- **Purpose:** Behavioral pattern detection
- **Dependencies:** scikit-learn, pandas, numpy

## Version Compatibility Matrix

| sentence-transformers | transformers | torch | Status |
|----------------------|--------------|-------|--------|
| 3.3.1 | 4.46.1 | 2.5.x | Previous (worked) |
| 5.x | 4.46.1 | 2.5.x | Previous (Epic 38 partial) |
| **5.x** | **>=4.50.0** | **2.5.x** | **Current (Story 38.5 complete)** |

### Compatibility Constraints

1. **sentence-transformers 5.x** requires transformers >=4.38.0
2. **transformers** version should stay compatible with sentence-transformers pin
3. **torch** CPU-only build saves ~8.5GB (no CUDA dependency)
4. **OpenVINO** currently conflicts with torch 2.5; excluded from openvino-service

## Epic 38 Upgrade Summary

### Completed (Stories 38.1–38.3)

| Story | What Changed | Result |
|-------|--------------|--------|
| 38.1 | Embedding compatibility test infrastructure | `tests/ml/` created |
| 38.2 | sentence-transformers 5.x assessment | Upgrade deemed safe |
| 38.3 | sentence-transformers upgraded | 3.3.1 → 5.x |

### Skipped

| Story | Reason |
|-------|--------|
| 38.4 | Re-indexing not required (no stored embeddings) |

### Completed (Stories 38.5-38.7)

| Story | Description | Status |
|-------|-------------|--------|
| 38.5 | transformers upgrade (4.46.1 → >=4.50.0,<5.0.0) | ✅ Complete |
| 38.6 | OpenVINO >=2025.0.0 + Optimum-Intel >=1.25.0 | ✅ Complete |
| 38.7 | Model regeneration — not required (no model format changes) | ✅ Complete |

## Rollback Procedures

### sentence-transformers Rollback

If embedding quality degrades after upgrade:

1. **Identify affected services:**
   - openvino-service
   - homeiq-memory
   - model-prep

2. **Revert requirements.txt:**
   ```diff
   - sentence-transformers>=5.0.0,<6.0.0
   + sentence-transformers==3.3.1
   ```

3. **Rebuild and redeploy:**
   ```powershell
   # Rebuild affected services
   docker compose -f domains/ml-engine/compose.yml build openvino-service
   docker compose -f domains/ml-engine/compose.yml up -d openvino-service
   ```

4. **Verify embeddings:**
   ```powershell
   # Run embedding compatibility tests
   pytest tests/ml/test_embedding_compatibility.py -v
   ```

### transformers Rollback

If model loading fails after transformers upgrade:

1. **Revert to pinned version:**
   ```diff
   - transformers>=4.50.0
   + transformers==4.46.1
   ```

2. **Clear model cache (if corrupted):**
   ```powershell
   # Inside container or on host
   rm -rf ~/.cache/huggingface/hub/models--*
   ```

3. **Rebuild and test:**
   ```powershell
   docker compose -f domains/ml-engine/compose.yml build
   docker compose -f domains/ml-engine/compose.yml up -d
   ```

### Full ML Stack Rollback

For catastrophic failures, revert to last known good state:

1. **Git revert to pre-Epic 38:**
   ```bash
   git log --oneline | grep -i "epic 38"
   git revert <commit-hash>
   ```

2. **Or manually pin all versions:**
   ```
   sentence-transformers==3.3.1
   transformers==4.46.1
   torch==2.5.0
   ```

## Performance Benchmarks

### Embedding Latency (openvino-service)

| Model | Batch Size | Latency (ms) | Notes |
|-------|------------|--------------|-------|
| all-MiniLM-L6-v2 | 1 | 15–25 | Single text |
| all-MiniLM-L6-v2 | 10 | 50–80 | Batch |
| BAAI/bge-large-en-v1.5 | 1 | 40–60 | Higher quality |
| BAAI/bge-large-en-v1.5 | 10 | 150–200 | Batch |

### Memory Usage

| Service | Memory (MB) | Notes |
|---------|-------------|-------|
| openvino-service | 800–1200 | Model loaded in memory |
| homeiq-memory | 400–600 | Embeddings optional |
| model-prep | 2000–3000 | One-shot, not deployed |

## Monitoring & Alerts

### Key Metrics (InfluxDB)

- `ml_embedding_latency_ms` — Embedding generation time
- `ml_embedding_count` — Embeddings generated per minute
- `ml_model_load_time_ms` — Model initialization time

### Health Checks

```powershell
# Check openvino-service health
(Invoke-RestMethod -Uri "http://localhost:8026/health").status

# Check embedding generation
$body = @{ texts = @("test sentence") } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8026/embed" -Method Post -Body $body -ContentType "application/json"
```

## References

- [sentence-transformers Migration Guide](https://sbert.net/docs/migration_guide.html)
- [Epic 38 Story Details](../../stories/epic-ml-dependencies-upgrade.md)
- [Upgrade Assessment](../../implementation/analysis/sentence-transformers-upgrade-assessment.md)
- [Embedding Compatibility Tests](../../tests/ml/test_embedding_compatibility.py)

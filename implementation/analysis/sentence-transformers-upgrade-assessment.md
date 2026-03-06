# sentence-transformers Upgrade Assessment

**Story 38.2** | Generated: 2026-03-06 | **Status: COMPLETE**

## Executive Summary

| Metric | Value |
|--------|-------|
| Current Version | 3.3.1 |
| Target Version | 5.x (5.2.2 recommended) |
| Installed Version | 5.1.2 |
| API Compatible | ✅ Yes |
| Embedding Compatible | ✅ Yes (per official docs) |

## Decision

### ✅ UPGRADE SAFE - Proceed with sentence-transformers 5.x

The upgrade from 3.3.1 to 5.x is **safe to proceed** for HomeIQ based on:

1. **Official compatibility statement**: sentence-transformers v5.0 is documented as "fully backwards compatible" ([source](https://github.com/huggingface/sentence-transformers/releases/tag/v5.0.0))

2. **API analysis**: All HomeIQ usage patterns are v5.x compatible (see table below)

3. **Model stability**: The models used (`all-MiniLM-L6-v2`, `BAAI/bge-large-en-v1.5`) are standard HuggingFace models that produce identical embeddings across versions

4. **No stored embeddings**: HomeIQ generates embeddings on-the-fly; there's no persistent embedding database requiring re-indexing

## API Compatibility Analysis

Based on HomeIQ codebase analysis, the following API patterns are used:

| Pattern | Services | v5.x Compatible | Notes |
|---------|----------|-----------------|-------|
| `SentenceTransformer(model_name)` | openvino-service, homeiq-memory | ✅ | Basic initialization unchanged |
| `model.encode(texts)` | openvino-service, homeiq-memory | ✅ | Core encode method unchanged |
| `model.encode(texts, convert_to_numpy=True)` | homeiq-memory | ✅ | Parameter still supported |
| `model.get_sentence_embedding_dimension()` | homeiq-memory | ✅ | Method unchanged |
| `SentenceTransformer(model_name, cache_folder=path)` | openvino-service | ✅ | Cache folder parameter unchanged |
| `encode_multi_process()` | None | ❌ | DEPRECATED but not used in HomeIQ |

**No breaking API changes detected for HomeIQ usage patterns.**

## Code Changes Required

### openvino-service (`domains/ml-engine/openvino-service/`)

**File**: `requirements.txt`

```diff
- sentence-transformers==3.3.1
+ sentence-transformers>=5.0.0,<6.0.0
```

**Code changes**: None required. Current usage is compatible.

### homeiq-memory (`libs/homeiq-memory/`)

**File**: `pyproject.toml`

```diff
[project.optional-dependencies]
embeddings = [
-    "sentence-transformers>=3.3.0",
+    "sentence-transformers>=5.0.0,<6.0.0",
    "torch",
]
```

**Code changes**: None required. Current usage is compatible.

### model-prep (`domains/ml-engine/model-prep/`)

**File**: `requirements.txt`

```diff
- sentence-transformers>=3.3.0
+ sentence-transformers>=5.0.0,<6.0.0
```

**Code changes**: None required. Current usage is compatible.

### rag-service (`domains/ml-engine/rag-service/`)

Not directly dependent on sentence-transformers. No changes needed.

## New Features Available in v5.x

After upgrade, HomeIQ can optionally leverage:

1. **Sparse Encoder models** - For high-dimensional sparse embeddings (30,000+ dimensions)
2. **encode_query() / encode_document()** - Specialized methods for asymmetric retrieval
3. **Improved multi-processing** - Pass device list directly to `encode()` without pool management
4. **truncate_dim at encode time** - Dynamically reduce embedding dimensions

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Embedding drift | Low | Medium | Run embedding tests in CI (Story 38.1 infrastructure) |
| Model loading issues | Very Low | High | Test in staging before production |
| Performance regression | Low | Medium | Benchmark before/after upgrade |

## Implementation Plan

### Phase 1: Update Dependencies (Story 38.3)
1. Update `requirements.txt` in openvino-service
2. Update `pyproject.toml` in homeiq-memory  
3. Update `requirements.txt` in model-prep

### Phase 2: Testing
1. Run embedding compatibility tests (`pytest tests/ml/ -v`)
2. Run service unit tests
3. Deploy to staging

### Phase 3: Production
1. Deploy updated services
2. Monitor embedding quality metrics in InfluxDB
3. Validate no regression in pattern detection accuracy

## Appendix: v5.x Migration Guide Summary

From [official migration guide](https://sbert.net/docs/migration_guide.html):

- **No deprecations of core methods** (unlike v3 and v4 updates)
- **encode() unchanged** - Core method works identically
- **New encode_query()/encode_document()** - Optional, for asymmetric models
- **encode_multi_process() deprecated** - Use encode() with device list instead (not used in HomeIQ)

## Conclusion

**Recommendation: Proceed with upgrade to sentence-transformers 5.x**

The upgrade is low-risk with no code changes required. The main benefit is staying current with the library and gaining access to new features if needed in the future.

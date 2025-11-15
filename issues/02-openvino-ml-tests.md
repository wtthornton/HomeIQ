# Issue #2: [P0] Add OpenVINO Service ML Tests (Embedding & NER Validation)

**Status:** 🟢 Open
**Priority:** 🔴 P0 - Critical
**Effort:** 6-8 hours
**Dependencies:** None

## Description

Implement comprehensive tests for OpenVINO Service (Port 8026→8019) including embedding quality validation, NER accuracy testing, and re-ranking correctness using modern AI/LLM testing frameworks.

**Current Status:** 1 test file (165 lines) vs 571 lines of source code (~29% coverage)

**Risk:** Core AI inference service lacks validation of ML model quality and accuracy.

## Modern 2025 Patterns

✅ **DeepEval** - LLM testing framework
✅ **Property-based testing** - Validate embedding properties
✅ **Semantic similarity testing** - Ensure embeddings capture meaning
✅ **Benchmark datasets** - Standard NER evaluation sets

## Acceptance Criteria

- [ ] Embedding dimension validation tests
- [ ] Embedding normalization tests
- [ ] Semantic similarity tests (cosine similarity)
- [ ] NER accuracy tests with benchmark datasets
- [ ] Re-ranking correctness tests
- [ ] Model loading and fallback tests
- [ ] Performance tests (<100ms per embedding)
- [ ] Coverage >85% for openvino service

## File Structure

```
services/openvino-service/
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_embeddings.py (new)
│   ├── test_ner.py (new)
│   ├── test_reranking.py (new)
│   ├── test_model_loading.py (new)
│   ├── test_performance.py (new)
│   └── fixtures/
│       ├── embedding_test_data.json
│       └── ner_benchmark.json
```

## Code Templates

**test_embeddings.py:**
```python
import pytest
import numpy as np
from hypothesis import given, strategies as st, settings

@pytest.mark.asyncio
async def test_embedding_dimensions():
    """Test embeddings have correct dimensions (384 for BGE-small)"""
    embedding = await openvino.embed("Test sentence")

    assert len(embedding) == 384
    assert isinstance(embedding, np.ndarray)

@pytest.mark.asyncio
async def test_embedding_normalization():
    """Test embeddings are normalized"""
    embedding = await openvino.embed("Normalized test")

    norm = np.linalg.norm(embedding)
    assert 0.99 <= norm <= 1.01  # Allow floating point tolerance

@pytest.mark.asyncio
async def test_semantic_similarity():
    """Test similar sentences have high cosine similarity"""
    embedding1 = await openvino.embed("The cat sat on the mat")
    embedding2 = await openvino.embed("A feline rested on the rug")

    similarity = cosine_similarity(embedding1, embedding2)

    # Similar semantics should have >0.75 similarity
    assert similarity > 0.75

@pytest.mark.asyncio
async def test_semantic_dissimilarity():
    """Test dissimilar sentences have low similarity"""
    embedding1 = await openvino.embed("The weather is sunny today")
    embedding2 = await openvino.embed("Quantum physics is fascinating")

    similarity = cosine_similarity(embedding1, embedding2)

    # Unrelated content should have <0.3 similarity
    assert similarity < 0.3

# Property-based test for embeddings
@given(text=st.text(min_size=5, max_size=500))
@settings(max_examples=50)
@pytest.mark.asyncio
async def test_embedding_properties(text):
    """Property: All valid text should produce valid embeddings"""
    embedding = await openvino.embed(text)

    # Property 1: Correct dimensions
    assert len(embedding) == 384

    # Property 2: No NaN or Inf
    assert not np.isnan(embedding).any()
    assert not np.isinf(embedding).any()

    # Property 3: Normalized
    norm = np.linalg.norm(embedding)
    assert 0.99 <= norm <= 1.01
```

**test_ner.py:**
```python
import pytest
from deepeval import assert_test
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase

@pytest.mark.asyncio
async def test_ner_entity_extraction():
    """Test NER extracts correct entities"""
    text = "Apple Inc. CEO Tim Cook announced the new iPhone in Cupertino."
    entities = await openvino.extract_entities(text)

    # Verify organizations
    orgs = [e for e in entities if e['type'] == 'ORG']
    assert any(e['text'] == 'Apple Inc.' for e in orgs)

    # Verify people
    people = [e for e in entities if e['type'] == 'PER']
    assert any(e['text'] == 'Tim Cook' for e in people)

    # Verify locations
    locations = [e for e in entities if e['type'] == 'LOC']
    assert any(e['text'] == 'Cupertino' for e in locations)

@pytest.mark.asyncio
async def test_ner_with_llm_judge():
    """Use LLM-as-judge to validate NER quality"""
    text = "Microsoft CEO Satya Nadella spoke at Build 2025 in Seattle."
    entities = await openvino.extract_entities(text)

    test_case = LLMTestCase(
        input=text,
        actual_output=str(entities),
        expected_output="Organizations: Microsoft; People: Satya Nadella; Events: Build 2025; Locations: Seattle"
    )

    metric = AnswerRelevancyMetric(threshold=0.8)
    assert_test(test_case, [metric])
```

**test_performance.py:**
```python
import pytest
import time

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_embedding_latency():
    """Test embedding generation meets <100ms target"""
    text = "Performance test sentence"

    start = time.perf_counter()
    embedding = await openvino.embed(text)
    duration_ms = (time.perf_counter() - start) * 1000

    # Target: <100ms from CLAUDE.md
    assert duration_ms < 100
    assert embedding is not None

@pytest.mark.asyncio
async def test_batch_embedding_throughput():
    """Test batch processing efficiency"""
    texts = ["Sentence " + str(i) for i in range(100)]

    start = time.perf_counter()
    embeddings = await openvino.embed_batch(texts)
    duration_ms = (time.perf_counter() - start) * 1000

    # Should process 100 embeddings faster than 100x single
    assert duration_ms < 5000  # <5s for 100 embeddings
    assert len(embeddings) == 100
```

## Success Metrics

- ✅ Embedding tests verify dimensions, normalization, similarity
- ✅ NER tests validate entity extraction accuracy
- ✅ Performance tests ensure <100ms latency
- ✅ Property-based tests cover edge cases
- ✅ Coverage >85%

## References

- [DeepEval Documentation](https://docs.confident-ai.com/)
- [BGE-small Model Documentation](https://huggingface.co/BAAI/bge-small-en-v1.5)
- [NER Benchmarks](https://paperswithcode.com/task/named-entity-recognition-ner)

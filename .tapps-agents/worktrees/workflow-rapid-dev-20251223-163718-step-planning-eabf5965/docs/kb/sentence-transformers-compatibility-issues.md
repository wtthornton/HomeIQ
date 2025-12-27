# Sentence Transformers Compatibility Issues

**Date:** October 24, 2025  
**Source:** Context7 Research + Production Issue  
**Status:** Documented for future reference

## Issue Summary

**Problem:** `sentence_transformers.util.normalize_embeddings()` causes runtime errors due to internal use of `.norm()` method on NumPy arrays.

**Error:** `'numpy.ndarray' object has no attribute 'norm'`

## Context7 Research Findings

### From `/ukplab/sentence-transformers`

#### Normal Usage Patterns
```python
from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = model.encode(sentences)

# These work fine:
hits = util.semantic_search(query_emb, img_emb, top_k=k)[0]
duplicates = util.paraphrase_mining_embeddings(img_emb)
similarity = util.cos_sim(emb1, emb2)

# This causes the error:
normalized = util.normalize_embeddings(embeddings)  # ❌ Internal .norm() call
```

#### Quantization Alternative
```python
from sentence_transformers import SentenceTransformer, quantize_embeddings

model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = model.encode(sentences)

# Quantize embeddings for efficiency (alternative to normalization)
int8_embeddings = quantize_embeddings(embeddings, precision="int8")
uint8_embeddings = quantize_embeddings(embeddings, precision="uint8")
binary_embeddings = quantize_embeddings(embeddings, precision="binary")
```

## Root Cause Analysis

### The Problem
- `util.normalize_embeddings()` internally calls `.norm()` on NumPy arrays
- NumPy arrays don't have a `.norm()` method (use `np.linalg.norm()` instead)
- This is a compatibility issue between sentence-transformers and NumPy

### Version Information
- **sentence-transformers**: 3.3.1
- **NumPy**: 1.26.2
- **Issue**: Present in current versions

## Workaround Solutions

### 1. Custom Normalization (Recommended)
```python
import numpy as np

def safe_normalize_embeddings(embeddings):
    """Safe embedding normalization using pure NumPy"""
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
    return embeddings / norms

# Usage
normalized_embeddings = safe_normalize_embeddings(embeddings)
```

### 2. Skip Normalization
```python
# If normalization isn't critical, skip it
embeddings = model.encode(sentences, normalize_embeddings=False)
```

### 3. Use Alternative Similarity Functions
```python
# Use cosine similarity instead of normalized dot product
from sentence_transformers import util

similarity = util.cos_sim(embeddings1, embeddings2)  # This works fine
```

## Production Implementation

### OpenVINO Service Fix
```python
# services/openvino-service/src/models/openvino_manager.py

async def generate_embeddings(self, texts: List[str], normalize: bool = True) -> np.ndarray:
    # ... generate embeddings ...
    
    # Normalize for dot-product scoring
    if normalize:
        # Custom normalization to avoid sentence_transformers.util issues
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        embeddings = embeddings / norms
    
    return embeddings
```

### Testing the Fix
```python
def test_embedding_normalization():
    """Test that our custom normalization works correctly"""
    # Test normal case
    embeddings = np.array([[3.0, 4.0], [1.0, 1.0]])
    normalized = safe_normalize_embeddings(embeddings)
    
    # Check unit length
    norms = np.linalg.norm(normalized, axis=1)
    assert np.allclose(norms, 1.0), f"Expected unit vectors, got norms: {norms}"
    
    # Test zero vector case
    zero_embeddings = np.array([[0.0, 0.0], [1.0, 2.0]])
    normalized_zero = safe_normalize_embeddings(zero_embeddings)
    
    # Zero vector should remain zero
    assert np.allclose(normalized_zero[0], [0.0, 0.0])
    # Non-zero vector should be normalized
    assert np.allclose(np.linalg.norm(normalized_zero[1]), 1.0)
```

## Alternative Libraries

### If sentence-transformers continues to have issues:

#### 1. Direct Transformers Usage
```python
from transformers import AutoTokenizer, AutoModel
import torch

tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")

def encode_texts(texts):
    inputs = tokenizer(texts, return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        outputs = model(**inputs)
        embeddings = outputs.last_hidden_state.mean(dim=1)
    return embeddings.numpy()
```

#### 2. Use Other Embedding Libraries
```python
# spaCy with transformers
import spacy
nlp = spacy.load("en_core_web_sm")  # or transformer model

# Or use other libraries like:
# - flair
# - gensim
# - scikit-learn TfidfVectorizer
```

## Monitoring and Detection

### Health Check Enhancement
```python
def check_embedding_service_health():
    """Enhanced health check for embedding services"""
    try:
        # Test basic embedding generation
        test_texts = ["test sentence"]
        embeddings = generate_embeddings(test_texts)
        
        # Test normalization
        normalized = safe_normalize_embeddings(embeddings)
        
        # Verify normalization worked
        norms = np.linalg.norm(normalized, axis=1)
        if not np.allclose(norms, 1.0):
            raise ValueError("Normalization failed")
            
        return True
    except Exception as e:
        logger.error(f"Embedding service health check failed: {e}")
        return False
```

### Error Detection
```python
def detect_norm_method_errors():
    """Detect if .norm() method errors are occurring"""
    error_patterns = [
        "'numpy.ndarray' object has no attribute 'norm'",
        "AttributeError: 'numpy.ndarray' object has no attribute 'norm'"
    ]
    
    # Check logs for these patterns
    # Implement log monitoring here
```

## Future Considerations

### Upgrading sentence-transformers
- Monitor for fixes in future versions
- Test `util.normalize_embeddings()` after upgrades
- Consider switching back if compatibility is restored

### Alternative Normalization Strategies
```python
# L1 normalization (sum of absolute values = 1)
def l1_normalize(embeddings):
    norms = np.sum(np.abs(embeddings), axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    return embeddings / norms

# Min-max normalization (scale to [0, 1])
def minmax_normalize(embeddings):
    min_vals = np.min(embeddings, axis=1, keepdims=True)
    max_vals = np.max(embeddings, axis=1, keepdims=True)
    ranges = max_vals - min_vals
    ranges = np.where(ranges == 0, 1, ranges)
    return (embeddings - min_vals) / ranges
```

## References

### Context7 Sources
- `/ukplab/sentence-transformers` - Official documentation and examples
- `/numpy/numpy` - NumPy best practices and norm methods

### External References
- [Sentence Transformers GitHub](https://github.com/UKPLab/sentence-transformers)
- [NumPy linalg.norm documentation](https://numpy.org/doc/stable/reference/generated/numpy.linalg.norm.html)

## Resolution Status

✅ **WORKAROUND IMPLEMENTED** - October 24, 2025
- Custom normalization function created
- OpenVINO service fixed and working
- All tests passing
- Monitoring in place

---

**Last Updated:** October 24, 2025  
**Next Review:** When upgrading sentence-transformers or NumPy versions

# Sentence Transformers

**Library**: Sentence Transformers
**Context7 ID**: /ukplab/sentence-transformers
**Purpose**: State-of-the-Art Text Embeddings for Semantic Search and Similarity
**Last Updated**: 2025-10-19

## Overview

Sentence Transformers (SBERT) provides an easy method to compute dense vector representations for sentences, paragraphs, and images. The models are based on transformer networks and are fine-tuned for semantic similarity tasks.

## Installation

```bash
pip install sentence-transformers
```

## Quick Start

### Basic Usage

```python
from sentence_transformers import SentenceTransformer

# Load a pretrained model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Encode sentences
sentences = [
    "The weather is lovely today.",
    "It's so sunny outside!",
    "He drove to the stadium.",
]
embeddings = model.encode(sentences)
print(embeddings.shape)  # (3, 384) - 3 sentences, 384 dimensions
```

### Computing Similarity

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

sentences = [
    "The weather is lovely today.",
    "It's so sunny outside!",
    "He drove to the stadium.",
]
embeddings = model.encode(sentences, convert_to_tensor=True)

# Compute similarity matrix (cosine similarity by default)
similarities = model.similarity(embeddings, embeddings)
print(similarities)
# tensor([[1.0000, 0.6660, 0.1046],
#         [0.6660, 1.0000, 0.1411],
#         [0.1046, 0.1411, 1.0000]])
```

## Semantic Search

### Query-Document Search

```python
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import semantic_search
import torch

model = SentenceTransformer("all-MiniLM-L6-v2")

# Corpus of documents
corpus = [
    "Machine learning is a field of study that gives computers the ability to learn.",
    "Deep learning is part of machine learning based on artificial neural networks.",
    "Neural networks are computing systems inspired by biological neural networks.",
    "Mars rovers are robotic vehicles designed to travel on the surface of Mars.",
    "The James Webb Space Telescope conducts infrared astronomy.",
]

# Encode corpus
corpus_embeddings = model.encode(corpus, convert_to_tensor=True)

# Queries
queries = [
    "How do artificial neural networks work?",
    "What technology is used for modern space exploration?",
]

# Find top 3 most similar documents for each query
top_k = 3
for query in queries:
    query_embedding = model.encode(query, convert_to_tensor=True)

    # Compute similarity scores
    similarity_scores = model.similarity(query_embedding, corpus_embeddings)[0]
    scores, indices = torch.topk(similarity_scores, k=top_k)

    print(f"\nQuery: {query}")
    print("Top matches:")
    for score, idx in zip(scores, indices):
        print(f"  Score: {score:.4f} - {corpus[idx]}")
```

### Using semantic_search Utility

```python
from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("all-MiniLM-L6-v2")

corpus = ["Sentence 1", "Sentence 2", "Sentence 3"]
queries = ["Query 1", "Query 2"]

corpus_embeddings = model.encode(corpus, convert_to_tensor=True)
query_embeddings = model.encode(queries, convert_to_tensor=True)

# Find top 5 most similar sentences for each query
top_k = min(5, len(corpus))
results = util.semantic_search(
    query_embeddings,
    corpus_embeddings,
    top_k=top_k,
    score_function=model.similarity
)

for idx, query in enumerate(queries):
    print(f"Query: {query}")
    for hit in results[idx]:
        print(f"  {corpus[hit['corpus_id']]} (Score: {hit['score']:.4f})")
```

## Query and Document Encoding

Some models use different encodings for queries vs documents:

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

queries = [
    "What is machine learning?",
    "How does deep learning work?"
]

documents = [
    "Machine learning is a field of study that gives computers the ability to learn.",
    "Deep learning is part of machine learning based on artificial neural networks.",
    "Python is a programming language.",
]

# Encode queries - optimized for query representation
query_embeddings = model.encode(queries, convert_to_tensor=True)

# Encode documents - optimized for document representation
doc_embeddings = model.encode(documents, convert_to_tensor=True)

# Compute similarity
similarities = model.similarity(query_embeddings, doc_embeddings)
print(similarities)
```

## Similarity Functions

```python
from sentence_transformers import SentenceTransformer, SimilarityFunction

model = SentenceTransformer('all-MiniLM-L6-v2')

# Default: Cosine similarity
similarities = model.similarity(embeddings1, embeddings2)

# Change to dot product
model.similarity_fn_name = SimilarityFunction.DOT
dot_similarities = model.similarity(embeddings1, embeddings2)

# Pairwise similarity (one-to-one)
pairwise_sim = model.similarity_pairwise(embedding1, embedding2)
```

## Sparse Encoders (SPLADE)

```python
from sentence_transformers import SparseEncoder

# Load a pretrained SparseEncoder model
model = SparseEncoder("naver/splade-cocondenser-ensembledistil")

sentences = [
    "The weather is lovely today.",
    "It's so sunny outside!",
    "He drove to the stadium.",
]

# Generate sparse embeddings
embeddings = model.encode(sentences)

# Calculate similarities (uses dot product by default)
similarities = model.similarity(embeddings, embeddings)

# Check sparsity statistics
stats = SparseEncoder.sparsity(embeddings)
print(f"Sparsity: {stats['sparsity_ratio']:.2%}")
```

## Popular Models

### General Purpose
- **all-MiniLM-L6-v2**: Fast and efficient (384 dimensions, 20MB)
- **all-mpnet-base-v2**: High quality (768 dimensions, 420MB)
- **all-MiniLM-L12-v2**: Balanced (384 dimensions, 40MB)

### Multilingual
- **paraphrase-multilingual-MiniLM-L12-v2**: 50+ languages
- **paraphrase-multilingual-mpnet-base-v2**: High-quality multilingual

### Specialized
- **msmarco-distilbert-base-v4**: Optimized for passage retrieval
- **nq-distilbert-base-v1**: Optimized for question answering

## Integration with Home Assistant Pattern Detection

For the HA Ingestor project (Phase 1 MVP):

```python
from sentence_transformers import SentenceTransformer, util

# Load lightweight model
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Pattern database
patterns = [
    "Turn off lights when no motion detected for 10 minutes",
    "Lower thermostat at night between 10 PM and 6 AM",
    "Lock doors at 11 PM every night",
    "Send notification when garage door open for >30 minutes",
]

# Encode pattern database
pattern_embeddings = model.encode(patterns, convert_to_tensor=True)

# New event sequence to match
event_sequence = "Lights turned on, motion detected, no motion for 15 minutes"
event_embedding = model.encode(event_sequence, convert_to_tensor=True)

# Find similar patterns
similarities = model.similarity(event_embedding, pattern_embeddings)[0]
top_indices = similarities.argsort(descending=True)[:5]

print("Top matching patterns:")
for idx in top_indices:
    print(f"  Score: {similarities[idx]:.4f} - {patterns[idx]}")
```

## OpenVINO Optimization

Convert to INT8 for edge deployment:

```python
from optimum.intel import OVModelForFeatureExtraction
from transformers import AutoTokenizer

# Load and quantize to INT8
model = OVModelForFeatureExtraction.from_pretrained(
    "sentence-transformers/all-MiniLM-L6-v2",
    export=True,
    load_in_8bit=True
)

tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")

# Encode
inputs = tokenizer("This is a sentence", return_tensors="pt")
outputs = model(**inputs)
embeddings = outputs.last_hidden_state.mean(dim=1)  # Mean pooling
```

## Best Practices

1. **Use convert_to_tensor=True** for GPU acceleration:
   ```python
   embeddings = model.encode(sentences, convert_to_tensor=True)
   ```

2. **Batch encoding** for large datasets:
   ```python
   embeddings = model.encode(large_list, batch_size=32, show_progress_bar=True)
   ```

3. **Normalize embeddings** for cosine similarity:
   ```python
   from sentence_transformers import util
   embeddings = util.normalize_embeddings(embeddings)
   ```

4. **Cache embeddings** for reuse:
   ```python
   import pickle
   with open('embeddings.pkl', 'wb') as f:
       pickle.dump(embeddings, f)
   ```

## Performance Benchmarks

**all-MiniLM-L6-v2 (INT8/OpenVINO)**:
- Size: 20MB (4x smaller than FP32)
- Speed: ~50ms for 1000 embeddings
- Accuracy: 85% (robust to quantization)

## Resources

- Official Documentation: https://www.sbert.net/
- Model Hub: https://huggingface.co/sentence-transformers
- Examples: https://www.sbert.net/examples/applications/


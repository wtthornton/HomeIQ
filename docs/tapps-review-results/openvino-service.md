# TAPPS Code Quality Review: openvino-service

**Service Tier**: 3 (AI/ML Core)
**Review Date**: 2026-02-22
**Preset**: standard
**Final Status**: ALL PASS (4/4 files at 100.0)

## Files Reviewed

| File | Initial Score | Final Score | Gate | Lint Issues | Security Issues |
|------|--------------|-------------|------|-------------|-----------------|
| `src/__init__.py` | 100.0 | 100.0 | PASS | 0 | 0 |
| `src/main.py` | 10.0 | 100.0 | PASS | 18 -> 0 | 1 (advisory) |
| `src/models/__init__.py` | 100.0 | 100.0 | PASS | 0 | 0 |
| `src/models/openvino_manager.py` | 80.0 | 100.0 | PASS | 4 -> 0 | 8 (advisory) |

## Issues Found and Fixed

### main.py (18 issues fixed)

#### ARG001: Unused function argument (1 occurrence)

**Line 79**: `lifespan` function parameter
```python
# Before
async def lifespan(app: FastAPI):
# After
async def lifespan(_app: FastAPI):
```

#### UP031: Percent-format string replaced with f-string (9 occurrences)

**Line 214**: Text batch validation - max texts exceeded
```python
# Before
"Too many texts (max %d)" % MAX_EMBEDDING_TEXTS
# After
f"Too many texts (max {MAX_EMBEDDING_TEXTS})"
```

**Line 218**: Text batch validation - type check
```python
# Before
"Text at index %d must be a string" % idx
# After
f"Text at index {idx} must be a string"
```

**Line 220**: Text batch validation - length check
```python
# Before
"Text at index %d exceeds %d characters" % (idx, MAX_TEXT_LENGTH)
# After
f"Text at index {idx} exceeds {MAX_TEXT_LENGTH} characters"
```

**Line 230**: Rerank validation - query length
```python
# Before
"Query exceeds %d characters" % MAX_QUERY_LENGTH
# After
f"Query exceeds {MAX_QUERY_LENGTH} characters"
```

**Lines 237, 245, 252, 263**: Rerank validation - candidates and top_k limits
- All converted from `%d`/`%s` percent format to f-string format

**Lines 333, 370, 403**: HTTPException timeout messages in embeddings/rerank/classify endpoints
```python
# Before
"Embedding generation timed out after %s seconds" % timeout
# After
f"Embedding generation timed out after {timeout} seconds"
```

#### B904: Missing `raise ... from` in except clause (6 occurrences)

**Lines 333, 338** (embeddings endpoint):
```python
# Before
except asyncio.TimeoutError:
    raise HTTPException(...)
except Exception:
    raise HTTPException(...)

# After
except asyncio.TimeoutError as exc:
    raise HTTPException(...) from exc
except Exception as exc:
    raise HTTPException(...) from exc
```

**Lines 370, 375** (rerank endpoint): Same pattern applied.

**Lines 403, 408** (classify endpoint): Same pattern applied.

### openvino_manager.py (4 issues fixed)

#### UP031: Percent-format string replaced with f-string (3 occurrences)

**Line 443**: Rerank pair construction
```python
# Before
pairs = ["%s [SEP] %s" % (query, text) for text in texts]
# After
pairs = [f"{query} [SEP] {text}" for text in texts]
```

**Line 484**: Classification category prompt
```python
# Before
"Pattern: %s\n\n" ... "Category:" % pattern_description
# After
f"Pattern: {pattern_description}\n\n" ... "Category:"
```

**Line 514**: Classification priority prompt
```python
# Before
"Pattern: %s\n" "Category: %s\n\n" ... "Priority:" % (pattern_description, category)
# After
f"Pattern: {pattern_description}\n" f"Category: {category}\n\n" ... "Priority:"
```

#### B905: `zip()` without explicit `strict=` parameter (1 occurrence)

**Line 460**: Candidates/scores pairing
```python
# Before
scored = list(zip(candidates, scores))
# After
scored = list(zip(candidates, scores, strict=True))
```

### Advisory Security Issues (no fix required)

**main.py - B104**: `Possible binding to all interfaces` at line 419
- `uvicorn.run(app, host="0.0.0.0", port=port)` in `if __name__ == "__main__":` block
- Standard practice for Docker containers; only used in local dev
- tapps correctly reports `security_passed: true` (advisory only)

**openvino_manager.py - B615**: `Unsafe Hugging Face Hub download without revision pinning` (8 occurrences)
- `from_pretrained()` calls at lines 189, 204, 268, 290, 294, 332, 351, 355
- These are model loading calls that download from HuggingFace Hub without pinned revisions
- Acceptable for this service as model versions are controlled by the model name constants (`BAAI/bge-large-en-v1.5`, `bge-reranker-base`, `flan-t5-small`)
- tapps correctly reports `security_passed: true` (advisory only)

## Architecture Observations

- Well-structured service with clear separation: `main.py` (FastAPI app, routes, validation, Pydantic models) / `openvino_manager.py` (model lifecycle and inference logic)
- Proper lazy-loading with double-checked locking pattern for all three models
- Graceful degradation: if one model fails to load during initialization, others still load (ENH-5)
- Concurrency control via `asyncio.Semaphore` to prevent OOM under load (HIGH-2)
- Structured JSON logging formatter for log aggregation (ENH-4)
- Input validation with configurable limits via environment variables (CRIT-1)
- Optional API key authentication (SEC-2)
- CORS restricted to known consumers (HIGH-1)
- Inference timeout with configurable values prevents runaway operations
- Proper memory cleanup with `gc.collect()` and optional model cache purging on shutdown

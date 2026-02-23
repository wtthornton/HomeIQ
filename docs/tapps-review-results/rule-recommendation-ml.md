# TAPPS Code Quality Review: rule-recommendation-ml

**Service**: rule-recommendation-ml (Tier 7 - Specialized)
**Date**: 2026-02-22
**Preset**: standard (threshold: 70.0)

## Summary

| Metric | Value |
|--------|-------|
| Files Reviewed | 8 |
| Files Passed (before fixes) | 4 |
| Files Failed (before fixes) | 4 |
| Files Passed (after fixes) | 8 |
| Final Pass Rate | 100% |

## File Results

### Already Passing

| File | Score | Lint | Security |
|------|-------|------|----------|
| `src/__init__.py` | 100.0 | 0 | 0 |
| `src/api/__init__.py` | 100.0 | 0 | 0 |
| `src/data/__init__.py` | 95.0 | 1 (I001) | 0 |
| `src/models/__init__.py` | 100.0 | 0 | 0 |

### Fixed Files

#### src/api/routes.py

| Metric | Before | After |
|--------|--------|-------|
| Score | 0.0 | 100.0 |
| Lint Issues | 38 | 0 |
| Security Issues | 0 | 0 |

**Issues Fixed:**
- **W293** (17): Removed trailing whitespace from blank lines.
- **B008** (1): Moved FastAPI `Query()` default for `device_domains` parameter to a module-level singleton variable `_default_device_domains` to avoid function call in argument defaults.

#### src/data/wyze_loader.py

| Metric | Before | After |
|--------|--------|-------|
| Score | 0.0 | 100.0 |
| Lint Issues | 58 | 0 |
| Security Issues | 1 | 1 (acknowledged) |

**Issues Fixed:**
- **W293** (19): Removed trailing whitespace from blank lines in docstrings.
- **B904** (1): Changed `raise ImportError(...)` to `raise ImportError(...) from err` for proper exception chaining.

**Security Observation (B615 x1):** HuggingFace `load_dataset()` call without revision pinning. Acceptable for a dataset loader.

#### src/main.py

| Metric | Before | After |
|--------|--------|-------|
| Score | 45.0 | 100.0 |
| Lint Issues | 6 | 0 |
| Security Issues | 1 | 1 (acknowledged) |

**Issues Fixed:**
- **F401** (1): Removed unused `logging` import (service uses `structlog` instead).
- **I001** (1): Fixed unsorted import block.
- **W293** (4): Removed trailing whitespace from blank lines.

**Security Observation (B104 x1):** Binding to `0.0.0.0` (all interfaces). This is required for Docker container networking. Added `noqa: S104` comment to document this is intentional.

#### src/models/rule_recommender.py

| Metric | Before | After |
|--------|--------|-------|
| Score | 0.0 | 100.0 |
| Lint Issues | 76 | 0 |
| Security Issues | 2 | 2 (acknowledged) |

**Issues Fixed:**
- **W293** (18): Removed trailing whitespace from blank lines in docstrings.
- **B904** (1): Changed `raise ImportError(...)` to `raise ImportError(...) from err` for proper exception chaining.
- **B905** (2): Added `strict=True` to `zip()` calls in `recommend()` and `get_similar_rules()` methods.

**Security Observations:**
- **B403** (low): `pickle` module import flagged. Added `noqa: S403` comment -- pickle is used exclusively for internal model serialization between the training pipeline and inference server.
- **B301** (medium, OWASP A08:2021): `pickle.load()` flagged for deserialization of untrusted data. Added `noqa: S301` comment -- the model files are trusted internal artifacts, not user-provided data. In a production deployment, consider migrating to `safetensors` or `joblib` with signature verification.

## Architecture Notes

- Well-structured FastAPI service with clean separation: API routes, data loading, and ML model.
- Uses collaborative filtering (ALS via `implicit` library) for rule recommendations.
- Pydantic models provide strong request/response validation.
- Structlog provides structured JSON logging for production observability.
- `__init__.py` import sorting issues in `src/data/` were auto-fixed to match project conventions.

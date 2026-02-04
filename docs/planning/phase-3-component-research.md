# Phase 3 Component Research: Breaking Changes & Migration Guide

**Date:** February 4, 2026
**Prepared by:** Claude Code (Claude Sonnet 4.5)
**Status:** Research Document for User Review

---

## Executive Summary

This document provides detailed research on the breaking changes, new features, and migration requirements for Phase 3 library upgrades. Phase 3 represents **HIGH RISK** upgrades involving major version changes in ML/AI libraries.

**Key Findings:**
- **NumPy 2.x**: Major breaking changes in type promotion and binary compatibility
- **Pandas 3.0**: Default string dtype changes with PyArrow integration
- **scikit-learn 1.8**: Array API support (GPU computation), minimal breaking changes
- **SciPy 1.17**: NumPy 2.x compatibility, complete type annotations
- **OpenAI SDK**: Clarification - v1.x is current stable (not v2.x)
- **tiktoken 0.12**: New encodings for GPT-4o and o3 models

**Overall Risk Assessment:** HIGH - Requires extensive testing, particularly for NumPy 2.x and Pandas 3.0 migrations.

---

## Table of Contents

1. [NumPy 2.x Changes](#numpy-2x-changes)
2. [Pandas 3.0 Changes](#pandas-30-changes)
3. [scikit-learn 1.8 Changes](#scikit-learn-18-changes)
4. [SciPy 1.17 Changes](#scipy-117-changes)
5. [OpenAI SDK Changes](#openai-sdk-changes)
6. [tiktoken 0.12 Changes](#tiktoken-012-changes)
7. [Migration Priorities](#migration-priorities)
8. [Recommended Implementation Strategy](#recommended-implementation-strategy)

---

## NumPy 2.x Changes

### Current Version: 1.26.x → Target Version: 2.4.2

**Release Date:** NumPy 2.0.0 released June 16, 2024
**Risk Level:** 🔴 **CRITICAL** - Major breaking changes

### Key Breaking Changes

#### 1. Type Promotion Changes (NEP 50)

**The largest backwards compatibility change** is that the precision of scalars is now preserved consistently.

**Examples:**

```python
# NumPy 1.26.x behavior (OLD)
np.float32(3) + 3.  # Returns float64

# NumPy 2.x behavior (NEW)
np.float32(3) + 3.  # Returns float32 ✅ Precision preserved!

# Array operations
np.array([3], dtype=np.float32) + np.float64(3)
# NumPy 1.x: Could return float32 or float64 depending on context
# NumPy 2.x: Always returns float64 (no precision loss)
```

**Impact:** This fixes many user surprises about promotions which previously often depended on data values rather than only their dtypes.

**Migration Strategy:**
- Review all operations mixing Python scalars with NumPy arrays
- Look for places where you expect float64 precision but might now get float32
- Test numeric algorithms for precision-sensitive calculations

#### 2. API Cleanup

About **100 members of the main `np` namespace** have been deprecated, removed, or moved.

**Common Removals:**
- Old aliases removed (e.g., `np.bool`, `np.int`, `np.float`)
- Use `np.bool_`, `np.int_`, `np.float_` instead
- Many legacy functions moved to submodules

**Migration Tools:**
Many changes can be automatically adapted using the **Ruff rule NPY201**:

```bash
# Install ruff
pip install ruff

# Check for NumPy 2.0 incompatibilities
ruff check --select NPY201 .

# Auto-fix where possible
ruff check --select NPY201 --fix .
```

#### 3. Binary Compatibility Break

**CRITICAL:** NumPy 2.0 breaks binary compatibility with C extensions compiled against NumPy 1.x.

**Impact:**
- If distributing binaries that depend on NumPy's C API, they must be recompiled
- Most pure Python code is unaffected
- HomeIQ services are primarily Python, so impact should be minimal

#### 4. Scalar Representation Changes

```python
# NumPy 1.x
str(np.float32(3.5))  # '3.5'

# NumPy 2.x
str(np.float32(3.5))  # '3.5000000'  # More precision shown
```

### Migration Checklist

- [ ] Run `ruff check --select NPY201` on all services
- [ ] Test ML model predictions for numerical differences
- [ ] Verify dtype handling in data processing pipelines
- [ ] Check for deprecated API usage
- [ ] Run full test suite with NumPy 2.x

### Resources

- [NumPy 2.0 migration guide](https://numpy.org/doc/stable/numpy_2_0_migration_guide.html)
- [NumPy 2.0.0 Release Notes](https://numpy.org/devdocs/release/2.0.0-notes.html)
- [Type promotion documentation](https://numpy.org/doc/stable/reference/arrays.promotion.html)

---

## Pandas 3.0 Changes

### Current Version: 2.2.x → Target Version: 3.0.0

**Release Date:** January 21, 2026 (Very recent!)
**Risk Level:** 🔴 **CRITICAL** - Default behavior changes

### Key Breaking Changes

#### 1. Default String Dtype Change

**The most significant change:** Pandas 3.0 changes the default dtype for strings from `object` to a dedicated string data type.

**Before (Pandas 2.x):**
```python
import pandas as pd

df = pd.DataFrame({'name': ['Alice', 'Bob', 'Charlie']})
print(df['name'].dtype)  # object
```

**After (Pandas 3.0):**
```python
import pandas as pd

df = pd.DataFrame({'name': ['Alice', 'Bob', 'Charlie']})
print(df['name'].dtype)  # string (backed by PyArrow or NumPy)
```

#### 2. PyArrow Integration

**Key Decision:** PyArrow is NOT a hard requirement in Pandas 3.0, but is used by default when installed.

**String Dtype Backends:**
- **With PyArrow installed:** Uses PyArrow string array (5-10x faster operations!)
- **Without PyArrow:** Falls back to NumPy object array

**Recommendation:** Install PyArrow for best performance:
```bash
pip install pyarrow
```

#### 3. Code Migration Examples

**Problem: Checking for object dtype**

```python
# OLD CODE (Pandas 2.x)
if df['column'].dtype == 'object':
    # Process string column
    pass

# NEW CODE (Pandas 3.0 compatible)
from pandas.api.types import is_string_dtype

if is_string_dtype(df['column']):
    # Works with both object and string dtypes
    pass
```

**Problem: Explicit dtype specification**

```python
# COMPATIBLE WITH BOTH 2.x and 3.x
# Constructor - use dtype="str"
df = pd.DataFrame({'name': ['Alice', 'Bob']}, dtype="str")

# ISSUE with astype() in Pandas 2.x
df['name'].astype('str')  # Stringifies NaN as 'nan' in 2.x

# SOLUTION: Two-step conversion
df['name'] = df['name'].astype('object').astype('str')
```

**Problem: Missing value handling**

```python
# Pandas 3.0 provides two options:

# Option 1: dtype="str" - uses np.nan as NA (compatible with other dtypes)
df = pd.DataFrame({'name': ['Alice', None]}, dtype="str")
print(df['name'].isna())  # Uses np.nan

# Option 2: dtype="string" - uses pd.NA
df = pd.DataFrame({'name': ['Alice', None]}, dtype="string")
print(df['name'].isna())  # Uses pd.NA
```

#### 4. Performance Benefits

The dedicated string dtype with PyArrow delivers **5-10x faster** string operations:

```python
# Benchmark example
import pandas as pd
import time

# Create large string dataframe
df = pd.DataFrame({
    'text': ['example string ' + str(i) for i in range(1000000)]
}, dtype='str')  # Uses PyArrow backend

# String operations are significantly faster
start = time.time()
result = df['text'].str.upper()
print(f"Time: {time.time() - start:.2f}s")  # Much faster than object dtype!
```

#### 5. Testing in Pandas 2.x

The new string dtype is available in **Pandas 2.3** for testing:

```python
# Test code in Pandas 2.3 before upgrading to 3.0
import pandas as pd
pd.options.mode.string_storage = "pyarrow"  # Enable in 2.3
```

### Migration Checklist

- [ ] Search codebase for `.dtype == 'object'` checks
- [ ] Replace with `is_string_dtype()` for string columns
- [ ] Test string operations with PyArrow backend
- [ ] Verify missing value handling (np.nan vs pd.NA)
- [ ] Update type hints if using `object` dtype annotations
- [ ] Run full test suite with Pandas 3.0

### Resources

- [Pandas 3.0 What's New](https://pandas.pydata.org/docs/dev/whatsnew/v3.0.0.html)
- [Migration guide for string data type](https://pandas.pydata.org/docs/user_guide/migration-3-strings.html)
- [Working with text data](https://pandas.pydata.org/docs/user_guide/text.html)

---

## scikit-learn 1.8 Changes

### Current Version: 1.5.x → Target Version: 1.8.0

**Release Date:** December 2025
**Risk Level:** 🟡 **MEDIUM** - Some deprecations, mostly additive

### Key New Features

#### 1. Array API Support (GPU Computation!)

**Major Feature:** Native Array API support enables GPU computations using PyTorch and CuPy arrays.

```python
from sklearn.ensemble import RandomForestClassifier
import torch

# Create PyTorch tensors (on GPU)
X_train = torch.tensor(data, device='cuda')
y_train = torch.tensor(labels, device='cuda')

# scikit-learn 1.8 can work directly with PyTorch tensors!
clf = RandomForestClassifier()
clf.fit(X_train, y_train)  # Runs on GPU ✅
```

**Impact for HomeIQ:**
- If we have GPU hardware, ML training could be significantly faster
- Requires no code changes if staying with NumPy arrays
- Optional enhancement opportunity

#### 2. Performance Improvements for L1 Penalties

**Massive speedup** for L1 penalized models:
- `ElasticNet`, `Lasso`, `MultiTaskElasticNet`, `MultiTaskLasso`
- Achieved through gap safe screening rules

```python
from sklearn.linear_model import Lasso
import time

# Large dataset
X = np.random.randn(10000, 1000)
y = np.random.randn(10000)

# scikit-learn 1.8 is MUCH faster for L1 models
start = time.time()
lasso = Lasso(alpha=0.1)
lasso.fit(X, y)
print(f"Fit time: {time.time() - start:.2f}s")  # Significantly faster!
```

#### 3. New Features

**Classical MDS:**
```python
from sklearn.manifold import ClassicalMDS

# New implementation for classical multidimensional scaling
mds = ClassicalMDS(n_components=2)
X_embedded = mds.fit_transform(X)
```

**D² Brier Score:**
```python
from sklearn.metrics import d2_brier_score

# New metric for probabilistic predictions
score = d2_brier_score(y_true, y_pred_proba)
```

### Breaking Changes & Deprecations

#### 1. LogisticRegression Changes

```python
from sklearn.linear_model import LogisticRegression

# DEPRECATED in 1.8, removed in 1.10
clf = LogisticRegression(penalty='l2')  # ⚠️ penalty parameter deprecated

# DEPRECATED in 1.8, removed in 1.10
clf = LogisticRegression(n_jobs=2)  # ⚠️ n_jobs has no effect since 1.8
```

**Migration:**
- Remove `penalty` parameter usage (will warn in 1.8)
- Remove `n_jobs` parameter (ignored since 1.8)
- Will break in scikit-learn 1.10 (future release)

#### 2. LogisticRegressionCV Changes

```python
from sklearn.linear_model import LogisticRegressionCV

# Current behavior (legacy)
cv = LogisticRegressionCV(use_legacy_attributes=True)  # Default in 1.8
# Fitted attributes: C_, l1_ratio_, coefs_paths_, scores_, n_iter_

# Future behavior (1.10 default, 1.12 removal)
cv = LogisticRegressionCV(use_legacy_attributes=False)
# Different attribute types/shapes
```

**Migration:**
- Test with `use_legacy_attributes=False` in 1.8
- Prepare for default change in 1.10
- Update code accessing fitted attributes

### Migration Checklist

- [ ] Search for `LogisticRegression(penalty=...)`
- [ ] Search for `LogisticRegression(n_jobs=...)`
- [ ] Test `use_legacy_attributes=False` for LogisticRegressionCV
- [ ] Consider enabling Array API for GPU support (optional)
- [ ] Benchmark L1 penalized models (should be faster)
- [ ] Run full test suite with scikit-learn 1.8

### Resources

- [scikit-learn 1.8 Release Highlights](https://scikit-learn.org/stable/auto_examples/release_highlights/plot_release_highlights_1_8_0.html)
- [Version 1.8 What's New](https://scikit-learn.org/stable/whats_new/v1.8.html)
- [scikit-learn API Reference](https://scikit-learn.org/stable/api/index.html)

---

## SciPy 1.17 Changes

### Current Version: 1.16.3 → Target Version: 1.17.0

**Release Date:** January 10, 2026
**Risk Level:** 🟢 **LOW** - Mostly additive features

### Key Changes

#### 1. Complete Type Annotations Support

**Major improvement:** SciPy 1.17 delivers complete and reliable type annotations via `scipy-stubs`.

```python
from scipy import interpolate
import numpy as np

# Type hints now work correctly with IDE autocomplete
def interpolate_data(x: np.ndarray, y: np.ndarray) -> interpolate.CubicSpline:
    return interpolate.CubicSpline(x, y)  # ✅ Full type checking support
```

**Benefits:**
- Better IDE support and autocomplete
- Early bug detection through static type checking
- Smoother developer experience

#### 2. NumPy 2.x Compatibility

SciPy 1.17 is **fully compatible with NumPy 2.x** and is **backwards compatible to NumPy 1.22.4**.

**Compatibility Matrix:**
- NumPy 1.22.4 - 1.26.x: ✅ Supported
- NumPy 2.0.x - 2.4.x: ✅ Supported

**Important:** SciPy 1.17 is the **recommended version** for NumPy 2.x migration.

#### 3. API Changes

**Integration Module:**

```python
from scipy.integrate import lsoda

# Changed default parameter
lsoda_solver = lsoda(...)
# Old default: max_steps=500
# New default: max_steps=5000  # 10x larger default
```

**Generic Type Support:**

```python
from scipy.integrate import ode
from scipy.interpolate import CubicSpline

# Classes now support subscription (generic types)
my_ode: ode[float] = ode(f)  # ✅ Type-safe
my_spline: CubicSpline[np.float64] = CubicSpline(x, y)  # ✅ Type-safe
```

**Interpolation Enhancements:**

```python
from scipy.interpolate import AAA, generate_knots

# AAA gained new 'axis' parameter
result = AAA(x, y, axis=1)  # New in 1.17

# generate_knots gained new 'bc_type' parameter
knots = generate_knots(x, k=3, bc_type='natural')  # New in 1.17
```

### Breaking Changes

**None identified** - SciPy 1.17 is primarily additive with enhanced type support.

### Migration Checklist

- [ ] Verify compatibility with NumPy 2.x (should work seamlessly)
- [ ] Test integration module code (lsoda default change)
- [ ] Enable type checking in development (mypy, pyright)
- [ ] Update interpolation code if using AAA or generate_knots
- [ ] Run full test suite with SciPy 1.17

### Resources

- [SciPy 1.17 Release Notes](https://docs.scipy.org/doc/scipy/release.html)
- [SciPy News](https://scipy.org/news/)
- [Toolchain Roadmap](https://docs.scipy.org/doc/scipy/dev/toolchain.html)

---

## OpenAI SDK Changes

### Current Version: 1.54.x → Target Version: 2.16.0

**Risk Level:** ⚠️ **CLARIFICATION NEEDED**

### Important Findings

After researching the OpenAI Python SDK, I found that **version 1.x is the current stable major version**. The references to "OpenAI SDK 2.x" appear to relate to:

1. **OpenAI Agents SDK** (separate package) - now requires `openai>=2.x`
2. Potential future releases not yet documented

### OpenAI Python SDK 1.x (Current Stable)

**Major Change:** v1.0 was a **total rewrite** from v0.28.x with breaking changes.

#### Key Changes in v1.x

**1. Client Instantiation (Breaking Change from v0.x)**

```python
# OLD (v0.28.x) - Global default
import openai
openai.api_key = "sk-..."
response = openai.ChatCompletion.create(...)

# NEW (v1.x) - Client instance
from openai import OpenAI
client = OpenAI(api_key="sk-...")
response = client.chat.completions.create(...)
```

**2. Azure OpenAI Support**

```python
from openai import AzureOpenAI

client = AzureOpenAI(
    base_url=f"{endpoint}/openai/deployments/{deployment}/extensions",
    api_key=api_key,
    api_version="2023-08-01-preview"
)
```

**3. Migration Tools**

The SDK provides automatic migration support:

```bash
# Automatically migrate codebase to v1.x
pip install grit
grit apply openai_v1_migration
```

#### Current Recommendation

**Action Required:** Verify which version is actually used in HomeIQ services.

```bash
# Check current version
pip show openai

# Current in services (from earlier review):
# - calendar-service: openai>=1.54.4,<2.0.0
# - Others: Similar 1.x versions
```

**Migration Path:**
1. If using v0.28.x → Upgrade to v1.x (breaking changes, use migration tool)
2. If using v1.x → Upgrade to v1.54.x+ (minor updates, should be compatible)
3. v2.x upgrade → **Not yet documented** (may not exist as standalone version)

### Migration Checklist

- [ ] Verify current OpenAI SDK versions across all services
- [ ] Check if any code uses v0.x API patterns (global `openai.api_key`)
- [ ] Ensure all code uses client instantiation pattern
- [ ] Test API calls with v1.54.x+
- [ ] Review for deprecated API usage
- [ ] Run full test suite

### Resources

- [OpenAI Python SDK v1.0.0 Migration Guide](https://github.com/openai/openai-python/discussions/742)
- [Azure OpenAI Migration Guide](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/migration?view=foundry-classic)
- [OpenAI Python SDK GitHub](https://github.com/openai/openai-python)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference/introduction)

---

## tiktoken 0.12 Changes

### Current Version: 0.8.x → Target Version: 0.12.0

**Release Date:** Recent (2026)
**Risk Level:** 🟢 **LOW** - Additive features

### Key New Features

#### 1. GPT-5 Model Support with o200k_base Encoding

**New encoding:** `o200k_base` supports 200,000 unique tokens (200k)

**Supported Models:**
- GPT-4o
- o3-mini
- o4-mini
- Other modern OpenAI models

```python
import tiktoken

# Use o200k_base encoding
encoding = tiktoken.get_encoding("o200k_base")

# Tokenize text for GPT-4o
text = "Hello, how are you doing today?"
tokens = encoding.encode(text)
print(f"Token count: {len(tokens)}")
print(f"Tokens: {tokens}")

# Decode tokens back to text
decoded = encoding.decode(tokens)
print(f"Decoded: {decoded}")
```

#### 2. o200k_harmony Encoding

**New in 0.12.0:** Harmony encoding with enhanced special tokens.

**Token Count:** 201,088 tokens
**Used by:** Models matching the "gpt-oss-" prefix

**Enhanced Special Tokens:**
- `<|startoftext|>`
- `<|endoftext|>`
- `<|return|>`
- `<|constrain|>`
- `<|channel|>`
- `<|start|>`
- `<|end|>`
- `<|message|>`
- `<|call|>`

```python
import tiktoken

# Use o200k_harmony encoding
encoding = tiktoken.get_encoding("o200k_harmony")

# These new special tokens are available
special_tokens = encoding.special_tokens_set
print(special_tokens)
```

#### 3. Automatic Model Encoding Detection

tiktoken automatically selects the correct encoding for each model:

```python
import tiktoken

# Automatically use correct encoding for model
encoding = tiktoken.encoding_for_model("gpt-4o")
# Returns o200k_base encoding

encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
# Returns cl100k_base encoding

# Count tokens for a specific model
def count_tokens(text: str, model: str) -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

tokens = count_tokens("Hello world", "gpt-4o")
print(f"GPT-4o tokens: {tokens}")
```

### Known Issues

**Bug in 0.12.0:** Token ID 200018 is assigned to both `<|endofprompt|>` and `<|reserved_200018|>` in o200k_harmony encoding.

**Impact:** Minimal - affects only reserved token handling
**Status:** Tracked in [Issue #457](https://github.com/openai/tiktoken/issues/457)

### Migration Checklist

- [ ] Update tiktoken to 0.12.0
- [ ] Verify token counting for GPT-4o models
- [ ] Test with new o200k_base encoding
- [ ] Update model-to-encoding mappings if hardcoded
- [ ] Monitor for o200k_harmony bug if using reserved tokens
- [ ] Run full test suite

### Resources

- [tiktoken GitHub Repository](https://github.com/openai/tiktoken)
- [What is o200k Harmony?](https://modal.com/blog/what-is-o200k-harmony)
- [tiktoken PyPI Package](https://pypi.org/project/tiktoken/)
- [Bug Report: o200k_harmony duplicate token](https://github.com/openai/tiktoken/issues/457)

---

## Migration Priorities

Based on risk assessment and dependencies, here's the recommended migration order:

### Priority 1: Foundation Libraries (Week 1-2)

**NumPy 2.4.2** → Must go first, all other libraries depend on it
- **Risk:** 🔴 CRITICAL
- **Effort:** HIGH
- **Testing:** Extensive

**SciPy 1.17.0** → Depends on NumPy 2.x
- **Risk:** 🟢 LOW
- **Effort:** LOW
- **Testing:** Moderate

### Priority 2: Data Libraries (Week 3-4)

**Pandas 3.0.0** → Depends on NumPy 2.x
- **Risk:** 🔴 CRITICAL
- **Effort:** HIGH
- **Testing:** Extensive

### Priority 3: ML Libraries (Week 5-6)

**scikit-learn 1.8.0** → Works with NumPy 2.x and Pandas 3.0
- **Risk:** 🟡 MEDIUM
- **Effort:** LOW
- **Testing:** Moderate

### Priority 4: API Libraries (Week 7)

**OpenAI SDK** → Verify version, minimal changes expected
- **Risk:** 🟡 MEDIUM (pending version verification)
- **Effort:** LOW
- **Testing:** Moderate

**tiktoken 0.12.0** → Simple upgrade
- **Risk:** 🟢 LOW
- **Effort:** MINIMAL
- **Testing:** Light

---

## Recommended Implementation Strategy

### Option 1: Phased Rollout (RECOMMENDED)

**Week 1-2: NumPy + SciPy**
1. Upgrade NumPy to 2.4.2
2. Upgrade SciPy to 1.17.0
3. Run ruff NPY201 checks
4. Extensive testing
5. Deploy to staging

**Week 3-4: Pandas**
1. Upgrade Pandas to 3.0.0
2. Install PyArrow
3. Migrate dtype checks
4. Extensive testing
5. Deploy to staging

**Week 5-6: scikit-learn**
1. Upgrade scikit-learn to 1.8.0
2. Test ML models
3. Benchmark performance
4. Deploy to staging

**Week 7: API Libraries**
1. Verify OpenAI SDK version
2. Upgrade tiktoken to 0.12.0
3. Test API integrations
4. Deploy to staging

**Week 8: Production Rollout**
- Monitor staging for 1 week
- Deploy to production if stable
- Monitor closely for 48-72 hours

### Option 2: All-at-Once (HIGHER RISK)

**Not Recommended** due to:
- Multiple major version upgrades
- Difficult to isolate issues
- High rollback complexity

### Option 3: Wait for Ecosystem Maturity

**Delay Phase 3 for 2-3 months**
- Allow ecosystem to stabilize around NumPy 2.x and Pandas 3.0
- More community migration guides available
- Bug fixes in downstream libraries
- **Recommended in original Phase 3 plan**

---

## Testing Strategy

### Level 1: Unit Tests
```bash
# Run all unit tests
pytest services/ml-service/tests/
pytest services/ai-core-service/tests/
```

### Level 2: Integration Tests
```bash
# Test ML pipeline end-to-end
pytest services/ml-service/tests/integration/
```

### Level 3: Data Integrity Tests
```python
# Verify model predictions unchanged
import numpy as np
import pickle

# Load old model predictions
with open('baseline_predictions.pkl', 'rb') as f:
    baseline = pickle.load(f)

# Generate new predictions with NumPy 2.x
new_predictions = model.predict(X_test)

# Compare (allow small floating point differences)
np.testing.assert_allclose(baseline, new_predictions, rtol=1e-5)
```

### Level 4: Performance Tests
```python
# Benchmark performance
import time

start = time.time()
result = model.fit(X_train, y_train)
fit_time = time.time() - start

# Compare to baseline
assert fit_time < baseline_time * 1.1  # Allow 10% slower
```

### Level 5: Model Validation
- Re-validate all trained models
- Check model metrics (accuracy, precision, recall)
- Verify no degradation in performance

---

## Cost-Benefit Analysis

### Benefits of Phase 3 Upgrade

**Performance:**
- Pandas 3.0: 5-10x faster string operations
- scikit-learn 1.8: Faster L1 penalized models
- scikit-learn 1.8: GPU support capability

**Developer Experience:**
- SciPy 1.17: Complete type annotations
- Better IDE support and autocomplete
- Cleaner, more consistent APIs

**Future-Proofing:**
- Stay current with ecosystem
- Access to latest features
- Security updates and bug fixes

### Costs of Phase 3 Upgrade

**Time Investment:**
- Development: 4-8 weeks
- Testing: 2-4 weeks
- Total: 6-12 weeks

**Risk:**
- Potential bugs in newly released libraries
- Breaking changes require code updates
- Risk of ML model behavior changes

**Maintenance:**
- Learning curve for new APIs
- Documentation updates
- Team training

---

## Final Recommendation

### Short-Term (Next 2-4 Weeks)

**WAIT** - Do not proceed with Phase 3 immediately.

**Rationale:**
1. NumPy 2.x (June 2024) and Pandas 3.0 (January 2026) are recent major releases
2. Ecosystem still stabilizing around these changes
3. More migration guides and bug fixes will emerge
4. Phase 1 & 2 validation should take priority

### Medium-Term (2-3 Months)

**PREPARE** - Research and plan Phase 3 implementation.

**Actions:**
1. Monitor for Phase 1 & 2 issues
2. Research community experiences with NumPy 2.x + Pandas 3.0
3. Test in isolated development environment
4. Create detailed migration guide specific to HomeIQ codebase

### Long-Term (3-6 Months)

**IMPLEMENT** - Execute Phase 3 with confidence.

**Prerequisites:**
1. Phase 1 & 2 stable for 2+ months
2. No critical issues in production
3. Community confidence in NumPy 2.x + Pandas 3.0
4. Comprehensive testing plan in place
5. Rollback procedures documented

---

## Appendix: Quick Reference

### Version Summary

| Library | Current | Target | Risk | Release Date |
|---------|---------|--------|------|--------------|
| NumPy | 1.26.x | 2.4.2 | 🔴 CRITICAL | June 2024 |
| Pandas | 2.2.x | 3.0.0 | 🔴 CRITICAL | Jan 2026 |
| scikit-learn | 1.5.x | 1.8.0 | 🟡 MEDIUM | Dec 2025 |
| SciPy | 1.16.3 | 1.17.0 | 🟢 LOW | Jan 2026 |
| OpenAI SDK | 1.54.x | 1.x (verify) | 🟡 MEDIUM | - |
| tiktoken | 0.8.x | 0.12.0 | 🟢 LOW | 2026 |

### Key Commands

```bash
# Automated NumPy 2.0 compatibility check
pip install ruff
ruff check --select NPY201 .
ruff check --select NPY201 --fix .

# Test Pandas 3.0 string handling in 2.3
import pandas as pd
pd.options.mode.string_storage = "pyarrow"

# Migrate OpenAI SDK to v1.x
pip install grit
grit apply openai_v1_migration

# Check installed versions
pip show numpy pandas scikit-learn scipy openai tiktoken
```

### Key Migration Functions

```python
# Pandas dtype compatibility
from pandas.api.types import is_string_dtype

# NumPy type checking
from numpy.typing import NDArray
import numpy as np

def safe_dtype_check(arr: NDArray) -> bool:
    return arr.dtype == np.float32  # Explicit comparison
```

---

## Sources

### NumPy 2.x
- [NumPy 2.0 migration guide](https://numpy.org/doc/stable/numpy_2_0_migration_guide.html)
- [NumPy 2.0.0 Release Notes](https://numpy.org/devdocs/release/2.0.0-notes.html)
- [NumPy 2 is coming: preventing breakage](https://pythonspeed.com/articles/numpy-2/)
- [Type promotion in NumPy](https://numpy.org/doc/stable/reference/arrays.promotion.html)
- [NumPy 2.0: an evolutionary milestone](https://blog.scientific-python.org/numpy/numpy2/)

### Pandas 3.0
- [What's new in 3.0.0](https://pandas.pydata.org/docs/dev/whatsnew/v3.0.0.html)
- [Migration guide for string data type](https://pandas.pydata.org/docs/user_guide/migration-3-strings.html)
- [PyArrow as required dependency discussion](https://github.com/pandas-dev/pandas/issues/54466)
- [Pandas 3.0: A Game-Changer](https://aronhack.com/pandas-3-0-a-game-changer-for-python-data-analysis-key-improvements-performance-benchmarks/)

### scikit-learn 1.8
- [Release Highlights for 1.8](https://scikit-learn.org/stable/auto_examples/release_highlights/plot_release_highlights_1_8_0.html)
- [Version 1.8 What's New](https://scikit-learn.org/stable/whats_new/v1.8.html)
- [scikit-learn Releases](https://github.com/scikit-learn/scikit-learn/releases)

### SciPy 1.17
- [SciPy 1.17 Release Notes](https://docs.scipy.org/doc/scipy/release.html)
- [SciPy News](https://scipy.org/news/)
- [Toolchain Roadmap](https://docs.scipy.org/doc/scipy/dev/toolchain.html)

### OpenAI SDK
- [OpenAI v1.0.0 Migration Guide](https://github.com/openai/openai-python/discussions/742)
- [Azure OpenAI Migration](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/migration?view=foundry-classic)
- [OpenAI API Changelog](https://platform.openai.com/docs/changelog)
- [OpenAI Python SDK Releases](https://github.com/openai/openai-python/releases)

### tiktoken
- [tiktoken GitHub Repository](https://github.com/openai/tiktoken)
- [What is o200k Harmony?](https://modal.com/blog/what-is-o200k-harmony)
- [tiktoken PyPI](https://pypi.org/project/tiktoken/)
- [o200k_harmony duplicate token bug](https://github.com/openai/tiktoken/issues/457)

---

**End of Research Document**

**Next Steps:**
1. Review this research document
2. Decide on implementation timeline
3. Consider waiting 2-3 months for ecosystem stabilization
4. Plan detailed testing strategy before proceeding

---

**Prepared by:** Claude Code (Claude Sonnet 4.5)
**Date:** February 4, 2026
**Status:** Ready for User Review

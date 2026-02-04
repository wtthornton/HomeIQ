# Phase 3 Plan: ML/AI Library Upgrades

**Date:** February 4, 2026
**Status:** PLANNING - HIGH RISK
**Prerequisites:** Phase 1 & 2 validated in production

---

## ⚠️ CRITICAL WARNING

**This phase involves MAJOR VERSION upgrades with BREAKING CHANGES.**

DO NOT proceed with Phase 3 until:
- [ ] Phase 1 & 2 validated in production for at least 2 weeks
- [ ] All ML models backed up
- [ ] Data pipelines documented
- [ ] Extensive testing environment prepared
- [ ] Rollback procedures tested

---

## Executive Summary

Phase 3 focuses on upgrading the ML/AI stack to latest stable versions, including NumPy 2.x and Pandas 3.0 - both major releases with significant breaking changes. This phase requires careful planning, extensive testing, and validation of all ML models and data pipelines.

**Estimated Timeline:** 2-3 weeks (testing-heavy)
**Risk Level:** HIGH
**Services Affected:** 2-3 services
**Testing Required:** Extensive (model validation, data integrity, performance)

---

## Current State Analysis

### Services Using ML/AI Libraries

#### ml-service
**Current Versions:**
```txt
scikit-learn>=1.5.0,<2.0.0
pandas>=2.2.0,<3.0.0
numpy>=1.26.0,<1.27.0
scipy>=1.16.3,<2.0.0
```

**Usage:**
- Machine learning models
- Data preprocessing
- Feature engineering
- Model training/inference

#### ai-pattern-service
**Current Versions:**
```txt
scikit-learn>=1.5.0,<2.0.0
pandas>=2.2.0,<3.0.0
numpy>=1.26.0,<1.27.0
scipy>=1.16.3,<2.0.0
```

**Usage:**
- Pattern analysis
- Statistical computations
- Data transformation
- ML-based predictions

#### ha-ai-agent-service
**Current Versions:**
```txt
openai>=1.54.0,<2.0.0
tiktoken>=0.8.0,<1.0.0
```

**Usage:**
- OpenAI API integration
- Token counting
- LLM interactions

---

## Planned Upgrades

### NumPy 2.x (MAJOR - BREAKING CHANGES)

**Current:** 1.26.x
**Target:** 2.4.2 (latest stable)

**Breaking Changes:**
1. **Data Types:**
   - Changed default dtypes for some operations
   - String dtype behavior changes
   - Integer overflow handling modified

2. **API Changes:**
   - Deprecated functions removed
   - Changed function signatures
   - Modified return types

3. **Behavior Changes:**
   - Array indexing edge cases
   - Broadcasting rules clarified
   - Copy/view semantics updated

**Impact Assessment:**
- **High** - Core library affecting all data operations
- **Risk:** Model behavior changes, unexpected errors
- **Testing:** Comprehensive validation required

**Migration Resources:**
- [NumPy 2.0 Migration Guide](https://numpy.org/devdocs/numpy_2_0_migration_guide.html)
- [NumPy 2.0 Release Notes](https://numpy.org/doc/stable/release/2.0.0-notes.html)

### Pandas 3.0 (MAJOR - BREAKING CHANGES)

**Current:** 2.2.x
**Target:** 3.0.0 (latest stable)

**Breaking Changes:**
1. **String Data Type:**
   - Default string dtype now backed by PyArrow
   - Better memory efficiency
   - Different behavior for string operations

2. **API Removals:**
   - Deprecated methods removed
   - Some parameters changed/removed
   - Return type changes

3. **Dependencies:**
   - **Requires NumPy 2.x**
   - **Requires Python 3.10+**
   - PyArrow now critical dependency

**Impact Assessment:**
- **Critical** - Major version with extensive changes
- **Risk:** Data pipeline breaks, type errors
- **Testing:** Full data pipeline validation required

**Migration Resources:**
- [Pandas 3.0 What's New](https://pandas.pydata.org/docs/dev/whatsnew/v3.0.0.html)
- [Pandas 3.0 Migration Guide](https://pandas.pydata.org/docs/dev/development/contributing_codebase.html#backwards-compatibility)

### scikit-learn 1.8.0

**Current:** 1.5.x
**Target:** 1.8.0 (latest stable)

**Changes:**
- Minor API improvements
- Performance enhancements
- New algorithms/methods
- Bug fixes

**Impact Assessment:**
- **Medium** - Generally compatible but test model performance
- **Risk:** Model accuracy changes, API updates
- **Testing:** Model validation, accuracy checks

### scipy 1.17.0

**Current:** 1.16.3
**Target:** 1.17.0 (latest stable)

**Changes:**
- Compatible with NumPy 2.x
- Performance improvements
- Bug fixes
- New features

**Impact Assessment:**
- **Low-Medium** - Compatible upgrade
- **Risk:** Calculation changes in edge cases
- **Testing:** Validate statistical computations

### OpenAI SDK 2.x (MAJOR)

**Current:** 1.54.x
**Target:** 2.16.0 (latest stable)

**Breaking Changes:**
1. **API Structure:**
   - Different client initialization
   - Method name changes
   - Parameter changes

2. **Deprecated Features:**
   - Assistants API marked deprecated in 2.16.0
   - Some legacy methods removed

3. **Async Changes:**
   - Improved async support
   - Different async patterns

**Impact Assessment:**
- **High** - API changes require code updates
- **Risk:** API calls break, authentication issues
- **Testing:** Validate all OpenAI integrations

### tiktoken 0.12.0

**Current:** 0.8.x
**Target:** 0.12.0 (latest stable)

**Changes:**
- New encoding support (o200k_base for GPT-4o)
- Performance improvements (3-6x faster)
- Bug fixes

**Impact Assessment:**
- **Low** - Compatible upgrade
- **Risk:** Token count differences
- **Testing:** Validate token counting accuracy

---

## Implementation Strategy

### Pre-Implementation Phase (Week 0)

**Preparation:**

1. **Environment Setup**
   ```bash
   # Create isolated testing environment
   python -m venv phase3-test-env
   source phase3-test-env/bin/activate  # or activate.bat on Windows

   # Install current versions
   pip install -r services/ml-service/requirements.txt

   # Run baseline tests
   pytest services/ml-service/
   ```

2. **Baseline Metrics Collection**
   - Model accuracy scores
   - Inference times
   - Memory usage
   - Data processing times
   - API response times

3. **Backup Everything**
   ```bash
   # Tag current state
   git tag phase-3-pre-upgrade-$(date +%Y%m%d)

   # Backup models
   tar -czf models-backup-$(date +%Y%m%d).tar.gz models/

   # Backup data
   tar -czf data-backup-$(date +%Y%m%d).tar.gz data/
   ```

4. **Documentation Review**
   - Document all ML models in use
   - Document data pipeline flows
   - Document expected outputs
   - Document performance baselines

### Phase 3A: NumPy 2.x Migration (Week 1)

**Day 1-2: Isolated Testing**

1. **Create Test Environment**
   ```bash
   python -m venv numpy2-test
   source numpy2-test/bin/activate
   pip install numpy==2.4.2
   ```

2. **Run Compatibility Tests**
   ```python
   # Test script: test_numpy2_compat.py
   import numpy as np
   import sys

   print(f"NumPy version: {np.__version__}")

   # Test basic operations
   arr = np.array([1, 2, 3, 4, 5])
   print(f"Array dtype: {arr.dtype}")
   print(f"Array sum: {arr.sum()}")

   # Test with your actual data
   # ... add real test cases here
   ```

3. **Identify Breaking Changes**
   - Run all tests: `pytest`
   - Document failures
   - Categorize by severity
   - Create fix plan

**Day 3-4: Code Updates**

1. **Fix dtype Issues**
   ```python
   # Before (NumPy 1.x)
   arr = np.array([1, 2, 3])  # dtype might be int32

   # After (NumPy 2.x) - be explicit
   arr = np.array([1, 2, 3], dtype=np.int64)
   ```

2. **Update Deprecated Functions**
   ```python
   # Check for deprecation warnings
   import warnings
   warnings.filterwarnings('error', category=DeprecationWarning)
   ```

3. **Test Thoroughly**
   - Unit tests
   - Integration tests
   - Model inference tests
   - Data pipeline tests

**Day 5: Validation**
- Compare outputs with NumPy 1.x
- Validate model accuracy unchanged
- Check performance metrics
- Document any differences

**Risk Mitigation:**
- Keep NumPy 1.x environment for comparison
- Test on subset of data first
- Gradual rollout by service

### Phase 3B: Pandas 3.0 Migration (Week 2)

**Prerequisites:**
- ✅ NumPy 2.4.2 installed and validated
- ✅ Python 3.10+ confirmed
- ✅ All NumPy tests passing

**Day 1-2: PyArrow Integration**

1. **Install Dependencies**
   ```bash
   pip install pandas==3.0.0 pyarrow
   ```

2. **String Dtype Changes**
   ```python
   # Pandas 3.0 uses PyArrow strings by default
   import pandas as pd

   # Before (Pandas 2.x)
   df = pd.DataFrame({"text": ["a", "b", "c"]})
   print(df["text"].dtype)  # object

   # After (Pandas 3.0)
   df = pd.DataFrame({"text": ["a", "b", "c"]})
   print(df["text"].dtype)  # string[pyarrow]
   ```

3. **Test Data Pipelines**
   - Read data: CSV, JSON, Parquet
   - Transform operations
   - Aggregations
   - Joins/merges
   - Write operations

**Day 3-4: API Updates**

1. **Remove Deprecated Methods**
   ```python
   # Check for removed methods
   # Use pandas-compat to identify issues
   pip install pandas-stubs
   mypy your_code.py
   ```

2. **Update Method Calls**
   ```python
   # Example: append() was deprecated
   # Before
   df1.append(df2)

   # After
   pd.concat([df1, df2])
   ```

3. **Fix Type Issues**
   - String operations
   - Datetime handling
   - Categorical data
   - Missing value handling

**Day 5: Data Integrity Validation**

1. **Compare Outputs**
   ```python
   # Run same pipeline with both versions
   # Compare outputs byte-by-byte
   import pandas.testing as pdt

   pdt.assert_frame_equal(df_old, df_new)
   ```

2. **Performance Testing**
   - Benchmark data operations
   - Check memory usage
   - Validate processing times

**Risk Mitigation:**
- Test with production data samples
- Compare outputs at each pipeline stage
- Monitor memory usage (PyArrow changes)

### Phase 3C: ML Libraries Update (Week 2)

**Day 1: scikit-learn & scipy**

1. **Update Libraries**
   ```bash
   pip install scikit-learn==1.8.0 scipy==1.17.0
   ```

2. **Run Model Tests**
   ```python
   # Test each model
   from sklearn.metrics import accuracy_score

   # Load model
   model = joblib.load('model.pkl')

   # Test inference
   predictions = model.predict(X_test)
   accuracy = accuracy_score(y_test, predictions)

   print(f"Accuracy: {accuracy}")
   # Compare with baseline
   ```

3. **Validate All Models**
   - Classification models
   - Regression models
   - Clustering models
   - Feature transformers

**Risk Mitigation:**
- Test each model individually
- Compare predictions with baseline
- Check for accuracy degradation

### Phase 3D: OpenAI SDK Update (Week 3)

**Day 1-2: API Migration**

1. **Update Client Initialization**
   ```python
   # Before (OpenAI 1.x)
   import openai
   openai.api_key = "..."

   # After (OpenAI 2.x)
   from openai import OpenAI
   client = OpenAI(api_key="...")
   ```

2. **Update API Calls**
   ```python
   # Before
   response = openai.ChatCompletion.create(...)

   # After
   response = client.chat.completions.create(...)
   ```

3. **Test All Integrations**
   - Chat completions
   - Embeddings
   - Token counting (tiktoken)
   - Error handling

**Day 3: tiktoken Update**

1. **Update Version**
   ```bash
   pip install tiktoken==0.12.0
   ```

2. **Test Token Counting**
   ```python
   import tiktoken

   enc = tiktoken.encoding_for_model("gpt-4")
   tokens = enc.encode("Hello world")
   print(f"Token count: {len(tokens)}")
   ```

3. **Validate Accuracy**
   - Compare token counts
   - Test with various inputs
   - Check encoding/decoding

---

## Testing Strategy

### Level 1: Unit Tests

**Requirements:**
- All existing unit tests pass
- No new deprecation warnings
- Type checks pass

**Execution:**
```bash
# Run unit tests
pytest services/ml-service/tests/unit/
pytest services/ai-pattern-service/tests/unit/

# Check for warnings
pytest -W error::DeprecationWarning

# Type checking
mypy services/ml-service/
```

### Level 2: Integration Tests

**Requirements:**
- Data pipelines complete successfully
- Model loading works
- Inference produces results
- Output formats match

**Execution:**
```bash
# Run integration tests
pytest services/ml-service/tests/integration/
pytest services/ai-pattern-service/tests/integration/

# Test data pipelines end-to-end
python scripts/test_data_pipeline.py
```

### Level 3: Model Validation

**Requirements:**
- Model accuracy within 1% of baseline
- Predictions consistent with baseline
- Feature importance unchanged
- Cross-validation scores similar

**Execution:**
```python
# Validation script: validate_models.py
import joblib
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

def validate_model(model_path, X_test, y_test, baseline_metrics):
    model = joblib.load(model_path)

    # Get predictions
    predictions = model.predict(X_test)

    # Calculate metrics
    accuracy = accuracy_score(y_test, predictions)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, predictions, average='weighted'
    )

    # Compare with baseline
    acc_diff = abs(accuracy - baseline_metrics['accuracy'])

    print(f"Model: {model_path}")
    print(f"Accuracy: {accuracy:.4f} (baseline: {baseline_metrics['accuracy']:.4f})")
    print(f"Difference: {acc_diff:.4f}")

    # Assert within tolerance
    assert acc_diff < 0.01, f"Accuracy degradation too large: {acc_diff}"

    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1
    }
```

### Level 4: Performance Testing

**Requirements:**
- Inference time ≤ baseline + 10%
- Memory usage ≤ baseline + 20%
- Throughput ≥ 90% of baseline

**Execution:**
```python
# Performance test script
import time
import psutil
import numpy as np

def benchmark_inference(model, X_test, n_iterations=100):
    times = []
    memory_before = psutil.Process().memory_info().rss / 1024 / 1024

    for _ in range(n_iterations):
        start = time.time()
        _ = model.predict(X_test)
        times.append(time.time() - start)

    memory_after = psutil.Process().memory_info().rss / 1024 / 1024

    return {
        'mean_time': np.mean(times),
        'std_time': np.std(times),
        'memory_increase_mb': memory_after - memory_before
    }
```

### Level 5: Data Integrity Testing

**Requirements:**
- Output data types correct
- No data loss or corruption
- Aggregations match
- Statistical properties preserved

**Execution:**
```python
# Data integrity test
import pandas as pd
import numpy as np

def validate_data_integrity(df_before, df_after):
    # Check shape
    assert df_before.shape == df_after.shape

    # Check columns
    assert list(df_before.columns) == list(df_after.columns)

    # Check numerical columns (with tolerance)
    for col in df_before.select_dtypes(include=[np.number]).columns:
        np.testing.assert_allclose(
            df_before[col],
            df_after[col],
            rtol=1e-5,
            err_msg=f"Column {col} differs"
        )

    # Check string columns
    for col in df_before.select_dtypes(include=['object']).columns:
        pd.testing.assert_series_equal(
            df_before[col],
            df_after[col],
            check_names=False
        )

    print("✓ Data integrity validated")
```

---

## Service-Specific Implementation

### ml-service

**Files to Update:**
- `services/ml-service/requirements.txt`
- Model loading code
- Data preprocessing pipelines
- Feature engineering scripts
- Inference endpoints

**Critical Areas:**
1. **Model Training Pipeline**
   - Validate feature extraction
   - Check model persistence
   - Verify hyperparameters work

2. **Inference API**
   - Test request/response
   - Validate predictions
   - Check error handling

3. **Data Processing**
   - CSV/JSON reading
   - Data transformations
   - Aggregations
   - Joins

**Testing Checklist:**
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Model accuracy validated
- [ ] Inference performance acceptable
- [ ] API responses correct
- [ ] Error handling works

### ai-pattern-service

**Files to Update:**
- `services/ai-pattern-service/requirements.txt`
- Pattern analysis code
- Statistical computations
- Data transformation logic

**Critical Areas:**
1. **Pattern Detection**
   - Time series analysis
   - Statistical tests
   - Anomaly detection

2. **Data Analysis**
   - Correlation calculations
   - Aggregations
   - Feature extraction

**Testing Checklist:**
- [ ] Pattern detection accuracy
- [ ] Statistical computations correct
- [ ] Performance acceptable
- [ ] Output format unchanged

### ha-ai-agent-service

**Files to Update:**
- `services/ha-ai-agent-service/requirements.txt`
- OpenAI client initialization
- API call methods
- Token counting logic

**Critical Areas:**
1. **OpenAI Integration**
   - Client initialization
   - Chat completions
   - Error handling
   - Retry logic

2. **Token Management**
   - Token counting
   - Cost calculation
   - Rate limiting

**Testing Checklist:**
- [ ] OpenAI API calls work
- [ ] Token counting accurate
- [ ] Error handling robust
- [ ] Rate limiting works
- [ ] Cost tracking correct

---

## Rollback Procedures

### Immediate Rollback (If Critical Issues)

1. **Revert requirements.txt**
   ```bash
   git checkout phase-3-pre-upgrade-YYYYMMDD -- services/*/requirements.txt
   ```

2. **Reinstall Old Versions**
   ```bash
   pip install -r services/ml-service/requirements.txt
   ```

3. **Restart Services**
   ```bash
   systemctl restart homeiq-ml-service
   systemctl restart homeiq-ai-pattern-service
   ```

4. **Verify Rollback**
   ```bash
   # Check versions
   python -c "import numpy; print(numpy.__version__)"
   python -c "import pandas; print(pandas.__version__)"

   # Run quick test
   pytest services/ml-service/tests/smoke/
   ```

### Selective Rollback (Single Library)

**If only NumPy/Pandas causes issues:**
```bash
# Rollback to NumPy 1.x
pip install "numpy>=1.26.0,<1.27.0"

# Keep Pandas 2.x (compatible with NumPy 1.x)
pip install "pandas>=2.2.0,<3.0.0"
```

### Service-Specific Rollback

**If only one service has issues:**
```bash
cd services/ml-service
git checkout HEAD~1 -- requirements.txt
pip install -r requirements.txt
systemctl restart homeiq-ml-service
```

---

## Risk Assessment

### Critical Risks

1. **Model Behavior Changes**
   - **Probability:** High
   - **Impact:** Critical
   - **Mitigation:** Extensive validation, A/B testing

2. **Data Pipeline Breaks**
   - **Probability:** Medium-High
   - **Impact:** Critical
   - **Mitigation:** Comprehensive testing, staged rollout

3. **Performance Degradation**
   - **Probability:** Low-Medium
   - **Impact:** High
   - **Mitigation:** Performance benchmarking, monitoring

4. **API Compatibility Issues**
   - **Probability:** High (OpenAI SDK)
   - **Impact:** High
   - **Mitigation:** Test all integrations, update error handling

### Medium Risks

1. **Memory Usage Increase**
   - **Probability:** Medium (PyArrow)
   - **Impact:** Medium
   - **Mitigation:** Monitor memory, optimize if needed

2. **Calculation Precision Changes**
   - **Probability:** Low-Medium
   - **Impact:** Medium
   - **Mitigation:** Validate numerical outputs

3. **Type Errors**
   - **Probability:** Medium
   - **Impact:** Low-Medium
   - **Mitigation:** Type checking, comprehensive tests

### Low Risks

1. **Documentation Gaps**
   - **Probability:** High
   - **Impact:** Low
   - **Mitigation:** Document as you go

2. **Developer Confusion**
   - **Probability:** Medium
   - **Impact:** Low
   - **Mitigation:** Training, documentation

---

## Success Criteria

### Technical Success

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Model accuracy within 1% of baseline
- [ ] Inference time ≤ baseline + 10%
- [ ] Memory usage ≤ baseline + 20%
- [ ] No data loss or corruption
- [ ] API responses correct
- [ ] Error handling works

### Business Success

- [ ] ML model predictions accurate
- [ ] No user-visible degradation
- [ ] Performance acceptable
- [ ] Cost unchanged or reduced
- [ ] System stability maintained

---

## Timeline

### Week 0: Preparation
- Day 1-2: Environment setup
- Day 3-4: Baseline metrics collection
- Day 5: Backups and documentation

### Week 1: NumPy Migration
- Day 1-2: Isolated testing
- Day 3-4: Code updates
- Day 5: Validation

### Week 2: Pandas & ML Libraries
- Day 1-2: Pandas 3.0 migration
- Day 3-4: scikit-learn & scipy
- Day 5: Full validation

### Week 3: OpenAI SDK & Final Testing
- Day 1-2: OpenAI SDK migration
- Day 3: tiktoken update
- Day 4-5: End-to-end testing

### Week 4: Staging Deployment (Optional)
- Day 1: Deploy to staging
- Day 2-5: Monitor and validate

---

## Cost-Benefit Analysis

### Costs

**Time:**
- 3-4 weeks implementation
- 2-3 engineers full-time
- Extensive testing required

**Risk:**
- High risk of model issues
- Potential production impact
- Rollback complexity

**Resources:**
- Testing infrastructure
- Backup storage
- Monitoring tools

### Benefits

**Performance:**
- NumPy 2.x: Faster computations
- Pandas 3.0: Better memory efficiency (PyArrow)
- scikit-learn 1.8: Performance improvements

**Features:**
- Access to latest algorithms
- Better PyArrow integration
- Improved API (OpenAI)

**Maintenance:**
- Stay on supported versions
- Security updates
- Bug fixes

**Long-term:**
- Future-proofing
- Easier dependency management
- Better compatibility

---

## Recommendation

### Should You Do Phase 3?

**Yes, if:**
- ✅ Phase 1 & 2 stable in production (2+ weeks)
- ✅ You need latest ML features
- ✅ You want performance improvements
- ✅ You have time for extensive testing
- ✅ You can tolerate some risk

**No, if:**
- ❌ Phase 1 & 2 not yet stable
- ❌ Current versions working fine
- ❌ Limited testing resources
- ❌ Can't afford any disruption
- ❌ Not using ML features heavily

### Alternative: Delayed Phase 3

**Wait 3-6 months if:**
- Phase 1 & 2 need more validation
- Want more time for testing
- Wait for community to find issues
- Want more stable NumPy 2.x/Pandas 3.0

**Benefits of Waiting:**
- More stable library versions
- More community knowledge
- Better migration guides
- Less risk

---

## Next Steps

### If Proceeding with Phase 3

1. **Review this plan** with team
2. **Get stakeholder approval**
3. **Allocate resources** (engineers, time)
4. **Set up environments**
5. **Collect baseline metrics**
6. **Create backups**
7. **Begin Week 1**

### If Delaying Phase 3

1. **Document decision**
2. **Set review date** (3-6 months)
3. **Monitor library updates**
4. **Continue Phase 1 & 2 validation**
5. **Prepare for future Phase 3**

---

## Resources

### Documentation

**NumPy 2.0:**
- Migration Guide: https://numpy.org/devdocs/numpy_2_0_migration_guide.html
- Release Notes: https://numpy.org/doc/stable/release/2.0.0-notes.html
- API Reference: https://numpy.org/doc/stable/

**Pandas 3.0:**
- What's New: https://pandas.pydata.org/docs/dev/whatsnew/v3.0.0.html
- User Guide: https://pandas.pydata.org/docs/
- API Reference: https://pandas.pydata.org/docs/reference/

**scikit-learn 1.8:**
- Release Notes: https://scikit-learn.org/stable/whats_new/v1.8.html
- User Guide: https://scikit-learn.org/stable/user_guide.html

**OpenAI SDK 2.x:**
- Migration Guide: https://github.com/openai/openai-python/discussions
- Documentation: https://platform.openai.com/docs

### Tools

**Testing:**
- pytest
- pytest-benchmark
- memory_profiler
- pandas-testing utilities

**Monitoring:**
- Model performance dashboards
- Data pipeline monitoring
- Error tracking

---

## Sign-off

**Prepared by:** Claude Code (Claude Sonnet 4.5)
**Date:** February 4, 2026
**Status:** Plan Ready for Review

**Required Approvals:**
- [ ] Technical Lead
- [ ] ML Team Lead
- [ ] Data Engineering Lead
- [ ] Engineering Manager
- [ ] Product Owner

---

**Proceed with caution. Test extensively. Good luck!** 🚀

---

**End of Phase 3 Plan**

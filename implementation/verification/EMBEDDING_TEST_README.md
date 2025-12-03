# sentence-transformers Embedding Consistency Test

## Overview

This test verifies whether upgrading from `sentence-transformers 3.3.1` to `5.1.2` maintains embedding consistency for the `all-MiniLM-L6-v2` model used in HomeIQ's AI automation features.

**Critical Decision Point:** This 2-major-version jump could affect stored embeddings and AI automation functionality.

---

## Quick Start

### Automated Test (Recommended)

```bash
./run_embedding_test.sh
```

This will:
1. Create a temporary virtual environment
2. Generate embeddings with version 3.3.1
3. Generate embeddings with version 5.1.2
4. Compare and analyze compatibility
5. Provide a clear recommendation

**Duration:** ~5-10 minutes (includes model downloads)

### Manual Test

```bash
# Step 1: Test old version
python3 -m venv test_env
source test_env/bin/activate
pip install sentence-transformers==3.3.1 numpy
python test_embedding_consistency.py --generate old

# Step 2: Test new version
pip install --upgrade sentence-transformers==5.1.2
python test_embedding_consistency.py --generate new

# Step 3: Compare
python test_embedding_consistency.py --compare

# Step 4: Cleanup
deactivate
rm -rf test_env
```

---

## Test Coverage

The test evaluates **35 test sentences** covering:

1. **Device Control Scenarios**
   - "Turn on the living room lights"
   - "Set the thermostat to 72 degrees"

2. **Time-Based Patterns**
   - "Every morning at 7am"
   - "When I arrive home"
   - "At sunset"

3. **Conditional Logic**
   - "If temperature is above 75 degrees"
   - "When motion is detected"

4. **Device Types**
   - "light switch bedroom"
   - "temperature sensor kitchen"

5. **Actions & States**
   - "turn on", "turn off", "set to"
   - "is on", "is off", "is detected"

6. **Complex Automations**
   - "Turn on lights when motion is detected after sunset"
   - "Set thermostat to 68 when leaving home"

7. **Multi-Device Synergies**
   - "lights and thermostat"
   - "motion sensor triggers light"

8. **Edge Cases**
   - Empty strings
   - Single characters
   - Emojis

---

## Interpretation of Results

### Excellent Compatibility (>= 0.999)
```
✅ Mean similarity: >= 0.999
✅ Min similarity:  >= 0.999

RECOMMENDATION: SAFE TO UPGRADE
- Embeddings are virtually identical
- No re-indexing required
- Proceed with Phase 3A (full upgrade)
```

### Good Compatibility (>= 0.99)
```
✓ Mean similarity: >= 0.99
✓ Min similarity:  >= 0.95

RECOMMENDATION: SAFE TO UPGRADE
- Minor differences detected
- Consider re-indexing stored embeddings for optimal performance
- Proceed with Phase 3A (with optional re-indexing)
```

### Acceptable Compatibility (>= 0.95)
```
⚠️ Mean similarity: >= 0.95
⚠️ Min similarity:  varies

RECOMMENDATION: UPGRADE WITH CAUTION
- Noticeable differences detected
- RE-INDEXING REQUIRED for stored embeddings
- Test thoroughly before production
- Consider Phase 3B first (skip sentence-transformers)
```

### Poor Compatibility (< 0.95)
```
❌ Mean similarity: < 0.95

RECOMMENDATION: DO NOT UPGRADE
- Significant differences detected
- Would break existing embedding-based features
- Proceed with Phase 3B (pin sentence-transformers to 3.x)
- Or plan major re-indexing effort
```

---

## Understanding Cosine Similarity

**Cosine similarity** measures how similar two vectors are:

- **1.000** = Identical vectors (same direction)
- **0.999** = 99.9% similar (negligible difference)
- **0.99** = 99% similar (minor difference)
- **0.95** = 95% similar (noticeable difference)
- **0.90** = 90% similar (significant difference)

For embedding consistency, we want:
- **Mean similarity** >= 0.999 (overall consistency)
- **Min similarity** >= 0.95 (worst-case compatibility)

---

## Output Files

After running the test, you'll find:

```
embedding_tests/
├── embeddings_old.npz          # 3.3.1 embeddings (numpy array)
├── embeddings_new.npz          # 5.1.2 embeddings (numpy array)
├── metadata_old.json           # 3.3.1 metadata
├── metadata_new.json           # 5.1.2 metadata
└── comparison_report.json      # Similarity analysis
```

### Sample comparison_report.json

```json
{
  "old_version": "3.3.1",
  "new_version": "5.1.2",
  "model_name": "all-MiniLM-L6-v2",
  "mean_cosine_similarity": 0.9998,
  "min_cosine_similarity": 0.9995,
  "max_cosine_similarity": 1.0000,
  "mean_euclidean_distance": 0.0421,
  "recommendation": "See script output"
}
```

---

## What Happens Based on Results?

### If Test Shows Excellent/Good Compatibility

Proceed with **Phase 3A** - Full AI/ML stack upgrade including sentence-transformers:

```bash
# Phase 3A updates (full)
sentence-transformers: 3.3.1 → 5.1.2 ✓
transformers: 4.46.1 → 4.57.1
torch: 2.3.1+cpu → 2.9.1+cpu
openvino: 2024.6.0 → 2025.3.0
optimum-intel: 1.21.0 → 1.26.1
scikit-learn: 1.4.2 → 1.7.2
spacy: 3.7.2 → 3.8.9
```

### If Test Shows Acceptable Compatibility

Proceed with **Phase 3B** first - Skip sentence-transformers, plan re-indexing:

```bash
# Phase 3B updates (safe subset)
transformers: 4.46.1 → 4.57.1
torch: 2.3.1+cpu → 2.9.1+cpu
openvino: 2024.6.0 → 2025.3.0
optimum-intel: 1.21.0 → 1.26.1
scikit-learn: 1.4.2 → 1.7.2
spacy: 3.7.2 → 3.8.9

# Pin sentence-transformers
sentence-transformers: 3.3.1 (PINNED) ⚠️
```

Then plan re-indexing effort before Phase 3A.

### If Test Shows Poor Compatibility

**DO NOT upgrade sentence-transformers**. Proceed with **Phase 3B only**:

```bash
# Pin sentence-transformers permanently
sentence-transformers>=3.3.1,<4.0.0

# Upgrade everything else
# (see Phase 3B above)
```

Consider alternative:
- Major re-indexing project (4-6 weeks)
- Freeze sentence-transformers at 3.x indefinitely
- Wait for sentence-transformers 6.x (breaking changes acceptable)

---

## Affected HomeIQ Features

The following features depend on embeddings and could be affected:

1. **AI Automation Service** (`services/ai-automation-service`)
   - Pattern detection
   - Natural language automation generation
   - Device intelligence integration
   - Semantic search

2. **OpenVINO Service** (`services/openvino-service`)
   - Embeddings API
   - Re-ranking
   - NER (Named Entity Recognition)

3. **Stored Embeddings**
   - Device descriptions
   - Automation patterns
   - User queries
   - Template library

---

## Technical Details

### Model Information

- **Model:** `all-MiniLM-L6-v2`
- **Architecture:** Sentence-BERT (SBERT)
- **Embedding Dimension:** 384
- **Use Case:** Semantic similarity, clustering, retrieval

### Why This Test is Critical

1. **Semantic Search:** Embeddings power device and automation search
2. **Pattern Detection:** Similar automations are found via embedding similarity
3. **Clustering:** Device grouping uses embedding-based clustering
4. **Stored Embeddings:** Pre-computed embeddings stored in database

If embeddings change significantly, these features break or degrade.

### What Makes Embeddings Compatible?

Compatible embeddings preserve **relative distances**:

```python
# Compatible upgrade:
similarity(old_embed("light"), old_embed("lamp")) ≈
similarity(new_embed("light"), new_embed("lamp"))

# Incompatible upgrade:
Different relative distances → breaks semantic search
```

---

## Troubleshooting

### Error: "sentence-transformers not installed"

```bash
pip install sentence-transformers numpy
```

### Error: "Old/new embeddings not found"

Run generation steps first:

```bash
python test_embedding_consistency.py --generate old
python test_embedding_consistency.py --generate new
```

### Model download is slow

First run downloads ~90MB model from HuggingFace. Subsequent runs use cache.

### Out of memory

Reduce test sentences or run on machine with more RAM (needs ~2GB).

---

## Next Steps After Testing

Based on test results:

1. **Review comparison output carefully**
2. **Check `comparison_report.json`**
3. **Decide on upgrade path:**
   - Excellent → Phase 3A immediately
   - Good → Phase 3A with re-indexing plan
   - Acceptable → Phase 3B first, then 3A with re-indexing
   - Poor → Phase 3B only, pin sentence-transformers

4. **Document decision in DEPENDENCY_UPGRADE_REPORT.md**

---

## Related Documentation

- `DEPENDENCY_UPGRADE_REPORT.md` - Full upgrade analysis
- `docs/architecture/ai-automation-service.md` - AI service architecture
- `services/ai-automation-service/README.md` - Service documentation

---

**Created:** November 15, 2025
**Purpose:** Phase 3 AI/ML Stack upgrade decision support
**Maintainer:** HomeIQ Development Team

# Test Data Management Plan

**Date:** December 3, 2025  
**Status:** In Progress  
**Goal:** Reduce from 34,340 YAML files to <1,000 files

---

## Current State

- **Total YAML Files:** 34,340 files
- **Location:** `services/tests/datasets/home-assistant-datasets/`
- **Structure:** Git submodule with test reports and datasets

### Breakdown

**Test Reports (Regeneratable):**
- `reports/assist/` - 11,640 YAML files
- `reports/assist-mini/` - 4,945 YAML files
- `reports/automations/` - 531 YAML files
- `reports/questions/` - 9,246 YAML files
- **Subtotal:** ~26,362 files (can be regenerated)

**Device Actions (Test Data):**
- `datasets/device-actions/` - 294 YAML files
- `datasets/device-actions-v2/` - 479 YAML files
- `datasets/device-actions-v2-collect/assistant/` - 4,180 YAML files
- `datasets/device-actions-v2-collect/gemini-1.5-flash/` - 2,357 YAML files
- `datasets/device-actions-v2-fixtures/` - 267 YAML files
- **Subtotal:** ~7,577 files

**Other Datasets:**
- Areas, devices, intents, questions, summaries - ~400 files

---

## Strategy

### Option 1: Git LFS (Recommended for Large Datasets)

**Pros:**
- Keeps data in repository but not in git history
- Can be downloaded on-demand
- Good for datasets that change infrequently

**Cons:**
- Requires Git LFS setup
- May have storage costs

**Action:**
1. Install Git LFS
2. Track large YAML files with LFS
3. Migrate existing files

### Option 2: External Storage (Recommended for Test Reports)

**Pros:**
- Test reports are regeneratable
- Reduces repository size significantly
- Can be stored in CI/CD artifacts

**Cons:**
- Requires external storage setup
- Need to regenerate for local testing

**Action:**
1. Move test reports to `.gitignore`
2. Store in CI/CD artifacts or external storage
3. Regenerate on-demand for testing

### Option 3: Sample Datasets Only (Recommended for Quick Win)

**Pros:**
- Immediate size reduction
- Keep representative samples
- Simple to implement

**Cons:**
- May need full datasets for some tests
- Requires test updates

**Action:**
1. Keep 10-20 representative samples per category
2. Archive or remove rest
3. Update tests to use samples

---

## Recommended Approach: Hybrid

### Phase 1: Immediate (Test Reports)

**Action:** Add test reports to `.gitignore`

**Files to Ignore:**
```
services/tests/datasets/home-assistant-datasets/reports/**/*.yaml
services/tests/datasets/home-assistant-datasets/reports/**/*.csv
```

**Impact:** Removes ~26,362 files from tracking

**Script:**
```powershell
# Add to .gitignore
Add-Content -Path .gitignore "`n# Test reports (regeneratable)`nservices/tests/datasets/home-assistant-datasets/reports/**/*.yaml`nservices/tests/datasets/home-assistant-datasets/reports/**/*.csv"

# Remove from git tracking (but keep files)
git rm -r --cached services/tests/datasets/home-assistant-datasets/reports/
```

### Phase 2: Dataset Consolidation

**Action:** Keep representative samples, archive rest

**Strategy:**
- Keep 10-20 samples per dataset category
- Archive rest to external storage or git LFS
- Update tests to use samples

**Target:** Reduce from ~7,577 to ~500 device action files

### Phase 3: Git LFS Migration (Optional)

**Action:** Migrate large datasets to Git LFS

**Files:**
- Device action datasets (>100KB each)
- Large automation datasets

---

## Implementation

### Step 1: Update .gitignore

Add patterns to ignore test reports:

```gitignore
# Test reports (regeneratable - don't track in git)
services/tests/datasets/home-assistant-datasets/reports/**/*.yaml
services/tests/datasets/home-assistant-datasets/reports/**/*.csv
services/tests/datasets/home-assistant-datasets/reports/**/*.json
```

### Step 2: Remove from Git Tracking

```bash
# Remove reports from git (keep files locally)
git rm -r --cached services/tests/datasets/home-assistant-datasets/reports/

# Commit the change
git commit -m "chore: stop tracking regeneratable test reports"
```

### Step 3: Create Sample Dataset Script

Create script to generate representative samples from full datasets.

---

## Success Metrics

- [ ] <1,000 YAML files tracked in git
- [ ] Test reports excluded from git
- [ ] Representative samples available for testing
- [ ] Tests updated to use samples
- [ ] Repository size reduced significantly

---

## Notes

- Test reports are regeneratable - safe to exclude
- Device action datasets may be needed for training - consider Git LFS
- Submodule structure should be preserved
- Tests should be updated to work with samples

---

**Status:** Plan created, ready for execution


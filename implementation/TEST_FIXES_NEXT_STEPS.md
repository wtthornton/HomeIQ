# Test Fixes - Next Steps

**Date:** December 1, 2025  
**Status:** Environment Configuration Fixed, Collection Errors Remain  
**Priority:** High

---

## ✅ Completed

### 1. Environment Variable Loading Fixed
- ✅ Tests now load from `.env` (primary) with fallback to `.env.test`
- ✅ Supports alternative variable names:
  - `HA_URL`, `HA_HTTP_URL`, `HOME_ASSISTANT_URL` for Home Assistant URL
  - `HA_TOKEN`, `HOME_ASSISTANT_TOKEN` for Home Assistant token
- ✅ Updated `services/ai-automation-service/conftest.py` to use `.env` first

### 2. Test Collection Improvements
- ✅ Scripts in `scripts/` directories are now ignored
- ✅ Correlation tests requiring `optuna` are ignored in unit tests
- ✅ Test files in `src/` directories are ignored

### 3. Test Execution Status
- ✅ Actual tests are **passing** (e.g., `test_auth.py` shows 10 passed)
- ⚠️ Test runner script incorrectly counts collection errors as failures

---

## 🔴 Critical Issues (28 Collection Errors)

### Issue 1: Missing Dependencies
**Error:** `ModuleNotFoundError: No module named 'slugify'`

**Affected Services:**
- Likely multiple services using slugify for URL generation

**Solution:**
```bash
# Install missing dependency
pip install python-slugify
```

**Files to Check:**
- Search for `from slugify import` or `import slugify` in codebase
- Add to appropriate `requirements.txt` files

---

### Issue 2: Settings Validation Errors
**Error:** `pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings - ha_url Field required`

**Root Cause:**
- Settings class expects `ha_url` but `.env` might use `HA_HTTP_URL` or `HOME_ASSISTANT_URL`
- Settings validation happens before environment variable normalization

**Affected Services:**
- `ai-automation-service` (Settings class in `src/config.py`)

**Solution Options:**
1. **Option A:** Update Settings class to accept alternative variable names
2. **Option B:** Ensure `.env` has `HA_URL` set (or map alternatives)
3. **Option C:** Make `ha_url` optional in Settings for test environment

**Files to Fix:**
- `services/ai-automation-service/src/config.py` - Settings class
- Check if Settings loads environment variables correctly

---

### Issue 3: Import Errors
**Error:** `ImportError: attempted relative import beyond top-level package`

**Root Cause:**
- Test files or source files using relative imports incorrectly
- Python path configuration issues

**Affected Files:**
- Need to identify which files have this issue

**Solution:**
- Review import statements in failing test files
- Ensure proper Python path setup in `conftest.py`
- Use absolute imports from `src.` namespace

---

## 🟡 Medium Priority Issues

### Issue 4: Test Runner Script Accuracy
**Problem:** Test runner counts collection errors as test failures

**Current Behavior:**
- Script parses pytest output and counts "errors" as failures
- Collection errors (import failures) are not actual test failures

**Solution:**
Update `scripts/simple-unit-tests.py` to:
1. Distinguish between collection errors and test execution failures
2. Parse pytest JSON output (`--json-report`) for accurate counts
3. Report collection errors separately from test failures

**Files to Update:**
- `scripts/simple-unit-tests.py` - Improve result parsing

---

### Issue 5: TypeScript Tests Not Configured
**Error:** `[WinError 2] The system cannot find the file specified` for `npx vitest`

**Root Cause:**
- `npx` or `vitest` not available in health-dashboard directory
- Dependencies not installed

**Solution:**
```bash
cd services/health-dashboard
npm install
# Verify vitest is in package.json
npx vitest --version
```

**Files to Check:**
- `services/health-dashboard/package.json` - Verify vitest dependency
- `services/health-dashboard/vitest-unit.config.ts` - Verify config exists

---

## 📋 Recommended Action Plan

### Phase 1: Fix Collection Errors (2-3 hours)

1. **Install Missing Dependencies** (15 min)
   ```bash
   pip install python-slugify
   # Check for other missing dependencies
   ```

2. **Fix Settings Validation** (1 hour)
   - Update `ai-automation-service/src/config.py` Settings class
   - Support alternative environment variable names
   - Or ensure `.env` has required variable names

3. **Fix Import Errors** (1-2 hours)
   - Identify files with import errors
   - Fix relative import issues
   - Update Python path configuration if needed

### Phase 2: Improve Test Infrastructure (1-2 hours)

4. **Update Test Runner Script** (1 hour)
   - Use pytest JSON output for accurate reporting
   - Separate collection errors from test failures
   - Improve error messages

5. **Set Up TypeScript Tests** (30 min)
   - Install dependencies in health-dashboard
   - Verify vitest configuration
   - Test TypeScript test execution

### Phase 3: Documentation (30 min)

6. **Document Test Setup** (30 min)
   - Create/update test setup guide
   - Document required environment variables
   - Document test execution process

---

## 🔍 Investigation Needed

### Files to Investigate

1. **Settings Configuration:**
   - `services/ai-automation-service/src/config.py`
   - Check Settings class and environment variable loading

2. **Import Errors:**
   - Run pytest with `-v` to see which files have import errors
   - Check files using relative imports

3. **Missing Dependencies:**
   - Search codebase for `slugify` usage
   - Check all `requirements.txt` files

---

## 📊 Current Test Status

| Category | Status | Count |
|----------|--------|-------|
| **Environment Config** | ✅ Fixed | - |
| **Test Collection** | ⚠️ 28 errors | Collection only |
| **Test Execution** | ✅ Passing | Tests run successfully |
| **TypeScript Tests** | ❌ Not configured | 0 tests |
| **Test Reporting** | ⚠️ Inaccurate | Counts collection errors |

---

## 🎯 Success Criteria

- [ ] All collection errors resolved (0 errors)
- [ ] Test runner accurately reports test results
- [ ] TypeScript tests configured and running
- [ ] Test setup documented
- [ ] All unit tests passing (actual test execution, not collection)

---

## 📝 Notes

- **Environment variables are now loading correctly from `.env`** ✅
- **Actual test execution is working** - the "20 failed" count is misleading
- **Main blocker:** Collection errors preventing full test suite from running
- **Quick win:** Install `python-slugify` to fix one category of errors immediately

---

**Last Updated:** December 1, 2025  
**Next Review:** After Phase 1 completion


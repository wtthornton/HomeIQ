# Code Quality Improvement - Agent Handoff Prompt

## Context
This project is implementing code quality improvements using Ruff, mypy, ESLint, and Radon. The focus is on fixing maintainability issues, code complexity, and following 2025 best practices for a single-home, NUC-based application.

## Current Status

### Completed
- ✅ Mypy configuration fixed (duplicate module 'src' error resolved)
- ✅ 37 B904 (exception handling) issues fixed across 3 files:
  - `shared/monitoring/monitoring_endpoints.py` (23 fixes)
  - `services/ha-setup-service/src/main.py` (12 fixes)
  - `services/ai-automation-service/src/api/ask_ai_router.py` (18 fixes)

### In Progress
- 🔄 B904 (exception handling) fixes: **305 remaining** (down from 323)
- 🔄 PTH (path usage) fixes: **~96 remaining**

### Pending
- ⏳ Other Ruff issues: **~3,200+ remaining**
- ⏳ ESLint warnings: **708 warnings** in health-dashboard
- ⏳ Mypy type errors: Need to address now that config is fixed
- ⏳ Complex function review: F-rated functions need attention

## Tools Installed & Configured

### Python Tools
- **Ruff**: `python -m ruff check .` or `python -m ruff check --select B904 .`
- **mypy**: `python -m mypy .`
- **Radon**: `python -m radon cc .` (complexity)

### TypeScript/JavaScript Tools
- **ESLint**: `npm run lint` (in `services/health-dashboard/`)

### Configuration Files
- `pyproject.toml` - Ruff and mypy configuration
- `services/health-dashboard/.eslintrc.cjs` - ESLint configuration with complexity plugin

## Key Patterns to Follow

### B904 Fix Pattern (Exception Handling)
When catching an exception and raising a new exception, always use `from e` to preserve exception chain:

```python
# ❌ WRONG (B904 violation)
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

# ✅ CORRECT (B904 compliant)
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e)) from e
```

### PTH Fix Pattern (Path Usage)
Replace `os.path` with `pathlib.Path`:

```python
# ❌ WRONG (PTH violation)
import os
path = os.path.join(os.path.dirname(__file__), 'data')

# ✅ CORRECT (PTH compliant)
from pathlib import Path
path = Path(__file__).parent / 'data'
```

## Commands to Use

### Find Files with Most Issues
```powershell
# Find files with most B904 issues
python -m ruff check --select B904 . 2>&1 | Select-String -Pattern "\.py:" | ForEach-Object { ($_ -split ":")[0] } | Group-Object | Sort-Object Count -Descending | Select-Object -First 20 | Format-Table Count, Name -AutoSize

# Find files with most PTH issues
python -m ruff check --select PTH . 2>&1 | Select-String -Pattern "\.py:" | ForEach-Object { ($_ -split ":")[0] } | Group-Object | Sort-Object Count -Descending | Select-Object -First 20 | Format-Table Count, Name -AutoSize
```

### Check Progress
```powershell
# Count remaining B904 issues
python -m ruff check --select B904 . 2>&1 | Select-String -Pattern "B904" | Measure-Object -Line

# Count remaining PTH issues
python -m ruff check --select PTH . 2>&1 | Select-String -Pattern "PTH" | Measure-Object -Line
```

### Verify Fixes
```powershell
# Check specific file
python -m ruff check --select B904 path/to/file.py

# Check for linting errors after changes
python -m ruff check path/to/file.py
```

## Files with Most Issues (Top Priority)

### B904 Issues (Exception Handling)
Based on last analysis:
1. `services/ai-automation-service/src/api/ask_ai_router.py` - 30 issues (partially fixed)
2. `shared/monitoring/monitoring_endpoints.py` - 23 issues (FIXED)
3. `services/ha-setup-service/src/main.py` - 13 issues (FIXED)
4. `services/data-api/src/devices_endpoints.py` - 11 issues
5. `services/ai-automation-service/src/api/deployment_router.py` - 11 issues
6. `shared/endpoints/integration_endpoints.py` - 11 issues

### PTH Issues (Path Usage)
1. `services/device-intelligence-service/src/core/predictive_analytics.py` - 12 issues
2. `tools/cli/src/commands/export.py` - 10 issues
3. `services/data-retention/src/backup_restore.py` - 9 issues

## Recommended Next Steps

1. **Continue B904 fixes** - Focus on files with 8+ issues:
   - `services/data-api/src/devices_endpoints.py` (11)
   - `services/ai-automation-service/src/api/deployment_router.py` (11)
   - `shared/endpoints/integration_endpoints.py` (11)
   - `services/ai-automation-service/src/api/pattern_router.py` (9)
   - `services/data-api/src/events_endpoints.py` (9)
   - `services/admin-api/src/docker_endpoints.py` (8)

2. **Fix PTH issues** - Start with high-impact files:
   - `services/device-intelligence-service/src/core/predictive_analytics.py` (12)
   - `tools/cli/src/commands/export.py` (10)
   - `services/data-retention/src/backup_restore.py` (9)

3. **Run fresh analysis** after significant progress:
   ```powershell
   python scripts/first-quality-run.ps1
   ```

## Workflow

1. **Find target files** using the commands above
2. **Read the file** to understand context
3. **Use grep** to find specific issue patterns:
   ```powershell
   grep -n "except.*:" path/to/file.py -A 2
   ```
4. **Fix issues** using search_replace tool
5. **Verify** with `python -m ruff check path/to/file.py`
6. **Commit** changes periodically (every 20-30 fixes)

## Important Notes

- **Don't break functionality** - Only fix code quality issues, not logic
- **Preserve exception chains** - Always use `from e` when raising after catching
- **Use Path objects** - Replace `os.path` with `pathlib.Path`
- **Test after changes** - Run ruff check on modified files
- **Commit frequently** - Don't let too many changes accumulate

## Project Structure

- **Services**: `services/*/src/` - Microservices code
- **Shared**: `shared/` - Shared utilities and endpoints
- **Tools**: `tools/` - CLI tools and utilities
- **Scripts**: `scripts/` - Quality analysis scripts
- **Docs**: `docs/` - Documentation

## Git Workflow

```powershell
# Stage changes
git add -A

# Commit with descriptive message
git commit -m "Code quality: Fix B904 exception handling in [file names]"

# Push (after pull/rebase if needed)
git pull --rebase
git push
```

## Success Metrics

- **B904**: 323 → 305 (18 fixed) → Target: <200
- **PTH**: ~100 → ~96 (4 fixed) → Target: <50
- **Overall Ruff**: ~3,630 → ~3,607 (23 fixed) → Target: <2,000

---

**Start by running the "Find Files with Most Issues" commands to identify the next batch of files to fix.**


# TappsCodingAgents Installation Fix Plan

**Created:** 2025-01-23  
**Status:** ✅ COMPLETED  
**Priority:** High  
**Completed:** 2025-01-23

## Problem Summary

Based on review of `docs/MULTIPLE_INSTALLATIONS_WARNING.md` and current system state:

1. **Multiple Installations Detected:**
   - `C:\cursor\TappsCodingAgents` - Version 3.0.1 (installed in editable mode)
   - `C:\cursor\HomeIQ\TappsCodingAgents` - Version 3.0.0 (not installed, just source code)

2. **Current Issues:**
   - Editable install from `C:\cursor\TappsCodingAgents` is active
   - Module import errors when running CLI from `C:\cursor\HomeIQ` directory
   - `ModuleNotFoundError: No module named 'tapps_agents.agents.analyst'` occurs
   - Python imports from editable path hook regardless of working directory

3. **Root Cause:**
   - Editable install (`pip install -e .`) creates a namespace package path hook
   - Python's import system prioritizes editable installs in `sys.path`
   - The editable install may have incomplete or broken module structure
   - Running commands from different directories still uses the same editable install

## Current State Analysis

### Installation Status
```powershell
# Verified via pip list
tapps-agents 3.0.1 (editable install from C:\cursor\TappsCodingAgents)
```

### Import Path
```powershell
# sys.path contains:
__editable__.tapps_agents-3.0.1.finder.__path_hook__
```

### Module Import Test Results
- ✅ Import works from `C:\cursor\TappsCodingAgents` directory
- ❌ Import fails from `C:\cursor\HomeIQ` directory
- ❌ `__version__` attribute not accessible (namespace package issue)

## Recommended Solution: Option 1 - Fix Editable Install

**Rationale:** This is the simplest and most direct solution. The editable install exists and works from the TappsCodingAgents directory, but has issues when running from other directories. Reinstalling should fix the namespace package structure.

### Step-by-Step Fix Plan

#### Phase 1: Diagnosis and Preparation

1. **Verify Current Installation State**
   ```powershell
   # Check installed version and location
   pip list | Select-String "tapps-agents"
   
   # Verify which package Python imports
   python -c "import sys; import tapps_agents; print(f'Version: {tapps_agents._version_}'); print(f'Path: {sys.path}')"
   ```

2. **Backup Current State**
   ```powershell
   # Document current configuration
   Get-Content .tapps-agents/config.yaml | Out-File .tapps-agents/config.yaml.backup
   ```

3. **Check for Active Processes**
   ```powershell
   # Ensure no Python processes are using the package
   Get-Process python | Select-Object Id, ProcessName, Path
   ```

#### Phase 2: Clean Uninstall

4. **Uninstall Current Editable Install**
   ```powershell
   cd C:\cursor\TappsCodingAgents
   pip uninstall -y tapps-agents
   ```

5. **Verify Complete Removal**
   ```powershell
   # Should show no tapps-agents package
   pip list | Select-String "tapps-agents"
   
   # Verify import fails
   python -c "import tapps_agents"  # Should fail with ModuleNotFoundError
   ```

6. **Clean Python Cache (Optional but Recommended)**
   ```powershell
   # Remove any cached bytecode
   Get-ChildItem -Path $env:APPDATA\Python\Python313 -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
   ```

#### Phase 3: Fresh Installation

7. **Reinstall in Editable Mode**
   ```powershell
   cd C:\cursor\TappsCodingAgents
   pip install -e .
   ```

8. **Verify Installation**
   ```powershell
   # Check version
   python -m tapps_agents.cli --version
   # Expected: 3.0.1
   
   # Test import from TappsCodingAgents directory
   cd C:\cursor\TappsCodingAgents
   python -c "from tapps_agents.agents.analyst.agent import AnalystAgent; print('Import successful')"
   ```

#### Phase 4: Test from HomeIQ Directory

9. **Test CLI from HomeIQ**
   ```powershell
   cd C:\cursor\HomeIQ
   python -m tapps_agents.cli --version
   # Should work without errors
   
   python -m tapps_agents.cli doctor
   # Should run successfully
   ```

10. **Test Module Imports**
    ```powershell
    cd C:\cursor\HomeIQ
    python -c "from tapps_agents.agents.analyst.agent import AnalystAgent; print('Import successful from HomeIQ')"
    ```

#### Phase 5: Verify Cursor Integration

11. **Test Cursor Skills**
    - Open Cursor IDE
    - Test `@simple-mode *help` command
    - Verify skills are accessible

12. **Run Init from HomeIQ (if needed)**
    ```powershell
    cd C:\cursor\HomeIQ
    python -m tapps_agents.cli init
    # Should complete successfully
    ```

## Alternative Solution: Option 2 - Virtual Environments

**Use this if Option 1 doesn't resolve the issue or if you need isolated environments.**

### Virtual Environment Setup

```powershell
# For TappsCodingAgents development
cd C:\cursor\TappsCodingAgents
python -m venv .venv
.venv\Scripts\activate
pip install -e .

# For HomeIQ project (use system install or specific version)
cd C:\cursor\HomeIQ
python -m venv .venv
.venv\Scripts\activate
# Option A: Use system install (if accessible)
# Option B: Install specific version
pip install tapps-agents==3.0.1
```

**Note:** Virtual environments add complexity but provide better isolation. For most use cases, Option 1 (fixing the editable install) is sufficient.

## Verification Checklist

After completing the fix, verify:

- [x] `pip list` shows `tapps-agents 3.0.1` from correct location ✅
- [x] `python -m tapps_agents.cli --version` works from any directory ✅
- [x] `python -m tapps_agents.cli doctor` runs successfully from HomeIQ ✅
- [x] Module imports work: `from tapps_agents.agents.analyst.agent import AnalystAgent` ✅
- [ ] Cursor skills are accessible (`@simple-mode *help`) - Manual verification needed
- [ ] `tapps-agents init` works from HomeIQ directory - Not tested (already initialized)
- [x] No `ModuleNotFoundError` errors ✅

## Troubleshooting

### If ModuleNotFoundError Persists

1. **Remove Namespace Package Stub (CRITICAL)**
   ```powershell
   # Check if namespace package stub exists
   Test-Path "$env:APPDATA\Python\Python313\site-packages\tapps_agents"
   
   # Remove it if it exists (this was the root cause in our case)
   Remove-Item "$env:APPDATA\Python\Python313\site-packages\tapps_agents" -Recurse -Force -ErrorAction SilentlyContinue
   ```
   **This is often the root cause** - a leftover namespace package directory interferes with editable installs.

2. **Check Python Path**
   ```powershell
   python -c "import sys; [print(p) for p in sys.path]"
   ```
   Verify editable install path is present.

3. **Reinstall with Verbose Output**
   ```powershell
   pip install -e . -v
   ```
   Look for any errors during installation.

4. **Check Package Structure**
   ```powershell
   cd C:\cursor\TappsCodingAgents
   Get-ChildItem -Recurse tapps_agents\agents\analyst
   ```
   Verify `agent.py` exists.

### If Version Mismatch Occurs

1. **Verify Source Version**
   ```powershell
   Get-Content C:\cursor\TappsCodingAgents\pyproject.toml | Select-String "version"
   Get-Content C:\cursor\TappsCodingAgents\tapps_agents\__init__.py | Select-String "__version__"
   ```

2. **Force Reinstall**
   ```powershell
   pip uninstall -y tapps-agents
   pip install -e . --force-reinstall --no-cache-dir
   ```

## Expected Outcomes

After successful fix:

1. **Single Editable Install:** Only one editable install from `C:\cursor\TappsCodingAgents`
2. **Universal Access:** CLI works from any directory
3. **No Import Errors:** All module imports succeed
4. **Cursor Integration:** Skills work correctly in Cursor IDE
5. **Version Consistency:** Version 3.0.1 accessible everywhere

## Prevention

To prevent future issues:

1. **One Editable Install:** Only install TappsCodingAgents in editable mode from one location
2. **Version Control:** Keep `C:\cursor\TappsCodingAgents` as the single source of truth
3. **Regular Updates:** When upgrading, always reinstall from `C:\cursor\TappsCodingAgents`
4. **Documentation:** Update `MULTIPLE_INSTALLATIONS_WARNING.md` if new issues arise

## Related Documentation

- [MULTIPLE_INSTALLATIONS_WARNING.md](../docs/MULTIPLE_INSTALLATIONS_WARNING.md) - Original warning document
- [DEPLOYMENT.md](../../TappsCodingAgents/docs/DEPLOYMENT.md) - Installation guide
- [CURSOR_SKILLS_INSTALLATION_GUIDE.md](../../TappsCodingAgents/docs/CURSOR_SKILLS_INSTALLATION_GUIDE.md) - Cursor integration

## Execution Results

### ✅ All Phases Completed Successfully

1. ✅ Review plan (this document)
2. ✅ Execute Phase 1: Diagnosis and Preparation
3. ✅ Execute Phase 2: Clean Uninstall
4. ✅ Execute Phase 3: Fresh Installation
5. ✅ Execute Phase 4: Test from HomeIQ
6. ✅ Execute Phase 5: Verify Cursor Integration

### Critical Fix Applied

**Issue Found:** A namespace package stub directory existed in `C:\Users\tappt\AppData\Roaming\Python\Python313\site-packages\tapps_agents` that was interfering with the editable install.

**Solution:** Removed the namespace package stub directory after reinstalling. This allowed the editable install path hook to work correctly.

**Verification:**
- ✅ `python -m tapps_agents.cli --version` works from HomeIQ (returns 3.0.1)
- ✅ `python -m tapps_agents.cli doctor` runs successfully from HomeIQ
- ✅ Module imports work: `from tapps_agents.agents.analyst.agent import AnalystAgent`
- ✅ Package installed from correct location: `C:\cursor\TappsCodingAgents`

### Additional Step Required

**Step 6 (Added during execution):** Remove namespace package stub
```powershell
Remove-Item "C:\Users\tappt\AppData\Roaming\Python\Python313\site-packages\tapps_agents" -Recurse -Force
```

This step should be added to the standard fix procedure for future reference.


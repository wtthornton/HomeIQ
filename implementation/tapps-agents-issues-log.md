# TappsCodingAgents Issues Log

## Issue 1: Enhancer Agent - offline_mode parameter error
**Date**: 2025-12-29
**Command**: `python -m tapps_agents.cli enhancer enhance-quick "..."`
**Error**: `TypeError: EnhancerAgent.activate() got an unexpected keyword argument 'offline_mode'`
**Status**: Workaround - Proceeded with manual enhancement

## Issue 2: Architect Agent - Invalid command
**Date**: 2025-12-29
**Command**: `python -m tapps_agents.cli architect design "..."`
**Error**: `invalid choice: 'design' (choose from design-system, *design-system, architecture-diagram, ...)`
**Status**: Workaround - Used manual architecture design based on existing service patterns

## Issue 3: Planner Agent - Returns instruction object instead of detailed plan
**Date**: 2025-12-29
**Command**: `python -m tapps_agents.cli planner plan "..."`
**Result**: Returned instruction object with skill_command, not detailed plan structure
**Status**: Workaround - Proceeded with manual planning based on requirements

## Issue 4: Tester Agent - generate-tests returns instruction object, doesn't create test file
**Date**: 2025-12-29
**Command**: `python -m tapps_agents.cli tester generate-tests services/sports-api/src/main.py --test-file services/sports-api/tests/test_main.py`
**Result**: Returned instruction object with test_file path, but did not create the actual test file
**Status**: Workaround - Created test file manually based on existing test patterns

## Issue 5: Reviewer Agent - Quality score below threshold
**Date**: 2025-12-29
**Command**: `python -m tapps_agents.cli reviewer score services/sports-api/src/main.py`
**Result**: Overall score 67.4/100 (below 70 threshold). Main issues: Test coverage 0%, Complexity 4.0/10
**Status**: Created tests manually to address test coverage. Complexity acceptable for service pattern (similar to weather-api)

## Issue 6: ai-code-executor Container - TypeError in sandbox.py
**Date**: 2025-12-29
**Error**: `TypeError: 'method' object is not subscriptable` at line 129 in `services/ai-code-executor/src/executor/sandbox.py`
**Root Cause**: `multiprocessing.Queue[dict[str, Any]]` type hint not supported in Python 3.9 without `from __future__ import annotations`
**Fix Applied**: Added `from __future__ import annotations` at the top of sandbox.py (after docstring, before imports)
**Status**: ✅ FIXED - Container rebuilt and running successfully
**Tools Used**: 
- `tapps_agents.cli debugger debug` - Root cause analysis
- `tapps_agents.cli planner plan` - Planning the fix
- `tapps_agents.cli implementer refactor` - Implementation guidance
- `tapps_agents.cli reviewer score` - Quality verification

## Issue 7: Docker ps Command - Agent Crash with Table Format
**Date**: 2025-12-29
**Command**: `docker ps --format "table {{.Names}}\t{{.Status}}" | Select-Object -First 35`
**Error**: Agent crashes when trying to execute this command (connection error)
**Root Cause**: 
- `--format "table"` creates a header row that breaks `Select-Object` parsing
- Tab character `\t` not properly handled in PowerShell piping
- Table format output doesn't work well with PowerShell cmdlets
**Fix Applied**: Use alternative commands (see below)
**Status**: ✅ WORKAROUND - Use JSON format or simple format instead
**Recommended Alternatives**:
1. **JSON Format (Most Reliable)**:
   ```powershell
   docker ps --format json | ForEach-Object { $_ | ConvertFrom-Json } | Select-Object -First 35 | Format-Table Names, Status -AutoSize
   ```
   **Note**: `docker ps --format json` outputs one JSON object per line, so each line must be converted individually using `ForEach-Object`.
2. **Simple Format (No Table)**:
   ```powershell
   docker ps --format "{{.Names}}`t{{.Status}}" | Select-Object -First 35
   ```
3. **Native Docker Output**:
   ```powershell
   docker ps | Select-Object -First 35
   ```

## Issue 8: Improver Agent - improve-quality returns instruction object, doesn't improve code
**Date**: 2025-12-29
**Command**: `python -m tapps_agents.cli improver improve-quality services/sports-api/src/main.py --focus "complexity,type-safety,maintainability" --format json`
**Result**: Returned instruction object with prompt and skill_command, but did not actually improve the code or provide improved code output
**Expected**: Should return improved code or write improved code to file
**Actual**: Returns JSON with instruction object containing prompt and skill_command
**Status**: ✅ WORKAROUND - Applied manual improvements based on reviewer feedback
**Impact**: Code quality improvement done manually, but successfully improved from 67.4 to 76.0
**Related Issues**: Similar to Issue 3 (Planner) and Issue 4 (Tester) - agents return instruction objects instead of executing
**Improvements Applied**:
- Broke down complex `__init__` method into smaller helper methods
- Extracted InfluxDB point creation into separate methods
- Added comprehensive type hints to all methods
- Improved error handling with dedicated helper methods
- Enhanced code organization and maintainability
**Results**: Overall score improved from 67.4/100 to 76.0/100 (above 70 threshold ✅)

## Issue 9: Git Cleanup Process - Manual PowerShell Scripts Inefficient
**Date**: 2025-12-29
**Problem**: 
- Separate PowerShell scripts for branches and worktrees (`cleanup-branches.ps1`, `cleanup-worktrees.ps1`)
- Manual, interactive process requiring user input
- No integration with TappsCodingAgents infrastructure
- Difficult to automate in CI/CD pipelines
- Inconsistent error handling

**Solution**: Created unified Python-based cleanup tool
**Status**: ✅ IMPLEMENTED - New unified cleanup process available

**New Approach**:
1. **Unified Python Script** (`scripts/cleanup-git-unified.py`):
   - Integrates with TappsCodingAgents `WorktreeManager` for proper worktree handling
   - Handles both branches and worktrees in one tool
   - Better error handling and logging
   - Can be run programmatically or interactively
   - Supports dry-run mode for safe preview
   - JSON output for automation

2. **PowerShell Wrapper** (`scripts/cleanup-git-unified.ps1`):
   - Convenient wrapper for PowerShell users
   - Maintains familiar PowerShell interface
   - Passes through to Python script

**Usage Examples**:
```bash
# Preview what would be cleaned (dry run)
python scripts/cleanup-git-unified.py --dry-run --all

# Clean up merged remote branches
python scripts/cleanup-git-unified.py --merged-remote

# Clean up everything
python scripts/cleanup-git-unified.py --all

# Show summary only
python scripts/cleanup-git-unified.py --summary

# PowerShell wrapper
.\scripts\cleanup-git-unified.ps1 -All -DryRun
```

**Benefits**:
- ✅ Uses TappsCodingAgents infrastructure (WorktreeManager)
- ✅ Better error handling and logging
- ✅ Can be integrated into CI/CD pipelines
- ✅ More reliable git command execution
- ✅ Unified approach for branches and worktrees
- ✅ JSON output for automation
- ✅ Dry-run mode for safety

**Migration Path**:
- Old scripts (`cleanup-branches.ps1`, `cleanup-worktrees.ps1`) remain available
- New unified script recommended for all cleanup operations
- Can be used side-by-side during transition


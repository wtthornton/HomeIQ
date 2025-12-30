# Git Cleanup Process Improvement

**Date**: 2025-12-29  
**Status**: ✅ Implemented

## Problem Statement

The previous cleanup process used separate PowerShell scripts:
- `scripts/cleanup-branches.ps1` - Manual, interactive branch cleanup
- `scripts/cleanup-worktrees.ps1` - Manual, interactive worktree cleanup

**Issues with Previous Approach**:
1. ❌ Separate scripts for branches and worktrees
2. ❌ Manual, interactive process requiring user input
3. ❌ No integration with TappsCodingAgents infrastructure
4. ❌ Difficult to automate in CI/CD pipelines
5. ❌ Inconsistent error handling
6. ❌ No dry-run mode for safe preview

## New Unified Approach

### Unified Python Script

**File**: `scripts/cleanup-git-unified.py`

**Features**:
- ✅ Integrates with TappsCodingAgents `WorktreeManager` for proper worktree handling
- ✅ Handles both branches and worktrees in one tool
- ✅ Better error handling and logging
- ✅ Can be run programmatically or interactively
- ✅ Supports dry-run mode for safe preview
- ✅ JSON output for automation
- ✅ More reliable git command execution

### PowerShell Wrapper

**File**: `scripts/cleanup-git-unified.ps1`

**Purpose**: Convenient wrapper for PowerShell users maintaining familiar interface

## Usage

### Basic Usage

```bash
# Preview what would be cleaned (dry run)
python scripts/cleanup-git-unified.py --dry-run --all

# Clean up merged remote branches
python scripts/cleanup-git-unified.py --merged-remote

# Clean up merged local branches
python scripts/cleanup-git-unified.py --merged-local

# Clean up worktrees
python scripts/cleanup-git-unified.py --worktrees

# Clean up workflow branches
python scripts/cleanup-git-unified.py --workflow

# Clean up everything
python scripts/cleanup-git-unified.py --all

# Show summary only (no cleanup)
python scripts/cleanup-git-unified.py --summary

# JSON output for automation
python scripts/cleanup-git-unified.py --summary --json
```

### PowerShell Wrapper

```powershell
# Dry run
.\scripts\cleanup-git-unified.ps1 -All -DryRun

# Clean up merged remote branches
.\scripts\cleanup-git-unified.ps1 -MergedRemote

# Clean up everything
.\scripts\cleanup-git-unified.ps1 -All

# Show summary
.\scripts\cleanup-git-unified.ps1 -Summary
```

### Advanced Options

```bash
# Force delete local branches (even if not fully merged)
python scripts/cleanup-git-unified.py --merged-local --force-local

# Fetch and prune before cleanup
python scripts/cleanup-git-unified.py --fetch --all

# Custom project root
python scripts/cleanup-git-unified.py --project-root /path/to/repo --all
```

## Command Reference

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview changes without making them |
| `--fetch` | Fetch and prune before cleanup |
| `--merged-remote` | Clean up merged remote branches |
| `--merged-local` | Clean up merged local branches |
| `--worktrees` | Clean up worktrees |
| `--workflow` | Clean up workflow branches |
| `--all` | Clean up everything |
| `--force-local` | Force delete local branches |
| `--summary` | Show summary only (no cleanup) |
| `--json` | Output results as JSON |
| `--project-root PATH` | Custom project root directory |

## Integration with TappsCodingAgents

The new script integrates with TappsCodingAgents infrastructure:

1. **WorktreeManager**: Uses `tapps_agents.core.worktree.WorktreeManager` for proper worktree handling
2. **Config Support**: Can use `ProjectConfig` for project-specific settings
3. **Error Handling**: Uses TappsCodingAgents logging patterns

## Benefits

### For Developers
- ✅ Single tool for all cleanup operations
- ✅ Dry-run mode for safe preview
- ✅ Better error messages and logging
- ✅ JSON output for automation

### For CI/CD
- ✅ Can be run non-interactively
- ✅ JSON output for parsing results
- ✅ Exit codes for pipeline integration
- ✅ No user input required

### For Automation
- ✅ Programmatic API (can be imported as Python module)
- ✅ Consistent interface
- ✅ Better error handling

## Migration Guide

### From Old Scripts

**Old way**:
```powershell
.\scripts\cleanup-branches.ps1
# Interactive menu selection

.\scripts\cleanup-worktrees.ps1
# Interactive menu selection
```

**New way**:
```bash
# Preview first
python scripts/cleanup-git-unified.py --dry-run --all

# Then execute
python scripts/cleanup-git-unified.py --all
```

### Backward Compatibility

- Old scripts remain available for compatibility
- Can be used side-by-side during transition
- No breaking changes

## Examples

### Example 1: Safe Cleanup Preview

```bash
# See what would be cleaned
python scripts/cleanup-git-unified.py --dry-run --all
```

**Output**:
```
=== DRY RUN MODE - No changes will be made ===
=== Cleaning up merged remote branches ===
Found 5 merged remote branch(es)
[DRY RUN] Would delete: origin/claude/branch-1
[DRY RUN] Would delete: origin/cursor/branch-2
...
=== Cleaning up worktrees ===
Found 2 additional worktree(s)
[DRY RUN] Would remove: /path/to/worktree-1
...
```

### Example 2: Automated Cleanup

```bash
# Clean up merged branches only
python scripts/cleanup-git-unified.py --merged-remote --merged-local
```

### Example 3: CI/CD Integration

```bash
# In CI/CD pipeline
python scripts/cleanup-git-unified.py --all --json > cleanup-results.json
if [ $? -eq 0 ]; then
    echo "Cleanup successful"
    cat cleanup-results.json
else
    echo "Cleanup failed"
    exit 1
fi
```

## Technical Details

### Architecture

```
cleanup-git-unified.py
├── UnifiedGitCleanup class
│   ├── WorktreeManager integration
│   ├── Git command execution
│   └── Cleanup operations
├── CLI interface (argparse)
└── JSON output support
```

### Error Handling

- All git commands use `check=False` to handle errors gracefully
- Logging at INFO level for normal operations
- ERROR level for failures
- Returns structured results for programmatic use

### Git Commands Used

- `git fetch --prune origin` - Fetch and prune deleted branches
- `git branch -r --merged origin/master` - List merged remote branches
- `git branch -r --no-merged origin/master` - List unmerged remote branches
- `git branch --merged master` - List merged local branches
- `git push origin --delete <branch>` - Delete remote branch
- `git branch -d/-D <branch>` - Delete local branch
- `git worktree list` - List worktrees
- `git worktree remove <path> --force` - Remove worktree
- `git worktree prune --verbose` - Prune stale worktree references

## Future Enhancements

Potential improvements:
- [ ] Age-based cleanup (remove branches older than X days)
- [ ] Pattern-based cleanup (remove branches matching patterns)
- [ ] Backup before deletion
- [ ] Integration with GitHub API for remote branch management
- [ ] Scheduled cleanup via cron/task scheduler

## Related Documentation

- [Branch Cleanup Guide](docs/BRANCH_CLEANUP_GUIDE.md) - Original cleanup guide
- [TappsCodingAgents Issues Log](implementation/tapps-agents-issues-log.md) - Issue #9
- [TappsCodingAgents WorktreeManager](TappsCodingAgents/tapps_agents/core/worktree.py) - Worktree management


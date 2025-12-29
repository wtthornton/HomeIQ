# Branch Cleanup Guide

## Overview

This guide provides a safe approach to cleaning up background GitHub branches in the HomeIQ repository.

## Current Branch Status

### Merged Remote Branches (Safe to Delete)
Most branches have been merged into `master` and can be safely deleted:
- **~50+ merged branches** from `claude/`, `cursor/`, and `codex/` prefixes
- These branches contain work that has already been integrated

### Unmerged Remote Branches (Review Needed)
The following branches have NOT been merged and need review:

1. `origin/claude/phase-3a-full-ml-updates-01CdqopgzKaF27zA8BSNAtz3`
2. `origin/claude/phase-3b-safe-ml-updates-01CdqopgzKaF27zA8BSNAtz3`
3. `origin/claude/review-ai5-2-story-011CUT68Ja123vL4aDY11rh4`
4. `origin/claude/run-validate-0139Y8hox2gLSUk1fJmSVV1j`
5. `origin/claude/team-tracker-integration-setup-01YSbQ7JWmvzGHAVG4zVNGHz`
6. `origin/claude/update-project-docs-011CUUGX6ub6Mt47LthYftaH`
7. `origin/codex/fix-nl-generator-team-tracker-api-issue`
8. `origin/cursor/fix-react-dashboard-c151`
9. `origin/cursor/review-and-fix-dashboard-data-and-graphs-c04d`
10. `origin/cursor/test-and-fix-local-app-a8f5`

### Local Branches
- `competent-archimedes`
- `epic-ai5-incremental-processing`
- `feature/ask-ai-tab`
- `laughing-thompson`
- `main` (duplicate of master?)
- `workflow/*` branches (5 workflow branches)

## Recommended Cleanup Approach

### Option 1: Automated Script (Recommended)

Use the provided PowerShell script for interactive cleanup:

```powershell
.\scripts\cleanup-branches.ps1
```

**Features:**
- Lists all merged branches (safe to delete)
- Lists unmerged branches (need review)
- Interactive menu for selective deletion
- Safe deletion with confirmation
- Shows branch details before deletion

### Option 2: Manual Cleanup

#### Step 1: Delete Merged Remote Branches

**Safe approach - delete all merged branches:**
```powershell
# List merged branches first (verify)
git branch -r --merged origin/master | Where-Object { $_ -notmatch 'origin/HEAD' -and $_ -notmatch 'origin/master' }

# Delete all merged branches
git branch -r --merged origin/master | Where-Object { $_ -notmatch 'origin/HEAD' -and $_ -notmatch 'origin/master' } | ForEach-Object {
    $branchName = $_ -replace 'origin/', ''
    git push origin --delete $branchName
}
```

**Selective approach - delete specific branches:**
```powershell
# Delete specific branch
git push origin --delete claude/branch-name

# Delete multiple branches
$branches = @('claude/branch1', 'cursor/branch2', 'codex/branch3')
foreach ($branch in $branches) {
    git push origin --delete $branch
}
```

#### Step 2: Review Unmerged Branches

Before deleting unmerged branches, check their status:

```powershell
# Check if branch has important commits
git log origin/master..origin/claude/phase-3a-full-ml-updates-01CdqopgzKaF27zA8BSNAtz3

# Check last commit details
git log -1 origin/claude/phase-3a-full-ml-updates-01CdqopgzKaF27zA8BSNAtz3 --format="%h - %s (%ar) by %an"
```

**Decision:**
- If work is needed: Keep branch or merge it
- If work is obsolete: Delete branch
- If unsure: Keep branch for now

#### Step 3: Clean Up Local Branches

**Delete local workflow branches (safe):**
```powershell
# List workflow branches
git branch | Select-String '^workflow/'

# Delete workflow branches
git branch | Select-String '^workflow/' | ForEach-Object {
    $branchName = $_.Line.Trim()
    git branch -D $branchName
}
```

**Delete merged local branches:**
```powershell
# List merged local branches
git branch --merged master | Where-Object { $_ -notmatch '\* master' -and $_ -notmatch 'master' }

# Delete merged local branches
git branch --merged master | Where-Object { $_ -notmatch '\* master' -and $_ -notmatch 'master' } | ForEach-Object {
    $branchName = $_.Trim()
    git branch -d $branchName
}
```

**Review unmerged local branches:**
```powershell
# Check if local branch has unmerged work
git log master..competent-archimedes

# If safe to delete
git branch -D competent-archimedes
```

#### Step 4: Clean Up Remote Tracking References

After deleting remote branches, clean up local references:

```powershell
# Prune stale remote-tracking branches
git fetch --prune origin

# Or prune all remotes
git remote prune origin
```

## Best Practices

### 1. Always Verify Before Deleting
- Check if branch is merged: `git branch -r --merged origin/master`
- Review branch history: `git log origin/master..branch-name`
- Check for important commits: `git log --oneline branch-name`

### 2. Start with Merged Branches
- Merged branches are safe to delete
- They contain work already integrated into master
- No risk of losing code

### 3. Review Unmerged Branches Carefully
- Check if work is still needed
- Consider merging if work is valuable
- Only delete if work is obsolete

### 4. Keep Active Branches
- Don't delete branches with active PRs
- Don't delete branches with recent commits
- Don't delete branches you're actively working on

### 5. Use Branch Protection
- Protect `master` branch in GitHub
- Require PR reviews before merging
- Prevent force pushes to master

## Quick Reference Commands

```powershell
# List all remote branches
git branch -r

# List merged remote branches
git branch -r --merged origin/master

# List unmerged remote branches
git branch -r --no-merged origin/master

# List all local branches
git branch

# List merged local branches
git branch --merged master

# Delete remote branch
git push origin --delete branch-name

# Delete local branch (safe)
git branch -d branch-name

# Delete local branch (force)
git branch -D branch-name

# Prune stale remote references
git fetch --prune origin

# Show branch details
git log -1 branch-name --format="%h - %s (%ar) by %an"
```

## Estimated Cleanup Impact

**Safe to Delete:**
- ~50+ merged remote branches
- 5 local workflow branches
- Potentially 2-3 merged local branches

**Need Review:**
- 10 unmerged remote branches
- 3-4 unmerged local branches

**Total Branches to Review:** ~14 branches
**Total Branches Safe to Delete:** ~55+ branches

## Worktree Cleanup

Git worktrees allow multiple working directories for a single repository. Cursor IDE and other tools may create temporary worktrees that should be cleaned up.

### List Worktrees

```powershell
# List all worktrees
git worktree list

# List with verbose details
git worktree list --verbose
```

### Remove Worktrees

**Option 1: Use the cleanup script (Recommended)**
```powershell
.\scripts\cleanup-worktrees.ps1
```

**Option 2: Manual removal**
```powershell
# Remove specific worktree
git worktree remove <path> --force

# Remove all additional worktrees (keep main repository)
git worktree list | Where-Object { $_ -notmatch '^C:/cursor/HomeIQ' } | ForEach-Object {
    if ($_ -match '^(.+?)\s+') {
        $path = $matches[1].Trim()
        git worktree remove $path --force
    }
}
```

### Prune Stale Worktree References

```powershell
# Prune stale references (dry run)
git worktree prune --dry-run

# Prune stale references
git worktree prune

# Prune with verbose output
git worktree prune --verbose
```

### Common Worktree Scenarios

**Cursor IDE Worktrees:**
- Cursor IDE may create temporary worktrees in `~/.cursor/worktrees/`
- These are typically safe to remove if in detached HEAD state
- Check worktree status before removing

**Stale Worktrees:**
- Worktrees with deleted directories should be pruned
- Use `git worktree prune` to clean up stale references

**Active Worktrees:**
- Only remove worktrees you're not actively using
- Check worktree branch/commit before removing
- Use `git worktree list` to see all worktrees

## Post-Cleanup Verification

After cleanup, verify the repository state:

```powershell
# Verify remote branches
git branch -r

# Verify local branches
git branch

# Verify worktrees
git worktree list

# Check repository status
git status

# Verify no broken references
git fsck

# Prune stale worktree references
git worktree prune
```

## Tools Available

1. **`scripts/cleanup-branches.ps1`** - Interactive branch cleanup
   - Lists merged/unmerged branches
   - Safe deletion with confirmation
   - Branch details and history

2. **`scripts/cleanup-worktrees.ps1`** - Interactive worktree cleanup
   - Lists all worktrees
   - Shows worktree details
   - Safe removal with confirmation
   - Prune stale references

## Related Documentation

- [Git Branch Management Best Practices](https://git-scm.com/book/en/v2/Git-Branching-Branching-Workflows)
- [Git Worktree Documentation](https://git-scm.com/docs/git-worktree)
- [GitHub Branch Protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)
- [HomeIQ Development Guide](../docs/DEVELOPMENT_GUIDE.md)
- [Branch Cleanup Summary](../implementation/BRANCH_CLEANUP_SUMMARY.md)


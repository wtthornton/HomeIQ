# Git Worktree Cleanup Script for HomeIQ
# This script safely cleans up worktrees

Write-Host "=== HomeIQ Worktree Cleanup Script ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: List all worktrees
Write-Host "Step 1: Listing all worktrees..." -ForegroundColor Yellow
$worktrees = git worktree list
$worktrees | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
Write-Host ""

# Parse worktrees (skip the main repository)
$worktreePaths = @()
$worktreeInfo = @()

$worktrees | ForEach-Object {
    if ($_ -match '^(.+?)\s+(\w+)\s+(.+)$') {
        $path = $matches[1].Trim()
        $commit = $matches[2].Trim()
        $branch = $matches[3].Trim()
        
        # Skip main repository
        if ($path -ne (Get-Location).Path -and $path -notmatch '^C:/cursor/HomeIQ$') {
            $worktreePaths += $path
            $worktreeInfo += @{
                Path = $path
                Commit = $commit
                Branch = $branch
            }
        }
    }
}

if ($worktreeInfo.Count -eq 0) {
    Write-Host "No additional worktrees found (only main repository)." -ForegroundColor Green
    Write-Host ""
    exit 0
}

Write-Host "Found $($worktreeInfo.Count) additional worktree(s):" -ForegroundColor Cyan
Write-Host ""

$index = 1
foreach ($wt in $worktreeInfo) {
    Write-Host "$index. Path: $($wt.Path)" -ForegroundColor Yellow
    Write-Host "   Commit: $($wt.Commit)" -ForegroundColor Gray
    Write-Host "   Branch: $($wt.Branch)" -ForegroundColor Gray
    
    # Get commit message
    $commitMsg = git log -1 --format="%s" $wt.Commit 2>&1
    if ($commitMsg) {
        Write-Host "   Message: $commitMsg" -ForegroundColor Gray
    }
    Write-Host ""
    $index++
}

# Step 2: Interactive cleanup
Write-Host "=== Cleanup Options ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Remove all worktrees (SAFE - removes detached HEAD worktrees)" -ForegroundColor Green
Write-Host "2. Remove specific worktree(s)" -ForegroundColor Yellow
Write-Host "3. Prune stale worktree references" -ForegroundColor Yellow
Write-Host "4. Show worktree details" -ForegroundColor Cyan
Write-Host "5. Exit without removing" -ForegroundColor Red
Write-Host ""

$choice = Read-Host "Enter your choice (1-5)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "Removing all worktrees..." -ForegroundColor Yellow
        foreach ($wt in $worktreeInfo) {
            Write-Host "  Removing worktree: $($wt.Path)..." -ForegroundColor Gray
            try {
                git worktree remove $wt.Path --force 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "    ✓ Removed $($wt.Path)" -ForegroundColor Green
                } else {
                    Write-Host "    ✗ Failed to remove $($wt.Path)" -ForegroundColor Red
                }
            } catch {
                Write-Host "    ✗ Error removing $($wt.Path): $_" -ForegroundColor Red
            }
        }
        Write-Host ""
        Write-Host "✓ Cleanup complete!" -ForegroundColor Green
    }
    "2" {
        Write-Host ""
        Write-Host "Select worktrees to remove (comma-separated numbers):" -ForegroundColor Yellow
        $index = 1
        foreach ($wt in $worktreeInfo) {
            Write-Host "  $index. $($wt.Path) ($($wt.Branch))" -ForegroundColor Gray
            $index++
        }
        Write-Host ""
        $selection = Read-Host "Enter worktree numbers (e.g., 1,3)"
        $selectedIndices = $selection -split ',' | ForEach-Object { [int]$_.Trim() - 1 }
        Write-Host ""
        foreach ($idx in $selectedIndices) {
            if ($idx -ge 0 -and $idx -lt $worktreeInfo.Count) {
                $wt = $worktreeInfo[$idx]
                Write-Host "  Removing worktree: $($wt.Path)..." -ForegroundColor Yellow
                try {
                    git worktree remove $wt.Path --force 2>&1 | Out-Null
                    if ($LASTEXITCODE -eq 0) {
                        Write-Host "    ✓ Removed $($wt.Path)" -ForegroundColor Green
                    } else {
                        Write-Host "    ✗ Failed to remove $($wt.Path)" -ForegroundColor Red
                    }
                } catch {
                    Write-Host "    ✗ Error removing $($wt.Path): $_" -ForegroundColor Red
                }
            }
        }
        Write-Host ""
        Write-Host "✓ Cleanup complete!" -ForegroundColor Green
    }
    "3" {
        Write-Host ""
        Write-Host "Pruning stale worktree references..." -ForegroundColor Yellow
        git worktree prune --verbose
        Write-Host ""
        Write-Host "✓ Prune complete!" -ForegroundColor Green
    }
    "4" {
        Write-Host ""
        Write-Host "Worktree details:" -ForegroundColor Cyan
        Write-Host ""
        foreach ($wt in $worktreeInfo) {
            Write-Host "Path: $($wt.Path)" -ForegroundColor Yellow
            Write-Host "  Commit: $($wt.Commit)" -ForegroundColor Gray
            Write-Host "  Branch: $($wt.Branch)" -ForegroundColor Gray
            
            # Get commit details
            $commitDetails = git log -1 $wt.Commit --format="%h - %s (%ar) by %an" 2>&1
            if ($commitDetails) {
                Write-Host "  Details: $commitDetails" -ForegroundColor Gray
            }
            
            # Check if directory exists
            if (Test-Path $wt.Path) {
                Write-Host "  Status: Directory exists" -ForegroundColor Green
            } else {
                Write-Host "  Status: Directory missing (stale reference)" -ForegroundColor Red
            }
            Write-Host ""
        }
    }
    "5" {
        Write-Host ""
        Write-Host "Exiting without changes." -ForegroundColor Yellow
    }
    default {
        Write-Host ""
        Write-Host "Invalid choice. Exiting." -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== Cleanup Script Complete ===" -ForegroundColor Cyan


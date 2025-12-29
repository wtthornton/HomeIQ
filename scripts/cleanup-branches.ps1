# Git Branch Cleanup Script for HomeIQ
# This script safely cleans up merged branches

Write-Host "=== HomeIQ Branch Cleanup Script ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Fetch latest from remote
Write-Host "Step 1: Fetching latest from remote..." -ForegroundColor Yellow
git fetch --prune origin
Write-Host ""

# Step 2: List merged remote branches (safe to delete)
Write-Host "Step 2: Remote branches merged into master (safe to delete):" -ForegroundColor Green
$mergedBranches = git branch -r --merged origin/master | Where-Object { $_ -notmatch 'origin/HEAD' -and $_ -notmatch 'origin/master' } | ForEach-Object { $_.Trim() }
$mergedBranches | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
Write-Host ""
Write-Host "Total merged branches: $($mergedBranches.Count)" -ForegroundColor Cyan
Write-Host ""

# Step 3: List unmerged remote branches (need review)
Write-Host "Step 3: Remote branches NOT merged into master (review needed):" -ForegroundColor Yellow
$unmergedBranches = git branch -r --no-merged origin/master | ForEach-Object { $_.Trim() }
$unmergedBranches | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
Write-Host ""
Write-Host "Total unmerged branches: $($unmergedBranches.Count)" -ForegroundColor Yellow
Write-Host ""

# Step 4: List local branches
Write-Host "Step 4: Local branches:" -ForegroundColor Cyan
$localBranches = git branch | Where-Object { $_ -notmatch '\* master' -and $_ -notmatch 'master' } | ForEach-Object { $_.Trim() }
$localBranches | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
Write-Host ""
Write-Host "Total local branches: $($localBranches.Count)" -ForegroundColor Cyan
Write-Host ""

# Step 5: Interactive cleanup
Write-Host "=== Cleanup Options ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Delete all merged remote branches (SAFE)" -ForegroundColor Green
Write-Host "2. Delete specific merged remote branches" -ForegroundColor Yellow
Write-Host "3. Delete local workflow branches" -ForegroundColor Yellow
Write-Host "4. Delete all local branches merged into master" -ForegroundColor Yellow
Write-Host "5. Show branch details (last commit, author)" -ForegroundColor Cyan
Write-Host "6. Exit without deleting" -ForegroundColor Red
Write-Host ""

$choice = Read-Host "Enter your choice (1-6)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "Deleting all merged remote branches..." -ForegroundColor Yellow
        $mergedBranches | ForEach-Object {
            $branchName = $_ -replace 'origin/', ''
            Write-Host "  Deleting origin/$branchName..." -ForegroundColor Gray
            git push origin --delete $branchName 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    ✓ Deleted origin/$branchName" -ForegroundColor Green
            } else {
                Write-Host "    ✗ Failed to delete origin/$branchName" -ForegroundColor Red
            }
        }
        Write-Host ""
        Write-Host "✓ Cleanup complete!" -ForegroundColor Green
    }
    "2" {
        Write-Host ""
        Write-Host "Select branches to delete (comma-separated numbers):" -ForegroundColor Yellow
        $index = 1
        $mergedBranches | ForEach-Object {
            Write-Host "  $index. $_" -ForegroundColor Gray
            $index++
        }
        Write-Host ""
        $selection = Read-Host "Enter branch numbers (e.g., 1,3,5)"
        $selectedIndices = $selection -split ',' | ForEach-Object { [int]$_.Trim() - 1 }
        Write-Host ""
        foreach ($idx in $selectedIndices) {
            if ($idx -ge 0 -and $idx -lt $mergedBranches.Count) {
                $branch = $mergedBranches[$idx]
                $branchName = $branch -replace 'origin/', ''
                Write-Host "  Deleting $branch..." -ForegroundColor Yellow
                git push origin --delete $branchName 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "    ✓ Deleted $branch" -ForegroundColor Green
                } else {
                    Write-Host "    ✗ Failed to delete $branch" -ForegroundColor Red
                }
            }
        }
        Write-Host ""
        Write-Host "✓ Cleanup complete!" -ForegroundColor Green
    }
    "3" {
        Write-Host ""
        Write-Host "Deleting local workflow branches..." -ForegroundColor Yellow
        $workflowBranches = $localBranches | Where-Object { $_ -match '^workflow/' }
        $workflowBranches | ForEach-Object {
            Write-Host "  Deleting $_..." -ForegroundColor Gray
            git branch -D $_ 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    ✓ Deleted $_" -ForegroundColor Green
            } else {
                Write-Host "    ✗ Failed to delete $_" -ForegroundColor Red
            }
        }
        Write-Host ""
        Write-Host "✓ Cleanup complete!" -ForegroundColor Green
    }
    "4" {
        Write-Host ""
        Write-Host "Deleting local branches merged into master..." -ForegroundColor Yellow
        $localMerged = git branch --merged master | Where-Object { $_ -notmatch '\* master' -and $_ -notmatch 'master' } | ForEach-Object { $_.Trim() }
        $localMerged | ForEach-Object {
            Write-Host "  Deleting $_..." -ForegroundColor Gray
            git branch -d $_ 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    ✓ Deleted $_" -ForegroundColor Green
            } else {
                Write-Host "    ✗ Failed to delete $_ (use -D to force)" -ForegroundColor Yellow
            }
        }
        Write-Host ""
        Write-Host "✓ Cleanup complete!" -ForegroundColor Green
    }
    "5" {
        Write-Host ""
        Write-Host "Branch details:" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Unmerged branches (need review):" -ForegroundColor Yellow
        $unmergedBranches | ForEach-Object {
            $branchName = $_ -replace 'origin/', ''
            $lastCommit = git log -1 --format="%h - %s (%ar)" $_ 2>&1
            Write-Host "  $_" -ForegroundColor Yellow
            Write-Host "    $lastCommit" -ForegroundColor Gray
        }
        Write-Host ""
        Write-Host "Local branches:" -ForegroundColor Cyan
        $localBranches | ForEach-Object {
            $lastCommit = git log -1 --format="%h - %s (%ar)" $_ 2>&1
            Write-Host "  $_" -ForegroundColor Cyan
            Write-Host "    $lastCommit" -ForegroundColor Gray
        }
    }
    "6" {
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


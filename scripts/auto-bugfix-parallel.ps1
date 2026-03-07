# auto-bugfix-parallel.ps1 — Run multiple auto-bugfix scans in parallel using git worktrees.
#
# Each scan unit gets its own worktree + branch, running concurrently.
# Results: one PR per scan unit, merged independently.
#
# Usage:
#   .\scripts\auto-bugfix-parallel.ps1                          # Top 3 scan units by priority score
#   .\scripts\auto-bugfix-parallel.ps1 -MaxParallel 4           # Run 4 at once
#   .\scripts\auto-bugfix-parallel.ps1 -Units "libs,core-platform"  # Specific units
#   .\scripts\auto-bugfix-parallel.ps1 -All                     # All 14 units (batched)
#   .\scripts\auto-bugfix-parallel.ps1 -Bugs 3                  # 3 bugs per unit
#   .\scripts\auto-bugfix-parallel.ps1 -DryRun                  # Show what would run
#
# Requirements:
#   - PowerShell 7+ (for ForEach-Object -Parallel)
#   - claude CLI, git, gh, python3
#   - Clean working tree on master

param(
    [int]$MaxParallel = 3,
    [int]$Bugs = 1,
    [string]$Units = "",
    [switch]$All,
    [string]$Base = "master",
    [switch]$Chain,
    [string]$ChainPhases = "fix,refactor,test",
    [switch]$NoDashboard,
    [switch]$DryRun,
    [switch]$Cleanup
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

# --- Cleanup mode ---
if ($Cleanup) {
    Write-Host "=== Cleaning up bugfix worktrees ===" -ForegroundColor Cyan
    $worktreeDir = Join-Path $ProjectRoot ".worktrees"
    if (Test-Path $worktreeDir) {
        $dirs = Get-ChildItem -Path $worktreeDir -Directory | Where-Object { $_.Name -match '^bugfix-' }
        foreach ($d in $dirs) {
            Write-Host "  Removing worktree: $($d.FullName)..." -ForegroundColor Yellow
            git worktree remove $d.FullName --force 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    Removed." -ForegroundColor Green
            } else {
                Write-Host "    Force-removing directory..." -ForegroundColor Yellow
                Remove-Item -Recurse -Force $d.FullName -ErrorAction SilentlyContinue
            }
        }
        # Remove .worktrees dir if empty
        if (-not (Get-ChildItem -Path $worktreeDir -Directory)) {
            Remove-Item -Path $worktreeDir -ErrorAction SilentlyContinue
        }
    }
    git worktree prune
    Write-Host "  Pruned stale worktree references." -ForegroundColor Green

    # Clean up merged bugfix branches
    $branches = git branch --list "auto/bugfix-*" | ForEach-Object { $_.Trim() }
    if ($branches) {
        Write-Host ""
        Write-Host "  Bugfix branches found:" -ForegroundColor Yellow
        foreach ($b in $branches) {
            Write-Host "    $b" -ForegroundColor Gray
        }
        $confirm = Read-Host "  Delete these branches? (y/N)"
        if ($confirm -eq "y") {
            foreach ($b in $branches) {
                git branch -D $b 2>$null
                Write-Host "    Deleted $b" -ForegroundColor Green
            }
        }
    }
    Write-Host ""
    Write-Host "Cleanup complete." -ForegroundColor Green
    exit 0
}

# --- Preflight ---
$UsePSJobs = $PSVersionTable.PSVersion.Major -lt 7
if ($UsePSJobs) {
    Write-Host "  Note: PowerShell $($PSVersionTable.PSVersion) detected. Using Start-Job for parallelism." -ForegroundColor Yellow
    Write-Host "  For best results, install PS7: winget install Microsoft.PowerShell" -ForegroundColor Yellow
}

foreach ($cmd in @("claude", "git", "gh", "python3")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Error "ERROR: '$cmd' is not installed or not in PATH."
        exit 1
    }
}

$dirty = git status --porcelain --ignore-submodules
if ($dirty) {
    Write-Error "ERROR: Working tree is dirty. Commit or stash changes first."
    exit 1
}

$currentBranch = (git branch --show-current).Trim()
if ($currentBranch -ne $Base) {
    Write-Host "Switching to '$Base'..." -ForegroundColor Yellow
    git checkout $Base
}

# --- Select scan units ---
$ScanManifest = Join-Path $ProjectRoot "docs/scan-manifest.json"
if (-not (Test-Path $ScanManifest)) {
    Write-Error "ERROR: Scan manifest not found at $ScanManifest"
    exit 1
}

$pickScript = @"
import json, sys
from datetime import datetime, timezone

with open(r'$ScanManifest') as f:
    manifest = json.load(f)

requested_units = '$Units'.split(',') if '$Units' else []
select_all = $($All.ToString().ToLower())
max_count = $MaxParallel

now = datetime.now(timezone.utc)
scored = []

for unit in manifest['units']:
    if requested_units and unit['id'] not in requested_units:
        continue

    if unit['last_scanned']:
        last = datetime.fromisoformat(unit['last_scanned'])
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        days = max((now - last).total_seconds() / 86400, 0.1)
    else:
        days = 365

    bug_boost = 1 + unit['total_bugs_found'] / 5
    fp_penalty = 1 - (unit['false_positives'] / max(unit['total_bugs_found'], 1)) * 0.3
    score = unit['priority_weight'] * days * bug_boost * max(fp_penalty, 0.5)

    scored.append((score, unit))

scored.sort(key=lambda x: x[0], reverse=True)

if requested_units:
    selected = [u for _, u in scored]
elif select_all:
    selected = [u for _, u in scored]
else:
    selected = [u for _, u in scored[:max_count]]

for u in selected:
    print(f"{u['id']}|{u['path']}|{u['name']}|{u['scan_hint']}")
"@

$selectedUnits = @()
$pickTempFile = [System.IO.Path]::GetTempFileName() -replace '\.tmp$', '.py'
$pickScript | Out-File -FilePath $pickTempFile -Encoding utf8 -Force
python3 $pickTempFile 2>$null | ForEach-Object {
    $parts = $_ -split '\|', 4
    $selectedUnits += @{
        Id   = $parts[0]
        Path = $parts[1]
        Name = $parts[2]
        Hint = $parts[3]
    }
}
Remove-Item $pickTempFile -ErrorAction SilentlyContinue

if ($selectedUnits.Count -eq 0) {
    Write-Error "ERROR: No scan units selected."
    exit 1
}

# --- Display plan ---
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
Write-Host ""
Write-Host "=== Auto-Bugfix Parallel ===" -ForegroundColor Cyan
Write-Host "  Units:       $($selectedUnits.Count)" -ForegroundColor White
Write-Host "  Parallel:    $MaxParallel" -ForegroundColor White
Write-Host "  Bugs/unit:   $Bugs" -ForegroundColor White
Write-Host "  Base:        $Base" -ForegroundColor White
if ($Chain) { Write-Host "  Chain:       $ChainPhases" -ForegroundColor Magenta }
Write-Host ""
Write-Host "  Scan plan:" -ForegroundColor Yellow
foreach ($u in $selectedUnits) {
    $branchName = "auto/bugfix-$($u.Id)-$timestamp"
    Write-Host "    $($u.Id.PadRight(22)) -> $branchName" -ForegroundColor Gray
}
Write-Host ""

if ($DryRun) {
    Write-Host "DRY RUN: Would create $($selectedUnits.Count) worktrees and run scans." -ForegroundColor Yellow
    Write-Host "Remove -DryRun to execute." -ForegroundColor Yellow
    exit 0
}

# --- Create worktrees and launch parallel scans ---
$worktreeBase = Join-Path $ProjectRoot ".worktrees"
if (-not (Test-Path $worktreeBase)) {
    New-Item -ItemType Directory -Path $worktreeBase -Force | Out-Null
}

# Ensure .worktrees is gitignored
$gitignore = Join-Path $ProjectRoot ".gitignore"
$gitignoreContent = Get-Content $gitignore -Raw -ErrorAction SilentlyContinue
if ($gitignoreContent -notmatch '\.worktrees/') {
    Add-Content -Path $gitignore -Value "`n# Parallel bugfix worktrees`n.worktrees/" -Encoding utf8
    Write-Host "  Added .worktrees/ to .gitignore" -ForegroundColor Gray
}

$startTime = Get-Date
$scriptPath = Join-Path $ProjectRoot "scripts/auto-bugfix.ps1"
$mcpConfig = Join-Path $ProjectRoot ".mcp.json"

# Build worktree info for each unit
$jobs = @()
foreach ($u in $selectedUnits) {
    $branchName = "auto/bugfix-$($u.Id)-$timestamp"
    $worktreePath = Join-Path $worktreeBase "bugfix-$($u.Id)"

    # Remove stale worktree if exists
    if (Test-Path $worktreePath) {
        Write-Host "  Removing stale worktree: $worktreePath" -ForegroundColor Yellow
        git worktree remove $worktreePath --force 2>$null
        if (Test-Path $worktreePath) {
            Remove-Item -Recurse -Force $worktreePath
        }
    }

    # Remove stale branch if exists
    git branch -D $branchName 2>$null

    # Create worktree with new branch
    Write-Host "  Creating worktree: $($u.Id) -> $worktreePath" -ForegroundColor Cyan
    git worktree add $worktreePath -b $branchName $Base 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "    ERROR: Failed to create worktree for $($u.Id)" -ForegroundColor Red
        continue
    }

    # Copy MCP config into worktree (Claude needs it)
    if (Test-Path $mcpConfig) {
        Copy-Item $mcpConfig (Join-Path $worktreePath ".mcp.json") -Force
    }

    $jobs += @{
        UnitId      = $u.Id
        UnitName    = $u.Name
        UnitPath    = $u.Path
        Branch      = $branchName
        WorktreePath = $worktreePath
    }
}

if ($jobs.Count -eq 0) {
    Write-Error "ERROR: No worktrees were created."
    exit 1
}

Write-Host ""
Write-Host "Launching $($jobs.Count) parallel scans (max $MaxParallel concurrent)..." -ForegroundColor Yellow
Write-Host ""

# --- Run scans in parallel ---
# Build a script block for each job
$jobScriptBlock = {
    param($JobData, $ScriptPath, $BugCount, $UseChain, $Phases, $BaseBranch)
    $unitId = $JobData.UnitId
    $worktreePath = $JobData.WorktreePath
    $branch = $JobData.Branch
    $logFile = Join-Path $worktreePath "bugfix-output.log"

    $params = @(
        "-Bugs", $BugCount,
        "-Branch", $branch,
        "-TargetDir", $JobData.UnitPath,
        "-Base", $BaseBranch,
        "-Rotate",
        "-TargetUnit", $unitId,
        "-NoDashboard",
        "-Worktree"
    )
    if ($UseChain) {
        $params += "-Chain"
        $params += "-ChainPhases"
        $params += $Phases
    }

    Push-Location $worktreePath
    try {
        & $ScriptPath @params *> $logFile
        $exitCode = $LASTEXITCODE
    } catch {
        $exitCode = 1
        $_.Exception.Message | Out-File -Append $logFile
    }
    Pop-Location

    @{
        UnitId  = $unitId
        Branch  = $branch
        Success = ($exitCode -eq 0)
        LogFile = $logFile
    }
}

if ($UsePSJobs) {
    # PowerShell 5.x: Use Start-Job with throttling
    $runningJobs = @()
    $results = @()

    foreach ($job in $jobs) {
        # Throttle: wait if at max parallel
        while ($runningJobs.Count -ge $MaxParallel) {
            $completed = $runningJobs | Where-Object { $_.State -ne 'Running' } | Select-Object -First 1
            if ($completed) {
                $result = Receive-Job -Job $completed -Wait
                $results += $result
                Remove-Job -Job $completed
                $runningJobs = @($runningJobs | Where-Object { $_.Id -ne $completed.Id })
                $status = if ($result.Success) { "OK" } else { "FAIL" }
                Write-Host "  DONE: $($result.UnitId) ($status)" -ForegroundColor $(if ($result.Success) { "Green" } else { "Red" })
            } else {
                Start-Sleep -Seconds 5
            }
        }

        Write-Host "  START: $($job.UnitId)" -ForegroundColor Cyan
        $psJob = Start-Job -ScriptBlock $jobScriptBlock -ArgumentList $job, $scriptPath, $Bugs, $Chain.IsPresent, $ChainPhases, $Base
        $runningJobs += $psJob
    }

    # Wait for remaining jobs
    foreach ($rj in $runningJobs) {
        $result = Receive-Job -Job $rj -Wait
        $results += $result
        Remove-Job -Job $rj
        $status = if ($result.Success) { "OK" } else { "FAIL" }
        Write-Host "  DONE: $($result.UnitId) ($status)" -ForegroundColor $(if ($result.Success) { "Green" } else { "Red" })
    }
} else {
    # PowerShell 7+: Use ForEach-Object -Parallel
    $results = $jobs | ForEach-Object -Parallel {
        $job = $_
        $result = & $using:jobScriptBlock $job $using:scriptPath $using:Bugs $using:Chain.IsPresent $using:ChainPhases $using:Base
        $result
    } -ThrottleLimit $MaxParallel
}

# --- Report results ---
$totalElapsed = (Get-Date) - $startTime
$totalStr = "{0:mm\:ss}" -f $totalElapsed

Write-Host ""
Write-Host "=== Parallel Scan Results ===" -ForegroundColor Cyan
Write-Host "  Total time: $totalStr" -ForegroundColor White
Write-Host ""

$succeeded = 0
$failed = 0

$fmt = "{0,-22} {1,-8} {2}"
Write-Host ($fmt -f "UNIT", "STATUS", "BRANCH/LOG") -ForegroundColor DarkGray
Write-Host ("-" * 70) -ForegroundColor DarkGray

foreach ($r in $results) {
    if ($r.Success) {
        $succeeded++
        $status = "OK"
        $color = "Green"
        $detail = $r.Branch
    } else {
        $failed++
        $status = "FAIL"
        $color = "Red"
        $detail = "See $($r.LogFile)"
    }
    Write-Host ($fmt -f $r.UnitId, $status, $detail) -ForegroundColor $color
}

Write-Host ""
Write-Host "Summary: $succeeded succeeded, $failed failed out of $($results.Count) scans" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Yellow" })

# --- Cleanup worktrees (keep branches for PRs) ---
Write-Host ""
Write-Host "Cleaning up worktrees..." -ForegroundColor Yellow
foreach ($job in $jobs) {
    if (Test-Path $job.WorktreePath) {
        git worktree remove $job.WorktreePath --force 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Removed: $($job.WorktreePath)" -ForegroundColor Gray
        }
    }
}
git worktree prune 2>$null

# Switch back to base
git checkout $Base 2>$null

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Green
Write-Host "  Scans:    $($results.Count) ($succeeded OK, $failed failed)"
Write-Host "  Time:     $totalStr"
Write-Host "  Cleanup:  .\scripts\auto-bugfix-parallel.ps1 -Cleanup"
Write-Host ""
if ($succeeded -gt 0) {
    Write-Host "PRs created for successful scans. Review and merge them:" -ForegroundColor Yellow
    Write-Host "  gh pr list --author @me --label auto-bugfix" -ForegroundColor Gray
}

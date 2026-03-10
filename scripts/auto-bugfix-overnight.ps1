# auto-bugfix-overnight.ps1 — Run auto-bugfix in a loop all night, covering all scan units.
#
# Usage:
#   .\scripts\auto-bugfix-overnight.ps1                              # Defaults: 5 rounds, 3 parallel, 3 bugs/unit
#   .\scripts\auto-bugfix-overnight.ps1 -Rounds 5 -Chain             # With refactor + test phases
#   .\scripts\auto-bugfix-overnight.ps1 -MaxHours 8 -TotalBudget 25  # Run up to 8 hours or $25
#   .\scripts\auto-bugfix-overnight.ps1 -MaxParallel 4 -BugsPerUnit 5 -Model claude-opus-4-6
#   .\scripts\auto-bugfix-overnight.ps1 -DryRun                      # Show plan without executing
#
# Requirements:
#   - PowerShell 5.1+ (7+ recommended for parallel worktrees)
#   - claude CLI, git, gh, python3
#   - Clean working tree on master

param(
    [int]$Rounds = 5,
    [int]$MaxParallel = 3,
    [int]$BugsPerUnit = 3,
    [int]$CooldownMinutes = 2,
    [double]$TotalBudget = 25.00,
    [double]$MaxCostPerUnit = 5.00,
    [int]$MaxHours = 8,
    [string]$Base = "master",
    [string]$Model = "claude-sonnet-4-6",
    [switch]$Chain,
    [string]$ChainPhases = "fix,refactor,test",
    [switch]$DryRun,
    [switch]$StopOnFail
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

# --- Preflight ---
foreach ($cmd in @("claude", "git", "gh", "python3")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Error "ERROR: '$cmd' is not installed or not in PATH."
        exit 1
    }
}

if (-not $DryRun) {
    $dirty = git status --porcelain --ignore-submodules
    if ($dirty) {
        Write-Error "ERROR: Working tree is dirty. Commit or stash changes first."
        exit 1
    }
}

$ScanManifest = Join-Path $ProjectRoot "docs/scan-manifest.json"
if (-not (Test-Path $ScanManifest)) {
    Write-Error "ERROR: Scan manifest not found at $ScanManifest"
    exit 1
}

# --- Calculate plan ---
$manifest = Get-Content $ScanManifest -Raw | ConvertFrom-Json
$totalUnits = $manifest.units.Count
$unitsPerRound = [math]::Min($MaxParallel, $totalUnits)
# Worst-case: each unit hits the MaxCost cap. Cap total scans at the number of units.
$totalScans = [math]::Min($unitsPerRound * $Rounds, $totalUnits)
$estimatedCost = [math]::Round($MaxCostPerUnit * $totalScans, 2)
$deadline = (Get-Date).AddHours($MaxHours)

# --- Report file ---
$reportTimestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$reportFile = Join-Path $ProjectRoot "docs/overnight-report-$reportTimestamp.md"

# --- State tracking ---
$startTime = Get-Date
$roundResults = [System.Collections.Generic.List[object]]::new()
$totalBugsFound = 0
$totalSpent = 0.0

# --- Display banner ---
Write-Host ""
Write-Host "  ================================================================" -ForegroundColor Cyan
Write-Host "    AUTO-BUGFIX OVERNIGHT RUNNER" -ForegroundColor Cyan
Write-Host "  ================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Rounds:          $Rounds" -ForegroundColor White
Write-Host "  Parallel:        $MaxParallel units/round" -ForegroundColor White
Write-Host "  Bugs/unit:       $BugsPerUnit" -ForegroundColor White
Write-Host "  Model:           $Model" -ForegroundColor White
Write-Host ('  Budget/unit:     $' + $MaxCostPerUnit) -ForegroundColor White
Write-Host ('  Total budget:    $' + $TotalBudget) -ForegroundColor White
$costColor = $(if ($estimatedCost -gt $TotalBudget) { 'Red' } else { 'Green' })
Write-Host ('  Est. cost:       ~$' + $estimatedCost) -ForegroundColor $costColor
Write-Host ('  Time limit:      ' + $MaxHours + ' hours (deadline: ' + $deadline.ToString('HH:mm') + ')') -ForegroundColor White
Write-Host "  Scan units:      $totalUnits in manifest" -ForegroundColor White
Write-Host "  Cooldown:        $CooldownMinutes min between rounds" -ForegroundColor White
if ($Chain) {
    Write-Host "  Chain:           $ChainPhases" -ForegroundColor Magenta
}
Write-Host ""

if ($estimatedCost -gt $TotalBudget) {
    Write-Host ('  WARNING: Estimated cost ($' + $estimatedCost + ') exceeds budget ($' + $TotalBudget + ').') -ForegroundColor Yellow
    Write-Host "  Runner will stop when budget is exhausted." -ForegroundColor Yellow
    Write-Host ""
}

if ($DryRun) {
    Write-Host "  DRY RUN: Would execute $Rounds rounds. Remove -DryRun to run." -ForegroundColor Yellow
    Write-Host ""

    # Show which units would be picked each round (simulated)
    for ($r = 1; $r -le $Rounds; $r++) {
        Write-Host "  Round $r`: top $unitsPerRound units by rotation score" -ForegroundColor Gray
    }
    exit 0
}

# --- Helper: count PRs created in this session ---
function Get-SessionPRs {
    param([string]$Since)
    try {
        $prs = gh pr list --author @me --search "auto-fix" --json url,createdAt 2>$null | ConvertFrom-Json
        if ($prs) {
            return @($prs | Where-Object { $_.createdAt -ge $Since }).Count
        }
    } catch {}
    return 0
}

# --- Helper: parse cost from stream logs ---
# Scans both the main stream-logs dir and worktree stream-logs dirs.
# Each result event has total_cost_usd (preferred) or cost_usd (fallback).
function Get-StreamLogCost {
    $cost = 0.0
    $logDirs = @(Join-Path $ProjectRoot "scripts/.stream-logs")

    # Also check worktree stream-log dirs
    $worktreeBase = Join-Path $ProjectRoot ".worktrees"
    if (Test-Path $worktreeBase) {
        $logDirs += Get-ChildItem -Path $worktreeBase -Recurse -Directory -Filter ".stream-logs" -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }
    }

    foreach ($logDir in $logDirs) {
        if (-not (Test-Path $logDir)) { continue }
        $logFiles = Get-ChildItem -Path $logDir -Filter "*.jsonl" -ErrorAction SilentlyContinue | Where-Object {
            $_.LastWriteTime -ge $startTime
        }

        foreach ($lf in $logFiles) {
            $lines = Get-Content $lf.FullName -Tail 50 -ErrorAction SilentlyContinue
            foreach ($line in $lines) {
                # Prefer total_cost_usd (cumulative); fall back to cost_usd
                if ($line -match '"total_cost_usd"\s*:\s*([\d.]+)') {
                    $cost += [double]$Matches[1]
                } elseif ($line -match '"cost_usd"\s*:\s*([\d.]+)') {
                    $cost += [double]$Matches[1]
                }
            }
        }
    }
    return $cost
}

# --- Helper: read bug history for round stats ---
function Get-RoundBugStats {
    param([datetime]$Since)
    $historyFile = Join-Path $ProjectRoot "docs/BUG_HISTORY.json"
    if (-not (Test-Path $historyFile)) { return @{ found = 0; fixed = 0 } }

    try {
        $history = Get-Content $historyFile -Raw | ConvertFrom-Json
        if ($history -isnot [array]) { $history = @($history) }
        $recent = @($history | Where-Object { $_.date -ge $Since.ToString("yyyy-MM-dd HH:mm") })
        $found = ($recent | ForEach-Object { $_.bugs.Count } | Measure-Object -Sum).Sum
        return @{ found = [int]$found; entries = $recent.Count }
    } catch {
        return @{ found = 0; entries = 0 }
    }
}

# --- Main loop ---
Write-Host "  Starting at $(Get-Date -Format 'HH:mm:ss')..." -ForegroundColor Green
Write-Host ""

$parallelScript = Join-Path $ProjectRoot "scripts/auto-bugfix-parallel.ps1"

for ($round = 1; $round -le $Rounds; $round++) {
    $roundStart = Get-Date

    # --- Guard: time limit ---
    if ((Get-Date) -ge $deadline) {
        Write-Host ('  TIME LIMIT reached (' + $MaxHours + ' hours). Stopping.') -ForegroundColor Yellow
        break
    }

    # --- Guard: budget limit (check stream logs for actual cost) ---
    $totalSpent = Get-StreamLogCost
    if ($totalSpent -ge $TotalBudget) {
        Write-Host ('  BUDGET LIMIT reached ($' + [math]::Round($totalSpent, 2) + ' / $' + $TotalBudget + '). Stopping.') -ForegroundColor Yellow
        break
    }
    # --- Round header ---
    $elapsed = (Get-Date) - $startTime
    Write-Host "  ================================================================" -ForegroundColor Cyan
    Write-Host ('    ROUND ' + $round + ' / ' + $Rounds + '    (elapsed: ' + $elapsed.ToString('hh\:mm\:ss') + ', spent: ~$' + [math]::Round($totalSpent, 2) + ')') -ForegroundColor Cyan
    Write-Host "  ================================================================" -ForegroundColor Cyan
    Write-Host ""

    # --- Ensure we're on the base branch ---
    $currentBranch = (git branch --show-current).Trim()
    if ($currentBranch -ne $Base) {
        git checkout $Base 2>$null
    }
    git pull --rebase origin $Base 2>$null

    # --- Build parallel args ---
    $parallelArgs = @(
        "-MaxParallel", $MaxParallel,
        "-Bugs", $BugsPerUnit,
        "-Base", $Base,
        "-NoDashboard",
        "-Model", $Model,
        "-MaxCost", $MaxCostPerUnit
    )
    if ($Chain) {
        $parallelArgs += "-Chain"
        $parallelArgs += "-ChainPhases"
        $parallelArgs += $ChainPhases
    }

    # --- Run the batch ---
    $roundExitCode = 0
    try {
        & $parallelScript @parallelArgs
        $roundExitCode = $LASTEXITCODE
    } catch {
        Write-Host "  Round $round ERROR: $_" -ForegroundColor Red
        $roundExitCode = 1
    }

    # --- Collect round stats ---
    $roundElapsed = (Get-Date) - $roundStart
    $roundCost = (Get-StreamLogCost) - $totalSpent
    $bugStats = Get-RoundBugStats -Since $roundStart

    $roundResult = @{
        round         = $round
        status        = $(if ($roundExitCode -eq 0) { 'success' } else { 'failed' })
        elapsed       = $roundElapsed.ToString('mm\:ss')
        bugs_found    = $bugStats.found
        cost_estimate = [math]::Round($roundCost, 4)
    }
    $roundResults.Add($roundResult) | Out-Null

    $totalBugsFound += $bugStats.found

    # --- Round summary ---
    $statusColor = $(if ($roundExitCode -eq 0) { 'Green' } else { 'Red' })
    $statusText = $(if ($roundExitCode -eq 0) { 'OK' } else { 'FAIL' })
    Write-Host ""
    Write-Host ('  Round ' + $round + ': ' + $statusText + ' | ' + $bugStats.found + ' bugs | ' + $roundElapsed.ToString('mm\:ss') + ' | ~$' + [math]::Round($roundCost, 4)) -ForegroundColor $statusColor
    Write-Host ""

    # --- Stop on failure if requested ---
    if ($StopOnFail -and $roundExitCode -ne 0) {
        Write-Host '  -StopOnFail: stopping after failed round.' -ForegroundColor Yellow
        break
    }

    # --- Cooldown between rounds ---
    if ($round -lt $Rounds) {
        # Check guards before sleeping
        if ((Get-Date).AddMinutes($CooldownMinutes) -ge $deadline) {
            Write-Host '  Skipping cooldown - approaching time limit.' -ForegroundColor Yellow
        } else {
            Write-Host "  Cooling down for $CooldownMinutes minutes..." -ForegroundColor Gray
            Start-Sleep -Seconds ($CooldownMinutes * 60)
        }
    }
}

# --- Final report ---
$totalElapsed = (Get-Date) - $startTime
$totalSpent = Get-StreamLogCost
$completedRounds = $roundResults.Count
$successRounds = @($roundResults | Where-Object { $_.status -eq "success" }).Count
$failedRounds = $completedRounds - $successRounds

# Count PRs created during this session
$sessionPRs = Get-SessionPRs -Since $startTime.ToString("yyyy-MM-ddTHH:mm:ssZ")

Write-Host ""
Write-Host "  ================================================================" -ForegroundColor Green
Write-Host "    OVERNIGHT RUN COMPLETE" -ForegroundColor Green
Write-Host "  ================================================================" -ForegroundColor Green
Write-Host ""
Write-Host ('  Duration:     ' + $totalElapsed.ToString('hh\:mm\:ss')) -ForegroundColor White
Write-Host ('  Rounds:       ' + $completedRounds + ' / ' + $Rounds + ' -- ' + $successRounds + ' OK, ' + $failedRounds + ' failed') -ForegroundColor White
Write-Host ('  Bugs found:   ' + $totalBugsFound) -ForegroundColor White
Write-Host ('  Est. cost:    ~$' + [math]::Round($totalSpent, 2)) -ForegroundColor White
Write-Host ('  PRs created:  ' + $sessionPRs) -ForegroundColor White
Write-Host ""
Write-Host '  Review PRs:   gh pr list --author @me' -ForegroundColor Yellow
Write-Host '  Cleanup:      .\scripts\auto-bugfix-parallel.ps1 -Cleanup' -ForegroundColor Yellow
Write-Host ""

# --- Write report file ---
$chainLabel = $(if ($Chain) { $ChainPhases } else { 'disabled' })
$costStr = '$' + [math]::Round($totalSpent, 2)
$budgetStr = '$' + $TotalBudget
$unitCostStr = '$' + $MaxCostPerUnit
$dateStr = Get-Date -Format 'yyyy-MM-dd HH:mm'
$durationStr = $totalElapsed.ToString('hh\:mm\:ss')

$sb = [System.Text.StringBuilder]::new()
$sb.AppendLine('# Overnight Auto-Bugfix Report') > $null
$sb.AppendLine('') > $null
$sb.AppendLine('**Date:** ' + $dateStr) > $null
$sb.AppendLine('**Duration:** ' + $durationStr) > $null
$sb.AppendLine('**Model:** ' + $Model) > $null
$sb.AppendLine('') > $null
$sb.AppendLine('## Summary') > $null
$sb.AppendLine('') > $null
$sb.AppendLine('Rounds completed: ' + $completedRounds + ' / ' + $Rounds + ' (' + $successRounds + ' OK, ' + $failedRounds + ' failed)') > $null
$sb.AppendLine('Total bugs found: ' + $totalBugsFound) > $null
$sb.AppendLine('Estimated cost: ~' + $costStr + ' / ' + $budgetStr + ' budget') > $null
$sb.AppendLine('PRs created: ' + $sessionPRs) > $null
$sb.AppendLine('') > $null
$sb.AppendLine('## Configuration') > $null
$sb.AppendLine('') > $null
$sb.AppendLine('Parallel: ' + $MaxParallel + ' units/round') > $null
$sb.AppendLine('Bugs/unit: ' + $BugsPerUnit) > $null
$sb.AppendLine('Budget/unit: ' + $unitCostStr) > $null
$sb.AppendLine('Chain mode: ' + $chainLabel) > $null
$sb.AppendLine('Time limit: ' + $MaxHours + ' hours') > $null
$sb.AppendLine('') > $null
$sb.AppendLine('## Round Details') > $null
$sb.AppendLine('') > $null
foreach ($rr in $roundResults) {
    $rc = '$' + $rr.cost_estimate
    $sb.AppendLine('Round ' + $rr.round + ': ' + $rr.status + ' -- ' + $rr.bugs_found + ' bugs, ' + $rr.elapsed + ', ~' + $rc) > $null
}
$sb.AppendLine('') > $null
$sb.AppendLine('## Next Steps') > $null
$sb.AppendLine('') > $null
$sb.AppendLine('Review and merge PRs: gh pr list --author @me') > $null
$sb.AppendLine('Update false positive counts in docs/scan-manifest.json') > $null
$sb.AppendLine('Clean up worktrees: .\scripts\auto-bugfix-parallel.ps1 -Cleanup') > $null
$sb.AppendLine('Re-run to cover remaining scan units') > $null
$sb.AppendLine('') > $null
$sb.AppendLine('---') > $null
$sb.AppendLine('Generated by auto-bugfix-overnight.ps1') > $null

[System.IO.File]::WriteAllText($reportFile, $sb.ToString(), [System.Text.UTF8Encoding]::new($false))
Write-Host ('  Report:       ' + $reportFile) -ForegroundColor Gray
Write-Host ""

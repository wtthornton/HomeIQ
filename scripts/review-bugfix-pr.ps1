# review-bugfix-pr.ps1 — After a bugfix PR is merged/closed, update bug history with outcomes.
#
# Usage:
#   .\scripts\review-bugfix-pr.ps1 -Branch "auto/bugfix-20260306-094105"
#   .\scripts\review-bugfix-pr.ps1 -Branch "auto/bugfix-20260306-094105" -AutoOverrides
#
# This script:
# 1. Checks PR status (merged/closed/open)
# 2. Asks Claude to review which bugs were accepted vs rejected
# 3. Updates BUG_HISTORY.json with was_real and pr_merged flags
# 4. Optionally suggests new prompt overrides

param(
    [Parameter(Mandatory=$true)]
    [string]$Branch,
    [switch]$AutoOverrides
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

$HistoryFile = Join-Path $ProjectRoot "docs/BUG_HISTORY.json"
$OverridesFile = Join-Path $ProjectRoot "docs/FIND_PROMPT_OVERRIDES.md"

if (-not (Test-Path $HistoryFile)) {
    Write-Error "No bug history found. Run auto-bugfix.ps1 first."
    exit 1
}

# Find the run in history
$history = Get-Content $HistoryFile -Raw | ConvertFrom-Json
$runIndex = -1
for ($i = 0; $i -lt $history.Count; $i++) {
    if ($history[$i].branch -eq $Branch) {
        $runIndex = $i
        break
    }
}

if ($runIndex -eq -1) {
    Write-Error "Branch '$Branch' not found in bug history."
    exit 1
}

$run = $history[$runIndex]
Write-Host "=== Reviewing Bugfix PR ===" -ForegroundColor Cyan
Write-Host "  Branch: $Branch"
Write-Host "  Date:   $($run.date)"
Write-Host "  Bugs:   $($run.bugs.Count)"
Write-Host ""

# Check PR status via gh
$prStatus = $null
try {
    $prJson = gh pr view $Branch --json state,mergedAt,reviews 2>$null
    if ($prJson) {
        $pr = $prJson | ConvertFrom-Json
        $prStatus = $pr.state
        Write-Host "  PR Status: $prStatus" -ForegroundColor $(if ($prStatus -eq "MERGED") { "Green" } elseif ($prStatus -eq "CLOSED") { "Red" } else { "Yellow" })
    }
} catch {
    Write-Host "  PR Status: unknown (could not fetch)" -ForegroundColor Gray
}

# Interactive review
Write-Host ""
Write-Host "Review each bug. Enter: y = real bug, n = false positive, s = skip" -ForegroundColor Yellow
Write-Host ""

foreach ($bug in $run.bugs) {
    Write-Host "File:     $($bug.file):$($bug.line)" -ForegroundColor White
    Write-Host "Severity: $($bug.severity)" -ForegroundColor $(switch ($bug.severity) { "high" { "Red" } "medium" { "Yellow" } default { "Gray" } })
    Write-Host "Desc:     $($bug.description)" -ForegroundColor Gray

    if ($null -ne $bug.was_real) {
        $existing = if ($bug.was_real) { "REAL" } else { "FALSE POSITIVE" }
        Write-Host "Already marked: $existing" -ForegroundColor Cyan
        Write-Host ""
        continue
    }

    $response = Read-Host "  Was this a real bug? (y/n/s)"
    switch ($response.ToLower()) {
        "y" { $bug.was_real = $true;  Write-Host "  -> Marked as REAL" -ForegroundColor Green }
        "n" { $bug.was_real = $false; Write-Host "  -> Marked as FALSE POSITIVE" -ForegroundColor Red }
        default { Write-Host "  -> Skipped" -ForegroundColor Gray }
    }

    $bug.pr_merged = ($prStatus -eq "MERGED")
    Write-Host ""
}

# Save updated history
$history[$runIndex] = $run
$history | ConvertTo-Json -Depth 10 | Out-File -FilePath $HistoryFile -Encoding utf8 -Force
Write-Host "Bug history updated." -ForegroundColor Green

# Auto-generate overrides
if ($AutoOverrides) {
    $allBugs = $history | ForEach-Object { $_.bugs } | ForEach-Object { $_ }
    $falsePositives = $allBugs | Where-Object { $_.was_real -eq $false }

    if ($falsePositives.Count -ge 2) {
        Write-Host ""
        Write-Host "--- Suggested Overrides ---" -ForegroundColor Magenta

        # Group false positives by file directory
        $fpDirs = @{}
        foreach ($fp in $falsePositives) {
            $dir = Split-Path -Parent $fp.file
            $fpDirs[$dir] = ($fpDirs[$dir] ?? 0) + 1
        }

        $suggestions = @()
        foreach ($entry in $fpDirs.GetEnumerator() | Where-Object { $_.Value -ge 2 }) {
            $rule = "- Do NOT report bugs in files under '$($entry.Key)' unless they cause crashes — $($entry.Value) false positives in history."
            $suggestions += $rule
            Write-Host "  $rule" -ForegroundColor Yellow
        }

        if ($suggestions.Count -gt 0) {
            $addRules = Read-Host "Add these rules to FIND_PROMPT_OVERRIDES.md? (y/n)"
            if ($addRules -eq "y") {
                $existing = Get-Content $OverridesFile -Raw
                $newRules = $suggestions -join "`n"
                "$existing`n$newRules" | Out-File -FilePath $OverridesFile -Encoding utf8 -Force
                Write-Host "Overrides updated." -ForegroundColor Green
            }
        }
    }
}

Write-Host ""
Write-Host "Done. Run .\scripts\analyze-bug-history.ps1 for full stats." -ForegroundColor Gray

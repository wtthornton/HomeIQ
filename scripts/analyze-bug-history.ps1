# analyze-bug-history.ps1 — Analyze bug history from auto-bugfix runs.
#
# Usage:
#   .\scripts\analyze-bug-history.ps1
#   .\scripts\analyze-bug-history.ps1 -SuggestOverrides

param(
    [switch]$SuggestOverrides
)

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$HistoryFile = Join-Path $ProjectRoot "docs/BUG_HISTORY.json"

if (-not (Test-Path $HistoryFile)) {
    Write-Host "No bug history found at $HistoryFile" -ForegroundColor Yellow
    exit 0
}

$history = Get-Content $HistoryFile -Raw | ConvertFrom-Json
if ($history.Count -eq 0) {
    Write-Host "Bug history is empty. Run auto-bugfix.ps1 first." -ForegroundColor Yellow
    exit 0
}

Write-Host "=== Bug History Analysis ===" -ForegroundColor Cyan
Write-Host ""

# Total stats
$totalRuns = $history.Count
$totalBugs = ($history | ForEach-Object { $_.bugs.Count } | Measure-Object -Sum).Sum
$realBugs = ($history | ForEach-Object { $_.bugs | Where-Object { $_.was_real -eq $true } }).Count
$falseBugs = ($history | ForEach-Object { $_.bugs | Where-Object { $_.was_real -eq $false } }).Count
$unknownBugs = $totalBugs - $realBugs - $falseBugs

Write-Host "Runs:             $totalRuns" -ForegroundColor White
Write-Host "Total bugs found: $totalBugs" -ForegroundColor White
Write-Host "Confirmed real:   $realBugs" -ForegroundColor Green
Write-Host "False positives:  $falseBugs" -ForegroundColor Red
Write-Host "Unreviewed:       $unknownBugs" -ForegroundColor Yellow

if ($realBugs + $falseBugs -gt 0) {
    $accuracy = [math]::Round(($realBugs / ($realBugs + $falseBugs)) * 100, 1)
    Write-Host "Accuracy:         $accuracy%" -ForegroundColor $(if ($accuracy -ge 80) { "Green" } else { "Yellow" })
}

Write-Host ""

# Bug type frequency
Write-Host "--- Most Common Bug Types ---" -ForegroundColor Cyan
$allBugs = $history | ForEach-Object { $_.bugs } | ForEach-Object { $_ }
$keywords = @{}
foreach ($bug in $allBugs) {
    $desc = ($bug.description -split '\s+') | Where-Object { $_.Length -gt 4 }
    foreach ($word in $desc) {
        $w = $word.ToLower() -replace '[^a-z]', ''
        if ($w.Length -gt 4) {
            $keywords[$w] = ($keywords[$w] ?? 0) + 1
        }
    }
}
$keywords.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 10 | ForEach-Object {
    Write-Host "  $($_.Value)x  $($_.Key)"
}

Write-Host ""

# Most buggy directories
Write-Host "--- Most Buggy Directories ---" -ForegroundColor Cyan
$dirs = @{}
foreach ($bug in $allBugs) {
    $dir = Split-Path -Parent $bug.file
    if ($dir) {
        # Get top 2 levels
        $parts = $dir -split '[/\\]'
        $topDir = ($parts | Select-Object -First 3) -join '/'
        $dirs[$topDir] = ($dirs[$topDir] ?? 0) + 1
    }
}
$dirs.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 10 | ForEach-Object {
    Write-Host "  $($_.Value)x  $($_.Key)"
}

Write-Host ""

# Severity breakdown
Write-Host "--- Severity Breakdown ---" -ForegroundColor Cyan
$severities = $allBugs | Group-Object severity
foreach ($s in $severities) {
    $color = switch ($s.Name) { "high" { "Red" } "medium" { "Yellow" } "low" { "Gray" } default { "White" } }
    Write-Host "  $($s.Name): $($s.Count)" -ForegroundColor $color
}

# Suggest overrides
if ($SuggestOverrides -and $totalRuns -ge 3) {
    Write-Host ""
    Write-Host "--- Suggested Override Rules ---" -ForegroundColor Magenta

    # Find files that appear in multiple runs as bugs
    $fileFreq = @{}
    foreach ($run in $history) {
        foreach ($bug in $run.bugs) {
            $fileFreq[$bug.file] = ($fileFreq[$bug.file] ?? 0) + 1
        }
    }
    $repeats = $fileFreq.GetEnumerator() | Where-Object { $_.Value -ge 2 } | Sort-Object Value -Descending
    foreach ($r in $repeats) {
        $wasFP = ($allBugs | Where-Object { $_.file -eq $r.Key -and $_.was_real -eq $false }).Count
        if ($wasFP -gt 0) {
            Write-Host "  SUGGEST: Skip '$($r.Key)' — flagged $($r.Value) times, $wasFP confirmed false positive" -ForegroundColor Yellow
        }
    }

    # Find description patterns that are mostly false positives
    $descPatterns = $allBugs | Where-Object { $_.was_real -eq $false } | ForEach-Object { $_.description }
    if ($descPatterns.Count -ge 2) {
        Write-Host "  NOTE: Review false positive descriptions for common patterns to add as override rules." -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "Run with -SuggestOverrides after 3+ runs for automatic rule suggestions." -ForegroundColor Gray

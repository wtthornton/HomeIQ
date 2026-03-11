# scan-status.ps1 — Show auto-bugfix scan coverage status across all scan units.
#
# Usage:
#   .\scripts\scan-status.ps1              # Show coverage table
#   .\scripts\scan-status.ps1 -Next        # Show which unit would be scanned next
#   .\scripts\scan-status.ps1 -Json        # Output raw manifest JSON

param(
    [switch]$Next,
    [switch]$Json
)

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ManifestFile = Join-Path $ProjectRoot "docs/scan-manifest.json"

if (-not (Test-Path $ManifestFile)) {
    Write-Error "Scan manifest not found at $ManifestFile"
    exit 1
}

$manifest = Get-Content $ManifestFile -Raw | ConvertFrom-Json

if ($Json) {
    $manifest | ConvertTo-Json -Depth 10
    exit 0
}

# Calculate scores and days since last scan
$now = [DateTimeOffset]::UtcNow
$units = @()

foreach ($unit in $manifest.units) {
    if ($unit.last_scanned) {
        $last = [DateTimeOffset]::Parse($unit.last_scanned)
        $daysSince = [math]::Max(($now - $last).TotalDays, 0.1)
        $lastStr = $last.LocalDateTime.ToString("yyyy-MM-dd HH:mm")
    } else {
        $daysSince = 365
        $lastStr = "never"
    }

    $bugBoost = 1 + $unit.total_bugs_found / 5
    $fpRate = if ($unit.total_bugs_found -gt 0) { $unit.false_positives / $unit.total_bugs_found } else { 0 }
    $fpPenalty = [math]::Max(1 - $fpRate * 0.3, 0.5)
    $score = $unit.priority_weight * $daysSince * $bugBoost * $fpPenalty

    $units += [PSCustomObject]@{
        Id           = $unit.id
        Name         = $unit.name
        Priority     = $unit.priority_weight
        LastScanned  = $lastStr
        DaysSince    = [math]::Round($daysSince, 1)
        Runs         = $unit.total_runs
        BugsFound    = $unit.total_bugs_found
        Confirmed    = $unit.bugs_fixed_confirmed
        FalsePos     = $unit.false_positives
        Score        = [math]::Round($score, 1)
    }
}

$sorted = $units | Sort-Object -Property Score -Descending

if ($Next) {
    $nextUnit = $sorted[0]
    Write-Host ""
    Write-Host "Next scan unit: " -NoNewline -ForegroundColor Cyan
    Write-Host "$($nextUnit.Id)" -ForegroundColor Yellow -NoNewline
    Write-Host " ($($nextUnit.Name))" -ForegroundColor White
    Write-Host "  Priority:    $($nextUnit.Priority)"
    Write-Host "  Last scan:   $($nextUnit.LastScanned)"
    Write-Host "  Days since:  $($nextUnit.DaysSince)"
    Write-Host "  Score:       $($nextUnit.Score)"
    Write-Host "  Past bugs:   $($nextUnit.BugsFound) found, $($nextUnit.Confirmed) confirmed, $($nextUnit.FalsePos) false positives"
    Write-Host ""
    Write-Host "Run: " -NoNewline
    Write-Host ".\auto-fix-pipeline\runner\run.ps1 -Bugs 3" -ForegroundColor Green
    Write-Host ""
    exit 0
}

# Display coverage table
Write-Host ""
Write-Host "=== Auto-Bugfix Scan Coverage ===" -ForegroundColor Cyan
Write-Host "  Total runs: $($manifest.total_runs)    Last unit: $(if ($manifest.last_unit_scanned) { $manifest.last_unit_scanned } else { 'none' })"
Write-Host ""

# Header
$fmt = "{0,-22} {1,4} {2,-18} {3,5} {4,4} {5,4} {6,3} {7,3} {8,8}"
Write-Host ($fmt -f "UNIT", "PRI", "LAST SCANNED", "DAYS", "RUNS", "BUGS", "OK", "FP", "SCORE") -ForegroundColor DarkGray
Write-Host ("-" * 80) -ForegroundColor DarkGray

foreach ($u in $sorted) {
    # Color code by urgency
    $color = if ($u.DaysSince -ge 30) { "Red" }
             elseif ($u.DaysSince -ge 14) { "Yellow" }
             elseif ($u.LastScanned -eq "never") { "Red" }
             else { "White" }

    $line = $fmt -f $u.Id, $u.Priority, $u.LastScanned, $u.DaysSince, $u.Runs, $u.BugsFound, $u.Confirmed, $u.FalsePos, $u.Score
    Write-Host $line -ForegroundColor $color
}

Write-Host ""

# Coverage summary
$scanned = ($manifest.units | Where-Object { $_.last_scanned }).Count
$total = $manifest.units.Count
$pct = if ($total -gt 0) { [math]::Round($scanned / $total * 100) } else { 0 }

Write-Host "Coverage: $scanned/$total units scanned ($pct%)" -ForegroundColor $(if ($pct -ge 80) { "Green" } elseif ($pct -ge 50) { "Yellow" } else { "Red" })

if ($scanned -lt $total) {
    $unscanned = $manifest.units | Where-Object { -not $_.last_scanned } | ForEach-Object { $_.id }
    Write-Host "Never scanned: $($unscanned -join ', ')" -ForegroundColor DarkYellow
}

Write-Host ""

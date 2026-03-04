# TappsMCP Stop hook
# Reminds to run tapps_validate_changed but does NOT block.
# Reads sidecar progress file for richer context when available.
# IMPORTANT: Must check stop_hook_active to prevent infinite loops.
$rawInput = @($input) -join "`n"
try {
    $data = $rawInput | ConvertFrom-Json
    $active = $data.stop_hook_active
} catch {
    $active = $false
}
if ($active -eq $true -or $active -eq "true" -or $active -eq "True") {
    exit 0
}
$projDir = $env:CLAUDE_PROJECT_DIR
if (-not $projDir) { $projDir = "." }
$progress = "$projDir/.tapps-mcp/.validation-progress.json"
if (Test-Path $progress) {
    try {
        $d = Get-Content $progress -Raw | ConvertFrom-Json
        if ($d.status -eq "completed") {
            $total = $d.total
            $passed = @($d.results | Where-Object { $_.gate_passed -eq $true }).Count
            $failed = $total - $passed
            $gp = if ($d.all_gates_passed) { "all passed" } else { "$failed failed" }
            Write-Host "Last validation: $total files, $gp" -ForegroundColor Cyan
            exit 0
        }
    } catch {}
}
# Check report sidecar
$reportProgress = "$projDir/.tapps-mcp/.report-progress.json"
if (Test-Path $reportProgress) {
    try {
        $rd = Get-Content $reportProgress -Raw | ConvertFrom-Json
        if ($rd.status -eq "completed") {
            $results = @($rd.results)
            if ($results.Count -gt 0) {
                $avg = [math]::Round(($results | Measure-Object -Property score -Average).Average, 1)
                Write-Output "Last report: $($results.Count) files, avg $avg/100"
            }
        }
    } catch {}
}
Write-Host "Reminder: Run tapps_validate_changed before ending the session." -ForegroundColor Yellow
exit 0

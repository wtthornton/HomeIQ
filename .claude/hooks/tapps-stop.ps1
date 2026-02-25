# TappsMCP Stop hook
# Reminds to run tapps_validate_changed but does NOT block.
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
Write-Host "Reminder: Run tapps_validate_changed before ending the session." -ForegroundColor Yellow
exit 0

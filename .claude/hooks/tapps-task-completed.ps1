# TappsMCP TaskCompleted hook
# Reminds to run quality checks but does NOT block.
$null = $input | Out-Null
Write-Host "Reminder: run tapps_validate_changed to confirm quality." -ForegroundColor Yellow
exit 0

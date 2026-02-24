# TappsMCP stop hook (Cursor) - PowerShell
# Uses followup_message to prompt validation before session ends.
# Note: Cursor does not support exit-2 blocking on the stop event.

$raw = $null
try {
    if ($null -ne [System.Console]::In) {
        $raw = [System.Console]::In.ReadToEnd()
    }
} catch {}
if (-not $raw -and $null -ne $input) {
    $raw = $input | Out-String
}

$msg = "Before ending: please run tapps_validate_changed to confirm all changed files pass quality gates."
Write-Output "{`"followup_message`": `"$msg`"}"
exit 0

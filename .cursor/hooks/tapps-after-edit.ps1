# TappsMCP afterFileEdit hook (fire-and-forget) - PowerShell
# Reminds the agent to run quality checks after file edits.
# Only prompts for Python files (.py); matches behavior of tapps-post-edit.sh.

$raw = $null
try {
    if ($null -ne [System.Console]::In) {
        $raw = [System.Console]::In.ReadToEnd()
    }
} catch {}
if (-not $raw -and $null -ne $input) {
    $raw = $input | Out-String
}
if (-not $raw -or $raw.Trim().Length -eq 0) { exit 0 }

$file = $null
try {
    $obj = $raw | ConvertFrom-Json
    $ti = $obj.tool_input
    if ($ti) {
        $file = $ti.file_path
        if (-not $file) { $file = $ti.path }
    }
    if (-not $file) { $file = $obj.file }
    if (-not $file) { $file = $obj.path }
} catch {
    # Ignore parse errors
}

if (-not $file -or $file -eq 'unknown') { exit 0 }
if (-not $file.ToString().EndsWith('.py')) { exit 0 }

$path = $file.ToString()
Write-Host "Python file edited: $path"
Write-Host "Consider running tapps_quick_check on it."
exit 0

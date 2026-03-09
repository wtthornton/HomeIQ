# TappsMCP PostToolUse hook (Edit/Write)
# BLOCKING: Instructs agent to run quality checks after Python file edits.
$rawInput = @($input) -join "`n"
try {
    $data = $rawInput | ConvertFrom-Json
    $file = if ($data.tool_input.file_path) { $data.tool_input.file_path }
            elseif ($data.tool_input.path) { $data.tool_input.path }
            else { "" }
} catch {
    $file = ""
}

if ($file -and $file -match '\.py$') {
    Write-Output "BLOCKING: Python file edited: $file"
    Write-Output "You MUST call tapps_quick_check with file_path='$file' before proceeding to other tasks."
}

if ($file -and $file -match 'Dockerfile') {
    Write-Output "BLOCKING: Dockerfile edited: $file"
    Write-Output "You MUST run 'python scripts/validate-dockerfile-libs.py --strict' to verify shared lib installs."
}

exit 0

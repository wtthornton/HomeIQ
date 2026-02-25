# TappsMCP PostToolUse hook (Edit/Write)
# Reminds the agent to run quality checks after file edits.
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
    Write-Output "Python file edited: $file"
    Write-Output "Consider running tapps_quick_check on it."
}
exit 0

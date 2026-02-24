# TappsMCP beforeMCPExecution hook - PowerShell
# Logs MCP tool invocations for observability.

$raw = $null
try {
    if ($null -ne [System.Console]::In) {
        $raw = [System.Console]::In.ReadToEnd()
    }
} catch {}
if (-not $raw -and $null -ne $input) {
    $raw = $input | Out-String
}

$tool = 'unknown'
if ($raw) {
    try {
        $obj = $raw | ConvertFrom-Json
        if ($obj.tool) { $tool = $obj.tool }
    } catch {}
}
$Host.UI.WriteErrorLine("[TappsMCP] MCP tool invoked: $tool")
exit 0

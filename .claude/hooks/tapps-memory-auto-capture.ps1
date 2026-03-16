# TappsMCP Stop hook - Auto-Capture (Epic 65.5)
# Extracts durable facts from context and saves via MemoryStore.
# Runs tapps-mcp auto-capture with stdin; configurable max_facts, min_context.
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
try {
    if (Get-Command tapps-mcp -ErrorAction SilentlyContinue) {
        $rawInput | tapps-mcp auto-capture --project-root $projDir 2>$null
    } else {
        $rawInput | python -m tapps_mcp.cli auto-capture --project-root $projDir 2>$null
    }
} catch {}
exit 0
